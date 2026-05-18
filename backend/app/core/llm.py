import os
from langchain_openai import ChatOpenAI

def get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        temperature=0.7,
        api_key=os.getenv("OPENAI_API_KEY")
    )

# Backward compatibility: module-level alias
# Only instantiated when accessed, not at import time
class _LazyLLM:
    _instance = None
    def __getattr__(self, name):
        if self._instance is None:
            self._instance = get_llm()
        return getattr(self._instance, name)

llm = _LazyLLM()
