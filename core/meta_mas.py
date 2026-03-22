import json
import re
import statistics
import uuid
import asyncio
from dataclasses import replace
from pathlib import Path
from typing import List

from models.dna import AgentDNA
from core.agent import BaseAgent, compute_prompt_fitness
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
        self.failed_questions_history = []  # Historique des questions échouées
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
            # Calcul de variance avec tolérance aux micro-variations
            variance = statistics.variance(recent) if len(recent) > 1 else 0.0
            variance_threshold = 0.0005  # Seuil de variance significatif
            
            if variance < variance_threshold:    # stagnation (scores quasi-identiques)
                trend_factor = 1.5                # +50% : explorer plus largement
            elif recent[-1] > recent[0] + 0.01:   # progrès réel (> 0.01)
                trend_factor = 0.6                # -40% : économiser
            else:
                trend_factor = 1.0                # stable

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

    async def mutate_dna(self, dna: AgentDNA, env: LogicEnvironment = None) -> AgentDNA:
        # Collecter les questions systématiquement échouées
        if env is None:
            env = LogicEnvironment()
            
        failed_questions = []
        expected = env.EXPECTED_ANSWERS
        for q_label in expected.keys():
            # Si cette question a été régulièrement échouée dans l'historique
            if any(q_label in failed_batch for failed_batch in self.failed_questions_history):
                failed_questions.append(q_label)
        
        # Construire le contexte d'erreurs pour le prompt
        error_context = ""
        if failed_questions:
            error_context = f"\n\n--- INFORMATIONS CRITIQUES ---\nCes questions ont été SYSTÉMATIQUEMENT échouées : {', '.join(failed_questions)}.\nLe nouveau prompt doit IMPÉRATIVEMENT trouver une approche DIFFERENTE pour ces questions spécifiques."
        
        system_prompt = (
            "Tu es l'Architecte Primordial. Analyse ce prompt d'agent qui a échoué "
            "à une tâche logique comportant 25 problèmes distincts.\n"
            "MISSION : Produis une version améliorée, plus rigoureuse et concise "
            "de ce prompt pour maximiser les chances de réussite.\n"
            "CONTRAINTES :\n"
            "1. Le prompt doit être en FRANÇAIS.\n"
            "2. DOIT mentionner explicitement les 25 PROBLÈMES (Q1 à Q25).\n"
            "3. DOIT exiger un raisonnement étape par étape (Chain of Thought) avant chaque réponse.\n"
            "4. DOIT exiger le format final 'Qx: [nombre]' pour l'évaluation.\n"
            "5. Supprime les fioritures inutiles (poèmes, etc.) qui gaspillent des tokens."
        )
        base_user_prompt = f"Voici le prompt actuel qui a échoué (Fitness = 0.0) :\n{dna.role_prompt}\n\nGénère uniquement le nouveau prompt, sans aucune introduction, conclusion ou balise de code.{error_context}"

        
        max_parallel = 3
        
        async def attempt_mutation(idx: int) -> str:
            # Calcul de température adaptative
            if len(self.best_scores_history) >= 3:
                recent_scores = self.best_scores_history[-3:]
                std = statistics.stdev(recent_scores) if len(recent_scores) > 1 else 0.0
                base_temp = 0.9 if std < 0.05 else 0.4
            else:
                base_temp = 0.7
            
            curr_temp = min(1.2, base_temp + (idx * 0.1))
            
            msg = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": base_user_prompt + (f"\n\nNote: Variante {idx+1}. Propose une approche originale." if idx > 0 else "")}
            ]
            
            res = await self.llm_service.generate_response(model="MiniMax-M2.5", messages=msg, temperature=curr_temp)
            if not res: return ""
            
            # Nettoyage robuste (identique à agent.py en esprit)
            cl = re.sub(r"^\s*<think>.*?</think>\s*(?:\n|$)", "", res, flags=re.DOTALL)
            if cl.strip().startswith("<think>"):
                m = re.search(r"\n\s*(Tu |Vous |Voici |Le |MISSION)", cl)
                if m: cl = cl[m.start():]
                else: cl = re.sub(r"^\s*<think>\s*", "", cl)
            
            cl = cl.strip()
            if cl.startswith("```"):
                cl = re.sub(r"```\w*\n?", "", cl)
                cl = re.sub(r"```$", "", cl.strip()).strip()
            
            return cl

        log(f"Lancement de {max_parallel} tentatives de mutation en parallèle...", category="Meta-MAS")
        tasks = [attempt_mutation(i) for i in range(max_parallel)]
        mutated_prompts = await asyncio.gather(*tasks)
        
        # --- Sélection par Fitness Structurelle (v38+) ---
        candidates = [c for c in mutated_prompts if c and not self.memory.is_regression(c)]
        
        final_prompt = dna.role_prompt
        if candidates:
            # On choisit le mutant qui a la meilleure structure (instructions, exemples, longueur)
            candidates.sort(key=lambda p: compute_prompt_fitness(p, dna.role_prompt), reverse=True)
            final_prompt = candidates[0]
            score_struct = compute_prompt_fitness(final_prompt, dna.role_prompt)
            log(f"Meilleure mutation sélectionnée (Qualité Structurelle: {score_struct:.2f})", category="Meta-MAS")
        else:
            # Fallback si toutes sont des régressions ou vides
            for candidate in mutated_prompts:
                 if candidate: 
                     final_prompt = candidate
                     break

        new_dna = replace(
            dna,
            uid=uuid.uuid4(),
            generation=dna.generation + 1,
            role_prompt=final_prompt
        )
        
        self.memory.add_mutation(str(dna.uid), new_dna)
        return new_dna
        
    async def evolve(self, generation_results: dict[str, dict | None], current_dna: AgentDNA) -> AgentDNA:
        env = LogicEnvironment()
        
        best_score = -1.0
        best_agent_id = None
        best_response = None
        
        # Deduct the base cost of running a generation
        self.budget -= self.base_cost
        
        # --- Évaluation Parallèle (v37) ---
        agent_items = list(generation_results.items())
        
        async def eval_one(agent_id, res_dict):
            if res_dict is None: return agent_id, 0.0, None
            score = await env.evaluate(res_dict)
            return agent_id, score, res_dict

        eval_tasks = [eval_one(aid, rd) for aid, rd in agent_items]
        evaluated_results = await asyncio.gather(*eval_tasks)

        for agent_id, score, result_dict in evaluated_results:
            if result_dict:
                # Déduction des coûts (Time & Tokens)
                time_cost = result_dict.get("time", 0.0) * 0.005
                token_cost = result_dict.get("tokens", 0) * 0.0001
                self.budget -= (time_cost + token_cost)
                
            if score > best_score:
                best_score = score
                best_agent_id = agent_id
                best_response = result_dict
        
        # Collecter les questions échouées pour l'historique
        if best_response is not None:
            agent_response = best_response.get("result", "")
            current_failed = []
            for q_label, expected in env.EXPECTED_ANSWERS.items():
                pattern = rf"{q_label}\s*:\s*{re.escape(expected)}\b"
                if not re.search(pattern, agent_response):
                    current_failed.append(q_label)
            
            if current_failed:
                self.failed_questions_history.append(set(current_failed))
                # Garder seulement les 3 derniers historiques
                if len(self.failed_questions_history) > 3:
                    self.failed_questions_history.pop(0)
        
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
            self.failed_questions_history.clear()  # Reset aussi l'historique des erreurs
            
        # For our simple loop, if any agent achieves close to perfect score, we return it.
        # Since fitness can be lower than 1.0 due to time/token penalties, we use a generous threshold.
        fitness_settings = self.settings.get("fitness", {})
        success_threshold = fitness_settings.get("success_threshold", 0.95)
        
        if best_score >= success_threshold:
            return current_dna
            
        # If no one succeeded, we mutate the DNA to create the next generation
        log(f"Meilleur score: {best_score:.3f}. Mutation en cours de l'ADN...", category="Meta-MAS")
        new_dna = await self.mutate_dna(current_dna, env)
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
                # Strip <think> blocks cleanly
                cleaned_response = re.sub(r"^\s*<think>.*?</think>\s*(?:\n|$)", "", response, flags=re.DOTALL)
                
                # If LLM didn't close <think>, just extract what looks like a JSON array.
                # Find the first opening bracket that could be an array.
                if cleaned_response.strip().startswith("<think>"):
                   match = re.search(r"\[", cleaned_response)
                   if match:
                       cleaned_response = cleaned_response[match.start():]
                   else:
                       cleaned_response = re.sub(r"^\s*<think>\s*", "", cleaned_response)
                
                cleaned_response = cleaned_response.strip()
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