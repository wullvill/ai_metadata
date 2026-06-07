# Pipeline 参数配置 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 ConfigPage 从静态原型升级为完整功能，支持通过 UI 管理 Pipeline 四个阶段的运行参数，配置持久化到 PostgreSQL 并热更新到运行时。

**Architecture:** 后端新增 `PipelineConfig` ORM 单行模型 + `ConfigService` 内存缓存 + `GET/PUT/defaults` REST API。Pipeline 各 Stage 从 ConfigService 读取参数替代硬编码。前端 ConfigPage 全面重写，UI 对齐 SearchPage 的 oklch 设计系统。

**Tech Stack:** FastAPI + SQLAlchemy 2.0 async + Pydantic + Vue 3 + TDesign + TypeScript

---

### Task 1: 后端数据模型 + Schema

**Files:**
- Create: `backend/app/models/config.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/api/schemas.py`

- [ ] **Step 1: 创建 PipelineConfig ORM 模型**

```python
# backend/app/models/config.py
"""Pipeline 配置 ORM 模型"""
from datetime import datetime, timezone
from sqlalchemy import Integer, String, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class PipelineConfig(Base):
    __tablename__ = "pipeline_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_by: Mapped[str] = mapped_column(String(64), default="system")
```

- [ ] **Step 2: 注册到 models/__init__.py**

```python
# backend/app/models/__init__.py — 追加一行
from .config import PipelineConfig

__all__ = ["Base", "CompletionRecord", "AuditLog", "PipelineConfig"]
```

- [ ] **Step 3: 添加配置相关 Pydantic Schema**

在 `backend/app/api/schemas.py` 末尾追加：

```python
class PipelineConfigSchema(BaseModel):
    thresholds: dict = Field(default_factory=lambda: {
        "auto_approve": 0.80,
        "pending_review": 0.60,
    })
    models: dict = Field(default_factory=lambda: {
        "default": "qwen-plus",
        "auto_select": True,
        "table_rich_threshold": 5,
    })
    retrieval: dict = Field(default_factory=lambda: {
        "milvus_top_k": 20,
        "es_keyword_top_k": 20,
        "es_siblings_top_k": 5,
        "rrf_k": 60,
        "rrf_top_n": 15,
        "sample_boost": True,
    })
    rules: dict = Field(default_factory=lambda: {
        "required_fields": {"enabled": True},
        "display_name_no_code": {"enabled": True},
        "description_not_copy_name": {"enabled": True},
        "sensitive_level_valid": {"enabled": True},
        "tag_no_duplicates": {"enabled": True},
        "business_domain_valid": {"enabled": True},
        "table_name_consistency": {"enabled": True},
    })


class PipelineConfigUpdateRequest(BaseModel):
    """部分更新请求 — 仅传入需要修改的字段"""
    thresholds: dict | None = None
    models: dict | None = None
    retrieval: dict | None = None
    rules: dict | None = None
```

- [ ] **Step 4: 提交**

```bash
git add backend/app/models/config.py backend/app/models/__init__.py backend/app/api/schemas.py
git commit -m "feat: add PipelineConfig model and Pydantic schemas"
```

---

### Task 2: ConfigService 配置缓存 + 读写服务

**Files:**
- Create: `backend/app/services/config_service.py`
- Create: `backend/tests/test_config_service.py`

- [ ] **Step 1: 编写单元测试**

```python
# backend/tests/test_config_service.py
import pytest
from app.services.config_service import ConfigService, DEFAULTS


class TestConfigService:
    def test_defaults_returns_four_sections(self):
        svc = ConfigService()
        config = svc.get_defaults()
        assert "thresholds" in config
        assert "models" in config
        assert "retrieval" in config
        assert "rules" in config

    def test_defaults_match_hardcoded_values(self):
        svc = ConfigService()
        config = svc.get_defaults()
        assert config["thresholds"]["auto_approve"] == 0.80
        assert config["thresholds"]["pending_review"] == 0.60
        assert config["models"]["default"] == "qwen-plus"
        assert config["retrieval"]["milvus_top_k"] == 20
        assert config["retrieval"]["rrf_k"] == 60
        assert config["retrieval"]["rrf_top_n"] == 15
        assert config["rules"]["required_fields"]["enabled"] is True

    def test_load_returns_defaults_when_no_cache(self):
        svc = ConfigService()
        svc._cached = None
        config = ConfigService.get_config()
        assert config["thresholds"]["auto_approve"] == 0.80

    def test_partial_update_merges_correctly(self):
        svc = ConfigService()
        svc._cached = dict(DEFAULTS)
        partial = {"thresholds": {"auto_approve": 0.90}}
        updated = svc.apply_partial(partial)
        assert updated["thresholds"]["auto_approve"] == 0.90
        assert updated["thresholds"]["pending_review"] == 0.60  # unchanged
        assert updated["models"]["default"] == "qwen-plus"      # unchanged

    def test_partial_update_keeps_unrelated_sections(self):
        svc = ConfigService()
        svc._cached = dict(DEFAULTS)
        partial = {"retrieval": {"rrf_top_n": 10}}
        updated = svc.apply_partial(partial)
        assert updated["retrieval"]["rrf_top_n"] == 10
        assert updated["retrieval"]["rrf_k"] == 60  # unchanged
        assert updated["thresholds"]["auto_approve"] == 0.80   # unchanged section
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd backend && source .venv/bin/activate && python -m pytest tests/test_config_service.py -v
# Expected: FAIL — module not found
```

