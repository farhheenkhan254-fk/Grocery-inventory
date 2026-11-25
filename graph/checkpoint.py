import logging
from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger("smart_grocery.graph.checkpoint")

_memory_checkpointer = MemorySaver()

def get_checkpointer() -> MemorySaver:
    """
    Returns persistent in-memory checkpointer for LangGraph human-in-the-loop state.
    """
    return _memory_checkpointer
