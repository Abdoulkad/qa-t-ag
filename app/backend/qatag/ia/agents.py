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
            "\n\nContraintes STRICTES :\n"
            "1) Relève au maximum 15 défauts, les plus importants (bloquants et majeurs en "
            "priorité), sans doublon.\n"
            "2) Chaque défaut : « ### DEF-nnn — <catégorie> — <criticité> », puis les lignes "
            "Section, Citation (mot pour mot entre « »), Constat, Justification, Question.\n"
            "3) Catégories permises, exactement : Contradiction certaine, Contradiction "
            "apparente, Ambiguïté, Terme non défini, Exigence non testable, Règle manquante, "
            "Cas limite à confirmer, Règle sans exigence, Incohérence avec les user stories. "
            "« Certaine » seulement si les deux règles ne peuvent pas être satisfaites "
            "ensemble ; si une exception peut les concilier : « apparente ».\n"
            "4) Criticité selon l'impact démontré. Bloquante si l'erreur change le montant "
            "versé, un droit, la sécurité ou les données, ou empêche de concevoir les tests ; "
            "la Justification est alors OBLIGATOIRE.\n"
            "5) Questions neutres : ne suggère jamais la réponse.\n"
            "6) Ce que le texte ne dit pas (règle absente : interactions entre règles, "
            "plafond partiellement atteint, statuts, droits, doublons, arrondis…) va dans "
            "« ## Questions complémentaires » (8 au plus, QC-01…, lignes Sujet, Pourquoi, "
            "Question), pas dans les défauts.\n"
            "7) Sections OBLIGATOIRES, dans cet ordre, même vides (écris « Aucune ») : "
            "« ## Alerte sécurité », « ## Inventaire REQ et BR », « ## Défauts », "
            "« ## Questions complémentaires », « ## Statut du livrable » suivi d'une valeur "
            "canonique. N'invente aucune règle métier.")


def consigne_reecriture(origine: str, defauts: list[dict], questions: list[dict]) -> str:
    """questions : [{code, question, reponse}] — seules les réponses comptent comme sources."""
    lignes = ["## Exigence d'origine", origine, "",
              "## Défauts relevés par la revue (AG-01) et retenus par l'humain"]
    lignes += ["- %s (%s, %s) : « %s »%s" % (d["code"], d["categorie"], d["gravite"],
                                             d["citation"] or "",
                                             " — %s" % d["constat"] if d.get("constat") else "")
               for d in defauts] or ["- aucun"]
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
                       "aucune règle ni critère dessus, range chaque sujet dans « ## Points "
                       "ouverts ». Un élément qui en cite une est marqué hypothèse, même s'il "
                       "a d'autres sources)"]
        lignes += ["- %s — %s%s" % (q["code"], q["question"],
                                    " (reportée)" if q.get("decision") == "REPORTEE" else "")
                   for q in ouvertes]
    lignes += ["", "Réécris la User Story en respectant EXACTEMENT ce format, sans rien avant "
                   "ni après, sans bloc de code. N'invente aucune règle métier.",
               "- Préserve le besoin et l'intention de la User Story d'origine.",
               "- Sépare la User Story, les règles métier (ce que le métier impose) et les "
               "critères d'acceptation (ce qu'on vérifie).",
               "- Chaque règle cite le passage d'origine qu'elle précise, mot pour mot entre "
               "« », et la réponse Q-n qui la précise s'il y en a une.",
               "- Chaque phrase de l'exigence d'origine doit être reprise par au moins une "
               "règle ou un critère (citée entre « »), ou rangée dans les points ouverts.",
               "",
               "## User Story réécrite",
               "<la User Story réécrite : En tant que …, je veux …, afin de …>", "",
               "## Règles métier",
               "### RG-01",
               "- **Règle** : <règle de gestion>",
               "- **Sources** : « passage exact de l'exigence d'origine » ; Q-1", "",
               "## Critères d'acceptation",
               "### CA-01",
               "- **Critère** : Étant donné …, quand …, alors …",
               "- **Règles** : RG-01",
               "### CA-02",
               "- **Critère** : …",
               "- **Sources** : « passage exact de l'exigence d'origine »", "",
               "## Points ouverts",
               "- <sujet sans source, donc ni règle ni critère> (Q-3)", "",
               "(« Règles métier » est obligatoire : écris « Aucune » s'il n'y en a pas. "
               "Un critère s'appuie sur ses règles, sur ses propres sources, ou les deux. "
               "« Points ouverts » est facultative.)"]
    return "\n".join(lignes)


def consigne_conception(texte_reecrit: str, criteres: list[dict], origine: str,
                        regles: list[dict] | None = None) -> str:
    lignes = ["## Exigence validée (PV-1)", texte_reecrit, ""]
    if regles:
        lignes += ["## Règles métier validées"]
        lignes += ["- %s : %s" % (r["code"], r["texte"]) for r in regles]
        lignes += [""]
    lignes += ["## Critères d'acceptation"]
    lignes += ["- %s : %s%s" % (c["code"], c["texte"],
                                " (vérifie %s)" % ", ".join(c["regles"]) if c.get("regles") else "")
               for c in criteres]
    lignes += ["", "## Exigence d'origine (pour les identifiants REQ/BR éventuels)", origine, "",
               "Conçois les cas de test. Contraintes STRICTES :",
               "1) Sors d'abord UNIQUEMENT le CSV brut, première ligne exactement : "
               "ID;Titre;Objectif;Exigence;Technique;Priorité;Type;Préconditions;"
               "Données de test;Étapes;Résultat attendu;Statut livrable",
               "2) Colonne Exigence : le ou les codes couverts, TOUJOURS au moins un critère CA-xx ; "
               "ajoute la règle RG-xx et les REQ/BR concernés s'il y en a (ex. « CA-03, RG-02 »). "
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
