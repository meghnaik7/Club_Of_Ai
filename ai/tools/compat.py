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

import json
from typing import Optional, List, Dict, Any, Union

class ChatOpenAICompat:
    def __init__(
        self,
        api_key: str = "",
        model: str = "openai/gpt-4o-mini",
        base_url: Optional[str] = None,
        default_headers: Optional[Dict[str, str]] = None,
        temperature: float = 0.2,
        request_timeout: float = 30.0,
        **kwargs
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.default_headers = default_headers
        self.temperature = temperature
        self.request_timeout = request_timeout
        self.tools: List[Any] = []
        self.response_metadata: Dict[str, Any] = {}

    def bind_tools(self, tools: List[Any]) -> "ChatOpenAICompat":
        bound = ChatOpenAICompat(
            api_key=self.api_key,
            model=self.model,
            base_url=self.base_url,
            default_headers=self.default_headers,
            temperature=self.temperature,
            request_timeout=self.request_timeout
        )
        bound.tools = list(tools)
        return bound

    def invoke(self, messages: Union[str, List[Any]]) -> AIMessage:
        import openai
        client = openai.OpenAI(
            api_key=self.api_key or "sk-dummy-key",
            base_url=self.base_url,
            default_headers=self.default_headers or None,
            timeout=self.request_timeout
        )
        formatted_messages = []
        if isinstance(messages, str):
            formatted_messages.append({"role": "user", "content": messages})
        elif isinstance(messages, list):
            for m in messages:
                if isinstance(m, dict):
                    formatted_messages.append(m)
                elif hasattr(m, "content"):
                    t_name = type(m).__name__.lower()
                    if "system" in t_name:
                        role = "system"
                    elif "ai" in t_name:
                        role = "assistant"
                    elif "tool" in t_name:
                        role = "tool"
                    else:
                        role = "user"
                    formatted_messages.append({"role": role, "content": str(m.content)})
                else:
                    formatted_messages.append({"role": "user", "content": str(m)})

        call_kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": formatted_messages,
            "temperature": self.temperature,
        }
        if self.tools:
            openai_tools = []
            for t in self.tools:
                t_name = getattr(t, "name", getattr(t, "__name__", "tool"))
                t_desc = getattr(t, "description", getattr(t, "__doc__", "") or "")
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": t_name,
                        "description": t_desc,
                        "parameters": {"type": "object", "properties": {}}
                    }
                })
            call_kwargs["tools"] = openai_tools

        resp = client.chat.completions.create(**call_kwargs)
        choice = resp.choices[0]
        content = choice.message.content or ""
        tool_calls = []
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                try:
                    args = json.loads(tc.function.arguments) if isinstance(tc.function.arguments, str) else tc.function.arguments
                except Exception:
                    args = {}
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "args": args
                })

        token_usage = {}
        if hasattr(resp, "usage") and resp.usage:
            token_usage = {
                "prompt_tokens": getattr(resp.usage, "prompt_tokens", 0),
                "completion_tokens": getattr(resp.usage, "completion_tokens", 0),
                "total_tokens": getattr(resp.usage, "total_tokens", 0),
            }

        ai_msg = AIMessage(content=content, tool_calls=tool_calls)
        ai_msg.response_metadata = {"token_usage": token_usage}
        return ai_msg

try:
    from langchain_openai import ChatOpenAI as _ChatOpenAI
    ChatOpenAI = _ChatOpenAI
except ImportError:
    ChatOpenAI = ChatOpenAICompat

__all__ = [
    "tool",
    "BaseMessage",
    "HumanMessage",
    "SystemMessage",
    "AIMessage",
    "ToolMessage",
    "ChatOpenAI",
    "ChatOpenAICompat"
]
