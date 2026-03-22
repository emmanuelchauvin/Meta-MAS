import os
import re
import matplotlib.pyplot as plt
from pathlib import Path

def plot_version_evolution():
    base_dir = Path(__file__).parent.parent
    reports_dir = base_dir / "versions" / "reports"
    output_path = base_dir / "logs" / "system_evolution_curve.png"
    
    if not reports_dir.exists():
        print(f"Erreur : Le dossier {reports_dir} n'existe pas.")
        return

    data = []
    
    # Regex pour extraire le numéro de version du nom de fichier
    # Formats: v2_report.md ou reportMAX_v44.md
    version_regex = re.compile(r"(?:v|v_?)([0-9]+)")
    # Regex pour extraire la fitness "Nouvelle" du tableau Markdown
    fitness_regex = re.compile(r"\|\s*Fitness Moyenne\s*\|\s*[\d.]+%?\s*\|\s*([\d.]+)%?\s*\|")

    for file in reports_dir.glob("*.md"):
        filename = file.name
        v_match = version_regex.search(filename)
        if not v_match:
            continue
        
        version_num = int(v_match.group(1))
        
        with open(file, "r", encoding="utf-8") as f:
            content = f.read()
            f_match = fitness_regex.search(content)
            if f_match:
                fitness = float(f_match.group(1))
                # On stocke (version, fitness)
                data.append((version_num, fitness))
    
    if not data:
        print("Erreur : Aucune donnée de fitness trouvée dans les rapports.")
        return

    # Trier par numéro de version
    data.sort()
    versions, fitness_scores = zip(*data)

    # Créer le graphique
    plt.figure(figsize=(12, 6))
    plt.plot(versions, fitness_scores, marker='s', linestyle='-', color='#3498db', linewidth=2, markersize=4, label="Fitness Système")
    
    # Lissage (optionnel, mais utile si trop de points)
    # plt.plot(versions, fitness_scores, alpha=0.3, color='#3498db')
    
    plt.title("Évolution de la Performance de Meta-MAS par Version Système", fontsize=16, fontweight='bold', pad=20)
    plt.xlabel("Version (Mise à jour logicielle)", fontsize=12)
    plt.ylabel("Fitness Moyenne du Benchmark (%)", fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.ylim(min(fitness_scores) - 5, 100)
    
    # Zone d'amélioration
    plt.fill_between(versions, fitness_scores, color='#3498db', alpha=0.1)

    # Annotation finale
    plt.annotate(f"v{versions[-1]}: {fitness_scores[-1]:.1f}%", 
                 xy=(versions[-1], fitness_scores[-1]),
                 xytext=(versions[-1], fitness_scores[-1] + 2),
                 ha='center', fontsize=10, fontweight='bold',
                 bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#3498db", lw=1))

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    print(f"Graphique de l'évolution logicielle sauvegardé dans : {output_path}")

if __name__ == "__main__":
    plot_version_evolution()
