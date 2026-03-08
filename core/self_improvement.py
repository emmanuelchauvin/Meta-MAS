import os
import sys
import shutil
import asyncio
import subprocess
import time
import re
import json
from pathlib import Path
from datetime import datetime

from services.llm_client import LLMService
from core.memory import EvolutionGraph

class SelfImprovementManager:
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service
        self.base_dir = Path("g:/devs/Antigravity/Meta-MAS")
        self.core_dir = self.base_dir / "core"
        # The temporary sandbox used for mutations
        self.sandbox_dir = self.base_dir / "versions" / "v_next"
        self.reports_dir = self.base_dir / "versions" / "reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        # Graph to remember what we tried to modify and failed
        self.meta_memory = EvolutionGraph()
        # Version tracking
        self._version_file = self.base_dir / "versions" / "version.json"
        self._load_version()

    def _load_version(self):
        if self._version_file.exists():
            with open(self._version_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.version = data.get("version", 1)
        else:
            self.version = 1
            self._save_version()

    def _save_version(self):
        with open(self._version_file, "w", encoding="utf-8") as f:
            json.dump({"version": self.version}, f)

    def _generate_report(self, modification: str, results: dict):
        """Génère un rapport en français expliquant les changements de la nouvelle version."""
        v_cur = results.get("v_current", {})
        v_next = results.get("v_next", {})
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        report = (
            f"# Rapport de Mise à Jour — Meta-MAS v{self.version}\n\n"
            f"**Date :** {now}\n\n"
            f"## Résumé de la modification\n\n"
            f"{modification}\n\n"
            f"## Résultats du Tournoi A/B\n\n"
            f"| Métrique | V{self.version - 1} (Ancienne) | V{self.version} (Nouvelle) |\n"
            f"|---|---|---|\n"
            f"| Fitness Moyenne | {v_cur.get('fitness', 0)*100:.1f}% | {v_next.get('fitness', 0)*100:.1f}% |\n"
            f"| Temps Total (s) | {v_cur.get('time', 0):.1f} | {v_next.get('time', 0):.1f} |\n"
            f"| Tokens Utilisés | {v_cur.get('tokens', 0)} | {v_next.get('tokens', 0)} |\n\n"
            f"## Décision\n\n"
            f"✅ **Déploiement validé.** La version {self.version} remplace la version {self.version - 1}.\n"
        )

        report_path = self.reports_dir / f"v{self.version}_report.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"[Self-Improvement] Rapport de mise à jour sauvegardé : {report_path.name}")
        print(f"--- Rapport V{self.version} ---")
        print(report)
        print(f"--- Fin du Rapport ---")

    async def reflect_on_architecture(self) -> str | None:
        """
        Analyse les fichiers sources (meta_mas et environment) et propose une unique modification.
        """
        print("\n[Self-Improvement] Initialisation de l'Essaim d'Architectes pour Méta-Réflexion...")
        
        # Read the files to reflect upon
        try:
            with open(self.core_dir / "meta_mas.py", "r", encoding="utf-8") as f:
                meta_mas_code = f.read()
            with open(self.core_dir / "environment.py", "r", encoding="utf-8") as f:
                env_code = f.read()
        except FileNotFoundError as e:
            print(f"[Self-Improvement] Erreur de lecture des sources : {e}")
            return None

        system_prompt = (
            "Tu es l'Essaim Architecte du projet Meta-MAS. Ton but est d'améliorer le code source de ton propre système.\n"
            "Tu dois proposer UNE ET UNE SEULE modification claire et précise du code.\n"
            "PRIVILÉGIE une modification SIMPLE de logique ou d'hyperparamètre (ex: changer une constante, ajuster un coefficient de pénalité) pour garantir la stabilité.\n"
            "Ne fournis QUE ta proposition explicative brève, pas de code complet."
        )
        
        user_prompt = f"Voici le code de core/meta_mas.py :\n```python\n{meta_mas_code}\n```\n\nVoici le code de core/environment.py :\n```python\n{env_code}\n```\n\nQuelle modification proposes-tu ?"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = await self.llm_service.generate_response(model="MiniMax-M2.5", messages=messages, temperature=0.8)
        
        if response:
            print(f"[Self-Improvement] Proposition retenue : {response.strip()[:200]}...")
            return response.strip()
        else:
            print("[Self-Improvement] L'Essaim n'a rien proposé.")
            return None

    async def sandbox_code(self, proposed_modification: str) -> bool:
        """
        Copie les fichiers actuels dans le bac à sable et demande au LLM d'y appliquer la modification.
        Inclut une validation syntaxique et un mécanisme de retry.
        """
        print("[Self-Improvement] Copie des sources dans la sandbox v_next...")
        
        # Nettoyage de v_next s'il existe déjà
        if self.sandbox_dir.exists():
            shutil.rmtree(self.sandbox_dir)
        self.sandbox_dir.mkdir(parents=True)
        
        # Copier tout le dossier core
        shutil.copytree(self.core_dir, self.sandbox_dir / "core")
        
        # Lire les fichiers sources
        with open(self.sandbox_dir / "core" / "environment.py", "r", encoding="utf-8") as f:
             env_code = f.read()
             
        with open(self.sandbox_dir / "core" / "meta_mas.py", "r", encoding="utf-8") as f:
            meta_code = f.read()
            
        system_prompt = (
            "Tu es un Développeur Expert Python.\n"
            "RÈGLES STRICTES :\n"
            "1. Renvoie UNIQUEMENT du code Python brut, PAS de markdown, PAS de commentaires explicatifs avant/après.\n"
            "2. Le code doit être syntaxiquement VALIDE. Attention aux chaînes multi-lignes et regex.\n"
            "3. Renvoie le fichier COMPLET (tous les imports, classes et méthodes) avec la modification appliquée.\n"
            "4. NE MODIFIE QUE le fichier concerné par la proposition. Ne mélange pas le contenu des deux fichiers."
        )
        user_prompt = (
            f"Proposition de modification :\n{proposed_modification}\n\n"
            f"--- environment.py ---\n{env_code}\n\n"
            f"--- meta_mas.py ---\n{meta_code}\n\n"
            f"Applique la modification au fichier concerné et renvoie LE FICHIER COMPLET modifié."
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        max_attempts = 2
        for attempt in range(max_attempts):
            print(f"[Self-Improvement] Mutation du code en cours par le LLM (tentative {attempt+1}/{max_attempts})...")
            response = await self.llm_service.generate_response(model="MiniMax-M2.5", messages=messages, temperature=0.1 + attempt * 0.1)
            
            if not response:
                continue
                
            # --- EXTRACTION DU CODE ---
            modified_code = self._extract_code(response)
            
            if not modified_code:
                print("[Self-Improvement] Impossible d'extraire du code valide de la réponse.")
                continue
            
            # --- VALIDATION SYNTAXIQUE ---
            try:
                compile(modified_code, "<sandbox>", "exec")
            except SyntaxError as e:
                print(f"[Self-Improvement] ❌ Code rejeté (SyntaxError ligne {e.lineno}): {e.msg}")
                # Ajouter le retour d'erreur au prochain essai
                messages.append({"role": "assistant", "content": response})
                messages.append({"role": "user", "content": 
                    f"ERREUR : Ton code contient une SyntaxError à la ligne {e.lineno}: {e.msg}. "
                    f"Corrige cette erreur et renvoie le fichier COMPLET corrigé. Code Python brut uniquement."
                })
                continue
            
            # --- DÉTERMINER LE FICHIER CIBLE ---
            target_file = self.sandbox_dir / "core" / "environment.py"
            if "MetaMAS" in modified_code and "LogicEnvironment" not in modified_code:
                target_file = self.sandbox_dir / "core" / "meta_mas.py"
                
            with open(target_file, "w", encoding="utf-8") as f:
                f.write(modified_code)
                
            print(f"[Self-Improvement] ✅ Fichier {target_file.name} muté dans la sandbox (syntaxe validée).")
            return True
        
        print("[Self-Improvement] ❌ Échec du sandboxing après toutes les tentatives.")
        # Nettoyage
        if self.sandbox_dir.exists():
            shutil.rmtree(self.sandbox_dir)
        return False

    def _extract_code(self, response: str) -> str | None:
        """Extrait le code Python d'une réponse LLM, en nettoyant le bruit."""
        # 1. Strip <think> blocks
        cleaned = re.sub(r"<think>.*?</think>", "", response, flags=re.DOTALL).strip()
        
        # 2. Try to extract from markdown code blocks
        code_blocks = re.findall(r"```python\s*(.*?)\s*```", cleaned, re.DOTALL)
        if not code_blocks:
            code_blocks = re.findall(r"```\s*(.*?)\s*```", cleaned, re.DOTALL)
        
        if code_blocks:
            return max(code_blocks, key=len).strip()
        
        # 3. Fallback: find first Python-like line
        match = re.search(r"^(import |from |class |def )", cleaned, re.MULTILINE)
        if match:
            return cleaned[match.start():].strip()
        
        # 4. Last resort: return cleaned text if it looks like code
        if "def " in cleaned or "class " in cleaned or "import " in cleaned:
            return cleaned
        
        return None

    def run_tournament(self) -> dict:
        """
        Lance meta_mas avec le code original et meta_mas avec le code sandboxé.
        Returns metrics dict.
        """
        print("[Tournoi] Début du tournoi A/B entre V_Current et V_Next...")
        
        # To truly test v_next, we need a wrapper script that forces python to load modules from v_next instead of core.
        # This is complex in Python without modifying sys.path fundamentally in a sub-process.
        # We will create a temporary launcher in the sandbox.
        
        launcher_code = f"""
import sys
import asyncio
import time
import re
from pathlib import Path
from dataclasses import replace

# Force the import of the sandboxed core module
sys.path.insert(0, str(Path(r"{self.sandbox_dir.absolute()}")))
# Also include base dir for models etc
sys.path.append(str(Path(r"{self.base_dir.absolute()}")))

from core.environment import LogicEnvironment
from core.executor import run_generation
from core.agent import BaseAgent
from models.dna import AgentDNA
from services.llm_client import LLMService

from dotenv import load_dotenv
import uuid

async def run_benchmark():
    try:
        load_dotenv(override=True)
        llm = LLMService()
        task = LogicEnvironment().get_benchmark_task()
        env = LogicEnvironment()
        
        # We don't need full evolution, just run 1 generation of 5 agents and see their fitness.
        base_dna = AgentDNA(
            uid=uuid.uuid4(), 
            generation=1, 
            role_prompt="Tu es un assistant logique. Résous ces équations calmement.", 
            temperature=0.3
        )
        
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
        
        print(f"{{avg_fitness}},{{end_time - start_time}},{{total_tokens}}")
    except Exception as e:
        sys.stderr.write(f"Launcher Error: {{str(e)}}\\n")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run_benchmark())
"""
        with open(self.sandbox_dir / "launcher.py", "w", encoding="utf-8") as f:
            f.write(launcher_code)
            
        # We also need a standard launcher for V_Current
        with open(self.base_dir / "launcher_current.py", "w", encoding="utf-8") as f:
            # Same code but WITHOUT modifying sys.path to point to sandbox
            f.write(launcher_code.replace(f'sys.path.insert(0, str(Path(r"{self.sandbox_dir.absolute()}")))', ''))

        results = {}
        
        try:
            # RUN V_CURRENT
            cp_current = subprocess.run(
                [sys.executable, str(self.base_dir / "launcher_current.py")],
                capture_output=True, text=True, timeout=120, cwd=self.base_dir
            )
            v_current_output = cp_current.stdout.strip()
            v_cur_fit, v_cur_time, v_cur_tokens = map(float, v_current_output.split(","))
            results["v_current"] = {"fitness": v_cur_fit, "time": v_cur_time, "tokens": int(v_cur_tokens)}
        except Exception as e:
            print(f"[Tournoi] Erreur lors de l'exécution de V_Current: {e}")
            results["v_current"] = {"fitness": 0.0, "time": 999.0, "tokens": 9999}
            
        try:
            # RUN V_NEXT
            cp_next = subprocess.run(
                [sys.executable, str(self.sandbox_dir / "launcher.py")],
                capture_output=True, text=True, timeout=120, cwd=self.sandbox_dir
            )
            v_next_output = cp_next.stdout.strip()
            v_next_fit, v_next_time, v_next_tokens = map(float, v_next_output.split(","))
            results["v_next"] = {"fitness": v_next_fit, "time": v_next_time, "tokens": int(v_next_tokens)}
        except Exception as e:
            # Likely SyntaxError or timeout because LLM broke the code
            print(f"[Tournoi] V_Next a crashé ou échoué à converger : {e}")
            if 'cp_next' in locals():
                print(f"[Tournoi] V_Next Stderr: {cp_next.stderr.strip()}")
            results["v_next"] = {"fitness": 0.0, "time": 999.0, "tokens": 9999}
            
        # Clean up launchers
        if (self.base_dir / "launcher_current.py").exists():
            (self.base_dir / "launcher_current.py").unlink()
            
        return results

    def deploy_or_rollback(self, results: dict, modification: str = "") -> bool:
        """
        Déploie si V_Next est victorieux, sinon rollback et log.
        """
        v_cur = results.get("v_current", {"fitness": 0.0})
        v_next = results.get("v_next", {"fitness": 0.0})
        
        print(f"[Tournoi] V1 Score: {v_cur['fitness']*100:.0f}%. V2 Score: {v_next['fitness']*100:.0f}%")
        
        # Condition de victoire : Fitness strictement supérieure
        if v_next["fitness"] > v_cur["fitness"] and v_next["fitness"] > 0:
            self.version += 1
            self._save_version()
            print(f"[Tournoi] V2 Score: {v_next['fitness']*100:.0f}%. Remplacement des fichiers sources. Meta-MAS passe en version {self.version}.")
            # Remplacement
            for file in (self.sandbox_dir / "core").iterdir():
                if file.is_file() and file.name.endswith(".py"):
                    shutil.copy(file, self.core_dir / file.name)
            
            # Générer le rapport de mise à jour
            self._generate_report(modification, results)
            
            # Nettoyage
            shutil.rmtree(self.sandbox_dir)
            return True
        else:
            print("[Tournoi] Déploiement annulé. Rollback effectué vers V1.")
            # Rollback
            shutil.rmtree(self.sandbox_dir)
            return False

    async def run_meta_evolution_cycle(self):
        modification = await self.reflect_on_architecture()
        if not modification:
            return
            
        success = await self.sandbox_code(modification)
        if not success:
            return
            
        tournament_results = self.run_tournament()
        self.deploy_or_rollback(tournament_results, modification=modification)
