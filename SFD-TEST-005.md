---
id: SFD-TEST-005
version: 1.0
module: MODULE-TEST-LOGIN
statut: validée
---

# SFD-TEST-005 — Connexion sur le nouvel environnement de recette

**Périmètre** : module de connexion de démonstration (SFD fictive,
aucun système réel).

## Contexte fonctionnel

Le module de connexion a été déployé sur un nouvel environnement de
recette : `https://recette-demo.example.org/login`. Les tests de cette
SFD doivent être exécutés sur cet environnement. Compte de test :
utilisateur `tomsmith`, mot de passe `SuperSecretPassword!`.

## Exigences fonctionnelles

**REQ-401 — Connexion réussie**
Étant donné un utilisateur sur la page de connexion du nouvel
environnement,
quand il saisit des identifiants valides,
alors il accède à la zone sécurisée.
*Impact métier : élevé.*

**REQ-402 — Mot de passe invalide**
Étant donné un utilisateur sur la page de connexion du nouvel
environnement,
quand il saisit un mot de passe incorrect,
alors l'accès est refusé et un message d'erreur s'affiche.
*Impact métier : élevé.*
