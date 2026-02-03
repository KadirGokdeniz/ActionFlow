import os
from langchain_openai import ChatOpenAI

# Centralized LLM configuration
llm = ChatOpenAI(
    model="gpt-4o-mini", 
    temperature=0,
    api_key=os.getenv("OPENAI_API_KEY"),
    timeout=5,
    max_retries=1
)