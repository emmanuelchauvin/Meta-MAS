# Meta-MAS

Meta-MAS est une architecture expérimentale de Système Multi-Agents (MAS) capable de s'auto-conception et d'évoluer de manière autonome. Construit intégralement en Python natif, le système s'articule autour d'une boucle darwinienne d'amélioration continue des prompts et des stratégies de résolution.

## Introduction

Dans un paradigme classique, les agents IA exécutent des tâches selon des prompts définis statiquement. **Meta-MAS** repense cette approche en dotant le système d'une **conscience d'orchestration**. Le système supervise une population de sous-agents qui tentent de résoudre des benchmarks complexes. À chaque itération, le Meta-MAS évalue les performances et fait évoluer soit les prompts (micro-évolution), soit son propre code source (méta-évolution).

## Innovations Majeures (v27)

Le projet franchit une étape critique de robustesse et de passage à l'échelle (scaling) :

1. **Stabilité des Mutations (v27)** :
   Implémentation de protocoles de sécurité logicielle interdisant les erreurs de syntaxe lors de l'auto-mutation. Le système auto-valide désormais la fermeture des chaînes de caractères et la complétude du code généré.

2. **Benchmark 25 - Pilotage par Objectifs** :
   Le moteur d'évolution a été reprogrammé pour cibler explicitement les 25 problèmes du nouveau benchmark, empêchant la stagnation sur les modèles de résolution simplifiés.

3. **Optimisation des Timeouts & Ressources** :
   Ajustement dynamique des temps de réflexion (180s/agent) et des fenêtres de validation (600s/tournoi) pour supporter la complexité accrue des problèmes de combinatoire et de géométrie.

4. **Méta-Évolution Profonde (v26-v27)** : 
   L'Essaim d'Architectes possède une vision holistique du dossier `core/`, lui permettant de refactorer l'orchestrateur, les agents et sa propre logique d'amélioration en temps réel.

5. **Élimination de la Dette Technique** :
   Application autonome du principe DRY (*Don't Repeat Yourself*). Le système garantit une cohérence structurelle parfaite et une fiabilité accrue.

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
