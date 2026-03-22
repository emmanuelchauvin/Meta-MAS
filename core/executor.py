import asyncio
from core.agent import BaseAgent
from utils.logger import log

async def run_generation(agents: list[BaseAgent], task: str) -> dict[str, dict | None]:
    """
    Exécute une génération d'agents en parallèle avec tolérance aux fautes.
    Un agent défaillant n'affecte pas les autres agents.
    """
    results = {}
    
    async def _safe_run(agent: BaseAgent) -> tuple[str, dict | None]:
        """Exécute un agent en capturant toutes les exceptions possibles."""
        try:
            result = await agent.run(task)
            return str(agent.dna.uid), result
        except asyncio.CancelledError:
            # Ne pas capturer CancelledError - la propagation est volontaire
            raise
        except Exception as e:
            log(f"Agent {agent.dna.uid} a échoué : {e}", category="SANDBOX-ERROR")
            return str(agent.dna.uid), None

    # Utilisation de gather avec return_exceptions=True pour isoler les crashs
    # Cette approche est plus robuste que TaskGroup pour ce cas d'usage
    task_coroutines = [_safe_run(agent) for agent in agents]
    
    # return_exceptions=True retourne les exceptions au lieu de les lever
    # Cela permet à TOUS les agents de terminer même si certains crashent
    outcomes = await asyncio.gather(*task_coroutines, return_exceptions=True)
    
    # Traitement des résultats avec gestion des exceptions retournées
    for outcome in outcomes:
        if isinstance(outcome, Exception):
            # Cas rare: exception non anticipée (hors de notre try/except)
            log(f"Exception inattendue dans gather: {outcome}", category="SYSTEM-ERROR")
            continue
        if isinstance(outcome, tuple):
            uid, result = outcome
            results[uid] = result

    return results