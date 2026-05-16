# 数据治理智能元数据补全系统 — 需求规格说明书

> 版本: v1.0 | 日期: 2026-05-16 | 状态: 评审阶段

---

## 1. 引言

### 1.1 项目背景

在企业数据治理过程中，元数据（表名、字段名、业务描述、标签等）的完整性和准确性是数据资产管理的基础。当前现状：

- 元数据管理平台为 **OpenMetadata**，已纳管千级表/万级字段
- 元数据覆盖率仅 **30%–60%**，大量表/字段缺少中文名、业务定义、标签等关键信息
- 人工补全效率低、周期长，且不同治理人员标准不一

本项目构建 RAG 驱动的智能元数据补全系统，利用大模型能力自动生成元数据补全建议，辅以质量校验和人工审核机制，高效、高质量地提升元数据覆盖率。

### 1.2 项目目标

| 目标 | 描述 |
|------|------|
| **智能补全** | 给定表/字段，自动补全中文名、业务描述、标签等缺失元数据 |
| **质量保障** | 多维度质量校验 + 置信度评估 + 人工审核，确保补全准确率 ≥ 90% |
| **高效审核** | 高置信度自动采纳，低置信度人工审核，支持批量操作 |
| **双向同步** | 审核确认后自动回写 OpenMetadata，保持数据一致 |
| **可扩展** | 架构支持后续分类分级、智能搜索等扩展场景 |

### 1.3 适用范围

- 关系型数据库表/字段的元数据补全
- OpenMetadata 已纳管但信息不完整的数据资产
- 千级表/万级字段的数据治理场景

### 1.4 术语定义

| 术语 | 说明 |
|------|------|
| **元数据实体** | 数据库表（Table）或字段（Column）|
| **元数据补全** | 为缺失中文名、描述、标签的实体自动生成建议内容 |
| **置信度** | LLM 生成结果的可靠程度评分（0–1） |
| **双路检索** | Milvus 向量检索 + Elasticsearch 关键词检索并行执行，RRF 合并排序 |
| **RRF** | Reciprocal Rank Fusion，多路检索结果融合算法 |
| **OM** | OpenMetadata，外部元数据管理平台 |

---

## 2. 用户角色

| 角色 | 职责 | 权限 |
|------|------|------|
| **数据治理人员** | 搜索元数据、触发智能补全、审核补全结果 | 元数据搜索、补全触发、审核操作 |
| **系统管理员** | 配置规则阈值、管理模型路由策略、查看审计日志 | 全部功能 + 系统配置 |

---

## 3. 功能性需求

### 3.1 元数据搜索 (FR-SEARCH)

#### FR-SEARCH-001 关键词搜索

- **描述**: 支持按表名、字段名、中文名、描述等字段进行关键词搜索
- **输入**: 搜索关键词（支持中英文）
- **处理**: 通过 Elasticsearch 执行全文检索，IK 分词器处理中文
- **输出**: 匹配的元数据实体列表，含高亮匹配信息
- **验收标准**:
  - 支持模糊搜索（fuzziness=AUTO）
  - 支持按数据库、Schema、实体类型筛选
  - 响应时间 < 500ms (P95)

#### FR-SEARCH-002 自然语言搜索（后续阶段）

- **描述**: 支持自然语言描述检索元数据，如"查找与用户订单相关的表"
- **输入**: 自然语言查询文本
- **处理**: 查询文本向量化后通过 Milvus 语义检索
- **优先级**: P2（后续版本）

#### FR-SEARCH-003 结构化过滤

- **描述**: 支持按数据库名、Schema、实体类型（表/字段）、数据类型等维度过滤
- **输入**: 一个或多个过滤条件
- **输出**: 过滤后的元数据列表
- **验收标准**: 多条件组合过滤结果正确，支持 AND 逻辑

---

### 3.2 智能补全 (FR-COMPLETE)

#### FR-COMPLETE-001 手工触发补全

