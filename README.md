# 数据治理智能元数据补全系统

基于 RAG 技术，利用大模型自动为数据库表和字段补全中文名、业务描述、标签等元数据，辅以质量校验和人工审核机制。

详细需求见 `docs/requirements-specification.md`，架构设计见 `docs/architecture-design.md`，OpenSpec 规范见 `openspec/specs/`。

## Tech Stack

| 层次 | 技术 | 版本 |
|------|------|------|
| 后端框架 | FastAPI | ≥ 0.115 |
| 编排框架 | LangGraph | ≥ 0.2 |
| LLM 框架 | LangChain | ≥ 0.3 |
| 模型服务 | 阿里云百炼 (DashScope) | ≥ 1.20 |
| 向量库 | ChromaDB (embedded) / Milvus (production) | ≥ 0.5 / ≥ 2.4 |
| 搜索引擎 | Tantivy + jieba (embedded) / Elasticsearch (production) | ≥ 0.22 |
| 数据库 | SQLite (embedded) / PostgreSQL (production) | - |
| 异步任务 | Celery + SQLite broker (embedded) / Celery + Redis (production) | ≥ 5.4 |
| 前端框架 | Vue 3 + TDesign | ≥ 3.5 |
| 前端构建 | Vite | ≥ 6.0 |

## Commands

### 后端

```bash
cd backend
source .venv/bin/activate

# 启动 API 服务
uvicorn app.main:app --reload --port 8000

# 启动统一服务（前端 + 后端，推荐）
python run.py

# 启动 Celery Worker (embedded)
celery -A app.celery_app worker -P solo

# 运行测试
pytest tests/ -v --cov=app --cov-report=term
```

### 前端

```bash
cd frontend
npm run dev    # 开发服务器
npm run build  # 生产构建
```

## Architecture

四阶段 LangGraph Pipeline：

```
用户触发 → [Stage 1: 双路检索] → [Stage 2: LLM 生成] → [Stage 3: 质量校验] → [Stage 4: 审核路由]
 ChromaDB/Tantivy + 百炼平台 置信度修正 + 规则 审核工作台 +
 Milvus/ES RRF 融合 qwen/deepseek 引擎 + 冲突检测 OpenMetadata 回写
```

### 项目结构

```
backend/app/
├── api/          # REST API 层 (search, complete, review, sync, history, assets, samples, config)
├── pipeline/     # LangGraph 四阶段 Pipeline
├── services/     # 服务封装 (vector_store, search_index, OM, DashScope)
├── models/       # ORM 数据模型
├── jobs/         # Celery 异步任务
└── utils/        # 工具函数

frontend/src/
├── pages/        # 4 个页面（搜索、审核、历史、配置）
├── components/   # 6 个组件 (SearchBar, MetadataCard, CompletionPanel 等)
├── composables/  # 3 个 composable (useSearch, useCompletion, useReview)
├── api/          # API 客户端 + 类型定义
└── router/       # Vue Router 配置
```

## 环境信息

### 开发环境

| 项目 | 说明 |
|------|------|
| 部署模式 | `embedded`（ChromaDB / Tantivy / SQLite，无需外部服务） |
| 生产模式 | `production`（需部署 Milvus / Elasticsearch / PostgreSQL / Redis） |
| Python 版本 | ≥ 3.12 |
| Node 版本 | ≥ 20 |

### 快速启动（嵌入式模式）

```bash
# 1. 安装后端依赖
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. 初始化数据库
python -c "
from app.database import engine
from app.models.base import Base
import asyncio
async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
asyncio.run(init())"

# 3. 构建前端
cd ../frontend
npm install
npm run build

# 4. 启动统一服务
cd ../backend
python run.py
# 访问 http://localhost:8000
```

### 开发模式（前后端分离）

```bash
# 终端 1：后端
cd backend && uvicorn app.main:app --reload --port 8000

# 终端 2：前端
cd frontend && npm run dev
# Vite 开发服务器 http://localhost:5173 自动代理 /api 到后端
```
