# 数据治理智能元数据补全系统 — 架构设计

> 版本: v1.0 | 日期: 2026-05-15 | 状态: 设计阶段

---

## 1. 项目背景

为数据治理场景构建 RAG 驱动的智能元数据补全系统。核心需求：

- **智能补全元数据**：给定表/字段，自动补全中文名、业务定义、数据类型等缺失信息
- **分类分级**：自动推荐分类标签和安全等级（后续阶段）
- **智能搜索**：自然语言检索元数据（后续阶段）
- 现有基础：**OpenMetadata** 作为元数据管理平台，系统独立运行，双向同步
- 数据规模：千级表/万级字段，元数据覆盖率 30-60%
- 模型服务：**阿里云百炼平台**统一接入
- 技术栈：Python + Vue3 + LangChain/LangGraph + Milvus + ES 8.x

---

## 2. 架构概览

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            管理前端 (Vue3)                                 │
│                                                                          │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │
│  │   元数据搜索       │  │   补全审核工作台    │  │   分类分级管理         │  │
│  │  (关键词/自然语言   │  │  (确认/修正/拒绝    │  │  (标签配置/规则管理    │  │
│  │   搜索 + 手工触发   │  │   AI 推荐结果)     │  │   分级结果审核)       │  │
│  │   自动补全)        │  │                   │  │                      │  │
│  └────────┬─────────┘  └────────┬─────────┘  └──────────┬───────────┘  │
│           │                     │                        │               │
│           │  搜索匹配的元数据     │  批量/单条补全审核       │  分类分级审核   │
│           │  选中后触发自动补全   │                        │               │
└───────────┼─────────────────────┼────────────────────────┼───────────────┘
            │                     │                        │
            │ REST API            │ REST API               │ REST API
            ▼                     ▼                        ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                          API 服务层 (FastAPI)                               │
│                                                                          │
│  /api/v1/search           /api/v1/complete         /api/v1/classify      │
│  /api/v1/metadata/{id}    /api/v1/complete/batch   /api/v1/review        │
│  /api/v1/sync             /api/v1/complete/trigger /api/v1/classify/     │
│                           manual                   batch                 │
└──────────────────────────────────────────────────────────────────────────┘
            │                     │                        │
            └─────────────────────┼────────────────────────┘
                                  │
┌─────────────────────────────────▼────────────────────────────────────────┐
│                       LangGraph Agent Pipeline                             │
│                                                                           │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐              │
│  │ Stage 1  │──▶│ Stage 2  │──▶│ Stage 3  │──▶│ Stage 4  │──▶ 输出      │
│  │ 双路检索  │   │ LLM 生成 │   │ 质量校验  │   │ 人工审核  │              │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘              │
│       │               │              │              │                     │
│       ▼               ▼              ▼              ▼                     │
│  Milvus+ES     阿里云百炼平台    置信度+规则      审核工作台               │
│  混合检索       (qwen-plus /     引擎过滤        (高置信度自动过，          │
│                 deepseek-v3)                    低置信度人工审)             │
└───────────────────────────────────────────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────────────┐
│                              数据层                                        │
│                                                                           │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────────────────────┐      │
│  │ Milvus   │  │  ES 8.x  │  │ OpenMetadata                      │      │
│  │ 向量检索  │  │ 关键词/   │  │ (外部元数据源，双向同步)            │      │
│  │          │  │ 结构化检索 │  │                                   │      │
│  └──────────┘  └──────────┘  │ * 定时拉取 OpenMetadata 元数据      │      │
│                              │ * 审核确认后回写补全结果              │      │
│                              └───────────────────────────────────┘      │
└──────────────────────────────────────────────────────────────────────────┘
```

### 2.1 核心设计决策

| 要点 | 选择 | 理由 |
|------|------|------|
| 检索策略 | Milvus 向量 + ES 关键词双路 | 语义相似 + 精确匹配互补 |
| 编排框架 | LangGraph StateGraph | 天然支持多阶段流程 + 人工审核节点 |
| 模型层 | 阿里云百炼平台 (dashscope SDK) | 统一 API 入口，灵活切换模型，集中计费 |
| 推荐模型 | qwen-plus 主力 / deepseek-v3 备选 | 千问中文理解好，DeepSeek 推理强，按场景路由 |
| 同步策略 | 定时 Job（增量 + 全量） | 避免强依赖 OpenMetadata 可用性 |
| 回写方式 | 人工确认后才回写 | 保证元数据质量，避免错误扩散 |
| 补全触发 | 手工触发 + API 批量 + 定时自动 | 覆盖交互式、自动化、批量三种场景 |

### 2.2 百炼平台接入

```python
# LangChain 集成方式
from langchain_community.chat_models import ChatTongyi

