# Meta-MAS

Meta-MAS est une architecture expérimentale de Système Multi-Agents (MAS) capable de s'auto-conception et d'évoluer de manière autonome. Construit intégralement en Python natif, le système s'articule autour d'une boucle darwinienne d'amélioration continue des prompts et des stratégies de résolution.

## Introduction

Dans un paradigme classique, les agents IA exécutent des tâches selon des prompts définis statiquement. **Meta-MAS** repense cette approche en dotant le système d'une **conscience d'orchestration**. Le système supervise une population de sous-agents qui tentent de résoudre des benchmarks complexes. À chaque itération, le Meta-MAS évalue les performances et fait évoluer soit les prompts (micro-évolution), soit son propre code source (méta-évolution).

## Innovations Majeures (v26)

Le projet a atteint un stade de maturité industrielle, consolidant ses performances records par une architecture logicielle épurée et hautement performante :

1. **Méta-Évolution Profonde (v26)** : 
   L'Essaim d'Architectes a désormais accès à l'intégralité du dossier `core/`. Il peut modifier non seulement les agents et l'orchestrateur, mais aussi sa propre logique d'auto-amélioration et son environnement.

2. **Benchmark Étendu à 25 Questions** :
   Le défi logique a été augmenté à **25 problèmes** complexes couvrant la logique, les mathématiques, la combinatoire et la géométrie, poussant le système vers ses limites théoriques.

3. **Optimisation Algorithmique Avancée** : 
   Refactorisation intégrale du pipeline de nettoyage de données avec une passe unique optimisée, réduisant drastiquement la charge computationnelle.

4. **Élimination de la Dette Technique** :
   Application autonome du principe DRY (*Don't Repeat Yourself*). Le système garantit une cohérence structurelle parfaite et une fiabilité accrue à **97.8% de fitness** (sur l'ancien benchmark).

5. **Allocation Dynamique et Mode Survie** : 
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
