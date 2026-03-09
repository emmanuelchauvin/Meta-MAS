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
from utils.logger import log

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
    
    log(f"{'='*60}", category="SYSTEM")
    log(f"  META-MAS v{meta_manager.version} — Système d'Auto-Conception", category="SYSTEM")
    log(f"{'='*60}", category="SYSTEM")
    log(f"  Mission  : {meta_mas.mission}", category="INFO")
    log(f"  Budget   : {meta_mas.budget:.0f}", category="INFO")
    log(f"  Générations max : {max_generations}", category="INFO")
    log(f"  Méta-Évolution toutes les {meta_evo_interval} générations", category="INFO")
    log(f"{'='*60}", category="SYSTEM")
    
    while current_generation <= max_generations:
        # --- EN-TÊTE DE GÉNÉRATION ---
        log(f"{'─'*50}", category="GEN")
        log(f"  Génération {current_generation}/{max_generations} | "
              f"Budget: {meta_mas.budget:.1f} | Version: {meta_manager.version}", category="GEN")
        log(f"{'─'*50}", category="GEN")
        log(f"  Prompt : {base_dna.role_prompt[:80]}...", category="DNA")
        
        # --- MÉTA-ÉVOLUTION PÉRIODIQUE ---
        if current_generation > 1 and current_generation % meta_evo_interval == 0:
            log(f"🧬 [Orchestrateur] Cycle de Méta-Évolution (Gen {current_generation})...", category="META")
            await meta_manager.run_meta_evolution_cycle()
            log(f"🔄 [Orchestrateur] Reprise de l'évolution classique.", category="META")

        # --- CHECK BANQUEROUTE ---
        if meta_mas.budget < meta_mas.base_cost and meta_mas.budget < 1.0:
            log("💀 [Meta-MAS] Banqueroute de l'essaim. Arrêt de l'évolution.", category="STOP")
            break
            
        # --- SPAWN & EXÉCUTION ---
        agents = meta_mas.spawn_generation(base_dna=base_dna, count=5)
        log(f"🚀 Lancement de {len(agents)} agents...", category="SWARM")
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
                log(f"{status} [{short_uid}] Fitness: {fit:.3f} "
                      f"(⏱ {res_dict['time']:.1f}s | 🔤 {res_dict['tokens']} tok)", category="AGENT")
            else:
                fitnesses.append(0.0)
                log(f"💥 [{short_uid}] Échec d'exécution", category="ERROR")
        
        # Diagnostic du meilleur agent
        if best_res:
            log("🔍 Détail du meilleur agent :", category="DEBUG")
            await env.evaluate(best_res, verbose=True)
        
        # --- RÉSUMÉ DE GÉNÉRATION ---
        if fitnesses:
            best = max(fitnesses)
            worst = min(fitnesses)
            avg = sum(fitnesses) / len(fitnesses)
            log(f"📊 Résumé Gen {current_generation} : "
                  f"Best={best:.3f} | Avg={avg:.3f} | Worst={worst:.3f}", category="GEN-SUM")
            
        # --- ÉVOLUTION ---
        next_dna = await meta_mas.evolve(results, base_dna)
        
        if next_dna.generation == base_dna.generation:
            # Si evolve() a redonné le même ADN, c'est que l'IA a refusé ou été bloquée
            log(f"⚠️ [Meta-MAS] Mutation bloquée ou refusée à la génération {current_generation}. Retrait d'agents pour forcer le changement...", category="WARNING")
            # On force tout de même le compteur de génération pour ne pas boucler indéfiniment
            current_generation += 1
            meta_mas.budget -= 50  # Pénalité de budget pour blocage
            continue
            
        base_dna = next_dna
        current_generation += 1

    # --- FIN ---
    if current_generation > max_generations and meta_mas.budget >= 1.0:
        log(f"⏰ [Meta-MAS] Limite de {max_generations} générations atteinte.", category="STOP")

    meta_mas.memory.save_graph("logs/evolution_graph.json")
    
    log(f"{'='*60}", category="SYSTEM")
    log(f"FIN — Budget restant : {meta_mas.budget:.1f} | Version finale : {meta_manager.version}", category="SYSTEM")
    log(f"{'='*60}", category="SYSTEM")

if __name__ == "__main__":
    asyncio.run(main())

