from models.dna import AgentDNA
from services.llm_client import LLMService

class BaseAgent:
    def __init__(self, dna: AgentDNA, llm_service: LLMService):
        self.dna = dna
        self.llm_service = llm_service

    async def run(self, task: str) -> dict:
        import time
        start_time = time.perf_counter()
        
        messages = [
            {"role": "system", "content": self.dna.role_prompt},
            {"role": "user", "content": task}
        ]
        
        response = await self.llm_service.generate_response(
            model="MiniMax-M2.5",
            messages=messages,
            temperature=self.dna.temperature
        )
        
        elapsed_time = time.perf_counter() - start_time
        # Estimation basique des tokens: 1 token ~= 4 caractères
        tokens = len(response) // 4 if response else 0
        
        return {
            "result": response,
            "time": elapsed_time,
            "tokens": tokens
        }
