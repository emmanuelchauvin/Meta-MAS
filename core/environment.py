import re
from utils.logger import log


class LogicEnvironment:
    """
    Environnement de benchmark pour le Meta-MAS.
    Les problèmes sont conçus pour nécessiter du raisonnement multi-étapes,
    rendant la convergence non triviale et forçant l'évolution architecturale.
    """

    # Réponses attendues (séparées du prompt pour éviter toute fuite)
    EXPECTED_ANSWERS = {
        "Q1": "9",     # Heure de croisement : 9h53 → arrondi inférieur = 9
        "Q2": "37",    # Âge de la mère de Bob
        "Q3": "200",   # Bénéfice total
        "Q4": "7",     # Nombres premiers entre 40 et 70
        "Q5": "62",    # Cases restantes sur l'échiquier
        "Q6": "3",     # Problème des nénuphars
        "Q7": "13",    # Problème de la suite
        "Q8": "120",   # Problème de vitesse moyenne
        "Q9": "5",     # Problème des machines
        "Q10": "64",   # Problème d'âge : père aura 64 ans (45+19=64, fils 13+19=32)
        "Q11": "24",   # Combinatoire
        "Q12": "30",   # Géométrie
        "Q13": "100",  # Pourcentages successifs
        "Q14": "14",   # Logique jours ouvrables
        "Q15": "8",     # Gouttes d'eau
        "Q16": "8",     # Somme des chiffres de 2^9 (512 -> 5+1+2=8)
        "Q17": "50",    # Probabilité pile-face (50%)
        "Q18": "720",   # Factorielle de 6
        "Q19": "25",    # Racines carrées
        "Q20": "10",    # Escargot dans le puits (10 jours)
        "Q21": "144",   # Douzaine de douzaines (12*12=144)
        "Q22": "121",   # Suite de carrés
        "Q23": "48",    # Diviseurs de 2520 (juste pour info : 48 est bon)
        "Q24": "420",   # PPCM de 12, 15, 20 et 21 = 420
        "Q25": "180"    # Somme des angles d'un triangle
    }

    def __init__(self, fitness_settings: dict = None):
        # Default settings if none provided
        self.settings = fitness_settings or {
            "time_penalty_factor": 0.0001,
            "token_penalty_factor": 0.0005,
            "success_threshold": 0.95
        }

    def get_benchmark_task(self) -> str:
        """
        Retourne un benchmark de 25 problèmes de difficulté croissante.
        Chaque problème nécessite plusieurs étapes de raisonnement.
        """
        return (
            "Résous les 25 problèmes suivants. Pour chaque question, donne UNIQUEMENT le nombre final "
            "au format 'Q1: [nombre]', 'Q2: [nombre]', etc. Aucune explication.\n\n"

            "Q1: Un train part de la Gare A à 8h00 à 160 km/h vers la Gare B. "
            "Un second train part de la Gare B (distante de 480 km) à 9h00 à 200 km/h vers la Gare A. "
            "À quelle heure (heure entière arrondie à l'inférieur) se croisent-ils ?\n\n"

            "Q2: Alice a 3 fois l'âge de Bob. Dans 12 ans, Alice aura exactement 2 fois l'âge de Bob. "
            "Quel est l'âge actuel de la mère de Bob, sachant qu'elle avait 25 ans quand Bob est né ?\n\n"

            "Q3: Un commerçant achète 50 articles à 8€ pièce. Il vend 30 articles à 15€ pièce, "
            "et brade les 20 restants à 7,50€ pièce. Quel est son bénéfice total (en euros) ?\n\n"

            "Q4: Combien de nombres premiers existe-t-il entre 40 et 70 (bornes incluses) ?\n\n"

            "Q5: Un échiquier standard fait 8×8 = 64 cases. "
            "On retire les 2 coins diagonalement opposés. Combien de cases reste-t-il ?\n\n"

            "Q6: Dans un lac, il y a des nénuphars. Chaque jour, la surface couverte par les nénuphars double. "
            "S'il faut 4 jours pour que le lac soit entièrement couvert, combien de jours faut-il pour qu'il soit à moitié couvert ?\n\n"

            "Q7: Quelle est la valeur du terme suivant dans cette suite : 1, 1, 2, 3, 5, 8, ... ?\n\n"

            "Q8: Si je parcours la première moitié d'un trajet à 60 km/h, à quelle vitesse constante (en km/h) dois-je effectuer "
            "la seconde moitié pour que ma vitesse moyenne sur tout le trajet soit de 80 km/h ?\n\n"

            "Q9: S'il faut 5 minutes à 5 machines pour fabriquer 5 objets, "
            "combien de minutes faudrait-il à 100 machines pour fabriquer 100 objets ?\n\n"

            "Q10: Un père a 45 ans et son fils a 13 ans. Dans combien d'années l'âge du père sera-t-il exactement le double de celui du fils ? "
            "Donne l'âge du père à ce moment-là.\n\n"

            "Q11: Combien de mots différents de 4 lettres peut-on former avec les lettres A, B, C et D sans les répéter ?\n\n"

            "Q12: Un rectangle a une aire de 50 cm² et sa longueur est le double de sa largeur. "
            "Quel est son périmètre (en cm) ?\n\n"

            "Q13: Un article coûte 100€. Son prix augmente d'abord de 25%, puis diminue de 20%. "
            "Quel est le nouveau prix de l'article (en euros) ?\n\n"

            "Q14: Une tâche nécessite 10 jours ouvrables pour être complétée. "
            "Si la tâche commence un mercredi, combien de jours complets se seront écoulés (incluant les week-ends) "
            "lorsque la tâche sera terminée à la fin du dernier jour ouvrable ?\n\n"

            "Q15: Un robinet fuit et remplit un seau de 10 litres en 24 heures. "
            "Sachant qu'il tombe exactement 2 gouttes par seconde, combien faut-il de gouttes pour faire 1 litre ? "
            "Réponds en divisant le résultat total par 2160 (pour un chiffre court).\n\n"

            "Q16: Quelle est la somme des chiffres du nombre 2 puissance 9 ?\n\n"

            "Q17: Jean lance une pièce de monnaie équilibrée. Quelle est la probabilité (en pourcentage) d'obtenir face ?\n\n"

            "Q18: Quelle est la valeur de 6 factorielle (6!) ?\n\n"

            "Q19: Quel est le nombre dont le carré est 625 ?\n\n"

            "Q20: Un escargot est au fond d'un puits de 12 mètres. Chaque jour, il monte de 3 mètres et chaque nuit, il redescend de 2 mètres. "
            "Combien de jours lui faudra-t-il pour sortir du puits ?\n\n"

            "Q21: Combien d'objets y a-t-il dans une douzaine de douzaines ?\n\n"

            "Q22: Quel est le nombre suivant dans la suite : 1, 4, 9, 16, 25, 36, 49, 64, 81, 100, ... ?\n\n"

            "Q23: Combien de diviseurs possède le nombre 2520 ?\n\n"

            "Q24: Quel est le plus petit commun multiple (PPCM) de 12, 15 et 21 ?\n\n"

            "Q25: Quelle est la somme des angles intérieurs d'un triangle (en degrés) ?\n\n"
        )

    async def evaluate(self, agent_response: dict | None, verbose: bool = False) -> float:
        """
        Évalue la réponse de l'agent (dict contenant result, time, tokens).
        Utilise un matching strict par question pour éviter les faux positifs.
        """
        if not agent_response or not agent_response.get("result"):
            return 0.0

        result_text = agent_response["result"]
        time_spent = agent_response.get("time", 0.0)
        tokens_used = agent_response.get("tokens", 0)

        # Strip <think> blocks if present
        cleaned = re.sub(r"<think>.*?</think>", "", result_text, flags=re.DOTALL).strip()


        # Score logique : vérification stricte par question
        score_logique = 0.0
        points_per_question = 1.0 / len(self.EXPECTED_ANSWERS)  # 0.2 par question

        for q_label, expected in self.EXPECTED_ANSWERS.items():
            # Chercher le pattern "Q1: 37" ou "Q1 : 37" ou "Q1:37"
            pattern = rf"{q_label}\s*:\s*{re.escape(expected)}\b"
            found = bool(re.search(pattern, cleaned))
            if found:
                score_logique += points_per_question
            if verbose:
                status = "✅" if found else "❌"
                # Show what the agent actually answered
                agent_match = re.search(rf"{q_label}\s*:\s*(\S+)", cleaned)
                agent_answer = agent_match.group(1) if agent_match else "?"
                log(f"    {status} {q_label}: attendu={expected}, reçu={agent_answer}", category="EVAL")

        # Pénalités économiques (cohérentes avec __init__)
        time_penalty = time_spent * self.settings.get("time_penalty_factor", 0.0001)
        token_penalty = tokens_used * self.settings.get("token_penalty_factor", 0.0005)

        fitness = score_logique - time_penalty - token_penalty
        return round(max(0.0, fitness), 5)