llm = ChatTongyi(
    model="qwen-plus",                    # qwen-plus / qwen-max / deepseek-v3
    dashscope_api_key=os.getenv("DASHSCOPE_API_KEY"),
    temperature=0.1,                       # 元数据场景需要低温度保证一致性
)
```

### 2.3 数据流：手工触发补全

```
用户在搜索页输入关键词 "用户订单"
  -> ES + Milvus 返回匹配的表/字段列表
  -> 用户浏览结果，选中 "t_user_order" 表
  -> 点击"智能补全"按钮
  -> 前端 POST /api/v1/complete/trigger/manual {table_id: "t_user_order"}
  -> API 层调用 LangGraph Pipeline
  -> Stage 1: 双路检索相似元数据 + 同库上下文
  -> Stage 2: LLM 分析候选 + 生成补全建议
  -> Stage 3: 质量校验，高置信度自动采纳，低置信度入审核队列
  -> Stage 4: 审核工作台展示待审核项
  -> 治理人员确认/修正/拒绝
  -> 确认后回写 OpenMetadata
  -> 前端展示补全结果
```

---

## 3. Stage 1 详细设计：双路检索

### 3.1 设计目标

给定一个待补全的元数据实体（表/字段），从已有元数据中检索出最有参考价值的上下文，作为后续 LLM 生成的 prompt 素材。

### 3.2 双路检索策略

| 检索路径 | 擅长 | 不足 |
|---------|------|------|
| **Milvus 向量检索** | 语义相似：表名不同但含义相近（如 `t_user` 和 `user_info`）| 精确匹配弱：`order_status` 搜不到同名字段 |
| **ES 关键词检索** | 精确匹配：字段名/表名完全或部分匹配；结构化过滤（数据库名、Schema、数据类型）| 语义盲区：`t_customer` 搜不到 `t_client` |

### 3.3 向量化策略

Embedding 模型：通过百炼平台调用 text-embedding-v3（千问嵌入模型）。

```python
from dashscope import TextEmbedding

def embed_text(text: str) -> list[float]:
    resp = TextEmbedding.call(
        model="text-embedding-v3",
        input=text,
        api_key=os.getenv("DASHSCOPE_API_KEY"),
    )
    return resp.output["embeddings"][0]["embedding"]
```

向量化文本模板：

```
# 表
"{database}.{schema}.{table_name} | 中文名:{display_name} | 描述:{description} | 标签:{tags} | 字段:{columns_summary}"

# 字段
"{database}.{schema}.{table_name}.{column_name} | 类型:{data_type} | 中文名:{display_name} | 描述:{description}"
```

### 3.4 Milvus Collection 设计

```python
COLLECTION_NAME = "metadata_embeddings"
DIM = 1024  # text-embedding-v3 输出维度

fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="entity_id", dtype=DataType.VARCHAR, max_length=256),
    FieldSchema(name="entity_type", dtype=DataType.VARCHAR, max_length=32),
    FieldSchema(name="database", dtype=DataType.VARCHAR, max_length=128),
    FieldSchema(name="schema", dtype=DataType.VARCHAR, max_length=128),
    FieldSchema(name="table_name", dtype=DataType.VARCHAR, max_length=256),
    FieldSchema(name="column_name", dtype=DataType.VARCHAR, max_length=256),
    FieldSchema(name="data_type", dtype=DataType.VARCHAR, max_length=64),
    FieldSchema(name="search_text", dtype=DataType.VARCHAR, max_length=4096),
    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=DIM),
]

index_params = {
    "index_type": "IVF_FLAT",
    "metric_type": "COSINE",
    "params": {"nlist": 128},
}
```

### 3.5 ES 索引设计

```json
{
  "mappings": {
    "properties": {
      "entity_id":   { "type": "keyword" },
      "entity_type": { "type": "keyword" },
      "database":    { "type": "keyword" },
      "schema":      { "type": "keyword" },
      "table_name":  { "type": "text", "fields": { "raw": { "type": "keyword" } } },
      "column_name": { "type": "text", "fields": { "raw": { "type": "keyword" } } },
      "display_name":    { "type": "text", "analyzer": "ik_max_word" },
      "description":     { "type": "text", "analyzer": "ik_max_word" },
      "data_type":       { "type": "keyword" },
      "tags":            { "type": "keyword" },
      "has_description": { "type": "boolean" }
    }
  }
}
```

### 3.6 检索流程

```
输入: entity = {entity_id, entity_type, database, schema, table_name, column_name?, data_type?}

