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
        v_label = f"v{self.version} MAX" if self.version > 26 else f"v{self.version}"

        report = (
            f"# Rapport de Mise à Jour — Meta-MAS {v_label}\n\n"
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

        report_path = self.reports_dir / f"reportMAX_v{self.version}.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)

        log(f"Rapport de mise à jour sauvegardé : {report_path.name}", category="Self-Improvement")
        log(f"--- Rapport V{self.version} ---", category="Self-Improvement")
        log(report, category="Self-Improvement")
        log(f"--- Fin du Rapport ---", category="Self-Improvement")

    async def reflect_on_architecture(self, failed_questions_context: str = "") -> str | None:
        """
        Analyse les fichiers sources pertinents du dossier core/ en se basant sur le contexte d'échec
        et propose une unique modification ciblée.
        """
        log("Initialisation de l'Essaim d'Architectes pour Méta-Réflexion Globale...", category="Self-Improvement")
        
        # === AMÉLIORATION : Sélection intelligente des fichiers à analyser ===
        # Au lieu d'envoyer TOUT le code, on identifie d'abord les fichiers pertinents
        # en fonction du contexte d'échec (failed_questions_context)
        
        priority_files = self._identify_priority_files(failed_questions_context)
        
        # Lire uniquement les fichiers prioritaires pour réduire la charge de tokens
        source_context = ""
        try:
            for file_path in priority_files:
                if file_path.name == "__init__.py" or not file_path.exists():
                    continue
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                # Limiter chaque fichier à 200 lignes pour éviter les prompts trop longs
                lines = content.split('\n')
                if len(lines) > 200:
                    content = '\n'.join(lines[:200]) + "\n# ... (contenu tronqué pour optimisation)"
                source_context += f"--- FICHIER : core/{file_path.name} ---\n```python\n{content}\n```\n\n"
        except Exception as e:
            log(f"Erreur de lecture des sources : {e}", category="ERROR")
            return None

        system_prompt = (
            "Tu es l'Essaim Architecte du projet Meta-MAS. Ton but est d'améliorer le code source de ton propre système.\n"
            "Tu as accès aux fichiers sources pertinents du cœur du système (ceux identifiés comme liés au problème).\n"
            "FICHIERS DISPONIBLES : [agent.py, meta_mas.py, environment.py, executor.py, memory.py, self_improvement.py]\n"
            "Note : 'meta_mas.py' est l'orchestrateur principal. Il n'existe pas de fichier nommé 'orchestrator.py'.\n"
            "MISSION : Tu dois proposer UNE ET UNE SEULE modification claire et précise du code.\n"
            "CONTRAINTE TECHNIQUE : Un seul fichier sera modifié à la fois. Ta proposition doit être réalisable en modifiant UN SEUL fichier du dossier 'core/'.\n"
            "Tu peux modifier la logique d'évolution, la sandbox, l'orchestrateur ou les agents eux-mêmes.\n"
            "PRIVILÉGIE une modification SIMPLE mais ayant un impact significatif sur la performance, la robustesse ou l'intelligence collective.\n"
            "Ne fournis QUE ta proposition explicative brève (max 150 mots), pas de code complet."
        )
        
        context_hint = f"\n\nContexte d'échec récent à prendre en compte:\n{failed_questions_context}" if failed_questions_context else ""
        user_prompt = f"Voici le contexte des fichiers sources du système :\n\n{source_context}{context_hint}\n\nQuelle modification architecturale ou algorithmique proposes-tu ?"
        
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

    def _identify_priority_files(self, failed_context: str) -> list:
        """
        Identifie les fichiers prioritaires à analyser en fonction du contexte d'échec.
        Cela réduit considérablement la charge de tokens en évitant d'envoyer tout le code.
        """
        priority = []
        
        # Mots-clés pour identifier le fichier à problèmes
        keywords_map = {
            "agent": ["agent.py", "executor.py"],
            "timeout": ["agent.py", "executor.py"],
            "executor": ["executor.py", "agent.py"],
            "meta_mas": ["meta_mas.py"],
            "meta orchestrator": ["meta_mas.py"],
            "environment": ["environment.py", "executor.py"],
            "benchmark": ["environment.py"],
            "memory": ["memory.py"],
            "evolution": ["memory.py", "meta_mas.py"],
            "llm": ["agent.py", "services/llm_client.py"],
            "prompt": ["agent.py", "meta_mas.py"],
            "token": ["agent.py", "environment.py"],
            "retry": ["executor.py", "meta_mas.py"],
            "stagnation": ["meta_mas.py", "memory.py"],
        }
        
        failed_lower = failed_context.lower() if failed_context else ""
        
        for keyword, files in keywords_map.items():
            if keyword in failed_lower:
                for f in files:
                    path = self.core_dir / f
                    if path.exists() and path not in priority:
                        priority.append(path)
        
        # Fallback: si pas de contexte ou pas de correspondance, prendre les fichiers principaux
        if not priority:
            priority = [
                self.core_dir / "meta_mas.py",
                self.core_dir / "agent.py",
                self.core_dir / "executor.py"
            ]
            # Filter existing files
            priority = [p for p in priority if p.exists()]
        
        return priority[:3]  # Maximum 3 fichiers pour garder le prompt concis

    async def sandbox_code(self, proposed_modification: str) -> bool:
        """
        Copie les fichiers actuels dans le bac à sable et demande au LLM d'y appliquer la modification.
        """
        log("Copie des sources dans la sandbox v_next...", category="Self-Improvement")
        
        if self.sandbox_dir.exists():
            shutil.rmtree(self.sandbox_dir, ignore_errors=True)
        self.sandbox_dir.mkdir(parents=True)
        shutil.copytree(self.core_dir, self.sandbox_dir / "core")
        
        # --- PHASE 1 : IDENTIFIER LE FICHIER CIBLE ---
        available_files = [f.name for f in self.core_dir.glob("*.py") if f.name != "__init__.py"]
        id_prompt = (
            f"Basé sur cette proposition d'amélioration :\n\"{proposed_modification}\"\n\n"
            f"Quel fichier unique du dossier 'core/' doit être modifié ?\n"
            f"FICHIERS DISPONIBLES : {available_files}\n\n"
            "Réponds UNIQUEMENT par le nom du fichier exact parmi la liste ci-dessus."
        )
        
        target_filename = await self.llm_service.generate_response(
            model="MiniMax-M2.5",
            messages=[{"role": "user", "content": id_prompt}],
            temperature=0.0
        )
        
        if not target_filename or ".py" not in target_filename or target_filename not in available_files:
            # Fallback intelligent basé sur le contenu de la proposition
            prop_lower = proposed_modification.lower()
            if "agent" in prop_lower: target_filename = "agent.py"
            elif any(x in prop_lower for x in ["meta", "orchestra", "budget", "stagnation"]): target_filename = "meta_mas.py"
            elif "environment" in prop_lower or "bench" in prop_lower: target_filename = "environment.py"
            elif "exec" in prop_lower or "parallel" in prop_lower: target_filename = "executor.py"
            elif "memory" in prop_lower or "graph" in prop_lower or "regress" in prop_lower: target_filename = "memory.py"
            elif "self" in prop_lower or "improvement" in prop_lower or "mutate" in prop_lower: target_filename = "self_improvement.py"
            else: target_filename = "meta_mas.py" # Default safe choice
            
        # Extraction propre du basename au cas où le LLM a mis des guillemets ou du texte
        target_filename = re.sub(r"[`']", "", target_filename).strip().split("/")[-1].split("\\")[-1].split()[-1]
        
        # Double vérification finale
        if target_filename not in available_files:
            # Si après extraction c'est toujours pas bon (ex: "orchestrator.py"), on force le fallback
            if "orchestra" in target_filename.lower(): target_filename = "meta_mas.py"
            elif target_filename not in available_files:
                target_filename = "meta_mas.py" # Default
        target_file_path = self.sandbox_dir / "core" / target_filename
        
        if not target_file_path.exists():
            log(f"Fichier cible {target_filename} non trouvé. Abandone.", category="ERROR")
            return False

        with open(target_file_path, "r", encoding="utf-8") as f:
            original_code = f.read()

        # --- PHASE 2 : MUTATION CIBLÉE AVEC VALIDATION FONCTIONNELLE ---
        system_prompt = (
            "Tu es un Développeur Expert Python. Tu dois appliquer une modification à UN SEUL FICHIER.\n"
            "RÈGLES D'OR :\n"
            "1. Renvoie le code Python COMPLET et corrigé.\n"
            "2. Ne change PAS la signature (nom, arguments, et TYPE DE RETOUR) des fonctions, classes ou méthodes existantes.\n"
            "   C'est CRITIQUE pour la compatibilité avec le reste du système.\n"
            "3. Assure-toi que toutes les chaînes (''' ou \"\"\") et parenthèses sont fermées.\n"
            "4. PAS de blabla, PAS d'introduction. Uniquement le bloc de code markdown."
        )
        
        user_prompt = (
            f"FICHIER À MODIFIER : core/{target_filename}\n"
            f"MODIFICATION DEMANDÉE : {proposed_modification}\n\n"
            f"--- CODE ORIGINAL ---\n{original_code}\n\n"
            "Applique la mutation et renvoie le fichier COMPLET."
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        max_attempts = 2
        for attempt in range(max_attempts):
            log(f"Mutation du code de {target_filename} (tentative {attempt+1}/{max_attempts})...", category="Self-Improvement")
            response = await self.llm_service.generate_response(
                model="MiniMax-M2.5", 
                messages=messages, 
                temperature=0.1 + attempt * 0.1,
                max_tokens=8000
            )
            
            if not response: continue
                
            modified_code = self._extract_code(response)
            if not modified_code: continue
            
            # Validation de sécurité (Anti-Snippet)
            is_valid = True
            error_msg = ""
            
            # 1. Vérification de la taille (un snippet est souvent bcp plus court)
            if len(modified_code) < len(original_code) * 0.5:
                is_valid = False
                error_msg = "Le code est trop court (possible troncature/snippet)."
            
            # 2. Vérification des imports et classes
            if "import " not in modified_code or ("class " not in modified_code and "def " not in modified_code):
                is_valid = False
                error_msg = "Structure Python manquante (imports ou classes absents)."

            # 3. Validation syntaxique
            if is_valid:
                try:
                    compile(modified_code, f"<sandbox:{target_filename}>", "exec")
                    with open(target_file_path, "w", encoding="utf-8") as f:
                        f.write(modified_code)
                    
                    # === NOUVELLE AMÉLIORATION : Validation fonctionnelle dry-run ===
                    # On vérifie que le module muté peut être importé et que les classes principales existent
                    if await self._validate_functional(target_filename, target_file_path):
                        log(f"✅ {target_filename} muté avec succès (syntaxe et structure validées).", category="Self-Improvement")
                        return True
                    else:
                        is_valid = False
                        error_msg = "Échec de la validation fonctionnelle (import ou classes manquants)."
                        
                except SyntaxError as e:
                    error_msg = f"Erreur de syntaxe (ligne {e.lineno}): {e.msg}"
                except Exception as e:
                    error_msg = f"Erreur de validation: {str(e)}"

            log(f"❌ Mutation rejetée : {error_msg}", category="Self-Improvement")
            messages.append({"role": "assistant", "content": response})
            messages.append({"role": "user", "content": f"ATTENTION : {error_msg} Tu dois impérativement renvoyer le fichier COMPLET du début à la fin, avec tous les imports et toutes les classes. NE TRONQUE PAS LE CODE."})
        
        return False

    async def _validate_functional(self, filename: str, file_path: Path) -> bool:
        """
        Validation fonctionnelle dry-run : vérifie que le module muté peut être importé
        et que les classes/fonctions principales sont toujours présentes.
        """
        validation_code = f"""
import sys
sys.path.insert(0, r"{self.sandbox_dir}")
sys.path.insert(0, r"{self.base_dir}")

try:
    # Extraire le nom du module (sans .py)
    module_name = "{filename[:-3]}"
    
    # Importer le module
    import importlib
    mod = importlib.import_module(f"core.{{module_name}}")
    
    # Vérifier les classes principales ( heuristics )
    required_classes = {{
        "agent.py": ["BaseAgent"],
        "meta_mas.py": ["MetaMAS"],
        "environment.py": ["LogicEnvironment"],
        "executor.py": ["run_generation"],
        "memory.py": ["EvolutionGraph"],
        "self_improvement.py": ["SelfImprovementManager"]
    }}
    
    if "{filename}" in required_classes:
        for cls in required_classes["{filename}"]:
            if not hasattr(mod, cls):
                print(f"ERREUR: Classe {{cls}} manquante")
                sys.exit(1)
    
    print("OK")
    sys.exit(0)
    
except Exception as e:
    print(f"ERREUR: {{str(e)}}")
    sys.exit(1)
"""
        
        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, "-c", validation_code,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
            
            if proc.returncode == 0 and b"OK" in stdout:
                return True
            else:
                log(f"Validation fonctionnelle échouée: {stderr.decode() if stderr else stdout.decode()}", category="Self-Improvement")
                return False
        except asyncio.TimeoutError:
            log("Validation fonctionnelle timeout", category="Self-Improvement")
            return False
        except Exception as e:
            log(f"Erreur validation fonctionnelle: {e}", category="Self-Improvement")
            return False

    def _extract_code(self, response: str) -> str | None:
        """Extrait le code Python d'une réponse LLM de manière robuste aux backticks imbriqués."""
        if not response:
            return None
        
        # 1. On cherche le contenu entre le PREMIER ```python et le DERNIER ``` 
        match = re.search(r"```(?:python)?\s*\n(.*?)\n\s*```", response, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
            
        # 2. Si pas de bloc fermé, on cherche le premier bloc et on prend tout jusqu'à la fin 
        match_open = re.search(r"```(?:python)?\s*\n(.*)", response, re.DOTALL | re.IGNORECASE)
        if match_open:
            return match_open.group(1).strip()

        # 3. Fallback : si pas de backticks, on nettoie les reflexions <think>
        cleaned = re.sub(r"^\s*<think>.*?</think>\s*(?:\n|$)", "", response, flags=re.DOTALL)
        if cleaned.strip().startswith("<think>"):
            match = re.search(r"^(?:import|from|class|def)\s+[a-zA-Z_]", cleaned, flags=re.MULTILINE)
            if match:
                cleaned = cleaned[match.start():]
            else:
                cleaned = re.sub(r"^\s*<think>\s*", "", cleaned)
                
        if "import " in cleaned or "class " in cleaned or "def " in cleaned:
            return cleaned.strip()

        return None

    async def run_tournament(self, best_dna: AgentDNA | None = None) -> dict:
        """
        Lance meta_mas avec le code original et meta_mas avec le code sandboxé de manière asynchrone.
        """
        log("Début du tournoi A/B entre V_Current et V_Next...", category="Tournoi")
        
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
        env = LogicEnvironment(fitness_settings={{
            "time_penalty_factor": 0.0001,
            "token_penalty_factor": 0.0001, 
            "success_threshold": 0.95
        }})
        task = env.get_benchmark_task()
        
        base_dna = AgentDNA(
            uid=uuid.uuid4(), 
            generation=1, 
            role_prompt={repr(role_prompt)}, 
            temperature={temp}
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
            
        with open(self.base_dir / "launcher_current.py", "w", encoding="utf-8") as f:
            f.write(launcher_code.replace(f'sys.path.insert(0, str(Path(r"{self.sandbox_dir.absolute()}")))', ''))

        results = {}
        timeout_val = 600
        
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
        
        baseline_crashed = v_cur["time"] >= 999.0 or (v_cur["fitness"] <= 0.0 and v_cur["tokens"] >= 9999)
        
        if v_next["fitness"] > v_cur["fitness"] and v_next["fitness"] > 0 and not baseline_crashed:
            self.version += 1
            self._save_version()
            log(f"V2 Score: {v_next['fitness']*100:.0f}%. Remplacement des fichiers sources. Meta-MAS passe en version {self.version}.", category="Tournoi")
            for file in (self.sandbox_dir / "core").iterdir():
                if file.is_file() and file.name.endswith(".py"):
                    shutil.copy(file, self.core_dir / file.name)
            
            self._generate_report(modification, results)
            
            shutil.rmtree(self.sandbox_dir, ignore_errors=True)
            return True
        else:
            log("Déploiement annulé. Rollback effectué vers V1.", category="Tournoi")
            shutil.rmtree(self.sandbox_dir, ignore_errors=True)
            return False

    async def run_meta_evolution_cycle(self, current_dna: AgentDNA | None = None, failed_context: str = ""):
        """
        Execute un cycle d'évolution méta avec contexte d'échec pour amélioration ciblée.
        """
        modification = await self.reflect_on_architecture(failed_questions_context=failed_context)
        if not modification:
            return
            
        success = await self.sandbox_code(modification)
        if not success:
            return
            
        tournament_results = await self.run_tournament(best_dna=current_dna)
        self.deploy_or_rollback(tournament_results, modification=modification)