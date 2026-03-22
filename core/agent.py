# core/agent.py
# IMPORTANT : Ne JAMAIS importer 'core.agent' dans ce fichier (Import Circulaire).
# Ces fonctions sont EXPORTÉES pour meta_mas.py.

__all__ = ["BaseAgent", "compute_prompt_fitness", "estimate_tokens", "clean_think_tags", "analyze_task_context"]

import re
import asyncio
from typing import Optional

_tiktoken_encoder = None
_tiktoken_init_failed = False

from models.dna import AgentDNA
from services.llm_client import LLMService


# Regex compilée une seule fois pour toutes les passes de nettoyage
_CLEAN_THINK_PATTERN = re.compile(
    r"<\|im_start\|>think.*?<\|im_end\|>"
    r"|<\|im_start\|>think.*"
    r"|<thought>.*?</thought>"
    r"|<thinking>.*?</thinking>"
    r"|<reasoning>.*?</reasoning>"
    r"|<context>.*?</context>",
    flags=re.DOTALL
)

# Patterns pour rétrocompatibilité et cas supplémentaires (appliqués après le nettoyage principal)
_SECONDARY_CLEAN_PATTERNS = [
    (re.compile(r"^\s*<think>\s*", flags=re.MULTILINE), ""),
    (re.compile(r"^\s*$", flags=re.MULTILINE), ""),
    (re.compile(r"^\s*\n\n", flags=re.MULTILINE), ""),
]

# Patterns pour détection précoce d'échec (early exit) - PRÉ-COMPILÉS pour performance
_FAILURE_INDICATORS = [
    re.compile(r"je\s+(ne\s+)?peux?\s+pas", re.IGNORECASE),
    re.compile(r"impossible", re.IGNORECASE),
    re.compile(r"je\s+ne\s+sais\s+pas", re.IGNORECASE),
    re.compile(r"unable\s+to", re.IGNORECASE),
    re.compile(r"cannot\s+be\s+solved", re.IGNORECASE),
    re.compile(r"erreur", re.IGNORECASE),
]

# Patterns pour évaluer la structure qualité d'un prompt (utilisé par le système d'évolution)
_QUALITY_PATTERNS = {
    "instructions": re.compile(r"(?:instruction|déterminer|analyser|évaluer|procédure|étape)", re.IGNORECASE),
    "examples": re.compile(r"(?:exemple|par exemple|comme|cas\s+(?:de|où)|tel\s+que)", re.IGNORECASE),
    "structure_markers": re.compile(r"(?:1\.|2\.|a\)|b\)|•|\-|\*)", re.IGNORECASE),
}

# Patterns pour l'analyse contextuelle des tâches
_TASK_CONTEXT_PATTERNS = {
    "debug": re.compile(r"(?:debug|débogage|bug|erreur|exception|crash|plantage|résoudre)", re.IGNORECASE),
    "code": re.compile(r"(?:code|programm|script|fonction|class|implément|écrire\s+du|générer\s+du)", re.IGNORECASE),
    "analyze": re.compile(r"(?:analys|évalue|examin|étudi|comprend|expliqu|pourquoi|comment\s+cela)", re.IGNORECASE),
    "creative": re.compile(r"(?:créative|invente|story|raconter|écris\s+une|romans|poème|imaginer)", re.IGNORECASE),
    "review": re.compile(r"(?:revue|review|check|valid|test|qualité|améliorer|optimiser)", re.IGNORECASE),
    "data": re.compile(r"(?:data|données|tableau|stats|calcul|chiffre|nom\s+NOMBRE|quantité)", re.IGNORECASE),
}

# Poids par défaut pour le calcul de fitness (équilibré pour tâches générales)
_DEFAULT_FITNESS_WEIGHTS = {
    "instructions": 0.30,
    "examples": 0.25,
    "structure": 0.15,
    "length": 0.20,
    "similarity": 0.10
}


def clean_think_tags(response: str) -> str:
    """
    Nettoie les balises de réflexion de manière robuste et optimisée.
    Une seule passe de regex pour tous les cas courants, puis nettoyage secondaire.
    """
    if not response:
        return ""
    
    # Première passe : nettoyage principal avec regex compilée
    cleaned = _CLEAN_THINK_PATTERN.sub("", response)
    
    # Deuxième passe : nettoyage des cas résiduels
    for pattern, replacement in _SECONDARY_CLEAN_PATTERNS:
        cleaned = pattern.sub(replacement, cleaned)
    
    return cleaned.strip()


