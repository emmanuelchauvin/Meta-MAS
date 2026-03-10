from models.dna import AgentDNA
from services.llm_client import LLMService
import re
import asyncio

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
        
        try:
            # Ajout d'un timeout pour éviter que l'agent ne bloque tout le système
            response = await asyncio.wait_for(
                self.llm_service.generate_response(
                    model="MiniMax-M2.5",
                    messages=messages,
                    temperature=self.dna.temperature
                ),
                timeout=120.0  # Timeout individuel par agent
            )
        except asyncio.TimeoutError:
            response = "ERREUR : Timeout de l'agent."
        except Exception as e:
            response = f"ERREUR : {str(e)}"
        
        # Nettoyage systématique des balises <think> si le LLM en a généré
        cleaned_response = re.sub(r"<think>.*?</think>", "", response or "", flags=re.DOTALL).strip()
        
        elapsed_time = time.perf_counter() - start_time
        # Estimation basique des tokens: 1 token ~= 4 caractères
        tokens = len(cleaned_response) // 4 if cleaned_response else 0
        
        return {
            "result": cleaned_response,
            "time": elapsed_time,
            "tokens": tokens
        }
