# AGENTS.md — Contexte de projet QA-T-AG (module de test)

Module de démonstration, sans rapport avec un système réel — sert
uniquement à valider le pipeline complet de QA-T-AG avant de le
brancher sur un vrai module.

Ce fichier vit à la racine de ce dépôt (git). Hermès le charge
automatiquement au démarrage de session (fichier de contexte de projet
standard). Il décrit ce qui est spécifique à **ce module**. La logique
générale de QA-T-AG (workflow, classification, escalade) vit dans le
skill `qa-t-ag-core`, chargé automatiquement en tête de toute analyse de
SFD.

## Déclenchement

- **Mode interactif** : lancer une session Hermès dans ce dépôt et
  demander l'analyse de `SFD-TEST-001.md`.
- **Mode autonome** : non testé à cette étape — viendra une fois le
  cycle interactif validé.

## Sandbox validée pour ce module

- `https://the-internet.herokuapp.com/login` — site public de
  démonstration pour l'automatisation de tests (Elemental Selenium),
  aucune donnée réelle, comportement stable et documenté.

Aucune autre URL n'est autorisée pour ce module.

## Dépôt de code du module

- Non applicable — module de démonstration public, pas de dépôt
  interne à consulter pour ce test.

## Compte de test

- Utilisateur : `tomsmith`
- Mot de passe : `SuperSecretPassword!`
- Ce compte est public, documenté par l'éditeur du site de
  démonstration — ce n'est pas une donnée sensible.

## Particularité connue de l'environnement

Ce site ne persiste pas la session entre plusieurs contextes de
navigateur. Voir la note dans `SFD-TEST-001.md` — un scénario qui en
dépendrait doit être classé inapplicable, pas en échec.

## Séquence de démarrage, dans l'ordre

1. Lire `mission-data/journal-qa.jsonl` de ce module (vide au premier
   cycle — c'est normal).
2. Charger le skill `qa-t-ag-core`.
3. Vérifier les entrées minimales : SFD identifiée ✓ (`SFD-TEST-001`,
   v1.0), périmètre défini ✓ (5 exigences fonctionnelles listées),
   Sandbox valide ✓ (ci-dessus).

## Fichiers de ce dépôt

| Fichier | Rôle |
|---|---|
| `AGENTS.md` | Ce fichier |
| `SFD-TEST-001.md` | La SFD fictive à analyser |
| `mission-data/journal-qa.jsonl` | Créé au premier cycle |
| `mission-data/MISSION-DATA.md` | Conventions (identiques à tout module) |