Step 1: 构建检索文本
  search_text = f"{database}.{schema}.{table_name}[.{column_name}] {data_type}"
  embedding = embed_text(search_text)

Step 2: 并行双路检索
  |-- Milvus: search(embedding, top_k=20, filter="has_description==true")
  |-- ES: multi_match + fuzziness=AUTO, filter: has_description=true, entity_type=target_type

Step 3: RRF 合并排序 (k=60)

Step 4: 附加上下文增强
  |-- ES 查询同库同 Schema 下的兄弟表/字段（top 5）

Step 5: 返回 Top 15 结果
```

### 3.7 RRF 合并算法

```python
def rrf_merge(milvus_results, es_results, k=60, top_n=15):
    scores = {}
    detail = {}
    for rank, item in enumerate(milvus_results):
        scores[item["entity_id"]] = scores.get(item["entity_id"], 0) + 1/(k + rank + 1)
        detail[item["entity_id"]] = {**item, "source": "milvus"}
    for rank, item in enumerate(es_results):
        scores[item["entity_id"]] = scores.get(item["entity_id"], 0) + 1/(k + rank + 1)
        prev = detail.get(item["entity_id"], {})
        source = "both" if prev.get("source") == "milvus" else "es"
        detail[item["entity_id"]] = {**prev, **item, "source": source}
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [detail[eid] for eid, _ in ranked[:top_n]]
```

### 3.8 Stage 1 关键设计要点

| 要点 | 决策 | 理由 |
|------|------|------|
| 只检索有描述的元数据 | `has_description=true` 过滤 | 空描述的元数据没有参考价值 |
| ES 使用 ik_max_word 分词器 | IK 中文分词 | 中英文混合字段名分词效果好 |
| 同库上下文增强 | 额外检索 5 条同 Schema 兄弟表 | LLM 需要了解表的"邻居" |
| 向量检索过滤 entity_type | 字段补全只检索字段，表补全只检索表 | 避免跨类型噪音 |
| Top 15 输出 | 兼顾覆盖和上下文长度 | 平衡 LLM 输入窗口和检索召回率 |

---

## 4. Stage 2 详细设计：LLM 生成

### 4.1 模型选择策略

```
if 表级补全 and 上下文复杂度高:
    model = "qwen-max"
elif 字段级补全 and 数据类型明确:
    model = "qwen-plus"      # 主力模型，性价比最优
elif 需要逻辑推理:
    model = "deepseek-v3"    # 推理能力强
else:
    model = "qwen-plus"      # 默认
```

### 4.2 Prompt 设计

#### 表级补全

```text
你是数据治理专家。请根据已有元数据参考，为下面这张数据库表补全元数据信息。

## 待补全的表
- 库名: {database}
- Schema: {schema}
- 表名: {table_name}
- 已有描述: {current_description}（可能为空）
- 已有中文名: {current_display_name}（可能为空）
- 该表包含的字段: {columns_summary}

## 同库兄弟表（了解表所处的业务上下文）
{schema_context}

## 相似表的元数据参考（按相关度排序）
{retrieved_context}

## 请补全以下信息，以 JSON 格式返回：
{{
  "display_name": "表的中文名称（简洁，10 字以内）",
  "description": "表的业务描述（1-3 句话）",
  "tags": ["标签1", "标签2", "标签3"],
  "business_domain": "所属业务域",
  "confidence": 0.85,
  "reasoning": "简要说明补全依据（可选）"
}}
```

#### 字段级补全

```text
你是数据治理专家。请根据已有元数据参考，为下面这个数据库字段补全元数据信息。

## 待补全的字段
- 所属表: {database}.{schema}.{table_name}
- 表的业务含义: {table_description}（可能为空）
- 字段名: {column_name}
- 数据类型: {data_type}
- 已有描述: {current_description}（可能为空）
- 已有中文名: {current_display_name}（可能为空）

## 同表其他字段（了解字段所在上下文）
{sibling_columns}

## 相似字段的元数据参考（按相关度排序）
{retrieved_context}