- **描述**: 用户在搜索界面选中元数据实体后，点击"智能补全"按钮触发
- **触发方式**: 前端 POST /api/v1/complete/trigger/manual
- **输入**: entity_id、entity_type
- **处理流程**:
  1. **Stage 1 — 双路检索**: Milvus 向量检索（语义相似）+ ES 关键词检索（精确匹配），RRF 合并取 Top 15
  2. **Stage 2 — LLM 生成**: 加载检索上下文，调用百炼平台模型（qwen-plus/deepseek-v3）生成补全建议
  3. **Stage 3 — 质量校验**: 置信度修正 + 规则引擎校验 + 冲突检测，输出分流结果
  4. **Stage 4 — 审核路由**: 高置信度自动采纳，低置信度入审核队列
- **输出**: 补全建议，含中文名、业务描述、标签、置信度、推理依据
- **验收标准**:
  - 单次补全响应时间 < 10s (P95)
  - LLM 输出格式符合 JSON Schema
  - 置信度在 0–1 范围内

#### FR-COMPLETE-002 批量补全

- **描述**: 通过 API 或后台 Job 对一批元数据实体批量触发补全
- **触发方式**:
  - API: POST /api/v1/complete/batch
  - 定时 Job: Celery 定时任务，扫描缺失元数据的实体
- **输入**: 实体 ID 列表（API）或自动扫描（Job）
- **处理**: 异步执行，每个实体独立走四阶段 Pipeline
- **输出**: 批量任务状态（进行中/已完成），各实体补全结果可查询
- **验收标准**:
  - 批量任务支持进度查询
  - 单实体失败不影响其他实体

#### FR-COMPLETE-003 表级补全

- **描述**: 为数据库表补全中文名、业务描述、标签、业务域
- **补全字段**:
  - display_name: 表中文名称（10 字以内）
  - description: 业务描述（1–3 句话）
  - tags: 标签列表（2–5 个）
  - business_domain: 所属业务域
  - confidence: 置信度评分
- **Prompt 上下文**: 同库兄弟表 + 相似表元数据参考

#### FR-COMPLETE-004 字段级补全

- **描述**: 为数据库字段补全中文名、业务描述、标签、敏感级别
- **补全字段**:
  - display_name: 字段中文名称（15 字以内）
  - description: 业务含义说明（1–2 句话）
  - tags: 标签列表
  - sensitive_level: 敏感级别（L1/L2/L3/L4）
  - confidence: 置信度评分
- **Prompt 上下文**: 同表其他字段 + 相似字段元数据参考

---

### 3.3 双路检索 (FR-RETRIEVE)

#### FR-RETRIEVE-001 向量检索

- **描述**: 将待补全实体向量化后，在 Milvus 中检索语义相似的已有元数据
- **Embedding 模型**: text-embedding-v3（百炼平台），输出 1024 维向量
- **检索范围**: 仅检索已有描述的元数据实体（has_description=true）
- **Top K**: 20
- **相似度度量**: COSINE（余弦相似度）

#### FR-RETRIEVE-002 关键词检索

- **描述**: 通过 ES 执行表名/字段名的精确和模糊匹配
- **分词器**: ik_max_word（中文分词）
- **检索字段**: table_name, column_name, display_name, description
- **过滤条件**: has_description=true, entity_type 匹配
- **Top K**: 20

#### FR-RETRIEVE-003 检索结果融合

- **描述**: 使用 RRF 算法合并双路检索结果
- **算法参数**: k=60
- **输出**: Top 15 融合结果，标注来源（milvus/es/both）
- **附加增强**: 额外检索同 Schema 下的 5 条兄弟表/字段

---

### 3.4 质量校验 (FR-QUALITY)

#### FR-QUALITY-001 置信度修正

- **描述**: 基于客观因子对 LLM 自评置信度进行修正
- **修正因子**:
  - 检索上下文平均得分低 → 降权 0.15
  - 描述过短 (< 10 字符) → 降权 0.20
  - 描述过长 (> 300 字符) → 降权 0.10
  - 中文名含特殊字符 → 降权 0.15
  - 标签数量异常 → 降权 0.05–0.10
- **输出**: 修正后的置信度 (0–1)

#### FR-QUALITY-002 规则引擎

- **描述**: 基于预定义规则校验 LLM 输出质量
- **规则列表**:

