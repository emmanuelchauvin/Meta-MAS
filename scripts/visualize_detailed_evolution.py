import os
import re
import matplotlib.pyplot as plt
from pathlib import Path

def plot_advanced_evolution():
    base_dir = Path(__file__).parent.parent
    reports_dir = base_dir / "versions" / "reports"
    output_path = base_dir / "logs" / "detailed_evolution_curve.png"
    
    if not reports_dir.exists():
        print(f"Erreur : Le dossier {reports_dir} n'existe pas.")
        return

    data = []
    
    version_regex = re.compile(r"(?:v|v_?)([0-9]+)")
    fitness_regex = re.compile(r"\|\s*Fitness Moyenne\s*\|\s*[\d.]+%?\s*\|\s*([\d.]+)%?\s*\|")
    time_regex = re.compile(r"\|\s*Temps Total \(s\)\s*\|\s*[\d.]+\s*\|\s*([\d.]+)\s*\|")
    tokens_regex = re.compile(r"\|\s*Tokens Utilisés\s*\|\s*[\d.]+\s*\|\s*([\d.]+)\s*\|")

    for file in reports_dir.glob("*.md"):
        filename = file.name
        v_match = version_regex.search(filename)
        if not v_match: continue
        
        v_num = int(v_match.group(1))
        
        with open(file, "r", encoding="utf-8") as f:
            content = f.read()
            f_match = fitness_regex.search(content)
            t_match = time_regex.search(content)
            tok_match = tokens_regex.search(content)
            
            if f_match:
                fitness = float(f_match.group(1))
                time_val = float(t_match.group(1)) if t_match else 0
                tokens_val = float(tok_match.group(1)) if tok_match else 0
                data.append({
                    "version": v_num,
                    "fitness": fitness,
                    "time": time_val,
                    "tokens": tokens_val
                })
    
    if not data:
        print("Erreur : Aucune donnée trouvée.")
        return

    data.sort(key=lambda x: x["version"])
    versions = [x["version"] for x in data]
    fitness = [x["fitness"] for x in data]
    times = [x["time"] for x in data]
    tokens = [x["tokens"] for x in data]

    # Création du graphique multi-axes
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 12), sharex=True)
    
    # 1. Fitness
    ax1.plot(versions, fitness, marker='o', color='#3498db', label="Fitness (%)")
    ax1.set_ylabel("Fitness (%)", fontweight='bold')
    ax1.set_title("Évolution de la Performance de Meta-MAS", fontsize=16, pad=15)
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim(0, 105)
    ax1.legend()

    # 2. Temps
    ax2.plot(versions, times, marker='s', color='#e67e22', label="Temps (s)")
    ax2.set_ylabel("Temps (s)", fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.legend()

    # 3. Tokens
    ax3.plot(versions, tokens, marker='^', color='#e74c3c', label="Tokens")
    ax3.set_ylabel("Tokens", fontweight='bold')
    ax3.set_xlabel("Version Système", fontweight='bold')
    ax3.grid(True, alpha=0.3)
    ax3.legend()

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    print(f"Graphique détaillé sauvegardé dans : {output_path}")

if __name__ == "__main__":
    plot_advanced_evolution()
