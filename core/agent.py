# core/agent.py

# Mise en cache de l'encodeur tiktoken pour optimiser les performances
_tiktoken_encoder = None

from models.dna import AgentDNA
from services.llm_client import LLMService
import re
import asyncio


def clean_think_tags(response: str) -> str:
    """
    Nettoie les balises de réflexion de manière robuste.
    Gère les blocs standard <think>...</think> et les balises MiniMax <|im_start|>think.
    """
    if not response:
        return ""
    
    # 1. Supprimer les blocs standard <think>...</think> (y compris mal fermés)
    cleaned = re.sub(r"<think>.*?</think>", "", response, flags=re.DOTALL)
    cleaned = re.sub(r"<think>.*", "", cleaned, flags=re.DOTALL)
    
    # 2. Supprimer les balises MiniMax <|im_start|>think et <|im_end|>
    cleaned = re.sub(r"<\|im_start\|>think.*?<\|im_end\|>", "", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"<\|im_start\|>think.*", "", cleaned, flags=re.DOTALL)
    
    # 3. Supprimer les fermetures orphelines
    cleaned = re.sub(r"</think>\s*", "", cleaned)
    
    return cleaned.strip()


def estimate_tokens(text: str) -> int:
    """
    Estimation réaliste du nombre de tokens.
    Utilise tiktoken si disponible pour plus de précision, sinon utilise
    une approximation hybride selon la longueur du texte.
    
    Args:
        text: Le texte à estimer
        
    Returns:
        Nombre estimé de tokens
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
        # Fallback: approximation hybride selon la longueur du texte
        char_count = len(text)
        if char_count < 20:
            # Pour très courts textes: 1 token ≈ 2-3 caractères
            return max(1, char_count // 3)
        elif char_count < 100:
            # Pour textes moyens: compromis
            return char_count * 3 // 10
        else:
            # Pour longs textes: approximation conservative
            return char_count // 4


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
        
        # Nettoyage robuste des balises de réflexion via fonction unifiée
        cleaned_response = clean_think_tags(response)
        
        elapsed_time = time.perf_counter() - start_time
        # Estimation réaliste des tokens (utilise tiktoken si disponible)
        tokens = estimate_tokens(cleaned_response)
        
        return {
            "result": cleaned_response,
            "time": elapsed_time,
            "tokens": tokens
        }