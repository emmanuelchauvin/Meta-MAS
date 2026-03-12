# Mise en cache de l'encodeur tiktoken pour optimiser les performances
_tiktoken_encoder = None

from models.dna import AgentDNA
from services.llm_client import LLMService
import re
import asyncio

def _clean_think_tags(response: str) -> str:
    """
    Nettoie récursivement les balises <think>...</think> de manière robuste.
    Utilise un traitement itératif pour gérer les cas de balises malformées
    ou imbriquées que le regex simple ne capturerait pas.
    """
    if not response:
        return ""
    
    cleaned = response
    max_iterations = 5  # Limite pour éviter les boucles infinies
    
    for _ in range(max_iterations):
        # Premier passage : nettoyer les balises standard
        prev = cleaned
        cleaned = re.sub(r"<think>.*?</think>", "", prev, flags=re.DOTALL).strip()
        
        # Deuxième passage : nettoyer les balises malformées (sans fermeture)
        cleaned = re.sub(r"<think>.*", "", cleaned, flags=re.DOTALL).strip()
        cleaned = re.sub(r".*</think>", "", cleaned, flags=re.DOTALL).strip()
        
        # Arrêter si plus de changement (convergence)
        if cleaned == prev:
            break
    
    return cleaned


def _estimate_tokens(text: str) -> int:
    """
    Estimation réaliste du nombre de tokens.
    Utilise tiktoken si disponible pour plus de précision, sinon utilise
    une approximation conservative (1 token ≈ 4 caractères) qui fonctionne
    mieux pour les textes mixtes (code + prompts).
    """
    global _tiktoken_encoder
    
    if not text:
        return 0
    
    try:
        import tiktoken
        # Mise en cache de l'encodeur pour éviter de le recharger à chaque appel
        if _tiktoken_encoder is None:
            _tiktoken_encoder = tiktoken.get_encoding("cl100k_base")
        return len(_tiktoken_encoder.encode(text))
    except ImportError:
        # Fallback: approximation conservative pour textes mixtes
        # 1 token ≈ 4 caractères est plus réaliste que 3 pour du code/prompts
        return len(text) // 4


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
        
        # Nettoyage robuste des balises <think> via fonction dédiée
        cleaned_response = _clean_think_tags(response)
        
        elapsed_time = time.perf_counter() - start_time
        # Estimation réaliste des tokens (utilise tiktoken si disponible)
        tokens = _estimate_tokens(cleaned_response)
        
        return {
            "result": cleaned_response,
            "time": elapsed_time,
            "tokens": tokens
        }