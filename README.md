# Meta-MAS

Meta-MAS est une architecture expérimentale de Système Multi-Agents (MAS) capable de s'auto-conception et d'évoluer de manière autonome. Construit intégralement en Python natif, le système s'articule autour d'une boucle darwinienne d'amélioration continue des prompts et des stratégies de résolution.

## Introduction

Dans un paradigme classique, les agents IA exécutent des tâches selon des prompts définis statiquement. **Meta-MAS** repense cette approche en dotant le système d'une **conscience d'orchestration**. Le système supervise une population de sous-agents qui tentent de résoudre des benchmarks complexes. À chaque itération, le Meta-MAS évalue les performances et fait évoluer soit les prompts (micro-évolution), soit son propre code source (méta-évolution).

## Innovations Majeures (v22)

Le projet a franchi des jalons critiques dans son autonomie, avec une attention particulière portée à la robustesse du traitement des données et à la précision algorithmique :

1. **Auto-Amélioration Architecturale (v22)** : 
   Le système s'est déjà auto-mis à jour **22 fois** de manière totalement autonome. Chaque version est validée par un tournoi A/B en sandbox, garantissant que seule une amélioration prouvée (fitness, temps ou coût) remplace le code source de production.

2. **Pipeline de Nettoyage Unifié (v16-v21)** :
   La logique de traitement des sorties LLM a été harmonisée. Le système utilise désormais une fonction `clean_think_tags` centralisée et robuste, capable de gérer les balises `<think>` mal fermées et d'éliminer les pensées internes des modèles de raisonnement (R1, o1) avant l'évaluation.

3. **Compatibilité Multi-Modèles Étendue (v20)** :
   Intégration du support natif pour les formats de réflexion spécifiques, notamment le format **MiniMax** (`<|im_start|>think...<|im_end|>`), assurant une compatibilité parfaite avec les derniers modèles de pointe.

4. **Optimisation des Structures de Données (v21)** :
   Le suivi de la stagnation et l'historique des scores ont été migrés vers des structures à complexité constante (**O(1)** via `collections.deque`), optimisant les cycles d'évolution prolongés.

5. **Estimation Hybride du Budget (v22)** :
   Le calcul des tokens (`estimate_tokens`) a été affiné avec un modèle hybride : des coefficients différenciés pour les messages courts, moyens et longs. Cela permet une gestion du budget beaucoup plus fine et évite les erreurs de prédiction sur les réponses concises.

6. **Benchmark de Raisonnement Multi-Dimensionnel** :
   L'environnement d'évaluation repose sur 15 problèmes de logique pure, mathématiques et géométrie. La complexité accrue force le système à faire émerger des stratégies de prompt (Chain-of-Thought) de haut niveau.

7. **Allocation Dynamique et Mode Survie** : 
   La population d'agents s'ajuste dynamiquement en fonction du budget restant et de la vitesse de progrès, avec un "mode survie" automatique si les ressources deviennent critiques.

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
