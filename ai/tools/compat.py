"""
Compatibility shim for LangChain tools and messages when running in environments
where langchain or langchain_core is not yet installed.
"""
try:
    from langchain_core.tools import tool
except ImportError:
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

    def tool(func):
        return MockTool(func)


try:
    from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage
except ImportError:
    class BaseMessage:
        def __init__(self, content: str = ""):
            self.content = content

    class HumanMessage(BaseMessage):
        pass

    class SystemMessage(BaseMessage):
        pass
