"""Agents IA : chaque agent = un skill (prompt) + un contrôle par script."""
from ..config import parametres


def prompt_skill(nom: str) -> str:
    """Corps du SKILL.md sans son en-tête YAML : c'est le prompt système."""
    chemin = parametres().dossier_skills / nom / "SKILL.md"
    lignes = chemin.read_text(encoding="utf-8").splitlines()
    if lignes and lignes[0].strip() == "---":
        fin = next((i for i in range(1, len(lignes)) if lignes[i].strip() == "---"), 0)
        lignes = lignes[fin + 1:]
    return "\n".join(lignes)


def consigne_revue(texte: str) -> str:
    return ("Voici l'exigence (SFD ou User Story) à revoir :\n\n" + texte +
            "\n\nContraintes de format STRICTES : "
            "1) Relève au maximum 15 défauts, les plus importants "
            "(bloquants et majeurs en priorité). "
            "2) Inventaire REQ/BR concis (une ligne par point). "
            "3) Chaque défaut a sa citation mot pour mot ET une ligne "
            "« - **Question** : » posant la question métier au rédacteur. "
            "4) Les quatre sections sont OBLIGATOIRES, dans cet ordre, même vides : "
            "« ## Alerte sécurité » (écris « Aucune » s'il n'y en a pas), "
            "« ## Inventaire REQ et BR », « ## Défauts », « ## Statut du livrable » "
            "suivi d'une valeur canonique. N'invente aucune règle métier.")


def consigne_reecriture(origine: str, defauts: list[dict], questions: list[dict]) -> str:
    """questions : [{code, question, reponse}] — seules les réponses comptent comme sources."""
    lignes = ["## Exigence d'origine", origine, "", "## Défauts relevés par la revue (AG-01)"]
    lignes += ["- %s (%s, %s) : « %s »" % (d["code"], d["categorie"], d["gravite"],
                                           d["citation"] or "") for d in defauts] or ["- aucun"]
    lignes += ["", "## Réponses humaines aux questions métier (sources Q-n utilisables)"]
    repondues = [q for q in questions if (q["reponse"] or "").strip()]
    lignes += ["- %s — Question : %s\n  Réponse : %s" % (q["code"], q["question"], q["reponse"])
               for q in repondues] or ["- aucune réponse"]
    hors = [q for q in questions if q.get("decision") == "HORS_PERIMETRE"]
    if hors:
        lignes += ["", "## Questions déclarées HORS PÉRIMÈTRE par l'humain "
                       "(n'écris rien à leur sujet, ni critère ni point ouvert)"]
        lignes += ["- %s — %s" % (q["code"], q["question"]) for q in hors]
    ouvertes = [q for q in questions if not (q["reponse"] or "").strip()
                and q.get("decision") != "HORS_PERIMETRE"]
    if ouvertes:
        lignes += ["", "## Questions sans réponse ou reportées (PAS des sources : "
                       "aucun critère dessus, range chaque sujet dans « ## Points ouverts »)"]
        lignes += ["- %s — %s%s" % (q["code"], q["question"],
                                    " (reportée)" if q.get("decision") == "REPORTEE" else "")
                   for q in ouvertes]
    lignes += ["", "Réécris l'exigence en respectant EXACTEMENT ce format, sans rien avant ni "
                   "après, sans bloc de code. N'invente aucune règle métier.", "",
               "## Exigence réécrite",
               "<l'exigence réécrite>", "",
               "## Critères d'acceptation",
               "### CA-01",
               "- **Critère** : Étant donné …, quand …, alors …",
               "- **Sources** : « passage exact de l'exigence d'origine » ; Q-1",
               "### CA-02",
               "- **Critère** : …",
               "- **Sources** : Q-2", "",
               "## Points ouverts",
               "- <sujet sans source, donc pas un critère> (Q-3)", "",
               "(La section « Points ouverts » est facultative.)"]
    return "\n".join(lignes)


def consigne_conception(texte_reecrit: str, criteres: list[dict], origine: str) -> str:
    lignes = ["## Exigence validée (PV-1)", texte_reecrit, "", "## Critères d'acceptation"]
    lignes += ["- %s : %s" % (c["code"], c["texte"]) for c in criteres]
    lignes += ["", "## Exigence d'origine (pour les identifiants REQ/BR éventuels)", origine, "",
               "Conçois les cas de test. Contraintes STRICTES :",
               "1) Sors d'abord UNIQUEMENT le CSV brut, première ligne exactement : "
               "ID;Titre;Objectif;Exigence;Technique;Priorité;Type;Préconditions;"
               "Données de test;Étapes;Résultat attendu;Statut livrable",
               "2) Colonne Exigence : le ou les codes couverts (CA-xx, et REQ/BR s'il y en a). "
               "Chaque critère CA doit être couvert par au moins un cas.",
               "3) Technique : partitions d'équivalence, valeurs limites, table de décision "
               "ou transitions d'état (en minuscules).",
               "4) Priorité : Critique, Haute ou Moyenne. Type : Fonctionnel, Interface "
               "utilisateur ou Sécurité/Habilitation.",
               "5) Données de test CONCRÈTES (valeurs exactes, jamais « valide » ou "
               "« {variable} ») ; écris « Sans objet » si le cas n'en demande aucune.",
               "6) Statut livrable : OK, ou À_CLARIFIER si une information manque.",
               "7) Jamais de point-virgule à l'intérieur d'un champ. CT numérotés CT-001, CT-002…",
               "8) APRÈS le CSV, une section « ## Justifications » avec une ligne par cas : "
               "« CT-001 : <quelle partition, quelle limite ou quelle règle de la table "
               "ce cas exerce, et pourquoi> »."]
    return "\n".join(lignes)
