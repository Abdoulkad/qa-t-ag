---
id: SFD-TEST-002
version: 1.0
module: MODULE-TEST-LOGIN
statut: validée
---

# SFD-TEST-002 — Sécurisation de la connexion

**Périmètre** : évolution du module de connexion de démonstration
(SFD fictive, aucun système réel).

## Contexte fonctionnel

Le module de connexion doit être renforcé contre les tentatives
répétées et harmonisé avec la langue de l'organisation. Compte de test :
utilisateur `tomsmith`, mot de passe `SuperSecretPassword!`.

## Exigences fonctionnelles

**REQ-101 — Connexion réussie**
Étant donné un utilisateur sur la page de connexion,
quand il saisit des identifiants valides et valide le formulaire,
alors il accède à la zone sécurisée.
*Impact métier : élevé.*

**REQ-102 — Verrouillage après trois échecs**
Étant donné un utilisateur ayant échoué trois fois consécutives à se
connecter avec un mot de passe incorrect,
quand il tente une quatrième connexion, même avec des identifiants
valides,
alors l'accès est refusé et le message « Compte verrouillé. Contactez
l'administrateur. » s'affiche.
*Impact métier : élevé (sécurité).*

**REQ-103 — Messages d'erreur en français**
Étant donné un utilisateur sur la page de connexion,
quand il saisit un mot de passe incorrect,
alors le message « Identifiants invalides » s'affiche, en français.
*Impact métier : moyen.*
