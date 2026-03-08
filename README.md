# Meta-MAS

Meta-MAS est une architecture expérimentale de Système Multi-Agents (MAS) capable de s'auto-conception et d'évoluer de manière autonome. Construit intégralement en Python natif, le système s'articule autour d'une boucle darwinienne d'amélioration continue des prompts et des stratégies de résolution.

## Introduction

Dans un paradigme classique, les agents IA exécutent des tâches selon des prompts définis statiquement. **Meta-MAS** repense cette approche en dotant le système d'une **conscience d'orchestration**. Le système supervise une population de sous-agents qui tentent de résoudre des benchmarks complexes. À chaque itération, le Meta-MAS évalue les performances et fait évoluer soit les prompts (micro-évolution), soit son propre code source (méta-évolution).

## Innovations Majeures (v2)

Le projet a atteint des jalons critiques dans son autonomie :

1. **Allocation Dynamique d'Agents** : 
   La population d'agents n'est plus statique. Le système ajuste le nombre d'agents (de 1 à 10) en fonction du **budget restant** et de la **tendance de fitness** (stagnation → exploration accrue, progrès → économie).

2. **Auto-Amélioration Architecturale (Tournoi A/B)** : 
   Toutes les 5 générations, un "Essaim d'Architectes" analyse le code source et propose des modifications. Ces modifications sont testées dans un environnement isolé (Sandbox). Si la version `V_Next` surpasse `V_Current` lors d'un tournoi réel, le code source original est écrasé. **Le système s'est déjà auto-mis à jour vers la v2 pour corriger ses propres bugs.**

3. **Validation Syntaxique et Robustesse** : 
   L'application de code généré par LLM inclut désormais une validation syntaxique (`compile()`) et un mécanisme de **retry par feedback**. Si le LLM produit une erreur de syntaxe, le système lui renvoie l'erreur pour auto-correction immédiate.

4. **Mémoire et Anti-Régression** :
   Utilisation de `NetworkX` pour maintenir un graphe d'évolution (`EvolutionGraph`). Le système compare chaque nouvelle mutation aux échecs passés via `difflib` pour bloquer les régressions avant même l'appel API.

5. **Diagnostic de Précision** :
   Intégration d'un mode `verbose` dans l'évaluation, permettant de voir la réussite ou l'échec pour chaque question individuelle du benchmark, facilitant la compréhension des goulots d'étranglement de raisonnement.

6. **Configuration Centrale (`settings.json`)** :
   Le comportement global du Meta-MAS est entièrement paramétrable sans modifier le code, via le fichier `config/settings.json`. Ce fichier définit les "lois de la physique" du système évolutif :
   - **`simulation`** : Définit la durée (`max_generations`), le `budget` total alloué à l'Essaim, et la fréquence de Méta-Évolution (`meta_evo_interval`).
   - **`fitness`** : Contrôle brutalement la difficulté de la tâche ("Hard Mode"). `time_penalty_factor` et `token_penalty_factor` permettent de sanctionner les agents trop bavards ou trop lents, forçant le darwinisme à privilégier l'efficience temporelle et le coût en tokens.
   - **`swarm`** : Limites de population d'agents (`min_agents`/`max_agents`) alloués dynamiquement selon la tendance, et seuil de `stagnation`.

## Architecture Modulaire

- `core/` : Cœur du système.
  - `meta_mas.py` : L'Orchestrateur (gestion du budget, cycles d'évolution).
  - `self_improvement.py` : Gestionnaire de méta-évolution, sandbox et tournois.
  - `environment.py` : Benchmark logique et calculateur de fitness.
- `versions/` : Historique des mises à jour architecturales et rapports de tournois.
- `logs/` : Graphique d'évolution et traces d'exécution.

## Exécution

```bash
# Installation
pip install -r requirements.txt

# Lancement de l'évolution
python main.py
```

Le système s'arrêtera automatiquement au succès (Fitness ≥ 0.95), à la fin des générations prévues (15+) ou par épuisement du budget.
