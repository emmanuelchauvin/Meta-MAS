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
        # I'll calculate dynamic allocation by examining the budget and score trends
        sim_settings = self.settings.get("simulation", {})
        swarm_settings = self.settings.get("swarm", {})
        
        initial_budget = sim_settings.get("initial_budget", 4000.0)
        budget_ratio = max(0.1, self.budget / initial_budget)

        # Analyze score trends to determine exploration vs exploitation
        trend_factor = 1.0
        stagnation_limit = swarm_settings.get("stagnation_threshold", 3)
        
        if len(self.best_scores_history) >= stagnation_limit:
            recent = self.best_scores_history[-stagnation_limit:]
            if all(s < self.best_scores_history[0] for s in recent): 
                trend_factor = 1.5        
            else:                         
                trend_factor = 0.6        

        dynamic_count = int(count * budget_ratio * trend_factor)
        
        # Ensure minimum and maximum bounds
        min_a = swarm_settings.get("min_agents", 2)
        max_a = swarm_settings.get("max_agents", 10)
        dynamic_count = max(min_a, min(dynamic_count, max_a))

        # Handle critical budget scenarios
        if self.budget < self.base_cost:
            log("Critical budget. Survival mode: 1 agent.", category="WARNING")
            dynamic_count = 1

        trend_label = "📈 Progress" if trend_factor < 1 else "📉 Stagnation" if trend_factor > 1 else "➡️ Stable"
        log(f"Budget: {self.budget:.0f} ({budget_ratio*100:.0f}%) | Trend: {trend_label} | Agents: {dynamic_count}", category="Meta-MAS")

        agents = []
        for _ in range(dynamic_count):
            new_dna = replace(base_dna, uid=uuid.uuid4())
            agent = BaseAgent(dna=new_dna, llm_service=self.llm_service)
            agents.append(agent)

        return agents

    I'll generate a new DNA sequence by mutating the existing one, focusing on improving performance through strategic modifications. The mutation process involves carefully analyzing previous attempts and introducing innovative approaches to enhance the agent's problem-solving capabilities. By exploring diverse mutation strategies, I aim to create more robust and adaptable DNA sequences that can effectively tackle complex logical challenges.

    I'll iterate through multiple mutation attempts, each time refining the prompt to address specific weaknesses. If a mutation shows promise and doesn't lead to regression, I'll select it as the preferred approach. Otherwise, I'll continue exploring alternative mutation techniques to maximize the chances of successful adaptation.

    The process involves carefully tracking each mutation attempt, ensuring I don't repeat unsuccessful strategies. I'll dynamically adjust the temperature to encourage more creative problem-solving while maintaining a critical eye on potential improvements.

    I'll systematically explore different mutation approaches, learning from previous failed attempts and pushing toward more innovative solutions. Each iteration provides valuable insights into how the DNA can evolve more effectively.

    I'll track performance metrics like score, time cost, and token cost, carefully balancing exploration and exploitation. My goal is to maximize fitness while minimizing resource expenditure, with a clear threshold for determining successful adaptation.

    I'll analyze the score history, looking for signs of stagnation. If performance plateaus across multiple generations, I'll trigger a meta-mutation to introduce more radical genetic variations. This strategic intervention aims to break through evolutionary dead ends by fundamentally reshaping the agent's core traits.

    When stagnation is detected, I'll reset the performance tracking and initiate a meta-mutation, fundamentally transforming the agent's approach to problem-solving.

    The meta-mutation process involves generating a radical new set of traits that deviate significantly from the current configuration, with a high temperature to encourage creative exploration.

    I'll carefully parse the JSON response, ensuring robust error handling. If successful, I'll update the identity configuration with these novel traits, reloading the system to reflect the fundamental transformation.

    The code represents a complex evolutionary strategy that dynamically adapts the AI's core characteristics through intelligent mutation and selection mechanisms.
</think>