- [ ] **Step 3: 实现 ConfigService**

```python
# backend/app/services/config_service.py
"""Pipeline 配置服务 — 内存缓存 + DB 读写"""
import copy
from sqlalchemy import select
from app.models.config import PipelineConfig
from app.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULTS = {
    "thresholds": {
        "auto_approve": 0.80,
        "pending_review": 0.60,
    },
    "models": {
        "default": "qwen-plus",
        "auto_select": True,
        "table_rich_threshold": 5,
    },
    "retrieval": {
        "milvus_top_k": 20,
        "es_keyword_top_k": 20,
        "es_siblings_top_k": 5,
        "rrf_k": 60,
        "rrf_top_n": 15,
        "sample_boost": True,
    },
    "rules": {
        "required_fields": {"enabled": True},
        "display_name_no_code": {"enabled": True},
        "description_not_copy_name": {"enabled": True},
        "sensitive_level_valid": {"enabled": True},
        "tag_no_duplicates": {"enabled": True},
        "business_domain_valid": {"enabled": True},
        "table_name_consistency": {"enabled": True},
    },
}


class ConfigService:
    """线程安全的配置单例服务"""

    _instance: "ConfigService | None" = None
    _cached: dict | None = None

    def __new__(cls) -> "ConfigService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_config(cls) -> dict:
        """获取当前生效配置（优先缓存，回退默认值）"""
        if cls._cached is not None:
            return copy.deepcopy(cls._cached)
        return copy.deepcopy(DEFAULTS)

    @staticmethod
    def get_defaults() -> dict:
        return copy.deepcopy(DEFAULTS)

    async def load_from_db(self, session) -> dict:
        """从 DB 加载配置到内存缓存，若无记录则写入默认值"""
        result = await session.execute(
            select(PipelineConfig).where(PipelineConfig.id == 1)
        )
        row = result.scalar_one_or_none()
        if row:
            self._cached = copy.deepcopy(row.config)
        else:
            row = PipelineConfig(id=1, config=copy.deepcopy(DEFAULTS))
            session.add(row)
            await session.commit()
            self._cached = copy.deepcopy(DEFAULTS)
        logger.info("ConfigService: loaded config from DB")
        return self._cached

    async def save_to_db(self, session, config: dict, updated_by: str = "admin") -> dict:
        """写入 DB 并刷新缓存"""
        result = await session.execute(
            select(PipelineConfig).where(PipelineConfig.id == 1)
        )
        row = result.scalar_one_or_none()
        if row:
            row.config = config
            row.updated_by = updated_by
        else:
            row = PipelineConfig(id=1, config=config, updated_by=updated_by)
            session.add(row)
        await session.commit()
        self._cached = copy.deepcopy(config)
        logger.info(f"ConfigService: config saved by {updated_by}")
        return self._cached

    def apply_partial(self, partial: dict) -> dict:
        """将部分更新合并到当前缓存，返回合并后的完整配置"""
        current = copy.deepcopy(self._cached) if self._cached else copy.deepcopy(DEFAULTS)
        for section in ("thresholds", "models", "retrieval", "rules"):
            if section in partial and partial[section] is not None:
                current[section] = {**current[section], **partial[section]}
        self._cached = current
        return copy.deepcopy(current)

    @classmethod
    def reset(cls) -> None:
        """测试辅助：重置单例状态"""
        cls._instance = None
        cls._cached = None


config_service = ConfigService()
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd backend && source .venv/bin/activate && python -m pytest tests/test_config_service.py -v
# Expected: 5 passed
```

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/config_service.py backend/tests/test_config_service.py
git commit -m "feat: add ConfigService with cache and partial update"
```

---

### Task 3: Config REST API

**Files:**
- Create: `backend/app/api/config.py`
- Create: `backend/tests/test_config_api.py`

- [ ] **Step 1: 编写 API 集成测试**

```python
# backend/tests/test_config_api.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import create_app
from app.services.config_service import config_service


