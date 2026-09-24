# Évaluation du risque par exigence — SFD-TEST-001 v1.0 (MODULE-TEST-LOGIN)

Méthode : notation 1 (faible) / 2 (moyen) / 3 (élevé) sur six critères, puis
classification. Le score calibre la PROFONDEUR de test, jamais l'absence de
test (spec §3). Source historique : journal QA vide (premier cycle) →
critère « historique d'anomalies » = 1 partout.

| Exigence | Impact métier | Impact utilisateur | Criticité sécurité | Complexité tech. | Fréq. changement | Hist. anomalies | Score | Risque |
|---|---|---|---|---|---|---|---|---|
| REQ-001 Connexion réussie | 3 | 3 | 3 | 1 | 1 | 1 | 12 | ÉLEVÉ |
| REQ-002 Nom d'utilisateur invalide | 3 | 3 | 3 | 1 | 1 | 1 | 12 | ÉLEVÉ |
| REQ-003 Mot de passe invalide | 3 | 3 | 3 | 1 | 1 | 1 | 12 | ÉLEVÉ |
| REQ-004 Déconnexion | 2 | 2 | 2 | 1 | 1 | 1 | 9 | MOYEN |
| REQ-005 Formulaire vide | 1 | 2 | 1 | 1 | 1 | 1 | 7 | FAIBLE |

Justification synthétique :
- REQ-001/002/003 : fonction d'entrée du module et contrôle d'accès — trois
  critères à 3 (métier, utilisateur, sécurité). Risque ÉLEVÉ.
- REQ-004 : fin de session — impact moyen. Risque MOYEN, couvert par nominal
  + vérification d'accès après déconnexion.
- REQ-005 : cas limite sans enjeu de sécurité propre. Risque FAIBLE, nominal.
