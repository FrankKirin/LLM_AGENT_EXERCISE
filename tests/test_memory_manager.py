from core.memory_manager import MemoryManager
from langchain.messages import HumanMessage
from types import SimpleNamespace
from unittest.mock import Mock, AsyncMock

# 测试短期记忆可存可取
def test_short_term_memory():
    manager = MemoryManager("user_1")

    manager.add_to_short_term(
        "session_1",
        HumanMessage(content="你好")
    )

    messages = manager.get_short_term("session_1").messages

    assert len(messages) == 1
    assert messages[0].content == "你好"

@pytest.mark.asyncio
async def test_extract_memory(monkeypatch, manager):
    for i in range(4):
        manager.add_to_short_term(
            "s1",
            HumanMessage(content=f"消息{i}")
        )

    mock_llm = Mock()
    mock_llm.ainvoke = AsyncMock(
        return_value=SimpleNamespace(
            content='["用户喜欢Python"]'
        )
    )

    monkeypatch.setattr(memory_module, "llm", mock_llm)

    result = await manager.extract_long_term_memories("s1")

    assert result == ["用户喜欢Python"]