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
from models.dna import AgentDNA
from utils.logger import log

class SelfImprovementManager:
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service
        self.base_dir = Path(__file__).parent.parent
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

        log(f"Rapport de mise à jour sauvegardé : {report_path.name}", category="Self-Improvement")
        log(f"--- Rapport V{self.version} ---", category="Self-Improvement")
        log(report, category="Self-Improvement")
        log(f"--- Fin du Rapport ---", category="Self-Improvement")

    async def reflect_on_architecture(self) -> str | None:
        """
        Analyse les fichiers sources (meta_mas et environment) et propose une unique modification.
        """
        log("Initialisation de l'Essaim d'Architectes pour Méta-Réflexion...", category="Self-Improvement")
        
        # Read the files to reflect upon
        try:
            with open(self.core_dir / "meta_mas.py", "r", encoding="utf-8") as f:
                meta_mas_code = f.read()
            with open(self.core_dir / "agent.py", "r", encoding="utf-8") as f:
                env_code = f.read()
        except FileNotFoundError as e:
            log(f"Erreur de lecture des sources : {e}", category="ERROR")
            return None

        system_prompt = (
            "Tu es l'Essaim Architecte du projet Meta-MAS. Ton but est d'améliorer le code source de ton propre système.\n"
            "Tu dois proposer UNE ET UNE SEULE modification claire et précise du code.\n"
            "PRIVILÉGIE une modification SIMPLE d'algorithmique ou d'optimisation locale (ex: gestion des appels, prompt system) pour garantir la stabilité. NE TOUCHE PAS à la logique d'évaluation externe.\n"
            "Ne fournis QUE ta proposition explicative brève, pas de code complet."
        )
        
        user_prompt = f"Voici le code de core/meta_mas.py :\n```python\n{meta_mas_code}\n```\n\nVoici le code de core/agent.py :\n```python\n{env_code}\n```\n\nQuelle modification proposes-tu ?"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = await self.llm_service.generate_response(model="MiniMax-M2.5", messages=messages, temperature=0.8)
        
        if response:
            log(f"Proposition retenue : {response.strip()[:200]}...", category="Self-Improvement")
            return response.strip()
        else:
            log("L'Essaim n'a rien proposé.", category="Self-Improvement")
            return None

    async def sandbox_code(self, proposed_modification: str) -> bool:
        """
        Copie les fichiers actuels dans le bac à sable et demande au LLM d'y appliquer la modification.
        Inclut une validation syntaxique et un mécanisme de retry.
        """
        log("Copie des sources dans la sandbox v_next...", category="Self-Improvement")
        
        # Nettoyage de v_next s'il existe déjà
        if self.sandbox_dir.exists():
            shutil.rmtree(self.sandbox_dir)
        self.sandbox_dir.mkdir(parents=True)
        
        # Copier tout le dossier core
        shutil.copytree(self.core_dir, self.sandbox_dir / "core")
        
        # Lire les fichiers sources
        with open(self.sandbox_dir / "core" / "agent.py", "r", encoding="utf-8") as f:
             env_code = f.read()
             
        with open(self.sandbox_dir / "core" / "meta_mas.py", "r", encoding="utf-8") as f:
            meta_code = f.read()
            
        system_prompt = (
            "Tu es un Développeur Expert Python chez Meta-MAS.\n"
            "TA MISSION : Appliquer la modification demandée et renvoyer le contenu du fichier MIS À JOUR.\n"
            "RÈGLES CRITIQUES :\n"
            "1. Renvoie le code Python COMPLET dans un bloc de code markdown (ex: ```python ... ```).\n"
            "2. Le code doit être TOTALEMENT EXÉCUTABLE et AUTO-SUFFISANT. Inclus TOUS les imports du fichier original.\n"
            "3. NE TRONQUE JAMAIS le code. Remplis les méthodes entières, pas de '# ... reste du code'.\n"
            "4. Vérifie les parenthèses, les guillemets et l'indentation.\n"
            "5. Un SEUL fichier par réponse."
        )
        user_prompt = (
            f"PROPOSITION DE MODIFICATION :\n{proposed_modification}\n\n"
            f"--- CONTENU ACTUEL DE agent.py ---\n{env_code}\n\n"
            f"--- CONTENU ACTUEL DE meta_mas.py ---\n{meta_code}\n\n"
            f"Choisis le fichier à modifier basé sur la proposition. "
            f"Applique la modification et renvoie le contenu ENTIER ET EXTREMEMENT PROPRE du fichier modifié (code pur).\n"
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        max_attempts = 2
        for attempt in range(max_attempts):
            log(f"Mutation du code en cours par le LLM (tentative {attempt+1}/{max_attempts}) (RETRY if > 1)...", category="Self-Improvement")
            response = await self.llm_service.generate_response(
                model="MiniMax-M2.5", 
                messages=messages, 
                temperature=0.1 + attempt * 0.1,
                max_tokens=8192
            )
            
            if not response:
                continue
                
            # --- EXTRACTION DU CODE ---
            modified_code = self._extract_code(response)
            
            if not modified_code:
                log("Impossible d'extraire du code valide de la réponse.", category="Self-Improvement")
                continue
            
            # --- VALIDATION SYNTAXIQUE ---
            try:
                compile(modified_code, "<sandbox>", "exec")
            except SyntaxError as e:
                log(f"❌ Code rejeté (SyntaxError ligne {e.lineno}): {e.msg} (RETRY queued)", category="Self-Improvement")
                # Ajouter le retour d'erreur au prochain essai
                messages.append({"role": "assistant", "content": response})
                messages.append({"role": "user", "content": 
                    f"ERREUR : Ton code contient une SyntaxError à la ligne {e.lineno}: {e.msg}. "
                    f"Corrige cette erreur et renvoie le fichier COMPLET corrigé. Code Python brut uniquement."
                })
                continue
            
            # --- DÉTERMINER LE FICHIER CIBLE ---
            if "class MetaMAS" in modified_code:
                target_file = self.sandbox_dir / "core" / "meta_mas.py"
            else:
                target_file = self.sandbox_dir / "core" / "agent.py"
                # Validation sémantique pour éviter un import error
                if "class BaseAgent" not in modified_code:
                    log("❌ Code rejeté: 'class BaseAgent' introuvable dans la mutation. (RETRY queued)", category="Self-Improvement")
                    messages.append({"role": "assistant", "content": response})
                    messages.append({"role": "user", "content": 
                        "ERREUR : Ton code ne contient pas 'class BaseAgent'. Tu as tronqué le fichier ou supprimé la classe principale. "
                        "Tu DOIS renvoyer le contenu COMPLET et avec la classe `BaseAgent`. "
                        "Corrige ça et renvoie le code complet."
                    })
                    continue
                
            with open(target_file, "w", encoding="utf-8") as f:
                f.write(modified_code)
                
            log(f"✅ Fichier {target_file.name} muté dans la sandbox (syntaxe validée).", category="Self-Improvement")
            return True
        
        log("❌ Échec du sandboxing après toutes les tentatives.", category="ERROR")
        # Nettoyage
        if self.sandbox_dir.exists():
            shutil.rmtree(self.sandbox_dir, ignore_errors=True)
        return False

    def _extract_code(self, response: str) -> str | None:
        """Extrait le code Python d'une réponse LLM, en privilégiant la structure complète."""
        if not response:
            return None

        # 1. Strip <think> blocks
        cleaned = re.sub(r"<think>.*?</think>", "", response, flags=re.DOTALL).strip()
        
        # 2. Try to extract from markdown code blocks
        code_blocks = re.findall(r"```(?:[pP]ython)?\s*\n(.*?)(?:```|$)", cleaned, re.DOTALL)
            
        if code_blocks:
            code = max(code_blocks, key=len).strip()
            code = re.sub(r"\\\s*\n", "\\\n", code)
            return code
            
        # 3. Fallback: Check if the whole string looks like python code
        if "import " in cleaned or "class " in cleaned or "def " in cleaned:
             return cleaned

        return None

    async def run_tournament(self, best_dna: AgentDNA | None = None) -> dict:
        """
        Lance meta_mas avec le code original et meta_mas avec le code sandboxé de manière asynchrone.
        """
        log("Début du tournoi A/B entre V_Current et V_Next...", category="Tournoi")
        
        # Fallback DNA if not provided
        role_prompt = best_dna.role_prompt if best_dna else "Tu es un assistant logique. Résous ces équations calmement."
        temp = best_dna.temperature if best_dna else 0.3
        
        launcher_code = f"""
import sys
import asyncio
import time
import re
from pathlib import Path
from dataclasses import replace
import uuid

# Force the import of the sandboxed core module
sys.path.insert(0, str(Path(r"{self.sandbox_dir.absolute()}")))
sys.path.append(str(Path(r"{self.base_dir.absolute()}")))

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
            role_prompt={repr(role_prompt)}, 
            temperature={temp}
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
        print(f"{{avg_fitness}},{{end_time - start_time}},{{total_tokens}}")
    except Exception as e:
        sys.stderr.write(f"Launcher Error: {{str(e)}}\\n")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run_benchmark())
"""
        with open(self.sandbox_dir / "launcher.py", "w", encoding="utf-8") as f:
            f.write(launcher_code)
            
        with open(self.base_dir / "launcher_current.py", "w", encoding="utf-8") as f:
            f.write(launcher_code.replace(f'sys.path.insert(0, str(Path(r"{self.sandbox_dir.absolute()}")))', ''))

        results = {}
        timeout_val = 300
        
        # Helper pour lancer un processus asynchrone
        async def run_proc(cmd, cwd):
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd
            )
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_val)
                return stdout.decode(errors="replace").strip(), stderr.decode(errors="replace").strip(), proc.returncode
            except asyncio.TimeoutError:
                try:
                    proc.kill()
                except:
                    pass
                return "", "Timeout", 1

        try:
            # RUN V_CURRENT
            stdout, stderr, returncode = await run_proc([sys.executable, str(self.base_dir / "launcher_current.py")], self.base_dir)
            lines = [l.strip() for l in stdout.split("\n") if "," in l]
            if returncode == 0 and lines:
                v_cur_fit, v_cur_time, v_cur_tokens = map(float, lines[-1].split(","))
                results["v_current"] = {"fitness": v_cur_fit, "time": v_cur_time, "tokens": int(v_cur_tokens)}
            else:
                log(f"V1 Stderr: {stderr}", category="Tournoi")
                raise ValueError(f"V1 output Error: {stderr[:200]}")
        except Exception as e:
            log(f"Erreur V_Current: {e}", category="ERROR")
            results["v_current"] = {"fitness": 0.0, "time": 999.0, "tokens": 9999}
            
        try:
            # RUN V_NEXT
            stdout, stderr, returncode = await run_proc([sys.executable, str(self.sandbox_dir / "launcher.py")], self.sandbox_dir)
            lines = [l.strip() for l in stdout.split("\n") if "," in l]
            if returncode == 0 and lines:
                v_next_fit, v_next_time, v_next_tokens = map(float, lines[-1].split(","))
                results["v_next"] = {"fitness": v_next_fit, "time": v_next_time, "tokens": int(v_next_tokens)}
            else:
                log(f"V2 Stderr: {stderr}", category="Tournoi")
                raise ValueError(f"V2 output Error: {stderr[:200]}")
        except Exception as e:
            log(f"V_Next crash ou timeout : {e}", category="Tournoi")
            results["v_next"] = {"fitness": 0.0, "time": 999.0, "tokens": 9999}
            
        if (self.base_dir / "launcher_current.py").exists():
            (self.base_dir / "launcher_current.py").unlink()
            
        return results

    def deploy_or_rollback(self, results: dict, modification: str = "") -> bool:
        """
        Déploie si V_Next est victorieux, sinon rollback et log.
        """
        v_cur = results.get("v_current", {"fitness": 0.0})
        v_next = results.get("v_next", {"fitness": 0.0})
        
        log(f"V1 Score: {v_cur['fitness']*100:.0f}%. V2 Score: {v_next['fitness']*100:.0f}%", category="Tournoi")
        
        # Ensure the baseline (v_cur) did not crash (indicated by time == 999.0 or fitness 0.0)
        baseline_crashed = v_cur["time"] >= 999.0 or (v_cur["fitness"] <= 0.0 and v_cur["tokens"] >= 9999)
        
        # Condition de victoire : Fitness strictement supérieure ET la baseline n'a pas planté
        if v_next["fitness"] > v_cur["fitness"] and v_next["fitness"] > 0 and not baseline_crashed:
            self.version += 1
            self._save_version()
            log(f"V2 Score: {v_next['fitness']*100:.0f}%. Remplacement des fichiers sources. Meta-MAS passe en version {self.version}.", category="Tournoi")
            # Remplacement
            for file in (self.sandbox_dir / "core").iterdir():
                if file.is_file() and file.name.endswith(".py"):
                    shutil.copy(file, self.core_dir / file.name)
            
            # Générer le rapport de mise à jour
            self._generate_report(modification, results)
            
            # Nettoyage
            shutil.rmtree(self.sandbox_dir, ignore_errors=True)
            return True
        else:
            log("Déploiement annulé. Rollback effectué vers V1.", category="Tournoi")
            # Rollback
            shutil.rmtree(self.sandbox_dir, ignore_errors=True)
            return False

    async def run_meta_evolution_cycle(self, current_dna: AgentDNA | None = None):
        modification = await self.reflect_on_architecture()
        if not modification:
            return
            
        success = await self.sandbox_code(modification)
        if not success:
            return
            
        tournament_results = await self.run_tournament(best_dna=current_dna)
        self.deploy_or_rollback(tournament_results, modification=modification)
