import os
import re
import matplotlib.pyplot as plt
from pathlib import Path

def plot_efficiency_evolution():
    base_dir = Path(__file__).parent.parent
    reports_dir = base_dir / "versions" / "reports"
    output_path = base_dir / "logs" / "efficiency_evolution_curve.png"
    
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
        if v_num < 21: continue # Filtrer à partir de la v21
        
        with open(file, "r", encoding="utf-8") as f:
            content = f.read()
            f_match = fitness_regex.search(content)
            t_match = time_regex.search(content)
            tok_match = tokens_regex.search(content)
            
            if f_match and t_match and tok_match:
                fitness = float(f_match.group(1))
                time_val = float(t_match.group(1))
                tokens_val = float(tok_match.group(1))
                
                # Formule d'efficacité :
                # On normalise le temps par 100s et les tokens par 5000 (valeurs max typiques)
                # Efficacité = Fitness / ((Temps/100) + (Tokens/5000))
                # Plus le score est haut, plus le système est "intelligent par unité de ressource"
                cost = (time_val / 100.0) + (tokens_val / 5000.0)
                efficiency = fitness / cost if cost > 0 else 0
                
                data.append({
                    "version": v_num,
                    "efficiency": efficiency,
                    "fitness": fitness,
                    "time": time_val,
                    "tokens": tokens_val
                })
    
    if not data:
        print("Erreur : Aucune donnée trouvée pour les versions > 21.")
        return

    data.sort(key=lambda x: x["version"])
    versions = [x["version"] for x in data]
    efficiency = [x["efficiency"] for x in data]

    # Créer le graphique
    plt.figure(figsize=(12, 6))
    plt.plot(versions, efficiency, marker='o', linestyle='-', color='#9b59b6', linewidth=2.5, markersize=6)
    
    plt.title("Score d'Efficacité du Système (v21 à v44)", fontsize=16, fontweight='bold', pad=20)
    plt.xlabel("Version Système", fontsize=12)
    plt.ylabel("Efficacité (Fitness / Coût Normalisé)", fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.5)
    
    # Zone d'amélioration
    plt.fill_between(versions, efficiency, color='#9b59b6', alpha=0.1)

    # Annoter le point actuel
    plt.annotate(f"v{versions[-1]}: {efficiency[-1]:.2f}", 
                 xy=(versions[-1], efficiency[-1]),
                 xytext=(versions[-1], efficiency[-1] + (max(efficiency) * 0.05)),
                 ha='center', fontsize=10, fontweight='bold',
                 bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#9b59b6", lw=1))

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    print(f"Graphique d'efficacité sauvegardé dans : {output_path}")

if __name__ == "__main__":
    plot_efficiency_evolution()
