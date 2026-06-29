"""LangGraph Pipeline 定义"""
from typing import Optional

from langgraph.graph import StateGraph, END
from .state import CompletionState


def create_completion_graph() -> StateGraph:
    """Assemble and compile the 4-stage metadata completion pipeline graph.

    Stages: retrieve -> generate -> quality_check -> (condition: review route).
    """
    # Lazy imports: stage modules do not exist yet (created in subsequent tasks).
    from .stage1_retrieve import stage1_retrieve
    from .stage2_generate import stage2_generate
    from .stage3_quality import stage3_quality
    # from .stage4_sync import stage4_review_router, stage4_sync

    graph = StateGraph(CompletionState)

    graph.add_node("retrieve", stage1_retrieve)
    graph.add_node("generate", stage2_generate)
    graph.add_node("quality_check", stage3_quality)
    # graph.add_node("sync", stage4_sync)

    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", "quality_check")
    graph.add_edge("quality_check", END)

    # Stage 4: 条件路由（已关闭 OpenMetadata 回写）
    # graph.add_conditional_edges(
    #     "sync",
    #     stage4_review_router,
    #     {
    #         "auto_approved": END,
    #         "pending_review": END,
    #         "rejected": END,
    #     },
    # )

    return graph.compile()


# Lazy initialization: do NOT instantiate at module level (stage modules don't exist yet).
_pipeline: Optional[StateGraph] = None


def get_pipeline():
    """Lazy getter for the compiled pipeline.

    The pipeline is created on first call and cached globally.
    Calling this will fail until stage1_retrieve, stage2_generate,
    stage3_quality, and stage4_sync modules are created.
    """
    global _pipeline
    if _pipeline is None:
        _pipeline = create_completion_graph()
    return _pipeline


def get_stages():
    """Return stage2 and stage3 functions for standalone use (column cascade)."""
    from .stage2_generate import stage2_generate
    from .stage3_quality import stage3_quality
    return stage2_generate, stage3_quality