| 规则 | 级别 | 说明 |
|------|------|------|
| required_fields | CRITICAL | display_name 和 description 任一缺失，直接拒绝 |
| display_name_no_code | WARNING | 中文名不应包含大段英文字符 |
| description_not_copy_name | WARNING | 描述不应与中文名完全一致 |
| sensitive_level_valid | WARNING | 敏感级别必须在 L1–L4 范围内 |
| tag_no_duplicates | INFO | 标签列表不应包含重复项 |
| business_domain_valid | INFO | 业务域名字符长度合理 |
| table_name_consistency | WARNING | 表中文名不应与英文表名完全相同 |

#### FR-QUALITY-003 冲突检测

- **描述**: 检测新生成的补全结果与已有元数据的冲突
- **检测项**:
  - **描述分歧**: 新描述与已有描述语义重叠度 < 0.3 → 标记 warning
  - **标签覆盖**: 新标签与已有标签无交集 → 标记 info
- **处理**: 仅标记，不自动拒绝（旧元数据可能确实需要更新）

#### FR-QUALITY-004 分流路由

| 状态 | 条件 | 行为 |
|------|------|------|
| auto_approved | confidence ≥ 0.80，无 CRITICAL/WARNING | 直接回写 OpenMetadata，记录审计日志 |
| pending_review | confidence ≥ 0.60，无 CRITICAL | 进入审核队列，高亮问题标记 |
| rejected | confidence < 0.60 或有 CRITICAL | 记录拒绝原因，可选通知 |

---

### 3.5 人工审核 (FR-REVIEW)

#### FR-REVIEW-001 审核队列

- **描述**: 展示待审核的补全记录列表，支持分页和筛选
- **筛选维度**: 状态、实体类型、数据库/Schema、置信度范围、提交时间
- **排序**: 按提交时间倒序（默认）、置信度高低
- **验收标准**:
  - 分页加载 < 500ms
  - 筛选条件组合正确

#### FR-REVIEW-002 审核操作

- **确认 (Approve)**: 接受 AI 补全建议，回写 OpenMetadata
- **修改 (Modify)**: 修改 AI 建议后确认，回写修改后版本
- **拒绝 (Reject)**: 拒绝 AI 建议，仅记录日志，不回写
- **验收标准**:
  - 每个操作有二次确认
  - 操作结果即时反馈
  - 支持撤销（回写前）

#### FR-REVIEW-003 批量审核

- **描述**: 支持同库同类实体批量确认或批量拒绝
- **操作**: 勾选多条记录 → 批量确认 / 批量拒绝
- **验收标准**:
  - 批量操作显示处理进度
  - 部分失败不影响其他记录

#### FR-REVIEW-004 审核详情

- **描述**: 展示单条补全的完整信息
- **展示内容**:
  - 原始元数据（表名/字段名、已有信息）
  - AI 补全建议（中文名、描述、标签等）
  - 检索参考上下文（相似元数据列表）
  - 质量校验结果（置信度、规则命中、冲突标记）
  - 操作历史（提交时间、审核人、审核时间）

---

### 3.6 OpenMetadata 同步 (FR-SYNC)

#### FR-SYNC-001 元数据拉取

- **描述**: 定时从 OpenMetadata 拉取元数据，更新本地索引
- **同步方式**: Celery 定时 Job（增量 + 全量）
- **增量同步**: 每 15 分钟拉取增量变更
- **全量同步**: 每日凌晨全量重建索引
- **索引更新**: 同时更新 Milvus 向量库和 ES 索引

#### FR-SYNC-002 补全结果回写

- **描述**: 审核确认后将补全结果回写 OpenMetadata
- **回写方式**: JSON Patch (RFC 6902)，最小化写入
- **回写字段**: tags, description, displayName
- **验收标准**:
  - 回写成功/失败状态记录到 completion_records
  - 回写失败自动重试 3 次，间隔递增
  - 最终失败记录错误详情并告警

#### FR-SYNC-003 同步状态监控

- **描述**: 提供同步任务的状态查询和异常告警
- **查询**: 最近一次同步时间、同步实体数量、失败数量
- **告警**: 连续 3 次同步失败触发通知

