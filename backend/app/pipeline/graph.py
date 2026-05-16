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
    from .stage4_sync import stage4_review_router

    graph = StateGraph(CompletionState)

    graph.add_node("retrieve", stage1_retrieve)
    graph.add_node("generate", stage2_generate)
    graph.add_node("quality_check", stage3_quality)

    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", "quality_check")

    # Stage 4: 条件路由
    graph.add_conditional_edges(
        "quality_check",
        stage4_review_router,
        {
            "auto_approved": END,
            "pending_review": END,
            "rejected": END,
        },
    )

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
