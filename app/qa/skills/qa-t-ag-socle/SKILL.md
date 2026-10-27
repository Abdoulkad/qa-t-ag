---
name: qa-t-ag-socle
description: "Use when a QA-T-AG statut ou contrat doit être calculé."
version: 0.2.0
metadata:
  hermes:
    tags: [qa, qa-t-ag, socle, deterministe, statuts, empreinte, contrats, journal, transitions]
    category: qa
---

# QA-T-AG — Socle déterministe (Phase 0/1)

Briques déterministes que la SFD QA-T-AG V2.0 impose de calculer par
script, jamais par le modèle. Principe : « Le script calcule, l'agent
analyse, l'humain arbitre. »

Ce skill est nouveau (créé par l'agent, approuvé par l'humain). Il ne
modifie pas `qa-t-ag-core` (user-owned). Il couvre la Phase 0/1 du plan
de migration (§13) : statuts, empreintes, contrats, journal, transitions.

## Briques

| Briques | Script | Réf. SFD | Défaut résolu |
|---|---|---|---|
| Statuts normalisés (agent / test / campagne) | `scripts/statuts.py` | §6.2, §7.1, §9.1 | DEF-001 |
| Empreinte SHA-256 des artefacts | `scripts/empreinte.py` | §6.1 | — |
| Contrats JSON Schema (enveloppes entrée/sortie) | `scripts/contrats.py` + `schemas/` | §6.1, §6.2 | DEF-005 (`attempt_id`) |
| Journal append-only (UTC, cycle_commence idempotent) | `scripts/journal.py` | §9, §8.2, §10 | — |
| Transitions de campagne + route V1 (2 portes) | `scripts/etat_chaine.py` | §7.1, §5.2 | hypothèse tracée |
| Manifeste de campagne (empreintes ↔ livrables) | `scripts/manifeste.py` | §6, §7.3 | invalidation cascade |
| Portes de validation (PV-1, PV-2) | `scripts/pv.py` | §AG-07 | bloque si ≠ VALIDÉ |

## Vocabulaire canonique des statuts

| Domaine | Valeurs canoniques |
|---|---|
| Livrable d'agent | `OK`, `A_CLARIFIER`, `EN_ATTENTE`, `ERREUR`, `BLOQUE` |
| Résultat de test | `PASS`, `FAIL`, `BLOCKED`, `NOT_RUN`, `NON_CONCLUANT` |
| Campagne (nominal) | `BROUILLON`, `PREPAREE`, `EN_COURS`, `CONTROLES`, `ATTENTE_VALIDATION`, `VALIDEE`, `REJETEE`, `CLOTUREE` |
| Campagne (exception) | `BLOQUEE`, `ECHEC`, `ANNULEE`, `INCOMPLETE` |

Les libellés historiques (`À_CLARIFIER`, `BLOQUÉ`, `NON EXÉCUTÉ`,
`INCONCLUSIF`…) sont des alias convertis par `statuts.py` ; jamais écrits
directement dans un livrable.

## Usage

```bash
python scripts/statuts.py        # auto-test (27 cas)
python scripts/empreinte.py --selftest
python scripts/contrats.py       # auto-test (7 cas)
python scripts/journal.py        # auto-test (append-only, UTC)
python scripts/etat_chaine.py    # auto-test (11 cas campagne + chaîne V1)
python scripts/manifeste.py     # auto-test (invalidation cascade)
python scripts/pv.py --selftest
```

Règle : le modèle appelle ces fonctions et reporte la valeur renvoyée.
Un statut inconnu lève `ValueError` — jamais deviné ni fabriqué.
