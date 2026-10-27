# QA-T-AG

*L'IA au service de la qualité logicielle.*

QA-T-AG est une application web d'assurance qualité : elle prend une exigence
(SFD, User Story), en relève les défauts, la fait clarifier et réécrire,
conçoit les cas de test, puis accompagne la recette jusqu'au cahier de recette
Word. Des agents IA proposent ; des scripts contrôlent chaque proposition ; un
humain décide à chaque étape.

**Principe directeur : le script calcule · l'agent analyse · l'humain arbitre.**

Version actuelle : **1.1.0** — FastAPI, React, PostgreSQL.
[Notes de version](docs/NOTES-VERSION-1.1.md) ·
[Installation](app/backend/README.md) ·
[Règles RA-01 à RA-68](docs/specifications.md)

## Le parcours d'une mission

```
Analyser ─► Clarifier ─► Réécrire ─► ◆ PV-1 ─► Concevoir ─► ◆ PV-2 ─► Recette ─► ◆ Clôture
 AG-01      questions    règles RG,   humain    AG-02        humain    exécution,   humain
 défauts    métier       critères CA            cas de test            anomalies,
                                                                       rapport AG-11
```

Les losanges sont les Human Gates : seul un humain habilité les franchit ;
l'IA ne valide jamais son propre travail.

| Agent | Rôle | Contrôle par script |
|---|---|---|
| AG-01 | Relève les défauts de l'exigence (grille QA-REV-02) et pose les questions métier | `controler_revue.py` : format, catégories, citations retrouvées mot pour mot |
| Réécriture | Réécrit l'exigence en règles (RG) et critères d'acceptation (CA) sourcés | `verifier_reecriture.py` : chaque règle cite le texte ou une réponse métier |
| AG-02 | Conçoit les cas de test (techniques ISTQB) | `controler_cas.py` : traçabilité, données, résultat attendu |
| AG-09 | Qualifie les anomalies de recette (titre, gravité, reproductibilité) | `controler_qualification.py` |
| AG-11 | Rédige le contexte, la synthèse, la conclusion et l'avis du rapport de test | `controler_rapport.py` : chiffres, références, avis cohérent |

Le fournisseur d'IA se choisit dans l'application : DeepSeek, OpenAI, Mistral,
Anthropic, ou Ollama en local.

## Ce que fait l'application

- Missions et versions d'exigence, journal chaîné en ajout seul.
- Score de clarté, couverture des phrases du texte d'origine par la réécriture.
- Export Word du cahier de cas de test et du cahier de recette, au gabarit DSI.
- Recette : passages successifs, captures en base, anomalies ANO-nnn, clôture
  avec ou sans réserves, levée des réserves.
- Sécurité : comptes créés par l'administrateur, mot de passe provisoire à
  changer, limitation des tentatives de connexion, sauvegardes vérifiées.
- Évaluation des agents : `python -m qatag.evaluation` exporte les sorties des
  agents, aide à les comparer à un corrigé humain et calcule les indicateurs
  de décision.

## Structure du dépôt

```
qa-t-ag/
├── app/
│   ├── backend/      # API FastAPI, base PostgreSQL (Alembic), tests
│   ├── frontend/     # Interface React (Vite, TypeScript)
│   └── qa/
│       ├── scripts/  # Scripts déterministes de contrôle
│       ├── skills/   # Consignes des agents IA
│       └── modeles/  # Gabarits Word de la DSI
└── docs/             # Spécifications et notes de version
```

La première version de QA-T-AG (agent Hermes et interface Streamlit) est
conservée dans la branche `archive/hermes-streamlit`.

## Sécurité et confidentialité

- Aucune clé d'API ni secret dans le dépôt : ils se renseignent dans
  `app/backend/.env`, jamais versionné.
- Avec un fournisseur d'IA en ligne, le texte des exigences quitte le poste.
  Pour des données réelles, utiliser Ollama (local) ou anonymiser.
- HTTPS est à mettre en place avant toute utilisation depuis un autre poste.
