# core/utils.py

import re


def strip_think_tags(text: str) -> str:
    """
    Nettoie tous les types de balises de reflection de maniere robuste.
    Gere les blocs standard <think>...</think> et les balises MiniMax.
    """
    if not text:
        return ""
    
    # 1. Supprimer les blocs standard <think>...</think> (inclusifs et non-gourmands)
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    cleaned = re.sub(r"<think>.*", "", cleaned, flags=re.DOTALL)
    
    # 2. Supprimer les balises MiniMax <|im_start|>think et <|im_end|>
    cleaned = re.sub(r"<\|im_start\|>think.*?<\|im_end\|>", "", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"<\|im_start\|>think.*", "", cleaned, flags=re.DOTALL)
    
    # 3. Supprimer les fermetures orphelines
    cleaned = re.sub(r"</think>\s*", "", cleaned)
    
    return cleaned.strip()


def clean_llm_response(response: str) -> str:
    """
    Nettoie completement une reponse LLM de tous les artefacts.
    Combine le stripping des balises de reflexion et la suppression
    des fences markdown.
    """
    # Strip think tags
    cleaned = strip_think_tags(response)
    
    # Remove markdown code fences
    cleaned = re.sub(r"^