## 请补全以下信息，以 JSON 格式返回：
{{
  "display_name": "字段的中文名称（15 字以内）",
  "description": "字段的业务含义说明（1-2 句话）",
  "tags": ["标签1", "标签2"],
  "sensitive_level": "L1|L2|L3|L4",
  "confidence": 0.85,
  "reasoning": "简要说明补全依据（可选）"
}}
```

### 4.3 LLM 响应解析

```python
def parse_llm_json(raw_response: str) -> dict:
    """从 LLM 文本响应中提取 JSON，处理常见格式问题"""
    try:
        return json.loads(raw_response)
    except json.JSONDecodeError:
        pass
    # 提取 ```json ... ``` 代码块
    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', raw_response)
    if match:
        return json.loads(match.group(1))
    # 提取第一个 { ... } 块
    match = re.search(r'\{[\s\S]*\}', raw_response)
    if match:
        return json.loads(match.group(0))
    raise ValueError(f"无法从 LLM 响应中解析 JSON: {raw_response[:500]}")
```

### 4.4 异常处理

| 场景 | 处理策略 |
|------|---------|
| LLM 返回格式非 JSON | 正则提取 JSON 块，失败则重试 1 次 |
| 返回字段缺失 | 缺失字段设为 null，confidence 降权 0.2 |
| 百炼 API 超时 (30s) | 降级切换备选模型重试 |
| 上下文过长超 token 限制 | 裁剪 retrieved_context 至 Top 10，schema_context 至 Top 3 |
| confidence 不在 0-1 范围 | clamp 到 [0, 1] 并记录告警 |

### 4.5 Stage 2 关键设计决策

| 要点 | 决策 | 理由 |
|------|------|------|
| temperature=0.1 | 低温度 | 元数据场景需要稳定一致的输出 |
| 表/字段用不同 Prompt | 分开设计 | 两者补全的字段和上下文差异大 |
| JSON 严格输出 | 结构化输出 | Stage 3 质量校验需要可编程解析 |
| 模型自动路由 | select_model 函数 | 按场景复杂度选模型，平衡质量和成本 |
| 单次调用 | 不链式调用 | 元数据补全是确定性问题，单次调用足够 |

---

## 5. Stage 3 详细设计：质量校验

### 5.1 分流策略

```
Stage 2 输出
    │
    ▼
Stage 3 质量校验
    │
    ├── confidence >= 0.80 且所有规则通过 → auto_approved（直接采纳）
    ├── confidence >= 0.60 且无关键违规  → pending_review（入审核队列）
    └── confidence < 0.60 或有关键违规  → rejected（标记拒绝 + 告警）
```

### 5.2 校验维度

#### 置信度修正

```python
def calculate_adjusted_confidence(result: dict, target: dict) -> float:
    score = result["confidence"]
    penalties = []

    # 检索上下文质量降权
    retrieval_scores = [ctx["score"] for ctx in target.get("retrieved_context", [])[:5]]
    avg_score = sum(retrieval_scores) / max(len(retrieval_scores), 1)
    if avg_score < 0.05:
        penalties.append(0.15)

    # 描述长度异常降权
    desc_len = len(result["description"])
    if desc_len < 10:
        penalties.append(0.20)
    elif desc_len > 300:
        penalties.append(0.10)

    # 中文名特殊字符降权
    if re.search(r'[{}[\]()\\]', result["display_name"]):
        penalties.append(0.15)

    # 标签数量异常降权
    if len(result["tags"]) == 0:
        penalties.append(0.10)
    elif len(result["tags"]) > 8:
        penalties.append(0.05)

    adjusted = score - sum(penalties)
    return max(0.0, min(1.0, adjusted))
```

#### 规则引擎

| 规则 | 级别 | 说明 |
|------|------|------|
| required_fields | critical | display_name 和 description 任一缺失直接拒绝 |
| display_name_no_code | warning | 中文名不应包含大段英文 |
| description_not_copy_name | warning | 描述不应与中文名完全一致 |
| sensitive_level_valid | warning | 敏感级别必须在 L1-L4 范围内 |
| tag_no_duplicates | info | 标签不应重复 |
| business_domain_valid | info | 业务域名不应过长 |
| table_name_consistency | warning | 表中文名不应与英文表名完全相同 |

#### 冲突检测

```python
def check_conflict(result: dict, target: dict) -> list[dict]:
    conflicts = []
    # 已有描述 vs 新描述语义重叠检测
    if target.get("current_description"):
        overlap = compute_text_overlap(result["description"], target["current_description"])
        if overlap < 0.3:
            conflicts.append({"type": "description_divergence", "severity": "warning"})
    # 已有标签 vs 新标签交集检测
    if target.get("current_tags") and result.get("tags"):
        if not set(target["current_tags"]).intersection(set(result["tags"])):
            conflicts.append({"type": "tag_overhaul", "severity": "info"})
    return conflicts