---

### 3.7 补全历史 (FR-HISTORY)

#### FR-HISTORY-001 补全记录查询

- **描述**: 查询所有补全记录的历史
- **筛选维度**: 实体 ID、状态、时间范围
- **输出**: 记录列表（分页），含各阶段结果
- **验收标准**: 状态变更轨迹完整可追溯

---

### 3.8 后续阶段需求 (FR-FUTURE)

以下需求在架构中预留扩展点，当前版本不实现：

| 需求 | 描述 | 优先级 |
|------|------|--------|
| 分类分级 | 自动推荐分类标签和安全等级 | P2 |
| 智能搜索 | 自然语言检索元数据 | P2 |
| 知识图谱 | 构建表间血缘和业务关联 | P3 |
| 规则配置化 | 质量规则和阈值通过 UI 动态配置 | P2 |

---

## 4. 非功能性需求

### 4.1 性能要求

| 指标 | 目标 |
|------|------|
| 搜索响应时间 (P95) | < 500ms |
| 单次补全端到端时间 (P95) | < 10s |
| 批量补全吞吐量 | ≥ 20 实体/分钟 |
| 审核队列加载 (P95) | < 500ms |
| API 并发支持 | ≥ 50 并发请求 |

### 4.2 可用性要求

| 指标 | 目标 |
|------|------|
| 系统可用性 | ≥ 99.5%（非核心系统） |
| 计划内维护窗口 | 每周日 02:00–04:00 |

### 4.3 安全要求

| 要求 | 说明 |
|------|------|
| API 认证 | 所有 API 需认证访问（JWT Token） |
| 密钥管理 | DashScope API Key 等敏感信息通过环境变量注入，不硬编码 |
| 审计日志 | 所有补全确认/回写操作记录审计日志，含操作人、时间、内容 |
| 输入校验 | 所有 API 输入参数校验，防止注入攻击 |
| CORS | 仅允许管理前端域名跨域访问 |

### 4.4 可扩展性要求

- LangGraph Pipeline 各 Stage 独立，可单独扩展或替换
- 质量规则采用字典注册式，新增规则无需修改核心流程
- 模型路由支持按场景配置，新增模型只需注册

### 4.5 可维护性要求

- 代码覆盖率 ≥ 80%
- 每个 Stage 独立可测试
- API 文档自动生成（OpenAPI/Swagger）
- 结构化日志，支持日志级别动态调整

### 4.6 技术栈

| 层次 | 选择 | 版本 |
|------|------|------|
| 后端框架 | FastAPI | ≥ 0.115 |
| 编排框架 | LangGraph | ≥ 0.2 |
| LLM 框架 | LangChain | ≥ 0.3 |
| 模型服务 | 阿里云百炼 (DashScope) | ≥ 1.20 |
| 向量库 | Milvus | ≥ 2.4 |
| 搜索引擎 | Elasticsearch | 8.x |
| 关系数据库 | SQLite (dev) / PostgreSQL (prod) | - |
| 异步任务 | Celery + Redis | ≥ 5.4 |
| 前端框架 | Vue 3 + TDesign | ≥ 3.5 |
| 前端构建 | Vite | ≥ 6.0 |

---

## 5. 系统架构

### 5.1 四阶段 Pipeline

```
用户触发 → [Stage 1: 双路检索] → [Stage 2: LLM 生成] → [Stage 3: 质量校验] → [Stage 4: 审核回写] → 输出
              │                       │                      │                      │
         Milvus + ES             百炼平台             置信度修正 + 规则       审核工作台 +
         RRF 融合              qwen-plus/deepseek-v3    引擎 + 冲突检测      OpenMetadata 回写
```

### 5.2 模块划分

