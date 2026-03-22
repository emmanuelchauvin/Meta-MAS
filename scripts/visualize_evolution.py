import json
import matplotlib.pyplot as plt
from pathlib import Path

def plot_evolution():
    # Chemins des fichiers
    base_dir = Path(__file__).parent.parent
    graph_path = base_dir / "logs" / "evolution_graph.json"
    output_path = base_dir / "logs" / "evolution_curve.png"
    
    if not graph_path.exists():
        print(f"Erreur : Le fichier {graph_path} n'existe pas.")
        return

    # Charger les données
    with open(graph_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    nodes = data.get("nodes", [])
    if not nodes:
        print("Erreur : Aucun nœud trouvé dans le graphe d'évolution.")
        return

    # Extraire et trier les données par génération
    # On prend la fitness maximum par génération pour voir la progression du "meilleur" agent
    gen_data = {}
    for node in nodes:
        gen = node.get("generation")
        fitness = node.get("fitness", 0)
        if gen not in gen_data or fitness > gen_data[gen]:
            gen_data[gen] = fitness
            
    generations = sorted(gen_data.keys())
    fitness_scores = [gen_data[g] for g in generations]

    # Créer le graphique
    plt.figure(figsize=(12, 6))
    plt.plot(generations, fitness_scores, marker='o', linestyle='-', color='#2ecc71', linewidth=2, markersize=6)
    
    # Personnalisation
    plt.title("Évolution de la Fitness de Meta-MAS", fontsize=16, fontweight='bold', pad=20)
    plt.xlabel("Génération", fontsize=12)
    plt.ylabel("Score de Fitness (Précision)", fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.ylim(0, 1.05)
    
    # Remplissage sous la courbe pour un effet visuel premium
    plt.fill_between(generations, fitness_scores, color='#2ecc71', alpha=0.1)

    # Ajouter des annotations pour les points clés
    if len(generations) > 0:
        plt.annotate(f"Final: {fitness_scores[-1]:.1%}", 
                     xy=(generations[-1], fitness_scores[-1]),
                     xytext=(generations[-1], fitness_scores[-1] + 0.05),
                     ha='center', fontsize=10, fontweight='bold',
                     bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#2ecc71", lw=1))

    # Sauvegarder
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    print(f"Graphique sauvegardé avec succès dans : {output_path}")

if __name__ == "__main__":
    plot_evolution()
