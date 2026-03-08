import re


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
    }

    def __init__(self, fitness_settings: dict = None):
        # Default settings if none provided
        self.settings = fitness_settings or {
            "time_penalty_factor": 0.001,
            "token_penalty_factor": 0.00002,
            "success_threshold": 0.95
        }

    def get_benchmark_task(self) -> str:
        """
        Retourne un benchmark de 5 problèmes de difficulté croissante.
        Chaque problème nécessite plusieurs étapes de raisonnement.
        """
        return (
            "Résous les 5 problèmes suivants. Pour chaque question, donne UNIQUEMENT le nombre final "
            "au format 'Q1: [nombre]', 'Q2: [nombre]', etc. Aucune explanation.\n\n"

            "Q1: Un train part de la Gare A à 8h00 à 160 km/h vers la Gare B. "
            "Un second train part de la Gare B (distante de 480 km) à 9h00 à 200 km/h vers la Gare A. "
            "À quelle heure (heure entière arrondie à l'inférieur) se croisent-ils ? "
            "Réponds uniquement le nombre de l'heure (ex: si 10h37, réponds 10).\n\n"

            "Q2: Alice a 3 fois l'âge de Bob. Dans 12 ans, Alice aura exactement 2 fois l'âge de Bob. "
            "Quel est l'âge actuel de la mère de Bob, sachant qu'elle avait 25 ans quand Bob est né ?\n\n"

            "Q3: Un commerçant achète 50 articles à 8€ pièce. Il vend 30 articles à 15€ pièce, "
            "et brade les 20 restants à 7,50€ pièce. Quel est son bénéfice total (en euros) ?\n\n"

            "Q4: Combien de nombres premiers existe-t-il entre 40 et 70 (bornes incluses) ?\n\n"

            "Q5: Un échiquier standard fait 8×8 = 64 cases. "
            "On retire les 2 coins diagonalement opposés. Combien de cases reste-t-il ?\n\n"
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

        # Strip <think>...</think> blocks if present
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
                print(f"    {status} {q_label}: attendu={expected}, reçu={agent_answer}")

        # Pénalités économiques (ajustées pour 5 questions)
        time_penalty = time_spent * self.settings.get("time_penalty_factor", 0.015)
        token_penalty = tokens_used * self.settings.get("token_penalty_factor", 0.0005)

        fitness = score_logique - time_penalty - token_penalty
        return round(max(0.0, fitness), 5)