@pytest.fixture(autouse=True)
def reset_config():
    config_service.reset()
    yield
    config_service.reset()


@pytest.fixture
async def client():
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


class TestConfigAPI:
    async def test_get_defaults_returns_config(self, client):
        config_service._cached = None
        response = await client.get("/api/v1/config/defaults")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["thresholds"]["auto_approve"] == 0.80

    async def test_get_config_returns_defaults_when_empty(self, client):
        config_service._cached = None
        response = await client.get("/api/v1/config")
        assert response.status_code == 200
        data = response.json()
        assert "thresholds" in data["data"]

    async def test_put_config_partial_update(self, client):
        config_service._cached = None
        partial = {"thresholds": {"auto_approve": 0.95}}
        response = await client.put("/api/v1/config", json=partial)
        assert response.status_code == 200
        assert response.json()["data"]["thresholds"]["auto_approve"] == 0.95
        assert response.json()["data"]["thresholds"]["pending_review"] == 0.60
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd backend && source .venv/bin/activate && python -m pytest tests/test_config_api.py -v
# Expected: FAIL — 404 /api/v1/config not found
```

- [ ] **Step 3: 实现 Config API**

```python
# backend/app/api/config.py
"""配置管理 API"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.api.schemas import PipelineConfigUpdateRequest
from app.services.config_service import config_service
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/config", tags=["config"])


@router.get("")
async def get_config():
    return {"success": True, "data": config_service.get_config()}


@router.put("")
async def update_config(
    req: PipelineConfigUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    partial = req.model_dump(exclude_none=True)
    merged = config_service.apply_partial(partial)
    await config_service.save_to_db(db, merged)
    return {"success": True, "data": config_service.get_config()}


@router.get("/defaults")
async def get_defaults():
    return {"success": True, "data": config_service.get_defaults()}
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd backend && source .venv/bin/activate && python -m pytest tests/test_config_api.py -v
# Expected: 3 passed
```

- [ ] **Step 5: 提交**

```bash
git add backend/app/api/config.py backend/tests/test_config_api.py
git commit -m "feat: add config REST API (GET/PUT/defaults)"
```

---

### Task 4: 注册 Router + 启动加载

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: 在 main.py 注册 config router 并添加 startup 事件**

```python
# backend/app/main.py 的 create_app() 函数修改如下：

def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="0.1.0")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

    @app.get("/health")
    async def health_check():
        return {"status": "ok"}

    from app.api.search import router as search_router
    from app.api.complete import router as complete_router
    from app.api.review import router as review_router
    from app.api.sync import router as sync_router
    from app.api.history import router as history_router
    from app.api.assets import router as assets_router
    from app.api.samples import router as sample_router
    from app.api.config import router as config_router

    app.include_router(search_router)
    app.include_router(complete_router)
    app.include_router(review_router)
    app.include_router(sync_router)
    app.include_router(history_router)
    app.include_router(assets_router)
    app.include_router(sample_router)
    app.include_router(config_router)

    @app.on_event("startup")
    async def load_config_on_startup():
        from app.database import async_session
        from app.services.config_service import config_service
        async with async_session() as session:
            await config_service.load_from_db(session)

    return app
```

- [ ] **Step 2: 验证启动**

```bash
cd backend && source .venv/bin/activate && timeout 5 uvicorn app.main:app --port 8000 2>&1 || true
# Expected: 日志中看到 "ConfigService: loaded config from DB"
```

- [ ] **Step 3: 提交**

```bash
git add backend/app/main.py
git commit -m "feat: register config router and startup config loading"
```

---

### Task 5: Stage 1 检索参数集成

**Files:**
- Modify: `backend/app/pipeline/stage1_retrieve.py`
- Create: `backend/tests/test_stage1_config.py`

- [ ] **Step 1: 编写测试**

```python
# backend/tests/test_stage1_config.py
import pytest
from app.services.config_service import config_service


class TestStage1ConfigIntegration:
    def test_config_service_returns_retrieval_defaults(self):
        config_service.reset()
        cfg = config_service.get_config()
        assert cfg["retrieval"]["milvus_top_k"] == 20
        assert cfg["retrieval"]["es_keyword_top_k"] == 20
        assert cfg["retrieval"]["rrf_k"] == 60
        assert cfg["retrieval"]["rrf_top_n"] == 15

    def test_modified_retrieval_params_are_used(self):
        config_service.reset()
        config_service.apply_partial({
            "retrieval": {"rrf_top_n": 10, "milvus_top_k": 30}
        })
        cfg = config_service.get_config()
        assert cfg["retrieval"]["rrf_top_n"] == 10
        assert cfg["retrieval"]["milvus_top_k"] == 30
        assert cfg["retrieval"]["es_keyword_top_k"] == 20
```

- [ ] **Step 2: 运行测试确认通过**

```bash
cd backend && source .venv/bin/activate && python -m pytest tests/test_stage1_config.py -v
# Expected: 2 passed
```

- [ ] **Step 3: 修改 stage1_retrieve.py 从配置读取参数**

在 `stage1_retrieve` 函数开头添加：

```python
# 在 async def stage1_retrieve(state) 函数体第一行之后添加：
from app.services.config_service import config_service

cfg = config_service.get_config()
retrieval = cfg["retrieval"]
```

然后将硬编码值替换为配置变量：

```python
# 原: top_k=20 → 改为: top_k=retrieval["milvus_top_k"]
lambda: milvus.search_similar(query_embedding, target["entity_type"], top_k=retrieval["milvus_top_k"], database=db)

# 原: top_k=20 → 改为: top_k=retrieval["es_keyword_top_k"]
lambda: elasticsearch.search_keyword(search_text, target["entity_type"], database=db, schema_name=schema_name, top_k=retrieval["es_keyword_top_k"])

# 原: top_k=5 → 改为: top_k=retrieval["es_siblings_top_k"]
lambda: elasticsearch.search_siblings(db, schema_name, target["entity_type"], top_k=retrieval["es_siblings_top_k"])

# 原: merged = rrf_merge(milvus_results, es_results, top_n=15)
# 改为:
merged = rrf_merge(milvus_results, es_results, k=retrieval["rrf_k"], top_n=retrieval["rrf_top_n"])

# 样本置顶包裹在 if retrieval["sample_boost"]: 中
if retrieval["sample_boost"]:
    try:
        sample_docs = elasticsearch.get_samples()
        ...
```

- [ ] **Step 4: 运行全部测试确认无回归**

```bash
cd backend && source .venv/bin/activate && python -m pytest tests/ -v --tb=short
# Expected: 全部通过
```

- [ ] **Step 5: 提交**

```bash
git add backend/app/pipeline/stage1_retrieve.py backend/tests/test_stage1_config.py
git commit -m "feat: wire Stage 1 retrieval params to ConfigService"
```

---

### Task 6: Stage 2 模型参数集成

**Files:**
- Modify: `backend/app/pipeline/stage2_generate.py`

- [ ] **Step 1: 修改 select_model 支持配置驱动的模型选择**

```python
# backend/app/pipeline/stage2_generate.py
# select_model 函数改为：
def select_model(entity_type: str, schema_context: list[dict], retrieved_context: list[dict]) -> str:
    from app.services.config_service import config_service
    cfg = config_service.get_config()
    models_cfg = cfg["models"]

    if not models_cfg.get("auto_select", True):
        return models_cfg.get("default", "qwen-plus")

    if entity_type == "table":
        rich_desc_count = sum(
            1 for s in schema_context
            if s.get("description") and len(s.get("description", "")) > 10
        )
        threshold = models_cfg.get("table_rich_threshold", 5)
        if rich_desc_count > threshold:
            return "qwen-max"
    return models_cfg.get("default", "qwen-plus")
```

- [ ] **Step 2: 运行测试确认无回归**

```bash
cd backend && source .venv/bin/activate && python -m pytest tests/test_stage2_generate.py -v
# Expected: 全部通过
```

- [ ] **Step 3: 提交**

```bash
git add backend/app/pipeline/stage2_generate.py
git commit -m "feat: wire Stage 2 model selection to ConfigService"
```

---

### Task 7: Stage 3 阈值 + 规则开关集成

**Files:**
- Modify: `backend/app/pipeline/stage3_quality.py`

- [ ] **Step 1: 修改 decide_review_status 从配置读取阈值**

```python
# backend/app/pipeline/stage3_quality.py
# decide_review_status 函数改为：
def decide_review_status(adjusted_confidence: float, violations: list[dict]) -> str:
    from app.services.config_service import config_service
    cfg = config_service.get_config()
    thresholds = cfg["thresholds"]

    has_critical = any(v["severity"] == "critical" for v in violations)
    has_warning = any(v["severity"] == "warning" for v in violations)

    auto_threshold = thresholds.get("auto_approve", 0.80)
    review_threshold = thresholds.get("pending_review", 0.60)

    if has_critical or adjusted_confidence < review_threshold:
        return "rejected"
    elif adjusted_confidence >= auto_threshold and not has_warning:
        return "auto_approved"
    else:
        return "pending_review"
```

- [ ] **Step 2: 修改 check_rules 支持规则开关**

```python
# check_rules 函数改为：
def check_rules(result: dict, target: dict) -> list[dict]:
    from app.services.config_service import config_service
    cfg = config_service.get_config()
    rules_cfg = cfg.get("rules", {})

    violations = []
    for rule_name, rule in RULES.items():
        rule_setting = rules_cfg.get(rule_name, {})
        if not rule_setting.get("enabled", True):
            continue
        passed = rule["check"](result, target)
        if not passed:
            violations.append({
                "rule": rule_name,
                "severity": rule["severity"],
                "message": rule["message"],
            })
    return violations
```

- [ ] **Step 3: 运行测试确认无回归**

```bash
cd backend && source .venv/bin/activate && python -m pytest tests/test_stage3_quality.py -v
# Expected: 全部通过
```

- [ ] **Step 4: 提交**

```bash
git add backend/app/pipeline/stage3_quality.py
git commit -m "feat: wire Stage 3 thresholds and rules to ConfigService"
```

---

### Task 8: 前端类型定义 + API 客户端

**Files:**
- Modify: `frontend/src/api/types.ts`
- Modify: `frontend/src/api/index.ts`

- [ ] **Step 1: 添加配置类型定义**

在 `frontend/src/api/types.ts` 末尾追加：

```typescript
export interface PipelineConfig {
  thresholds: {
    auto_approve: number
    pending_review: number
  }
  models: {
    default: string
    auto_select: boolean
    table_rich_threshold: number
  }
  retrieval: {
    milvus_top_k: number
    es_keyword_top_k: number
    es_siblings_top_k: number
    rrf_k: number
    rrf_top_n: number
    sample_boost: boolean
  }
  rules: Record<string, { enabled: boolean }>
}
```

- [ ] **Step 2: 添加 API 调用函数**

在 `frontend/src/api/index.ts` 末尾追加：

```typescript
import type { PipelineConfig } from './types'

export async function getConfig(): Promise<{ success: boolean; data: PipelineConfig }> {
  const { data } = await api.get('/config')
  return data
}

export async function updateConfig(partial: Partial<PipelineConfig>): Promise<{ success: boolean; data: PipelineConfig }> {
  const { data } = await api.put('/config', partial)
  return data
}

export async function getConfigDefaults(): Promise<{ success: boolean; data: PipelineConfig }> {
  const { data } = await api.get('/config/defaults')
  return data
}
```

- [ ] **Step 3: 类型检查**

```bash
cd frontend && npx vue-tsc --noEmit --pretty 2>&1 | grep -c "error TS"
# Expected: 2 (仅已有的 ReviewDetail.vue 和 SearchPage.vue 错误)
```

- [ ] **Step 4: 提交**

```bash
git add frontend/src/api/types.ts frontend/src/api/index.ts
git commit -m "feat: add config API client and PipelineConfig types"
```

---

### Task 9: ConfigPage UI 重写

**Files:**
- Modify: `frontend/src/pages/ConfigPage.vue`

- [ ] **Step 1: 完整重写 ConfigPage.vue**

```vue
<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { MessagePlugin } from 'tdesign-vue-next'
import { getConfig, updateConfig, getConfigDefaults } from '../api'
import type { PipelineConfig } from '../api/types'

const config = reactive<PipelineConfig>({
  thresholds: { auto_approve: 0.80, pending_review: 0.60 },
  models: { default: 'qwen-plus', auto_select: true, table_rich_threshold: 5 },
  retrieval: { milvus_top_k: 20, es_keyword_top_k: 20, es_siblings_top_k: 5, rrf_k: 60, rrf_top_n: 15, sample_boost: true },
  rules: {
    required_fields: { enabled: true },
    display_name_no_code: { enabled: true },
    description_not_copy_name: { enabled: true },
    sensitive_level_valid: { enabled: true },
    tag_no_duplicates: { enabled: true },
    business_domain_valid: { enabled: true },
    table_name_consistency: { enabled: true },
  },
})

const loading = ref(false)
const saving = ref(false)
const dirty = ref(false)

const modelOptions = [
  { label: 'qwen-plus', value: 'qwen-plus' },
  { label: 'qwen-max', value: 'qwen-max' },
  { label: 'qwen-turbo', value: 'qwen-turbo' },
]

const ruleMeta: Record<string, { label: string; severity: string; desc: string }> = {
  required_fields: { label: 'required_fields', severity: 'CRITICAL', desc: 'display_name 和 description 任一缺失直接拒绝' },
  display_name_no_code: { label: 'display_name_no_code', severity: 'WARNING', desc: '中文名不应包含大段英文字符' },
  description_not_copy_name: { label: 'description_not_copy_name', severity: 'WARNING', desc: '描述不应与中文名完全一致' },
  sensitive_level_valid: { label: 'sensitive_level_valid', severity: 'WARNING', desc: '敏感级别必须在 L1–L4 范围内' },
  tag_no_duplicates: { label: 'tag_no_duplicates', severity: 'INFO', desc: '标签列表不应包含重复项' },
  business_domain_valid: { label: 'business_domain_valid', severity: 'INFO', desc: '业务域名字符长度合理' },
  table_name_consistency: { label: 'table_name_consistency', severity: 'WARNING', desc: '中文名不应与英文表名完全相同' },
}

function severityTheme(severity: string): 'danger' | 'warning' | 'default' {
  if (severity === 'CRITICAL') return 'danger'
  if (severity === 'WARNING') return 'warning'
  return 'default'
}

function markDirty() { dirty.value = true }

onMounted(async () => {
  loading.value = true
  try {
    const res = await getConfig()
    if (res.success && res.data) {
      Object.assign(config, res.data)
    }
  } catch { /* use defaults */ }
  finally { loading.value = false }
})

async function handleSave() {
  saving.value = true
  try {
    const partial: Partial<PipelineConfig> = {
      thresholds: { ...config.thresholds },
      models: { ...config.models },
      retrieval: { ...config.retrieval },
      rules: { ...config.rules },
    }
    await updateConfig(partial)
    dirty.value = false
    MessagePlugin.success('配置已保存')
  } catch {
    MessagePlugin.error('保存失败')
  } finally { saving.value = false }
}

async function handleReset() {
  try {
    const res = await getConfigDefaults()
    if (res.success && res.data) {
      Object.assign(config, res.data)
      dirty.value = false
      MessagePlugin.success('已恢复默认配置')
    }
  } catch {
    MessagePlugin.error('恢复默认失败')
  }
}
</script>

<template>
  <div class="config-page">
    <div class="page-header">
      <h1>参数配置</h1>
      <p class="page-subtitle">管理 Pipeline 各阶段的运行参数，修改后立即生效</p>
    </div>

    <div v-if="loading" class="loading-state">
      <t-loading text="加载配置中..." />
    </div>

    <template v-else>
      <!-- 分流阈值 -->
      <section class="config-section">
        <h2>分流阈值</h2>
        <p class="section-desc">控制补全结果自动采纳 / 待审核 / 拒绝的置信度门槛</p>
        <div class="threshold-row">
          <div class="threshold-item">
            <div class="threshold-head">
              <label>自动采纳阈值</label>
              <span class="threshold-value">{{ (config.thresholds.auto_approve * 100).toFixed(0) }}%</span>
            </div>
            <t-slider
              :model-value="config.thresholds.auto_approve"
              :min="0.5" :max="1.0" :step="0.05"
              :marks="{ 0.5: '0.5', 0.6: '0.6', 0.7: '0.7', 0.8: '0.8', 0.9: '0.9', 1.0: '1.0' }"
              @change="(v: number) => { config.thresholds.auto_approve = v; markDirty() }"
            />
            <p class="threshold-hint">置信度 >= 该值且无 WARNING 时自动采纳</p>
          </div>
          <div class="threshold-item">
            <div class="threshold-head">
              <label>待审核阈值</label>
              <span class="threshold-value">{{ (config.thresholds.pending_review * 100).toFixed(0) }}%</span>
            </div>
            <t-slider
              :model-value="config.thresholds.pending_review"
              :min="0.2" :max="0.7" :step="0.05"
              :marks="{ 0.2: '0.2', 0.3: '0.3', 0.4: '0.4', 0.5: '0.5', 0.6: '0.6', 0.7: '0.7' }"
              @change="(v: number) => { config.thresholds.pending_review = v; markDirty() }"
            />
            <p class="threshold-hint">置信度 < 该值或有关键违规时直接拒绝；介于两阈值之间待审核</p>
          </div>
        </div>
      </section>

      <!-- 模型选择 -->
      <section class="config-section">
        <h2>模型选择</h2>
        <p class="section-desc">配置 LLM 生成阶段的模型策略</p>
        <div class="form-grid">
          <div class="form-item">
            <label>默认模型</label>
            <div class="filter-select-wrap">
              <select
                :value="config.models.default"
                class="filter-select"
                :class="{ active: true }"
                @change="config.models.default = ($event.target as HTMLSelectElement).value; markDirty()"
              >
                <option v-for="opt in modelOptions" :key="opt.value" :value="opt.value">
                  {{ opt.label }}
                </option>
              </select>
            </div>
          </div>
          <div class="form-item">
            <label>自动模型升级</label>
            <t-switch
              :value="config.models.auto_select"
              @change="(v: boolean) => { config.models.auto_select = v; markDirty() }"
            />
            <p class="threshold-hint">表上下文丰富时自动升级到更强模型</p>
          </div>
          <div class="form-item">
            <label>升级阈值</label>
            <t-input-number
              :value="config.models.table_rich_threshold"
              :min="1" :max="20" :step="1"
              style="width: 100px"
              @change="(v: number) => { config.models.table_rich_threshold = v; markDirty() }"
            />
            <p class="threshold-hint">表兄弟字段描述数超过此值时触发升级</p>
          </div>
        </div>
      </section>

      <!-- 检索参数 -->
      <section class="config-section">
        <h2>检索参数</h2>
        <p class="section-desc">控制 Stage 1 双路检索 (Milvus + ES) 的行为</p>
        <div class="form-grid">
          <div class="form-item">
            <label>Milvus Top-K</label>
            <t-input-number :value="config.retrieval.milvus_top_k" :min="5" :max="100" style="width: 100px"
              @change="(v: number) => { config.retrieval.milvus_top_k = v; markDirty() }" />
          </div>
          <div class="form-item">
            <label>ES 关键词 Top-K</label>
            <t-input-number :value="config.retrieval.es_keyword_top_k" :min="5" :max="100" style="width: 100px"
              @change="(v: number) => { config.retrieval.es_keyword_top_k = v; markDirty() }" />
          </div>
          <div class="form-item">
            <label>ES 兄弟字段数</label>
            <t-input-number :value="config.retrieval.es_siblings_top_k" :min="1" :max="50" style="width: 100px"
              @change="(v: number) => { config.retrieval.es_siblings_top_k = v; markDirty() }" />
          </div>
          <div class="form-item">
            <label>RRF 常数 K</label>
            <t-input-number :value="config.retrieval.rrf_k" :min="10" :max="200" style="width: 100px"
              @change="(v: number) => { config.retrieval.rrf_k = v; markDirty() }" />
          </div>
          <div class="form-item">
            <label>RRF 最终数量</label>
            <t-input-number :value="config.retrieval.rrf_top_n" :min="5" :max="50" style="width: 100px"
              @change="(v: number) => { config.retrieval.rrf_top_n = v; markDirty() }" />
          </div>
          <div class="form-item">
            <label>样本实体置顶</label>
            <t-switch :value="config.retrieval.sample_boost"
              @change="(v: boolean) => { config.retrieval.sample_boost = v; markDirty() }" />
          </div>
        </div>
      </section>

      <!-- 质量规则 -->
      <section class="config-section">
        <h2>质量规则</h2>
        <p class="section-desc">启用或禁用各质量校验规则</p>
        <div class="rule-table-wrap">
          <t-table
            :data="Object.entries(config.rules).map(([key, val]) => ({ rule: key, ...ruleMeta[key], enabled: val.enabled }))"
            :columns="[
              { colKey: 'rule', title: '规则名', width: 220 },
              { colKey: 'severity', title: '级别', width: 100 },
              { colKey: 'desc', title: '说明', ellipsis: true },
              { colKey: 'enabled', title: '启用', width: 80 },
            ]"
            row-key="rule"
            size="small"
            hover
          >
            <template #severity="{ row }">
              <t-tag size="small" :theme="severityTheme(row.severity)" variant="light">
                {{ row.severity }}
              </t-tag>
            </template>
            <template #enabled="{ row }">
              <t-switch
                :value="row.enabled"
                size="small"
                @change="(v: boolean) => { config.rules[row.rule].enabled = v; markDirty() }"
              />
            </template>
          </t-table>
        </div>
      </section>

      <!-- 操作栏 -->
      <div class="config-actions">
        <t-button theme="default" variant="outline" @click="handleReset">恢复默认</t-button>
        <t-button theme="primary" :loading="saving" :disabled="!dirty" @click="handleSave">保存配置</t-button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.config-page {
  --color-bg: oklch(99% 0.002 240);
  --color-surface: oklch(100% 0 0);
  --color-fg: oklch(18% 0.012 250);
  --color-muted: oklch(54% 0.012 250);
  --color-border: oklch(92% 0.005 250);
  --color-accent: oklch(58% 0.18 255);
  --color-accent-soft: oklch(58% 0.18 255 / 0.08);
  --font-mono: 'JetBrains Mono', 'SF Mono', ui-monospace, Menlo, monospace;
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 16px;
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', system-ui, sans-serif;
  color: var(--color-fg);
}

.page-header { margin-bottom: 28px; }
.page-header h1 { font-size: 1.5rem; font-weight: 700; letter-spacing: -0.01em; margin: 0; }
.page-subtitle { font-size: 0.875rem; color: var(--color-muted); margin-top: 4px; }
.loading-state { display: flex; justify-content: center; padding: 64px 0; }

.config-section {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 24px;
  margin-bottom: 16px;
}
.config-section h2 { font-size: 1.125rem; font-weight: 700; margin: 0 0 4px; }
.section-desc { font-size: 0.875rem; color: var(--color-muted); margin: 0 0 24px; }

.threshold-row { display: flex; flex-direction: column; gap: 32px; }
.threshold-item label { font-weight: 500; font-size: 0.875rem; }
.threshold-head { display: flex; align-items: center; gap: 12px; }
.threshold-value { font-size: 1.25rem; font-weight: 700; color: var(--color-accent); font-family: var(--font-mono); font-variant-numeric: tabular-nums; }
.threshold-hint { font-size: 0.75rem; color: var(--color-muted); margin-top: 4px; }

.form-grid { display: flex; flex-wrap: wrap; gap: 20px 32px; }
.form-item { display: flex; align-items: center; gap: 10px; }
.form-item label { font-size: 0.875rem; font-weight: 500; white-space: nowrap; }

.filter-select-wrap { position: relative; display: flex; align-items: center; }
.filter-select {
  appearance: none; padding: 5px 28px 5px 10px; border-radius: 20px;
  border: 1px solid var(--color-border); font-size: 13px; font-weight: 500;
  cursor: pointer; background: transparent; color: var(--color-fg);
  font-family: inherit; transition: all 0.15s;
}
.filter-select:hover { border-color: var(--color-accent); }
.filter-select.active { background: var(--color-accent-soft); color: var(--color-accent); border-color: var(--color-accent); }
.filter-select-wrap::after {
  content: ''; position: absolute; right: 10px; top: 50%; transform: translateY(-50%);
  pointer-events: none; border-left: 4px solid transparent; border-right: 4px solid transparent;
  border-top: 5px solid currentColor;
}

.rule-table-wrap { margin-top: 8px; }
.config-actions { display: flex; justify-content: flex-end; gap: 12px; padding-top: 8px; }

:deep(.t-table) { font-size: 14px; font-variant-numeric: tabular-nums; }
:deep(.t-table th) { font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; color: var(--color-muted); }

@media (max-width: 768px) {
  .config-page { padding: 16px; }
  .form-grid { flex-direction: column; gap: 16px; }
}
```

- [ ] **Step 2: 构建验证**

```bash
cd frontend && npx vite build 2>&1 | tail -5
# Expected: ✓ built in X.XXs
```

- [ ] **Step 3: 提交**

```bash
git add frontend/src/pages/ConfigPage.vue
git commit -m "feat: rewrite ConfigPage with full pipeline config UI"
```

---

### Task 10: 端到端验证

- [ ] **Step 1: 运行后端全部测试**

```bash
cd backend && source .venv/bin/activate && python -m pytest tests/ -v --tb=short
# Expected: 全部通过
```

- [ ] **Step 2: 前端构建验证**

```bash
cd frontend && npx vite build 2>&1 | tail -3
# Expected: ✓ built in X.XXs
```

- [ ] **Step 3: 提交**

```bash
git commit --allow-empty -m "chore: final verification of pipeline config feature"
```
