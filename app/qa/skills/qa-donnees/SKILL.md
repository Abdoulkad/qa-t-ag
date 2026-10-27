---
name: qa-donnees
description: "Use when inventorying and validating test data (RG-11)."
version: 0.1.0
metadata:
  hermes:
    tags: [qa, qa-t-ag, donnees, test, rg11, ag04]
    category: qa
---

# AG-04 — Données de test

Inventorie les données des cas de test, les contrôle contre RG-11, et fournit
le jeu de recette. Ne crée ni ne modifie jamais une valeur.

## Rôle

Inventaire et contrôle des données de test. Le script produit le jeu de
recette et les écarts ; l'agent écrit le dictionnaire et les valeurs.

## RG-11 (données fictives, reconnaissables, exactes)

- Champs texte désignant une personne/entreprise/adresse/libellé/commentaire :
  contiennent `TEST`.
- Identifiants numériques et RIB : commencent par `99`.
- Montants, dates, périodes, statuts : libres.

## Formats (grammaire fermée)

- `dictionnaire-<projet>.csv` : `Champ;Catégorie` — Catégorie ∈ {texte,
  identifiant, montant, date, statut}.
- `valeurs-<projet>.csv` : `CT;Champ;Valeur` — une ligne par valeur, recopiée
  mot pour mot depuis le CT.

## Script

`python scripts/donnees.py <sfd> <cas.csv> <dictionnaire.csv> <valeurs.csv>` :
- vérifie chaque valeur présente mot pour mot dans son CT (E11) ;
- contrôle RG-11 (texte → TEST, identifiant → 99) ;
- écrit `td-<projet>.csv` (jeu de recette) et `ecarts-donnees-<projet>.csv`.
- Codes : 0 = aucun écart, 1 = des écarts, 2 = format invalide, 3 = défaut.

## Contraintes

- **LLM02** : aucune donnée réelle. **LLM09** : chaque valeur vient d'un CT,
  mot pour mot ; aucun écart inventé.
- Ne jamais créer ni compléter une valeur.

## Livrables

- `dictionnaire-<projet>.csv`, `valeurs-<projet>.csv` (par l'agent).
- `td-<projet>.csv`, `ecarts-donnees-<projet>.csv` (par le script).
- `rapport-donnees-<projet>.md` (par l'agent).
