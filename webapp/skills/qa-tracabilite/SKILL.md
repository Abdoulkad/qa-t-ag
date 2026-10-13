---
name: qa-tracabilite
description: "Use when tracing REQ/BR to test cases and finding gaps."
version: 0.1.0
metadata:
  hermes:
    tags: [qa, qa-t-ag, tracabilite, matrice, ecarts, ag03]
    category: qa
---

# AG-03 — Traçabilité

Construit la matrice REQ/BR ↔ CT et signale chaque trou, sans jamais le
combler. Troisième agent de la chaîne V1 (SFD §5.2, fiche AG-03).

## Rôle

Gardien de la chaîne de traçabilité. Le script calcule la matrice et les
écarts ; l'agent lit les sorties et rédige le rapport. Jamais l'inverse.

## Workflow

1. Repérer les entrées : une SFD, `cas-<projet>.csv`, `notes-<projet>.md`.
   Entrée absente ou ambigüe → `EN_ATTENTE` (ERR-01).
2. Lire le statut d'AG-02 (notes). `EN_ATTENTE`/`ERREUR` → arrêt (ERR-02).
3. Lancer `python scripts/tracer.py <sfd> <cas.csv>`. Codes :
   0 = aucun écart ; 1 = des écarts (cas normal) ; 2 = matrice impossible ;
   3 = défaut du script.
4. Lancer `python scripts/controler_cas.py <sfd> <cas.csv>` et comparer la
   ligne « Couverture » des deux scripts : elles doivent être identiques.
   Désaccord → `ERREUR` (ERR-10), aucun des deux ne fait foi.
5. Lire `ecarts-<projet>.csv` ; pour chaque écart, une phrase d'explication.
6. Écrire `rapport-<projet>.md` et poser le statut.

## Contraintes

- Ne jamais modifier la matrice, les écarts, ni un script.
- Ne jamais combler un trou (même en suggestion) : l'action se dit
  « Compléter les cas (AG-02) », jamais avec un CT proposé.
- Aucun écart hors de `ecarts-<projet>.csv`.
- Pas de jugement de qualité sur un CT (« bien testé », « non testable »).

## Catalogue des écarts (base déterministe)

- **E01** : exigence sans CT.
- **E02** : CT citant une exigence inconnue du SFD.
- **E03** : CT sans exigence citée.

Le catalogue complet T01-T12 reste à fixer par la DSI (SFD §16) ; ces trois
codes sont la base déterministe, pas un catalogue définitif.

## Script

`python scripts/tracer.py <sfd> <cas.csv>` écrit `matrice-<projet>.csv` et
`ecarts-<projet>.csv`, codes 0/1/2/3.

## Livrables

- `matrice-<projet>.csv`, `ecarts-<projet>.csv` (par le script).
- `rapport-<projet>.md` (par l'agent).
