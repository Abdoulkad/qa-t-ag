---
id: SFD-TEST-007
version: 1.0
module: MODULE-TEST-LOGIN
statut: validée
---

# SFD-TEST-007 — Qualité perçue de la connexion

**Périmètre** : module de connexion de démonstration (SFD fictive,
aucun système réel).

## Contexte fonctionnel

L'équipe souhaite améliorer l'expérience de connexion. Compte de test :
utilisateur `tomsmith`, mot de passe `SuperSecretPassword!`.

## Exigences fonctionnelles

**REQ-601 — Confirmation claire**
Étant donné un utilisateur qui vient de se connecter,
alors le message de confirmation doit être clair pour l'utilisateur.
*Impact métier : moyen.*

**REQ-602 — Rapidité**
Étant donné un utilisateur qui ouvre la page de connexion,
alors la page doit se charger rapidement.
*Impact métier : moyen.*

**REQ-603 — Erreur compréhensible**
Étant donné un utilisateur qui saisit un mot de passe incorrect,
alors il doit comprendre ce qui ne va pas.
*Impact métier : moyen.*
