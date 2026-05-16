"""Stage 2: LLM 生成补全建议"""
import json
import re
from datetime import datetime, timezone
from langchain_core.messages import HumanMessage
from .state import CompletionState
from .prompts import TABLE_COMPLETION_PROMPT, COLUMN_COMPLETION_PROMPT
from app.services.dashscope import create_llm
from app.utils.logger import get_logger

logger = get_logger(__name__)


def select_model(entity_type: str, schema_context: list[dict], retrieved_context: list[dict]) -> str:
    """Select model based on task complexity.

    Table completion with rich context -> qwen-max
    Otherwise -> qwen-plus (default)
    """
    if entity_type == "table":
        rich_desc_count = sum(
            1 for s in schema_context
            if s.get("description") and len(s.get("description", "")) > 10
        )
        if rich_desc_count > 5:
            return "qwen-max"
    return "qwen-plus"


def parse_llm_json(raw_response: str) -> dict:
    """从 LLM 文本响应中提取 JSON"""
    # 尝试直接解析
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


def _format_context_list(ctx_list: list[dict]) -> str:
    """格式化上下文列表为 Prompt 文本"""
    lines = []
    for i, ctx in enumerate(ctx_list, 1):
        text = ctx.get('search_text', '')
        score = ctx.get('score', 0)
        lines.append(f"{i}. {text} [相关度: {score:.3f}]")
    return "\n".join(lines) if lines else "（无参考数据）"


def _build_table_prompt(target: dict, state: CompletionState) -> str:
    """构建表级补全 Prompt"""
    columns = target.get("columns", [])
    columns_summary = ", ".join(
        f"{c.get('name', '?')}({c.get('dataType', '?')})" for c in columns[:20]
    )
    schema_lines = [
        f"- {s.get('table_name', '?')}: {s.get('description', '无描述')}"
        for s in (state.get("schema_context") or [])
    ]
    return TABLE_COMPLETION_PROMPT.format(
        database=target.get("database", ""),
        schema=target.get("schema", ""),
        table_name=target.get("table_name", ""),
        current_description=target.get("current_description") or "（空）",
        current_display_name=target.get("current_display_name") or "（空）",
        columns_summary=columns_summary,
        schema_context="\n".join(schema_lines) if schema_lines else "（无同库兄弟表）",
        retrieved_context=_format_context_list(state.get("retrieved_context") or []),
    )


def _build_column_prompt(target: dict, state: CompletionState) -> str:
    """构建字段级补全 Prompt"""
    sib_lines = [
        f"- {s.get('column_name', '?')} ({s.get('data_type', '?')}): {s.get('description', '无描述')}"
        for s in (state.get("sibling_columns") or [])
    ]
    return COLUMN_COMPLETION_PROMPT.format(
        database=target.get("database", ""),
        schema=target.get("schema", ""),
        table_name=target.get("table_name", ""),
        table_description=target.get("table_description") or "（空）",
        column_name=target.get("column_name", ""),
        data_type=target.get("data_type", ""),
        current_description=target.get("current_description") or "（空）",
        current_display_name=target.get("current_display_name") or "（空）",
        sibling_columns="\n".join(sib_lines) if sib_lines else "（无同表字段信息）",
        retrieved_context=_format_context_list(state.get("retrieved_context") or []),
    )


async def stage2_generate(state: CompletionState) -> CompletionState:
    """Stage 2: LLM 生成补全建议"""
    if state.get("error"):
        return state

    target = state["target_entity"]

    # 选择模型
    model_name = select_model(
        target["entity_type"],
        state.get("schema_context") or [],
        state.get("retrieved_context") or [],
    )

    llm = create_llm(model=model_name, temperature=0.1)

    # 构建 Prompt
    if target["entity_type"] == "table":
        prompt = _build_table_prompt(target, state)
    else:
        prompt = _build_column_prompt(target, state)

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        result = parse_llm_json(response.content)

        # 修正字段缺失：缺失字段降权
        missing_penalty = 0.0
        if not result.get("display_name"):
            missing_penalty += 0.1
        if not result.get("description"):
            missing_penalty += 0.1

        confidence = result.get("confidence", 0.5)
        confidence = max(0.0, min(1.0, confidence - missing_penalty))

        state["completion_result"] = {
            "target_entity_id": target["entity_id"],
            "entity_type": target["entity_type"],
            "display_name": result.get("display_name") or "",
            "description": result.get("description") or "",
            "tags": result.get("tags") or [],
            "business_domain": result.get("business_domain"),
            "sensitive_level": result.get("sensitive_level"),
            "confidence": confidence,
            "reasoning": result.get("reasoning", ""),
            "model_used": model_name,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        logger.info(f"Stage 2 complete: model={model_name}, confidence={confidence:.2f}")
    except Exception as e:
        logger.error(f"Stage 2 failed: {e}")
        state["error"] = str(e)
        state["completion_result"] = None

    return state
