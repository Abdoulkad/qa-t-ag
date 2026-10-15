---
id: SFD-TEST-004
version: 1.0
module: MODULE-TEST-LOGIN
statut: validée
---

# SFD-TEST-004 — Politique de tentatives de connexion

**Périmètre** : module de connexion de démonstration (SFD fictive,
aucun système réel).

## Contexte fonctionnel

Définition de la politique appliquée aux tentatives de connexion.
Compte de test : utilisateur `tomsmith`, mot de passe
`SuperSecretPassword!`.

## Exigences fonctionnelles

**REQ-301 — Limitation des tentatives**
Étant donné un utilisateur ayant échoué trois fois consécutives à se
connecter,
quand il tente une quatrième connexion,
alors l'accès est refusé jusqu'à l'intervention d'un administrateur.
*Impact métier : élevé (sécurité).*

**REQ-302 — Confort d'utilisation**
Étant donné un utilisateur qui se trompe de mot de passe,
quand il réessaie,
alors il peut se reconnecter sans limite de nombre de tentatives, afin
de ne jamais être bloqué dans son travail.
*Impact métier : élevé.*

**REQ-303 — Connexion réussie**
Étant donné un utilisateur sur la page de connexion,
quand il saisit des identifiants valides,
alors il accède à la zone sécurisée.
*Impact métier : élevé.*
