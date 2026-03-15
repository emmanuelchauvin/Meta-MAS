import json
import networkx as nx
import difflib
from typing import Dict, Any, Optional
from models.dna import AgentDNA

class EvolutionGraph:
    def __init__(self):
        self.graph = nx.DiGraph()

    def add_node(self, dna: AgentDNA, fitness: float):
        """Adds a node to the evolution graph representing an AgentDNA and its fitness."""
        node_id = str(dna.uid)
        self.graph.add_node(
            node_id,
            role_prompt=dna.role_prompt,
            fitness=fitness,
            generation=dna.generation
        )
        return node_id

    def add_mutation(self, parent_uid: str, child_dna: AgentDNA, child_fitness: float = 0.0):
        """Adds a directed edge representing a mutation from parent to child."""
        child_id = self.add_node(child_dna, child_fitness)
        self.graph.add_edge(str(parent_uid), child_id, type="mutation")
        return child_id

    def update_fitness(self, uid: str, fitness: float):
        """Updates the fitness of an existing node in the graph."""
        node_id = str(uid)
        if node_id in self.graph:
            self.graph.nodes[node_id]['fitness'] = fitness

    def is_regression(self, new_prompt: str, distance_threshold: float = 0.85) -> bool:
        """
        Checks if the new prompt is too similar to any historical prompt that failed (fitness == 0).
        Returns True if it's a regression, False otherwise.
        """
        for node, data in self.graph.nodes(data=True):
            if data.get('fitness', -1.0) == 0.0:
                past_prompt = data.get('role_prompt', "")
                similarity = difflib.SequenceMatcher(None, past_prompt, new_prompt).ratio()
                if similarity >= distance_threshold:
                    print(f"[Mémoire] Mutation refusée : Ce chemin évolutif a déjà mené à un échec (Fitness 0.0). Régénération...")
                    return True
        return False

    def save_graph(self, filepath: str = "logs/evolution_graph.json"):
        """Saves the graph to a JSON file (node_link_data format)."""
        import os
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        data = nx.node_link_data(self.graph)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"[EvolutionGraph] Graphe sauvegardé dans {filepath} ({self.graph.number_of_nodes()} noeuds, {self.graph.number_of_edges()} arêtes).")
