# QA-T-AG — Agent QA/BA autonome

QA-T-AG transforme une exigence (SFD, User Story) en cas de test
fonctionnels et non fonctionnels (Gherkin, ISTQB), les exécute en
Sandbox isolée, et produit un verdict **prouvé** par des sorties
d'exécution — jamais affirmé.

## Structure du dépôt

```
qa-t-ag-test-module/
├── agent/                     # Définition de l'agent (à déployer)
│   ├── SOUL.md                # Identité + règles non négociables
│   └── skills/qa-t-ag-core/   # Workflow, classification, escalade,
│                              #   générateur de rapport Word (section 9)
├── AGENTS.md                  # Contexte du module de démonstration
├── SFD-TEST-*.md              # SFD fictives (banc de test)
├── mission-data/              # Journal QA, matrice, exécutions, rapports
│   └── MODULE-TEST-LOGIN/     # Livrables du cycle (append-only)
└── journal-qa.schema.json     # Schéma du journal QA
```

## Module de démonstration

Sans rapport avec un système CNPS réel : sert à valider le pipeline de
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