def analyze_task_context(task: str) -> dict:
    """
    Analyse le contexte d'une tâche pour adapter les critères de fitness.
    
    Cette fonction détecte le type de tâche (debug, code, analyse, créatif, etc.)
    et retourne les poids recommandés pour chaque critère de fitness.
    
    Types de tâches détectés:
    - "debug": Tâches de débogage/résolution de problèmes
    - "code": Tâches de génération de code
    - "analyze": Tâches d'analyse/explication
    - "creative": Tâches créatives (rédaction, storytelling)
    - "review": Tâches de revue/validation
    - "data": Tâches impliquant des données/calculs
    
    Args:
        task: La description de la tâche à analyser
        
    Returns:
        Dictionary avec:
        - "task_type": Le type principal de tâche détecté ("general" par défaut)
        - "weights": Dictionnaire des poids pour chaque critère
        - "confidence": Niveau de confiance de la détection (0.0-1.0)
    """
    if not task or len(task.strip()) < 5:
        return {
            "task_type": "general",
            "weights": _DEFAULT_FITNESS_WEIGHTS.copy(),
            "confidence": 0.0
        }
    
    # Compter les correspondances pour chaque type de tâche
    task_lower = task.lower()
    scores = {}
    
    for task_type, pattern in _TASK_CONTEXT_PATTERNS.items():
        match = pattern.search(task_lower)
        scores[task_type] = len(match.group()) if match else 0
    
    # Trouver le type de tâche avec le meilleur score
    max_score = max(scores.values())
    
    if max_score == 0:
        task_type = "general"
        confidence = 0.1
    else:
        task_type = max(scores, key=scores.get)
        # Confidence basée sur la différence avec le deuxième meilleur score
        sorted_scores = sorted(scores.values(), reverse=True)
        if len(sorted_scores) > 1:
            confidence = min(1.0, 0.5 + (sorted_scores[0] - sorted_scores[1]) / 20)
        else:
            confidence = 0.7
    
    # Définir les poids selon le type de tâche
    # Chaque type de tâche privilégie certains critères de qualité
    weights_by_type = {
        "debug": {
            # Pour le debug, les instructions structurées et les étapes sont cruciales
            "instructions": 0.40,
            "examples": 0.15,
            "structure": 0.20,
            "length": 0.15,
            "similarity": 0.10
        },
        "code": {
            # Pour le code, les exemples et la structure sont importants
            "instructions": 0.25,
            "examples": 0.30,
            "structure": 0.20,
            "length": 0.15,
            "similarity": 0.10
        },
        "analyze": {
            # Pour l'analyse, les instructions et les exemples sont clés
            "instructions": 0.35,
            "examples": 0.25,
            "structure": 0.15,
            "length": 0.15,
            "similarity": 0.10
        },
        "creative": {
            # Pour le créatif, moins de structure stricte, plus de liberté
            "instructions": 0.20,
            "examples": 0.20,
            "structure": 0.10,
            "length": 0.30,
            "similarity": 0.20
        },
        "review": {
            # Pour la revue, structure et exemples sont importants
            "instructions": 0.30,
            "examples": 0.25,
            "structure": 0.20,
            "length": 0.15,
            "similarity": 0.10
        },
        "data": {
            # Pour les données, précision et structure
            "instructions": 0.35,
            "examples": 0.20,
            "structure": 0.20,
            "length": 0.15,
            "similarity": 0.10
        },
        "general": _DEFAULT_FITNESS_WEIGHTS.copy()
    }
    
    return {
        "task_type": task_type,
        "weights": weights_by_type.get(task_type, weights_by_type["general"]),
        "confidence": confidence
    }


