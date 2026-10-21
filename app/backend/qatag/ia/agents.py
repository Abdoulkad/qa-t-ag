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
            "4) Termine TOUJOURS par « ## Statut du livrable » suivi d'une "
            "valeur canonique. N'invente aucune règle métier.")
