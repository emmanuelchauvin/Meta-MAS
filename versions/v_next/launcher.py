
import sys
import asyncio
import time
import re
from pathlib import Path
from dataclasses import replace
import uuid

# Force the import of the sandboxed core module
sys.path.insert(0, str(Path(r"C:\Devs\Meta-MAS\versions\v_next")))
sys.path.append(str(Path(r"C:\Devs\Meta-MAS")))

from core.environment import LogicEnvironment
from core.executor import run_generation
from core.agent import BaseAgent
from models.dna import AgentDNA
from services.llm_client import LLMService
from dotenv import load_dotenv

async def run_benchmark():
    try:
        load_dotenv(override=True)
        llm = LLMService()
        env = LogicEnvironment()
        task = env.get_benchmark_task()
        
        base_dna = AgentDNA(
            uid=uuid.uuid4(), 
            generation=1, 
            role_prompt='Tu dois résoudre 15 PROBLÈMES LOGIQUES numérotés Q1 à Q15. Chaque problème exige une réponse numérique exacte.\n\nINSTRUCTIONS OBLIGATOIRES :\n\n- Réponds UNIQUEMENT avec 15 lignes, une par problème\n- Format strict pour chaque ligne : "Qx: [nombre]" où x = 1 à 15\n- Chaque [nombre] est la SOLUTION numérique du problème Qx correspondant\n- Zéro texte additionnel : pas d\'introduction, pas d\'explication, pas de conclusion\n- Les 15 lignes doivent être consécutives, sans ligne vide\n\nEXEMPLE DE FORMAT CORRECT :\nQ1: 42\nQ2: 7\nQ3: 15\n...\n\nLes 15 problèmes Q1-Q15 sont ci-dessous. Extrais les réponses numériques de chaque problème et inscris-les au format exact shown above.\n\n[INSÉRER LES 15 PROBLÈMES LOGIQUES ICI]\n\nGénère maintenant tes 15 réponses au format strict "Qx: [nombre]".', 
            temperature=0.8
        )
        
        # 3 agents en parallèle pour robustesse
        agents = [BaseAgent(dna=replace(base_dna, uid=uuid.uuid4()), llm_service=llm) for _ in range(3)]
        
        start_time = time.perf_counter()
        results = await run_generation(agents, task)
        end_time = time.perf_counter()
        
        total_fitness = 0.0
        valid_results = 0
        total_tokens = 0
        
        for _, res in results.items():
            if res:
                valid_results += 1
                total_tokens += res.get("tokens", 0)
                fit = await env.evaluate(res)
                total_fitness += fit
                
        avg_fitness = total_fitness / 3.0 if valid_results > 0 else 0.0
        print(f"{avg_fitness},{end_time - start_time},{total_tokens}")
    except Exception as e:
        sys.stderr.write(f"Launcher Error: {str(e)}\n")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run_benchmark())