```

### 5.3 分流阈值

| 状态 | 条件 | 行为 |
|------|------|------|
| **auto_approved** | confidence >= 0.80, 无 critical/warning | 直接回写 OpenMetadata，记录审计日志 |
| **pending_review** | confidence >= 0.60, 无 critical | 进入审核工作台，带高亮问题标记 |
| **rejected** | confidence < 0.60 或有关键违规 | 记录拒绝原因，通知用户手工补全 |

### 5.4 Stage 3 关键设计决策

| 要点 | 决策 | 理由 |
|------|------|------|
| 置信度修正 | 客观因子降权 | LLM self-confidence 常有偏差 |
| 规则分级 | critical/warning/info 三级 | 灵活分流，后续可配置化 |
| 冲突检测 | 仅标记不拒绝 | 旧描述可能需更新覆盖 |
| 自动采纳门槛 | 高门槛起步 (0.80) | 数据治理容错率低 |
| 规则可扩展 | 字典注册式 | 分类分级场景可直接复用 |

---

## 6. Stage 4 详细设计：人工审核 + 同步回写

### 6.1 审核流程

```
Stage 3 输出
    │
    ├── auto_approved ──▶ 直接回写 OpenMetadata + 记录审计日志
    │
    ├── pending_review ──▶ 进入审核队列
    │                     ├── 治理人员：确认 / 修改 / 拒绝
    │                     ├── 确认 → 回写 OpenMetadata + 日志
    │                     ├── 修改 → 回写修改后版本 + 日志
    │                     └── 拒绝 → 仅记录日志
    │
    └── rejected ────────▶ 记录拒绝原因 + 可选通知
```

### 6.2 API 设计

```
GET    /api/v1/review/queue          # 审核队列（分页、筛选）
GET    /api/v1/review/{id}            # 单条审核详情
POST   /api/v1/review/{id}/approve    # 确认补全
POST   /api/v1/review/{id}/reject     # 拒绝补全
POST   /api/v1/review/{id}/modify     # 修改后确认
POST   /api/v1/review/batch/approve   # 批量确认
POST   /api/v1/review/batch/reject    # 批量拒绝
GET    /api/v1/complete/history       # 补全历史
```

### 6.3 审核数据模型

```python
class CompletionRecord(Base):
    __tablename__ = "completion_records"
    id: str              # UUID
    entity_id: str       # OpenMetadata FQN
    entity_type: str     # "table" | "column"
    target_data: dict    # Stage 1 输入快照 (JSON)
    completion_result: dict   # Stage 2 输出 (JSON)
    quality_check: dict       # Stage 3 校验结果 (JSON)
    review_status: str  # auto_approved/pending_review/rejected/approved/modified/human_rejected
    reviewer: str | None
    review_comment: str | None
    reviewed_at: datetime | None
    synced_to_om: bool
    synced_at: datetime | None
    created_at: datetime
    updated_at: datetime
```

### 6.4 OpenMetadata 回写

```python
async def sync_to_openmetadata(record: CompletionRecord):
    client = OpenMetadataClient(
        base_url=settings.OM_BASE_URL,
        jwt_token=await get_access_token(),
    )
    patch = [
        {"op": "add", "path": "/tags/...", "value": record.result["tags"]},
        {"op": "add", "path": "/description", "value": record.result["description"]},
        {"op": "add", "path": "/displayName", "value": record.result["display_name"]},
    ]
    if record.entity_type == "table":
        await client.patch_table(record.entity_id, patch)
    else:
        await client.patch_column(record.entity_id, patch)
