from openai import AsyncOpenAI
from typing import List, Dict, Any

class LLMService:
    def __init__(self, api_key: str = None, base_url: str = None):
        """
        Initializes the LLMService with optional dependency injection.
        If not provided, AsyncOpenAI will automatically use OPENAI_API_KEY and OPENAI_BASE_URL from the environment.
        """
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def generate_response(self, model: str, messages: List[Dict[str, Any]], **kwargs) -> str | None:
        """
        Simple asynchronous method to generate a response from the LLM.
        """
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            **kwargs
        )
        return response.choices[0].message.content
