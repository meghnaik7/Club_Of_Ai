"""
Compatibility shim for LangChain tools and messages when running in environments
where langchain or langchain_core is not yet installed.
"""
from typing import Any

class MockTool:
    def __init__(self, func):
        self.func = func
        self.__name__ = getattr(func, "__name__", "tool")
        self.__doc__ = getattr(func, "__doc__", "")
        self.name = self.__name__
        self.description = self.__doc__

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    def invoke(self, input_data, *args, **kwargs):
        if isinstance(input_data, dict):
            return self.func(**input_data)
        return self.func(input_data)

def mock_tool(func):
    return MockTool(func)

tool = mock_tool

try:
    from langchain_core.tools import tool as _tool
    tool = _tool
except ImportError:
    pass


class BaseMessage:
    tool_calls: Any = None
    def __init__(self, content: str = "", **kwargs):
        self.content = content
        self.additional_kwargs = kwargs


class HumanMessage(BaseMessage):
    pass

class SystemMessage(BaseMessage):
    pass

class AIMessage(BaseMessage):
    def __init__(self, content: str = "", tool_calls=None, **kwargs):
        super().__init__(content, **kwargs)
        self.tool_calls = tool_calls or []

class ToolMessage(BaseMessage):
    def __init__(self, content: str = "", tool_call_id: str = "", **kwargs):
        super().__init__(content, **kwargs)
        self.tool_call_id = tool_call_id

try:
    from langchain_core.messages import (
        HumanMessage as _HumanMessage,
        SystemMessage as _SystemMessage,
        BaseMessage as _BaseMessage,
        AIMessage as _AIMessage,
        ToolMessage as _ToolMessage
    )
    HumanMessage = _HumanMessage
    SystemMessage = _SystemMessage
    BaseMessage = _BaseMessage
    AIMessage = _AIMessage
    ToolMessage = _ToolMessage
except ImportError:
    pass

__all__ = [
    "tool",
    "BaseMessage",
    "HumanMessage",
    "SystemMessage",
    "AIMessage",
    "ToolMessage"
]
