# mission-data/ — Conventions

Ce dossier contient tout ce que QA-T-AG lit et écrit **pour un module
donné**. Rien ici n'est propre à l'agent : c'est la mémoire du projet, y
compris pour les autres agents de l'écosystème (BA-AG, Dev-AG) — voir
`README.md`, § Décision d'architecture.

## Structure attendue, par module

```
mission-data/
├── journal-qa.schema.json          # schéma + exemples (ce dossier)
├── <module>/
│   ├── journal-qa.jsonl            # append-only, jamais réécrit
│   ├── features/                   # cas de test .feature (fonctionnels + non fonctionnels)
│   ├── traceability-matrix.json    # exigence→test, attribut→test
│   ├── executions/                 # logs d'exécution Sandbox, par execution_id
│   ├── defects/                    # fiches d'anomalies
│   └── reports/                    # rapports de recette signés au Human Gate
```

## Données lues, écrites, jamais touchées (spec §9)

**Lit** : SFD, User Stories, maquettes, règles métier, code source du
dépôt ciblé (lecture seule), historique du journal QA, jeux de test
dédiés ou données déjà masquées.

**Écrit** : fichiers `.feature`, matrice de traçabilité, fiches
d'anomalies, rapport de recette, logs d'exécution Sandbox, entrées du
journal QA (append).

**Ne touche jamais** :
- une base ou un environnement de production ;
- une PII réelle, en entrée comme en sortie — masquage systématique
  avant toute écriture ;
- un fichier source de la SFD ou du code — lecture seule stricte ;
- une entrée existante du journal QA — append-only, une correction se
  fait par une nouvelle entrée référencée, jamais un écrasement.

Aucune suppression. DELETE non accordé (`config.yaml`, `permissions`).

## Rétention

- `executions/` et `reports/` : conservés 90 jours, purge automatique
  ensuite.
- `journal-qa.jsonl` : **jamais purgé** — c'est la mémoire longue du
  module.

## Preuves (spec §19)

Chaque verdict publié dans un rapport référence :
- le fichier `.feature` exécuté ;
- le log d'exécution correspondant (`executions/<execution_id>/`) ;
- pour un résultat qui pèse sur la conclusion (couverture proche du
  seuil, anomalie critique) : la trace du second chemin de vérification.

Ce que le rapport contient, au minimum :
- rapport d'analyse de sécurité de la SFD ;
- cas de test anonymisés (`.feature`) ;
- matrice de traçabilité, calcul de couverture horodaté et scripté ;
- logs d'exécution référencés depuis chaque verdict ;
- fiches d'anomalies classées fait / hypothèse / inapplicable / instable,
  sévérité et priorité séparées ;
- rapport de recette signé au Human Gate ;
- entrées du journal QA du cycle.

## Identifiants

Pour que tout artefact soit reliable à son origine :
- `module_id` : identifiant du module.
- `execution_id` : un par exécution de test (horodaté).
- `test_id` : un par cas de test, stable d'un cycle à l'autre.
- `defect_id` : un par anomalie confirmée, jamais réutilisé même si
  l'anomalie est fermée.