```

### 6.5 Stage 4 关键设计决策

| 要点 | 决策 | 理由 |
|------|------|------|
| auto_approved 不经过人工 | 直接回写 + 审计日志 | 减少审核负担，日志可追溯 |
| 修改后确认 | 审核工作台支持修改 | 微调后采纳是常态 |
| 回写格式 | JSON Patch (RFC 6902) | 最小化写入，避免覆盖 |
| 批量操作 | 支持同库同类批量确认 | 提效，同库表风格往往一致 |

---

## 7. 工程化设计

### 7.1 后端项目结构

```
backend/
├── app/
│   ├── main.py                  # FastAPI 入口
│   ├── config.py                # 配置管理 (pydantic-settings)
│   ├── api/
│   │   ├── search.py            # 元数据搜索 API
│   │   ├── complete.py          # 补全 API
│   │   ├── review.py            # 审核 API
│   │   └── sync.py              # OpenMetadata 同步 API
│   ├── pipeline/
│   │   ├── graph.py             # LangGraph StateGraph 定义
│   │   ├── stage1_retrieve.py   # Stage 1: 双路检索
│   │   ├── stage2_generate.py   # Stage 2: LLM 生成
│   │   ├── stage3_quality.py    # Stage 3: 质量校验
│   │   └── stage4_sync.py       # Stage 4: 审核路由 + OM 同步
│   ├── services/
│   │   ├── milvus.py            # Milvus 客户端封装
│   │   ├── elasticsearch.py     # ES 客户端封装
│   │   ├── openmetadata.py      # OpenMetadata API 封装
│   │   ├── dashscope.py         # 百炼模型调用封装
│   │   └── embedding.py         # 向量嵌入服务
│   ├── models/
│   │   ├── completion.py        # 补全记录 ORM
│   │   ├── metadata.py          # 元数据索引模型
│   │   └── audit.py             # 审计日志 ORM
│   ├── jobs/
│   │   ├── metadata_sync.py     # OpenMetadata → 本地索引同步 Job
│   │   └── batch_complete.py    # 批量补全 Job
│   └── utils/
│       ├── retry.py             # 重试工具
│       └── logger.py            # 日志配置
├── alembic/
├── tests/
│   ├── test_stage1_retrieve.py
│   ├── test_stage2_generate.py
│   ├── test_stage3_quality.py
│   └── test_api.py
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── requirements.txt
```

### 7.2 前端项目结构

```
frontend/
├── src/
│   ├── pages/
│   │   ├── SearchPage.vue        # 元数据搜索 + 手动触发补全
│   │   ├── ReviewPage.vue        # 补全审核工作台
│   │   ├── HistoryPage.vue       # 补全历史
│   │   └── ConfigPage.vue        # 规则配置/阈值管理
│   ├── components/
│   │   ├── MetadataCard.vue      # 元数据卡片
│   │   ├── CompletionPanel.vue   # 补全建议展示面板
│   │   ├── ReviewQueue.vue       # 审核队列列表
│   │   ├── ReviewDetail.vue      # 审核详情弹窗
│   │   ├── QualityBadge.vue      # 置信度/状态徽章
│   │   └── SearchBar.vue         # 搜索栏
│   ├── composables/
│   │   ├── useSearch.ts
│   │   ├── useCompletion.ts
│   │   └── useReview.ts
│   ├── api/
│   │   └── index.ts
│   ├── router/
│   │   └── index.ts
│   └── styles/
│       └── tokens.css
├── package.json
└── vite.config.ts
```

### 7.3 核心依赖

```txt
# backend/requirements.txt
langchain>=0.3.0
langgraph>=0.2.0
langchain-community>=0.3.0
dashscope>=1.20.0
fastapi>=0.115.0
uvicorn>=0.30.0
pymilvus>=2.4.0
elasticsearch>=8.15.0
openmetadata-ingestion>=1.4.0
sqlalchemy>=2.0.0
alembic>=1.13.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
httpx>=0.27.0
celery>=5.4.0
redis>=5.0.0
```

```json
// frontend/package.json (核心依赖)
{
  "vue": "^3.5",
  "axios": "^1.7",
  "pinia": "^2.2",
  "vue-router": "^4.4",
  "vite": "^6.0",
  "tdesign-vue-next": "^1.10"
}
```

### 7.4 关键技术决策

| 类别 | 决策 | 理由 |
|------|------|------|
| 异步任务 | Celery + Redis | 批量补全和 OM 同步耗时较长 |
| 状态管理 | Pinia | Vue3 官方推荐 |
| UI 组件库 | TDesign Vue Next | 企业级，含审核流所需组件 |
| 数据库 | SQLite(dev) / PostgreSQL(prod) | 仅存储补全记录和审计日志 |
| 向量模型 | text-embedding-v3 (百炼) | 统一平台，避免多供应商 |
| Celery 并发 | gevent pool | I/O 密集型任务 |
