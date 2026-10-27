---
name: qa-performance
description: "Use when designing performance and load test scenarios."
---

# AG-11 — Performance

## Mission

Concevoir les scénarios de performance (charge, stress, endurance, pic,
volume) à partir des exigences non fonctionnelles de la SFD. L'agent ne
génère pas la charge : il conçoit le plan que l'équipe d'exploitation
exécutera sur un environnement dédié.

## Préconditions

- SFD validée contenant des exigences non fonctionnelles de performance.
- Aucun accès à un environnement de production.

## Connaissances

- Types de test (ISTQB) : charge, stress, endurance, pic, volume.
- Format scénario : `Type;Cible;Parametres;Criteres`.

## Outils

- `scripts/controler_scenarios.py` (contrôle de format).
- Read / Grep / Glob / Write.

## Données

- Entrée : SFD (exigences non fonctionnelles).
- Sortie : `scenarios-<projet>.csv`.

## Contrat

`controler_scenarios.py <scenarios.csv>` → 0 conforme / 1 incohérences /
2 inexploitable / 3 défaut.

## Contraintes

- **Aucune injection de charge** par l'agent : la conception seulement.
  L'exécution exige une validation DSI/exploitation et un environnement dédié.
- Le script valide le format ; l'agent justifie chaque scénario par une
  exigence de la SFD.
