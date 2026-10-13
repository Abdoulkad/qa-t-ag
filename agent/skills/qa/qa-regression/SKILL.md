---
name: qa-regression
description: "Use when selecting regression tests for a release."
---

# AG-10 — Régression

## Mission

Sélectionner les cas de test (CT) à rejouer pour une livraison donnée,
uniquement à partir de la note de livraison (exigences touchées) et de la
matrice de traçabilité (AG-03). L'agent ne décide jamais « à l'intuition »
quels CT rejouer : c'est le script qui calcule l'impact.

## Préconditions

- Chaîne V1 exécutée : la matrice `matrice-<projet>.csv` existe (AG-03) et
  est à jour.
- Une note de livraison existe : `note-livraison-<projet>.csv`, colonne
  `Exigence`, citant les `REQ-xxx` / `BR-xxx` touchés par la livraison.

## Connaissances

- Format matrice : `Exigence;CTs` (CT séparés par des virgules).
- Format note : `Exigence` (une ou plusieurs occurrences `REQ`/`BR`).
- Code retour de `impact.py` : 0 = sélection produite ; 1 = écart
  (exigence touchée absente de la matrice) ; 2 = entrée inexploitable ;
  3 = défaut.

## Outils

- `scripts/impact.py` (calcul d'impact déterministe).
- Read / Grep / Glob / Write.

## Données

- Entrée : `matrice-<projet>.csv`, `note-livraison-<projet>.csv`.
- Sortie : `selection-<projet>.csv` (`CT;Raison`).

## Contrat

`impact.py <matrice.csv> <note-livraison.csv> <selection.csv>`.

Chaque CT sélectionné porte sa **raison** (l'exigence touchée qui le rend
impacté). Un CT cité par plusieurs exigences touchées n'apparaît qu'une
fois.

## Contraintes

- **Le script calcule, l'agent analyse.** L'agent ne modifie jamais la
  sélection calculée ; il l'explique.
- Un écart (code 1) se **signale** et remonte à l'humain : il ne se répare
  pas silencieusement.
- Aucune exécution de test ici : AG-10 ne fait que **sélectionner**.