```
前端 (Vue3 + TDesign)
├── 元数据搜索页 (SearchPage)       — 关键词搜索 + 结构化过滤 + 手工触发补全
├── 补全审核工作台 (ReviewPage)     — 审核队列 + 确认/修改/拒绝 + 批量操作
├── 补全历史页 (HistoryPage)        — 历史记录查询
└── 配置管理页 (ConfigPage)         — 规则阈值管理（后续版本）

后端 (FastAPI + LangGraph)
├── API 服务层                       — RESTful API，请求校验，路由分发
├── Pipeline                         — LangGraph 四阶段状态图
│   ├── Stage 1: 双路检索            — Milvus + ES 混合检索
│   ├── Stage 2: LLM 生成            — 百炼模型调用 + Prompt 管理
│   ├── Stage 3: 质量校验            — 置信度修正 + 规则引擎 + 分流
│   └── Stage 4: 审核路由 + 同步     — 审核管理 + OM 回写
├── 服务层                           — Milvus/ES/OM/DashScope 客户端封装
├── 数据模型                         — ORM + 数据库迁移
└── 异步任务                         — Celery Job: 元数据同步 / 批量补全

数据层
├── Milvus                           — 向量存储与语义检索
├── Elasticsearch 8.x                — 全文检索与结构化过滤
├── PostgreSQL                       — 补全记录、审核记录、审计日志
└── Redis                            — Celery Broker + 缓存
```

### 5.3 数据流

```
1. 用户搜索 "用户订单"
2. ES 返回匹配元数据列表
3. 用户选中 t_user_order，点击"智能补全"
4. POST /api/v1/complete/trigger/manual → API 层
5. Stage 1: 构建检索文本 → 向量化 → Milvus + ES 双路检索 → RRF 融合
6. Stage 2: 加载检索上下文 → 组装 Prompt → 百炼 LLM 生成 → 解析 JSON 响应
7. Stage 3: 置信度修正 → 规则校验 → 冲突检测 → 分流
8. Stage 4: auto_approved 直接回写 / pending_review 入审核队列
9. 审核工作台展示待审核项 → 治理人员确认/修改/拒绝
10. 确认后回写 OpenMetadata
```

---

## 6. 接口需求

