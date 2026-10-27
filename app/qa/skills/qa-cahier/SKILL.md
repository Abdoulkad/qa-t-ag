---
name: qa-cahier
description: "Use when generating the Word test case booklet."
version: 0.1.0
metadata:
  hermes:
    tags: [qa, qa-t-ag, cahier, word, docx, ag06]
    category: qa
---

# AG-06 — Cahier de test Word

Recopie le fichier des cas validé (PV-2) dans le gabarit Word de la DSI, sans
reformuler une seule cellule. Script déterministe : aucun modèle.

## Rôle

Producteur du cahier de cas de test au gabarit DSI. Un bloc par CT, priorité
et type cochés (☒), note dans Commentaires pour chaque CT À_CLARIFIER.

## Dépendance

Gabarit Word de la DSI (`modele-cahier-cas.docx`) : jetons {{ORGANISATION}},
{{ID}}, {{TITRE}}, {{OBJECTIF}}, {{PRECONDITIONS}}, {{DONNEES}}, {{ETAPE}},
{{EXIGENCE}}, {{P1/P2/P3}}, {{T1/T2/T3}}, {{RESULTAT}}, {{COMMENTAIRE}}.
Nécessite `python-docx` (`pip install python-docx`).

## Script

`python scripts/cahier_word.py <modele.docx> <cas.csv> <sortie.docx>` :
remplit {{ORGANISATION}}, un bloc par CT ; codes 0/2/3.

## Contraintes

- **LLM05** : le contenu des CT est recopié mot pour mot, jamais réécrit.
- Ne pas modifier la structure ni la mise en forme du gabarit.

## Livrables

`cahier-cas-<projet>.docx` (chemin fixe, remplacé à chaque exécution).
