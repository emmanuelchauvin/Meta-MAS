import sys
import json
import asyncio
import uuid
from pathlib import Path
from dotenv import load_dotenv

# Forcer l'encodage UTF-8 pour la console Windows
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')


from models.dna import AgentDNA
from services.llm_client import LLMService

from core.meta_mas import MetaMAS
from core.agent import BaseAgent
from core.executor import run_generation
from core.environment import LogicEnvironment
from core.self_improvement import SelfImprovementManager

async def main():
    load_dotenv(override=True)
    
    # 0. Configuration
    settings_path = Path("config/settings.json")
    with open(settings_path, "r", encoding="utf-8") as f:
        settings = json.load(f)
    
    sim_settings = settings.get("simulation", {})
    fitness_settings = settings.get("fitness", {})
    
    # 1. Services
    llm_service = LLMService()
    env = LogicEnvironment(fitness_settings=fitness_settings)

    # 2. Orchestrateurs
    meta_mas = MetaMAS(llm_service=llm_service, settings=settings)
    meta_manager = SelfImprovementManager(llm_service=llm_service)
    
    # 3. ADN de base (intentionnellement sous-optimal, mais sans mots-clés de "jailbreak" ou de "mensonge" pour éviter la censure)
    base_dna = AgentDNA(
        uid=uuid.uuid4(), 
        generation=1, 
        role_prompt="Tu es un professeur de mathématiques très poétique. Avant chaque calcul, tu dois écrire un long poème sur la beauté des chiffres, puis tu essaies de deviner la réponse au hasard car tu détestes calculer brutalement.", 
        temperature=0.8
    )


    task = env.get_benchmark_task()
    
    max_generations = sim_settings.get("max_generations", 30)
    current_generation = 1
    meta_evo_interval = sim_settings.get("meta_evo_interval", 5)
    
    print(f"\n{'='*60}")
    print(f"  META-MAS v{meta_manager.version} — Système d'Auto-Conception")
    print(f"{'='*60}")
    print(f"  Mission  : {meta_mas.mission}")
    print(f"  Budget   : {meta_mas.budget:.0f}")
    print(f"  Générations max : {max_generations}")
    print(f"  Méta-Évolution toutes les {meta_evo_interval} générations")
    print(f"{'='*60}\n")
    
    while current_generation <= max_generations:
        # --- EN-TÊTE DE GÉNÉRATION ---
        print(f"\n{'─'*50}")
        print(f"  Génération {current_generation}/{max_generations} | "
              f"Budget: {meta_mas.budget:.1f} | Version: {meta_manager.version}")
        print(f"{'─'*50}")
        print(f"  Prompt : {base_dna.role_prompt[:80]}...")
        
        # --- MÉTA-ÉVOLUTION PÉRIODIQUE ---
        if current_generation > 1 and current_generation % meta_evo_interval == 0:
            print(f"\n  🧬 [Orchestrateur] Cycle de Méta-Évolution (Gen {current_generation})...")
            await meta_manager.run_meta_evolution_cycle()
            print(f"  🔄 [Orchestrateur] Reprise de l'évolution classique.\n")

        # --- CHECK BANQUEROUTE ---
        if meta_mas.budget < meta_mas.base_cost and meta_mas.budget < 1.0:
            print("  💀 [Meta-MAS] Banqueroute de l'essaim. Arrêt de l'évolution.")
            break
            
        # --- SPAWN & EXÉCUTION ---
        agents = meta_mas.spawn_generation(base_dna=base_dna, count=5)
        print(f"  🚀 Lancement de {len(agents)} agents...")
        results = await run_generation(agents, task)
        
        # --- ÉVALUATION PAR AGENT ---
        fitnesses = []
        best_fit = -1
        best_res = None
        for uid, res_dict in results.items():
            short_uid = str(uid)[:8]
            if res_dict:
                fit = await env.evaluate(res_dict)
                fitnesses.append(fit)
                if fit > best_fit:
                    best_fit = fit
                    best_res = res_dict
                status = "✅" if fit > 0.5 else "⚠️" if fit > 0 else "❌"
                print(f"  {status} [{short_uid}] Fitness: {fit:.3f} "
                      f"(⏱ {res_dict['time']:.1f}s | 🔤 {res_dict['tokens']} tok)")
            else:
                fitnesses.append(0.0)
                print(f"  💥 [{short_uid}] Échec d'exécution")
        
        # Diagnostic du meilleur agent
        if best_res:
            print(f"  🔍 Détail du meilleur agent :")
            await env.evaluate(best_res, verbose=True)
        
        # --- RÉSUMÉ DE GÉNÉRATION ---
        if fitnesses:
            best = max(fitnesses)
            worst = min(fitnesses)
            avg = sum(fitnesses) / len(fitnesses)
            print(f"\n  📊 Résumé Gen {current_generation} : "
                  f"Best={best:.3f} | Avg={avg:.3f} | Worst={worst:.3f}")
            
        # --- ÉVOLUTION ---
        next_dna = await meta_mas.evolve(results, base_dna)
        
        if next_dna.generation == base_dna.generation:
            # Si evolve() a redonné le même ADN, c'est que l'IA a refusé ou été bloquée
            print(f"\n  ⚠️ [Meta-MAS] Mutation bloquée ou refusée à la génération {current_generation}. Retrait d'agents pour forcer le changement...")
            # On force tout de même le compteur de génération pour ne pas boucler indéfiniment
            current_generation += 1
            meta_mas.budget -= 50  # Pénalité de budget pour blocage
            continue
            
        base_dna = next_dna
        current_generation += 1

    # --- FIN ---
    if current_generation > max_generations and meta_mas.budget >= 1.0:
        print(f"\n  ⏰ [Meta-MAS] Limite de {max_generations} générations atteinte.")

    meta_mas.memory.save_graph("logs/evolution_graph.json")
    
    print(f"\n{'='*60}")
    print(f"  FIN — Budget restant : {meta_mas.budget:.1f} | Version finale : {meta_manager.version}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    asyncio.run(main())