def compute_prompt_fitness(prompt: str, reference: str = "", weights: Optional[dict] = None, task: Optional[str] = None) -> float:
    """
    Calcule un score de qualité structurelle pour un prompt muté.
    
    Cette fonction évalue la qualité intrinsèque d'un prompt muté en analysant
    sa structure plutôt que son contenu sémantique. Elle est utilisée par le
    système d'évolution (Meta-MAS) pour sélectionner les meilleures mutations.
    
    Critères de scoring (pondération adaptative selon le contexte):
    - Présence d'instructions explicites (bonus important)
    - Présence d'exemples (bonus moyen)
    - Structure claire avec marqueurs (bonus léger)
    - Longueur suffisante (indicateur de détail)
    - Similarité lexicale avec le parent (évite les mutations trop extrêmes)
    
    IMPORTANT: Si le paramètre 'task' est fourni, les poids seront automatiquement
    adaptés au type de tâche détecté (debug, code, créatif, etc.). Vous pouvez
    également fournir des poids explicites via le paramètre 'weights'.
    
    Args:
        prompt: Le prompt muté à évaluer
        reference: Optionnel, le prompt parent pour calculer la similarité lexicale
        weights: Optionnel, dictionnaire des poids pour chaque critère de fitness.
                 Si non fourni, utilise les poids du contexte de tâche (si disponible)
                 ou les poids par défaut (compatibilité).
                 Les clés attendues sont: "instructions", "examples", "structure",
                 "length", "similarity"
        task: Optionnel, la description de la tâche pour adapter automatiquement
              les poids au contexte. Si 'weights' est fourni, ce paramètre est ignoré.
        
    Returns:
        Score de fitness entre 0.0 et 1.0 (1.0 = qualité optimale)
    """
    if not prompt or len(prompt.strip()) < 10:
        return 0.0
    
    # Déterminer les poids effectifs selon la priorité: weights explicites > task > défaut
    effective_weights = weights
    if weights is None:
        if task:
            # Analyser le contexte de la tâche pour adapter les poids automatiquement
            # Cette intégration permet au système d'évolution d'être contextuellement intelligent
            task_context = analyze_task_context(task)
            effective_weights = task_context["weights"]
        else:
            effective_weights = _DEFAULT_FITNESS_WEIGHTS.copy()
    
    # S'assurer que toutes les clés de poids existent (robustesse)
    for key in ["instructions", "examples", "structure", "length", "similarity"]:
        if key not in effective_weights:
            effective_weights[key] = 0.15  # Valeur par défaut équilibrée
    
    score = 0.0
    
    # 1. Présence d'instructions explicites
    # Les prompts avec des verbes d'action sont généralement plus efficaces
    has_instructions = _QUALITY_PATTERNS["instructions"].search(prompt)
    score += effective_weights["instructions"] if has_instructions else 0.0
    
    # 2. Présence d'exemples
    # Les exemples améliorent significativement la qualité des réponses
    has_examples = _QUALITY_PATTERNS["examples"].search(prompt)
    score += effective_weights["examples"] if has_examples else 0.0
    
    # 3. Structure claire avec marqueurs
    # Les listes et structures numérotées indiquent un prompt bien organisé
    has_structure = _QUALITY_PATTERNS["structure_markers"].search(prompt)
    score += effective_weights["structure"] if has_structure else 0.0
    
    # 4. Longueur suffisante
    # Les prompts trop courts manquent généralement de contexte
    prompt_length = len(prompt)
    if prompt_length >= 200:
        score += effective_weights["length"]
    elif prompt_length >= 100:
        score += effective_weights["length"] * 0.5
    elif prompt_length >= 50:
        score += effective_weights["length"] * 0.25
    
    # 5. Similarité lexicale avec le parent
    # Évite les mutations trop extrêmes qui perdent le contexte original
    if reference:
        parent_words = set(reference.lower().split())
        prompt_words = set(prompt.lower().split())
        
        if len(parent_words) > 0:
            overlap = len(parent_words & prompt_words) / len(parent_words)
            # On pénalise si le overlap est trop faible (< 20%) ou trop élevé (< 10%)
            # Le "sweet spot" est entre 30% et 70% de similarité
            if 0.3 <= overlap <= 0.7:
                score += effective_weights["similarity"]
            elif 0.1 <= overlap < 0.3 or 0.7 < overlap <= 0.9:
                score += effective_weights["similarity"] * 0.5
    
    return min(1.0, score)


