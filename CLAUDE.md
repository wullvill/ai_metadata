# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

数据治理智能元数据补全系统 — 基于 RAG 技术，利用大模型自动为数据库表和字段补全中文名、业务描述、标签等元数据，辅以质量校验和人工审核机制。

详细需求见 `docs/requirements-specification.md`，架构设计见 `docs/architecture-design.md`，OpenSpec 规范见 `openspec/specs/`。

## Tech Stack

| 层次 | 技术 | 版本 |
|------|------|------|
| 后端框架 | FastAPI | ≥ 0.115 |
| 编排框架 | LangGraph | ≥ 0.2 |
| LLM 框架 | LangChain | ≥ 0.3 |
| 模型服务 | 阿里云百炼 (DashScope) | ≥ 1.20 |
| 向量库 | Milvus | ≥ 2.4 |
| 搜索引擎 | Elasticsearch | 8.x |
| 数据库 | SQLite (dev) / PostgreSQL (prod) | - |
| 异步任务 | Celery + Redis | ≥ 5.4 |
| 前端框架 | Vue 3 + TDesign | ≥ 3.5 |
| 前端构建 | Vite | ≥ 6.0 |

## Commands

```bash
# 后端
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000    # 启动 API 服务
celery -A app.celery_app worker -P gevent    # 启动 Celery Worker
pytest tests/ -v --cov=app --cov-report=term # 运行测试

# 前端
cd frontend
npm run dev      # 启动开发服务器 (Vite)
npm run build    # 生产构建
```

## Architecture

四阶段 LangGraph Pipeline：

```
用户触发 → [Stage 1: 双路检索] → [Stage 2: LLM 生成] → [Stage 3: 质量校验] → [Stage 4: 审核路由]
              Milvus + ES          百炼平台              置信度修正 + 规则        审核工作台 +
              RRF 融合           qwen/deepseek           引擎 + 冲突检测        OpenMetadata 回写
```

项目结构：

```
backend/app/
├── api/          # REST API 层 (search, complete, review)
├── pipeline/     # LangGraph 四阶段 Pipeline
├── services/     # 外部服务封装 (Milvus, ES, OM, DashScope)
├── models/       # ORM 数据模型
├── jobs/         # Celery 异步任务
└── utils/        # 工具函数

frontend/src/
├── pages/        # 4 个页面 (搜索、审核、历史、配置)
├── components/   # 6 个组件 (SearchBar, MetadataCard, CompletionPanel 等)
├── composables/  # 3 个 composable (useSearch, useCompletion, useReview)
├── api/          # API 客户端 + 类型定义
└── router/       # Vue Router 配置
```

## 环境信息

前端地址: http://localhost:5173/search
后端地址: http://localhost:8000/
接口规范: http://localhost:8000/docs