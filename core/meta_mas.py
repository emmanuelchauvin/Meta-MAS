import json
import re
import uuid
from dataclasses import replace
from pathlib import Path
from typing import List

from models.dna import AgentDNA
from core.agent import BaseAgent
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
                # Strip <think>...</think> blocks from the response
                cleaned = re.sub(r"<think>.*?</think>", "", response, flags=re.DOTALL).strip()
                # Also strip markdown code fences if present
                if cleaned.startswith("```"):
                    cleaned = re.sub(r"```\w*\n?", "", cleaned).strip()
                new_role_prompt = cleaned if cleaned else dna.role_prompt
                
            if not self.memory.is_regression(new_role_prompt):
                break
            log(f"Tentative de mutation {attempt+1}/{max_retries} rejetée : régression détectée (RETRY).", category="Meta-MAS")

            
        new_dna = replace(
            dna,
            uid=uuid.uuid4(),
            generation=dna.generation + 1,
            role_prompt=new_role_prompt
        )
        
        self.memory.add_mutation(str(dna.uid), new_dna)
        return new_dna
        
    async def evolve(self, generation_results: dict[str, dict | None], current_dna: AgentDNA) -> AgentDNA:
        env = LogicEnvironment()
        
        best_score = -1.0
        best_agent_id = None
        
        # Deduct the base cost of running a generation
        self.budget -= self.base_cost
        
        for agent_id, result_dict in generation_results.items():
            if result_dict is None:
                score = 0.0
            else:
                score = await env.evaluate(result_dict)
                # Deduct dynamic cost based on actual execution time and tokens
                time_cost = result_dict.get("time", 0.0) * 0.005
                token_cost = result_dict.get("tokens", 0) * 0.0001
                self.budget -= (time_cost + token_cost)
                
            if score > best_score:
                best_score = score
                best_agent_id = agent_id
                
        self.memory.add_node(current_dna, best_score)
        
        # Tracking stagnation
        self.best_scores_history.append(best_score)
        if len(self.best_scores_history) > 3:
            self.best_scores_history.pop(0)
            
        # If we have 3 scores and they haven't improved (all equal to the first one)
        if len(self.best_scores_history) == 3 and all(s <= self.best_scores_history[0] for s in self.best_scores_history):
            log("Stagnation détectée sur 3 générations ! Déclenchement de la Méta-Mutation...", category="Meta-MAS")
            await self.meta_mutation()
            self.best_scores_history.clear()
            
        # For our simple loop, if any agent achieves close to perfect score, we return it.
        # Since fitness can be lower than 1.0 due to time/token penalties, we use a generous threshold.
        fitness_settings = self.settings.get("fitness", {})
        success_threshold = fitness_settings.get("success_threshold", 0.95)
        
        if best_score >= success_threshold:
            return current_dna
            
        # If no one succeeded, we mutate the DNA to create the next generation
        log(f"Meilleur score: {best_score:.3f}. Mutation en cours de l'ADN...", category="Meta-MAS")
        new_dna = await self.mutate_dna(current_dna)
        return new_dna

    async def meta_mutation(self) -> None:
        """
        Méta-mutation : le système modifie ses propres traits/règles internes 
        en cas de stagnation prolongée.
        """
        system_prompt = (
            "Tu es le Meta-MAS, un système d'évolution consciente. Tu as stagné en essayant de faire "
            "évoluer tes sous-agents. Tu dois réécrire ton propre fichier d'identité ('traits') "
            "pour renouveler radicalement ton approche de sélection et de mutation."
        )
        user_prompt = f"Voici ton identité actuelle :\n{json.dumps({'traits': self.traits}, indent=2, ensure_ascii=False)}\n\nGénère uniquement un nouveau tableau JSON pur de 3 ou 4 traits radicalement différents (ex: ['chaotique', 'strict', 'minimaliste'])."
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = await self.llm_service.generate_response(
            model="MiniMax-M2.5",
            messages=messages,
            temperature=0.9 # High temperature for radical changes
        )
        
        if response:
            try:
                # Strip <think> blocks first
                cleaned_response = re.sub(r"<think>.*?</think>", "", response, flags=re.DOTALL).strip()
                # Remove markdown code fences
                cleaned_response = re.sub(r"```json\s*", "", cleaned_response)
                cleaned_response = re.sub(r"```\s*", "", cleaned_response)
                # Try to find a JSON array in the response
                match = re.search(r'(\[.*?\])', cleaned_response, re.DOTALL)
                if match:
                    new_traits = json.loads(match.group(1))
                else:
                    new_traits = json.loads(cleaned_response)
                
                if isinstance(new_traits, list):
                    # Save back to identity.json
                    with open(self.identity_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        
                    data["traits"] = new_traits
                    
                    with open(self.identity_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=4, ensure_ascii=False)
                        
                    log(f"*** MÉTA-MUTATION ! Nouveaux traits adoptés : {new_traits} ***", category="Meta-MAS")
                    self._load_identity()  # Reload
                    return
            except json.JSONDecodeError as e:
                log(f"Échec de la méta-mutation (parse error) : {e}", category="ERROR")
                
        log("La méta-mutation n'a pas produit de changement valide.", category="Meta-MAS")