### 6.1 API 概览

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/v1/search` | GET | 元数据搜索 |
| `/api/v1/metadata/{id}` | GET | 元数据详情 |
| `/api/v1/complete/trigger/manual` | POST | 手工触发补全 |
| `/api/v1/complete/batch` | POST | 批量补全 |
| `/api/v1/complete/history` | GET | 补全历史 |
| `/api/v1/review/queue` | GET | 审核队列 |
| `/api/v1/review/{id}` | GET | 审核详情 |
| `/api/v1/review/{id}/approve` | POST | 确认补全 |
| `/api/v1/review/{id}/reject` | POST | 拒绝补全 |
| `/api/v1/review/{id}/modify` | POST | 修改后确认 |
| `/api/v1/review/batch/approve` | POST | 批量确认 |
| `/api/v1/review/batch/reject` | POST | 批量拒绝 |
| `/api/v1/sync/status` | GET | 同步状态 |

### 6.2 通用响应格式

```json
{
  "success": true,
  "data": {},
  "error": null,
  "meta": {
    "total": 100,
    "page": 1,
    "limit": 20
  }
}
```

---

## 7. 数据模型

### 7.1 核心实体

```
completion_records（补全记录）
├── id: UUID (PK)
├── entity_id: str          — OpenMetadata FQN
├── entity_type: str        — "table" | "column"
├── target_data: JSON       — Stage 1 输入快照
├── completion_result: JSON — Stage 2 LLM 输出
├── quality_check: JSON     — Stage 3 校验结果
├── review_status: str      — auto_approved | pending_review | rejected | approved | modified | human_rejected
├── reviewer: str?          — 审核人
├── review_comment: str?    — 审核备注
├── synced_to_om: bool      — 是否已回写 OM
├── created_at: datetime
├── updated_at: datetime
```

### 7.2 Milvus Collection

```
metadata_embeddings
├── id: INT64 (auto_id, PK)
├── entity_id: VARCHAR(256)
├── entity_type: VARCHAR(32)
├── database: VARCHAR(128)
├── schema: VARCHAR(128)
├── table_name: VARCHAR(256)
├── column_name: VARCHAR(256)
├── data_type: VARCHAR(64)
├── search_text: VARCHAR(4096)
├── embedding: FLOAT_VECTOR(1024)
```

### 7.3 ES 索引

```
metadata_index
├── entity_id: keyword
├── entity_type: keyword
├── database: keyword
├── schema: keyword
├── table_name: text + keyword
├── column_name: text + keyword
├── display_name: text (ik_max_word)
├── description: text (ik_max_word)
├── data_type: keyword
├── tags: keyword[]
├── has_description: boolean
```

---

## 8. 异常处理

| 场景 | 处理策略 |
|------|---------|
| LLM 返回格式非 JSON | 正则提取 JSON 块，失败则重试 1 次 |
| 百炼 API 超时 (30s) | 降级切换备选模型重试 |
| 上下文过长超 Token 限制 | 裁剪 retrieved_context 至 Top 10，schema_context 至 Top 3 |
| OpenMetadata 不可用 | 本地任务排队，恢复后自动重试 |
| Milvus 不可用 | 回退为仅 ES 检索 |
| ES 不可用 | 回退为仅 Milvus 检索 |
| 双路均不可用 | 返回错误，提示用户稍后重试 |
| OM 回写失败 | 自动重试 3 次，间隔递增，最终失败告警 |
| 批量操作部分失败 | 成功的继续，失败的记录错误并展示 |

---

## 9. 约束与假设

### 9.1 技术约束

- 模型服务统一通过阿里云百炼平台接入
- OpenMetadata 作为外部元数据源，系统不替代其管理功能
- 模型选择：qwen-plus 为主力模型，deepseek-v3 为备选推理模型

### 9.2 业务假设

- OpenMetadata 已稳定运行且 API 可用
- 元数据以中文业务场景为主
- 已有描述的元数据质量可信，可作为检索参考
- 数据治理人员具备基本的元数据审核判断能力

### 9.3 规模假设

| 维度 | 规模 |
|------|------|
| 表数量 | ~1,000 |
| 字段数量 | ~10,000 |
| 当前覆盖率 | 30%–60% |
| 并发用户 | 1–5 人（治理团队规模） |

---

## 10. 验收标准总览

| 编号 | 场景 | 验收标准 |
|------|------|---------|
| AC-01 | 关键词搜索 | 输入"用户"，返回含"用户"的表/字段，< 500ms |
| AC-02 | 手工触发补全 | 选中表点击"智能补全"，返回含中文名/描述/标签/置信度的 JSON |
| AC-03 | 自动采纳 | 高置信度补全自动回写 OM，不进入审核队列 |
| AC-04 | 人工审核 | 低置信度补全进入审核队列，支持确认/修改/拒绝 |
| AC-05 | 批量补全 | 通过 API 提交 50 个实体批量补全，返回任务 ID 可查询进度 |
| AC-06 | 回写验证 | 审核确认后，OpenMetadata 中对应元数据已更新 |
| AC-07 | 同步验证 | 定时任务从 OM 拉取增量变更，本地索引在 15 分钟内更新 |
| AC-08 | 异常降级 | Milvus 不可用时，系统回退为仅 ES 检索并返回结果 |
| AC-09 | 审计追溯 | 所有补全操作有完整审计日志，含操作人、时间、变更内容 |
| AC-10 | 性能指标 | 搜索 < 500ms，单次补全 < 10s，并发 50 请求不降级 |

---

## 11. 版本规划

| 阶段 | 内容 | 预估周期 |
|------|------|---------|
| Phase 1 | 项目脚手架 + Docker 基础设施 | 1 周 |
| Phase 2 | 后端核心（配置、数据库、服务层封装） | 1 周 |
| Phase 3 | Pipeline Stage 1–3（核心补全链路） | 2 周 |
| Phase 4 | Pipeline Stage 4 + API 层 + 审核工作台 | 2 周 |
| Phase 5 | 前端页面（搜索、审核、历史） | 2 周 |
| Phase 6 | Celery Job + 联调 + 部署验证 | 1 周 |

---

> **相关文档**:
> - [架构设计文档](./architecture-design.md)
> - [实现计划](./superpowers/plans/2026-05-15-metadata-completion.md)
