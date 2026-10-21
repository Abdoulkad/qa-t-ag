# QA-T-AG — Agent QA/BA autonome

> **Application web v1.0.0 (conception)** — FastAPI + React + PostgreSQL.
> Analyser → Clarifier → Réécrire → PV-1 → Concevoir → PV-2, avec agents IA
> contrôlés par script et validation humaine à chaque Human Gate.
> Installation : [`app/backend/README.md`](app/backend/README.md) ·
> Notes de version : [`docs/NOTES-VERSION-1.0.md`](docs/NOTES-VERSION-1.0.md) ·
> Règles : [`docs/specifications.md`](docs/specifications.md).
> La suite de ce document décrit la vision complète à 13 agents (agent Hermes).

QA-T-AG transforme une exigence (SFD, User Story) en cas de test
fonctionnels et non fonctionnels (Gherkin, ISTQB), les exécute en
Sandbox isolée, et produit un verdict **prouvé** par des sorties
d'exécution — jamais affirmé.

## Les 13 agents

| Agent | Rôle | Skill |
|---|---|---|
| AG-01 | Revue SFD (détection des défauts) | `qa-revue-sfd` |
| AG-02 | Conception des cas de test | `qa-conception` |
| AG-03 | Traçabilité (matrice REQ/BR ↔ CT) | `qa-tracabilite` |
| AG-04 | Données de test (RG-11) | `qa-donnees` |
| AG-05 | Relecture des cas | `qa-relecteur` |
| AG-06 | Cahier de recette (Word) | `qa-cahier` |
| AG-07 | Orchestrateur | `qa-orchestrateur` |
| AG-08 | Exécution (résultats + preuves) | `qa-execution` |
| AG-09 | Analyse des anomalies | `qa-anomalies` |
| AG-10 | Tests de régression | `qa-regression` |
| AG-11 | Performance / charge | `qa-performance` |
| AG-12 | Sécurité (OWASP) | `qa-securite` |
| AG-13 | Ergonomie / accessibilité (WCAG/RGAA) | `qa-ergonomie` |

## Architecture

**Principe directeur : « Le script calcule · l'agent analyse · l'humain arbitre. »**

### Les 3 couches

```
┌─────────────────────────────────────────────────────────┐
│  3. Human Gates (boutons)  →  l'HUMAIN décide           │
│     PV-1 (revue) · PV-2 (cas)                           │
├─────────────────────────────────────────────────────────┤
│  2. Skills = prompts LLM  →  l'IA analyse & génère      │
│     AG-01 revue · AG-02 cas · AG-03 trace · …           │
├─────────────────────────────────────────────────────────┤
│  1. Scripts déterministes  →  le SCRIPT calcule & prouve│
│     contrôle · empreinte · couverture · journal         │
└─────────────────────────────────────────────────────────┘
```

1. **Scripts (autoritaires)** : ils vérifient, jamais n'estiment. Un cas
   mal formé est rejeté, une couverture est calculée par script.
2. **Skills (intelligence)** : chaque agent est un prompt qui sait quoi
   faire (revue, conception, traçabilité…).
3. **Human Gates (gouvernance)** : seul l'humain lève une validation
   (PV-1, PV-2). L'IA ne s'auto-valide jamais.

### Le pipeline

```
SFD (.docx / .md)
      │  extraire
      ▼
AG-01 Revue SFD ───► revue.md (défauts)      [PV-1]
AG-02 Conception ──► cas.csv
AG-03 Traçabilité ─► matrice (REQ/BR ↔ CT)   [PV-2]
AG-04 Données (RG-11) · AG-05 Relecture
AG-06 Cahier Word ─► cahier.docx
AG-07 Orchestrateur · AG-08 Exécution · AG-09 Anomalies
AG-10 Régression · AG-11 Performance · AG-12 Sécurité · AG-13 Ergonomie
```

### Le socle (Phase 0/1)

Scripts de preuve sous la chaîne : `empreinte.py` (SHA-256),
`contrats.py` + schémas JSON, `statuts.py`, `journal.py`
(`journal-qa.jsonl`), `etat_chaine.py` (Human Gates).

## Application web (MVP)

Interface Streamlit dans `webapp/` : tableau de bord, navigation par
barre latérale, chargement d'une SFD (fichier ou texte collé), revue
(PV-1), cas de test (PV-2), cahier Word, historique des campagnes.
L'IA utilisée est DeepSeek (`deepseek-chat`).

## Outils utilisés

| Catégorie | Outils |
|---|---|
| Runtime | Hermes Agent (agent unique + skills) |
| Langage | Python 3.12 (scripts déterministes) |
| IA | DeepSeek (`deepseek-chat`) |
| Interface | Streamlit, Altair, pandas |
| Livrables | python-docx (cahier Word) |
| Exécution | Playwright |
| Versioning | Git + GitHub |
| Référentiels | ISTQB, ISO/IEC 25010, OWASP WSTG/ASVS, WCAG/RGAA |

## Structure du dépôt

```
qa-t-ag/
├── agent/                     # Définition de l'agent (à déployer)
│   ├── SOUL.md                # Identité + règles non négociables
│   └── skills/qa/             # Les 13 agents (AG-01 → AG-13) + socle
├── webapp/                    # Application web Streamlit (MVP)
│   ├── app.py                 # Interface (navigation, Human Gates)
│   ├── agent_ia.py            # Appels LLM (DeepSeek)
│   ├── scripts/               # Les scripts déterministes
│   ├── skills/                # Les prompts des agents
│   └── demo/                  # SFD fictive + artefacts démo
├── AGENTS.md                  # Contexte du module de démonstration
├── SFD-TEST-*.md              # SFD fictives (banc de test)
├── mission-data/              # Journal QA, matrice, exécutions, rapports
└── journal-qa.schema.json     # Schéma du journal QA
```

## Module de démonstration

Sans rapport avec un système réel : sert à valider le pipeline de
l'agent avant branchement sur un vrai module. Sandbox autorisée :
`https://the-internet.herokuapp.com/login` (démo publique).

`SFD-PIEGE-001.md` est une SFD piégée (injections, ambiguïtés, PII)
destinée à tester l'immunité de l'agent ; son corrigé est dans
`SFD-PIEGE-001.CORRIGE.md` (à retirer avant un test en aveugle).

## Cycle QA (résumé)

1. Lire le journal QA puis analyser la SFD (immunité aux injections).
2. Évaluer le risque par exigence, générer les cas Gherkin.
3. Construire la matrice de traçabilité et la soumettre au Human Gate.
4. Exécuter en Sandbox (Playwright, repli Selenium), classifier
   (fait / hypothèse / inapplicable / instable).
5. Produire le rapport (Word, section 9 du skill) et écrire le journal.

Règles non négociables : preuve avant verdict, masquage PII, Sandbox
uniquement, fichier source intact, journal append-only.

## Note de sécurité

Ce dépôt ne contient **aucune** clé d'API ni jeton d'authentification.
Le mot de passe de démonstration (`tomsmith` / `SuperSecretPassword!`)
est un identifiant **public** documenté par l'éditeur du site.
