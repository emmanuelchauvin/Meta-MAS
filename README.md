# Meta-MAS

Meta-MAS est une architecture expérimentale de Système Multi-Agents (MAS) capable de s'auto-conception et d'évoluer de manière autonome. Construit intégralement en Python natif, le système s'articule autour d'une boucle darwinienne d'amélioration continue des prompts et des stratégies de résolution.

## Introduction

Dans un paradigme classique, les agents IA exécutent des tâches selon des prompts définis statiquement. **Meta-MAS** repense cette approche en dotant le système d'une **conscience d'orchestration**. Le système supervise une population de sous-agents qui tentent de résoudre des benchmarks complexes. À chaque itération, le Meta-MAS évalue les performances et fait évoluer soit les prompts (micro-évolution), soit son propre code source (méta-évolution).

## Innovations Majeures (v13)

Le projet a atteint des jalons critiques dans son autonomie et son efficacité :

1. **Auto-Amélioration Architecturale Continue (Tournoi A/B)** : 
   Toutes les 5 générations, un "Essaim d'Architectes" analyse le code source et propose des modifications. Ces modifications sont testées dans un environnement isolé (Sandbox). Si la version `V_Next` surpasse `V_Current` lors d'un tournoi réel, le code source original est écrasé. **Le système s'est déjà auto-mis à jour 13 fois pour corriger ses propres bugs et optimiser ses performances.**

2. **Benchmark de Raisonnement Avancé (15 Questions)** :
   L'environnement d'évaluation a été musclé pour passer de 5 à **15 problèmes de logique et de mathématiques** (casse-têtes temporels, probabilités, géométrie). Cette complexité accrue force le système à développer des stratégies de prompt (Chain-of-Thought) plus sophistiquées.

3. **Optimisation des Performances (Caching Tiktoken)** :
   Pour accélérer les cycles d'évaluation, le calcul des tokens utilise désormais une mise en cache globale de l'encodeur `tiktoken` (modèle `cl100k_base`), réduisant drastiquement le temps de chargement lors des mutations d'agents.

4. **Nettoyage Robuste des Pensées (Think Tags)** :
   Un mécanisme de regex optimisé permet de purifier les réponses des agents des balises `<think>...</think>` générées par les modèles de type raisonnement (R1/O1), évitant que la "réflexion" interne ne pollue le format de réponse attendu.

5. **Validation Syntaxique et Sémantique (Robustesse)** : 
   L'application de code généré par LLM inclut une validation syntaxique (`compile()`) complète. S'ajoute à cela une **validation sémantique** stricte. En cas d'erreur, le système déclenche un mécanisme de **retry par feedback** en renvoyant l'erreur au LLM.

6. **Allocation Dynamique d'Agents** : 
   La population d'agents s'ajuste dynamiquement (de 2 à 20) en fonction du **budget restant** et de la **tendance de fitness** (stagnation → exploration accrue, progrès → économie).

7. **Configuration Centrale (`settings.json`)** :
   Le comportement global est paramétrable via `config/settings.json`, définissant les "lois de la physique" du système : pénalités de temps/tokens, seuils de succès (0.95 fitness), et intervalles de méta-évolution.

## Architecture Modulaire

- `core/` : Cœur du système.
  - `meta_mas.py` : L'Orchestrateur (gestion du budget, cycles d'évolution).
  - `agent.py` : Définition des agents et leur logique d'exécution.
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

Le système s'arrêtera automatiquement au succès (Fitness ≥ 0.95), à la fin des générations prévues ou par épuisement du budget.
