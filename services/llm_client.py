import asyncio
from openai import AsyncOpenAI
from typing import List, Dict, Any
from utils.logger import log

class LLMService:
    def __init__(self, api_key: str = None, base_url: str = None):
        """
        Initializes the LLMService with optional dependency injection.
        If not provided, AsyncOpenAI will automatically use OPENAI_API_KEY and OPENAI_BASE_URL from the environment.
        """
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def generate_response(self, model: str, messages: List[Dict[str, Any]], **kwargs) -> str | None:
        """
        Asynchronous method to generate a response from the LLM with retry logic.
        """
        max_retries = 3
        base_delay = 2

        for attempt in range(max_retries):
            try:
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    **kwargs
                )
                return response.choices[0].message.content
            except Exception as e:
                log(f"Erreur appel API (tentative {attempt+1}/{max_retries}): {e}", category="LLM-RETRY")
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    log(f"Nouvelle tentative dans {delay} secondes...", category="LLM-RETRY")
                    await asyncio.sleep(delay)
                else:
                    log(f"Échec définitif après {max_retries} tentatives.", category="ERROR")
                    return None