def estimate_tokens(text: str) -> int:
    """
    Estimation réaliste du nombre de tokens.
    Utilise tiktoken si disponible pour plus de précision, sinon utilise
    une approximation hybride tenant compte de la distribution des mots.
    
    Args:
        text: Le texte à estimer
        
    Returns:
        Nombre estimé de tokens
    """
    global _tiktoken_encoder, _tiktoken_init_failed
    
    if not text:
        return 0
    
    # Si tiktoken a déjà échoué, ne pas réessayer
    if not _tiktoken_init_failed and _tiktoken_encoder is None:
        try:
            import tiktoken
            _tiktoken_encoder = tiktoken.get_encoding("cl100k_base")
        except (ImportError, Exception):
            _tiktoken_init_failed = True
    
    if _tiktoken_encoder is not None:
        try:
            return len(_tiktoken_encoder.encode(text))
        except Exception:
            # Si l'encodage échoue, fallback sur l'approximation
            pass
    
    # Fallback: approximation hybride avec distribution des mots
    # Pour le français et les textes techniques: ~0.65 tokens par mot en moyenne
    # Plus conservateur: 0.75 tokens par mot + compensation pour caractères spéciaux
    char_count = len(text)
    word_count = len(text.split())
    
    # Estimation basée sur les mots (plus précis pour le texte naturel)
    word_based = int(word_count * 0.75)
    
    # Estimation basée sur les caractères (plus précis pour les mots techniques)
    char_based = char_count // 4
    
    # Prendre la moyenne pondérée (favorise légèrement les mots pour le français)
    return max(1, int(word_based * 0.6 + char_based * 0.4))


def _detect_failure_indicators(task: str) -> bool:
    """Détecte si le task contient des indicateurs d'échec probable."""
    for pattern in _FAILURE_INDICATORS:
        if pattern.search(task):
            return True
    return False


class BaseAgent:
    def __init__(self, dna: AgentDNA, llm_service: LLMService, model_name: str = "MiniMax-M2.5"):
        self.dna = dna
        self.llm_service = llm_service
        self.model_name = model_name

    def _compute_adaptive_timeout(self, stagnation_count: int = 0, 
                                   previous_attempts: int = 0) -> float:
        """
        Calcule un timeout adaptatif basé sur le contexte d'exécution.
        
        Args:
            stagnation_count: Nombre de générations consécutives sans improvement
            previous_attempts: Nombre de tentatives précédentes pour cette tâche
            
        Returns:
            Timeout en secondes (entre 30 et 180)
        """
        BASE_TIMEOUT = 180.0
        MIN_TIMEOUT = 30.0
        
        # Facteur de réduction basé sur la stagnation
        # Après 3 stagnations consécutives, le timeout diminue progressivement
        stagnation_factor = max(0.3, 1.0 - (stagnation_count * 0.15))
        
        # Facteur basé sur les tentatives précédentes
        # Chaque tentative infructueuse réduit légèrement le timeout
        attempt_factor = max(0.5, 1.0 - (previous_attempts * 0.1))
        
        # Facteur basé sur la température (températures élevées = plus de variabilité = timeout plus long)
        # Température normale: 0.7, explorative: 1.0+
        temp_factor = max(0.8, min(1.3, self.dna.temperature / 0.7))
        
        # Calcul du timeout final
        adaptive_timeout = BASE_TIMEOUT * stagnation_factor * attempt_factor * temp_factor
        
        return max(MIN_TIMEOUT, min(BASE_TIMEOUT, adaptive_timeout))

    async def run(self, task: str, stagnation_count: int = 0,
                  previous_attempts: int = 0) -> dict:
        import time
        start_time = time.perf_counter()
        
        # Détection précoce d'échec potentiel (early exit)
        # Si le task contient des indicateurs de problème, on utilise un timeout réduit
        has_failure_indicators = _detect_failure_indicators(task)
        
        # Calcul du timeout adaptatif
        adaptive_timeout = self._compute_adaptive_timeout(
            stagnation_count=stagnation_count,
            previous_attempts=previous_attempts
        )
        
        # Réduction supplémentaire si indicateurs d'échec détectés
        if has_failure_indicators:
            adaptive_timeout = max(30.0, adaptive_timeout * 0.6)
        
        messages = [
            {"role": "system", "content": self.dna.role_prompt},
            {"role": "user", "content": task}
        ]
        
        try:
            # Timeout adaptatif basé sur le contexte d'exécution
            response = await asyncio.wait_for(
                self.llm_service.generate_response(
                    model=self.model_name,
                    messages=messages,
                    temperature=self.dna.temperature
                ),
                timeout=adaptive_timeout
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
            "tokens": tokens,
            "timeout_used": adaptive_timeout  # Debug info
        }