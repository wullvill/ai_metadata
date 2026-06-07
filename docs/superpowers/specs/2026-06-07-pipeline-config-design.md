# Pipeline 参数配置功能设计

## 概述

将 ConfigPage（参数配置）从静态原型升级为完整功能：支持通过 UI 管理 Pipeline 各阶段的运行参数，配置持久化到数据库并影响运行时行为。同时 UI 风格对齐 SearchPage（资产目录页面）。

## 数据模型

`pipeline_config` 表，single-row key-value 模式：

```python
class PipelineConfig(Base):
    __tablename__ = "pipeline_config"
    id: int (PK, 固定为 1)
    config: JSON  # 全部配置的 JSON 对象
    updated_at: datetime
    updated_by: str
```

配置 JSON 结构：

```json
{
  "thresholds": {
    "auto_approve": 0.80,
    "pending_review": 0.60
  },
  "models": {
    "default": "qwen-plus",
    "auto_select": true,
    "table_rich_threshold": 5
  },
  "retrieval": {
    "milvus_top_k": 20,
    "es_keyword_top_k": 20,
    "es_siblings_top_k": 5,
    "rrf_k": 60,
    "rrf_top_n": 15,
    "sample_boost": true
  },
  "rules": {
    "required_fields": {"enabled": true},
    "display_name_no_code": {"enabled": true},
    "description_not_copy_name": {"enabled": true},
    "sensitive_level_valid": {"enabled": true},
    "tag_no_duplicates": {"enabled": true},
    "business_domain_valid": {"enabled": true},
    "table_name_consistency": {"enabled": true}
  }
}
```

## API

| 方法 | 路径 | 用途 |
|------|------|------|
| `GET` | `/api/v1/config` | 获取当前完整配置 |
| `PUT` | `/api/v1/config` | 更新配置（部分或全部） |
| `GET` | `/api/v1/config/defaults` | 获取系统默认值 |

### GET /api/v1/config

返回当前生效配置。

### PUT /api/v1/config

请求体为部分或完整配置 JSON，仅更新传入的字段（partial update）。同时写 DB + 刷新内存缓存。

### GET /api/v1/config/defaults

返回代码中定义的默认配置值，供前端"恢复默认"使用。

## 运行时集成

**配置缓存：** 应用启动时从 DB 加载到内存单例（`ConfigService`）。`PUT` 时同步更新 DB 和内存。

**Pipeline 改造：** 各 Stage 从 `ConfigService` 读取参数而非硬编码：

- **Stage 1 检索：** milvus_top_k, es_keyword_top_k, es_siblings_top_k, rrf_k, rrf_top_n, sample_boost
- **Stage 2 LLM 生成：** model default, auto_select 开关, table_rich_threshold
- **Stage 3 质量校验：** auto_approve_threshold, pending_review_threshold, 每条规则的 enabled 状态

## 前端 UI

### 布局（与 SearchPage 一致）

- 页面宽度：`max-width: 1200px`
- 设计 tokens：oklch 色彩、JetBrains Mono 字体
- 卡片用 `border` + `border-radius`，无阴影
- 底部固定保存按钮 + MessagePlugin 反馈

### 四组配置卡片

1. **分流阈值：** 两个滑块（auto_approve / pending_review），带百分比显示和说明文字
2. **模型选择：** 默认模型下拉框 + 自动选择开关 + 阈值输入
3. **检索参数：** 5 个数字滑块/输入（top_k 系列）+ 样本置顶开关
4. **质量规则：** 7 条规则的表格，含规则名、级别标签、启用开关

### 交互

- 修改任一配置项后，"保存配置"按钮高亮
- 保存调用 `PUT /api/v1/config`
- 支持"恢复默认"按钮，调用 `GET /api/v1/config/defaults` 获取默认值并填充
- 保存成功后 MessagePlugin 提示

## 文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/app/models/config.py` | 新增 | PipelineConfig ORM 模型 |
| `backend/app/services/config_service.py` | 新增 | 配置缓存 + 读写服务 |
| `backend/app/api/config.py` | 新增 | 配置 REST API 路由 |
| `backend/app/main.py` | 修改 | 注册 config router + 启动加载 |
| `backend/app/pipeline/stage1_retrieve.py` | 修改 | 检索参数从配置读取 |
| `backend/app/pipeline/stage2_generate.py` | 修改 | 模型参数从配置读取 |
| `backend/app/pipeline/stage3_quality.py` | 修改 | 阈值 + 规则开关从配置读取 |
| `frontend/src/pages/ConfigPage.vue` | 重写 | 完整 UI 实现 |
| `frontend/src/api/index.ts` | 修改 | 新增 config API 调用 |
| `frontend/src/api/types.ts` | 修改 | 新增配置类型定义 |

## 测试

- 后端：ConfigService 单元测试（缓存读写、默认值、partial update）
- 后端：Config API 集成测试（GET/PUT/defaults）
- 后端：Stage 集成测试验证配置生效（修改阈值后审核状态变化）
- 前端：E2E 测试 ConfigPage 保存/恢复默认流程
