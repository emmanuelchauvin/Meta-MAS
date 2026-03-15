import json
import re
import uuid
from dataclasses import replace
from pathlib import Path
from typing import List

from models.dna import AgentDNA
from core.agent import BaseAgent, clean_think_tags
from core.environment import LogicEnvironment
from services.llm_client import LLMService
from core.memory import EvolutionGraph
from utils.logger import log


class MetaMAS:
    def __init__(self, llm_service: LLMService, settings: dict = None, identity_path: str = "config/identity.json"):
        self.llm_service = llm_service
        self.settings = settings or {}
        self.identity_path = Path(identity_path)
        self.memory = EvolutionGraph()
        
        # Load hyperparams from settings
        sim_settings = self.settings.get("simulation", {})
        self.budget = sim_settings.get("initial_budget", 4000.0)
        self.base_cost = 10.0
        self.best_scores_history = []
        self._load_identity()
        
    def _load_identity(self):
        with open(self.identity_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.name = data.get("name", "MetaMAS")
            self.mission = data.get("mission", "")
            self.traits = data.get("traits", [])

    def spawn_generation(self, base_dna: AgentDNA, count: int) -> List[BaseAgent]:
        # --- ALLOCATION DYNAMIQUE ---
        sim_settings = self.settings.get("simulation", {})
        swarm_settings = self.settings.get("swarm", {})
        
        initial_budget = sim_settings.get("initial_budget", 4000.0)
        budget_ratio = max(0.1, self.budget / initial_budget)

        # Facteur tendance basé sur l'historique des scores
        trend_factor = 1.0
        stagnation_limit = swarm_settings.get("stagnation_threshold", 3)
        
        if len(self.best_scores_history) >= stagnation_limit:
            recent = self.best_scores_history[-stagnation_limit:]
            if all(s < self.best_scores_history[0] for s in recent): # v2 fix already here
                trend_factor = 1.5        # +50% : explorer plus largement
            else:                         # progrès
                trend_factor = 0.6        # -40% : économiser

        dynamic_count = int(count * budget_ratio * trend_factor)
        
        # Bornes dynamiques
        min_a = swarm_settings.get("min_agents", 2)
        max_a = swarm_settings.get("max_agents", 10)
        dynamic_count = max(min_a, min(dynamic_count, max_a))

        # Sécurité budget critique
        if self.budget < self.base_cost:
            log("Budget critique. Mode survie : 1 agent.", category="WARNING")
            dynamic_count = 1

        trend_label = "📈 Progrès" if trend_factor < 1 else "📉 Stagnation" if trend_factor > 1 else "➡️ Stable"
        log(f"Budget: {self.budget:.0f} ({budget_ratio*100:.0f}%) | "
              f"Tendance: {trend_label} | Agents: {dynamic_count}", category="Meta-MAS")

        agents = []
        for _ in range(dynamic_count):
            new_dna = replace(base_dna, uid=uuid.uuid4())
            agent = BaseAgent(dna=new_dna, llm_service=self.llm_service)
            agents.append(agent)

        return agents

    async def mutate_dna(self, dna: AgentDNA) -> AgentDNA:
        system_prompt = (
            "Tu es l'Architecte Primordial. Analyse ce prompt d'agent qui a échoué "
            "à une tâche logique comportant 15 problèmes distincts.\n"
            "MISSION : Produis une version améliorée, plus rigoureuse et concise "
            "de ce prompt pour maximiser les chances de réussite.\n"
            "RÈGLE CRITIQUE : Ton nouveau prompt DOIT explicitement mentionner qu'il y a 15 PROBLÈMES à résoudre (Q1 à Q15) "
            "et qu'il faut répondre au format exact 'Qx: [nombre]'."
        )
        base_user_prompt = f"Voici le prompt actuel qui a échoué (Fitness = 0.0) :\n{dna.role_prompt}\n\nGénère uniquement le nouveau prompt, sans aucune introduction, conclusion ou balise de code."

        
        max_retries = 3
        new_role_prompt = dna.role_prompt
        
        for attempt in range(max_retries):
            user_prompt = base_user_prompt
            if attempt > 0:
                user_prompt += "\n\nATTENTION : Tes précédentes propositions étaient trop similaires à des approches ayant déjà échoué. Propose une approche RADICALEMENT DIFFÉRENTE."
                
            # We assume generate_response takes a list of messages
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            response = await self.llm_service.generate_response(
                model="MiniMax-M2.5",
                messages=messages,
                temperature=0.7 + (attempt * 0.1)
            )
            
            if response is not None:
                # Utilisation de la fonction unifiée de nettoyage des balises de réflexion
                cleaned = clean_think_tags(response)
                
                cleaned = cleaned.strip()
                # Also strip markdown code fences if present
                if cleaned.startswith("