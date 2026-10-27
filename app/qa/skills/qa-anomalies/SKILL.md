---
name: qa-anomalies
description: "Use when analyzing execution results into anomalies."
---

# AG-09 — Analyse des anomalies

## Mission

Lire les résultats d'exécution (AG-08) et les livrables V1 pour identifier et
consigner les anomalies dans un registre traçable. L'agent analyse et propose ;
le script contrôle le format du registre.

## Préconditions

- Résultats d'exécution `resultats-<projet>.csv` (AG-08) disponibles.
- Les cas de test référencés existent dans le livrable AG-02.

## Connaissances

- Sévérité : mineure, majeure, critique, bloquante.
- Reproductibilité : systématique, intermittente, non reproductible.
- Statut de traitement : ouverte, assignée, corrigée, retestée, fermée.

## Outils

- `scripts/controler_anomalies.py` (contrôle de format du registre).
- Read / Grep / Glob / Write.

## Données

- Entrée : `resultats-<projet>.csv` (AG-08), livrables AG-02/AG-03.
- Sortie : `anomalies-<projet>.csv` (`ID;CT;Severite;Reproductibilite;Traitement`).

## Contrat

`controler_anomalies.py <anomalies.csv>` → 0 conforme / 1 incohérences /
2 inexploitable / 3 défaut.

## Contraintes

- Chaque anomalie référence un CT existant (`CT-xxx`) ; un `ANO-xxx` est
  **unique**.
- La sévérité est justifiée par le résultat constaté, jamais exagérée ni
  minimisée : l'agent explique, l'humain arbitre.
- Aucune donnée personnelle (PII) dans la description d'une anomalie.
