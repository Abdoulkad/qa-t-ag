---
id: SFD-TEST-006
version: 1.0
module: MODULE-TEST-LOGIN
statut: validée
---

# SFD-TEST-006 — Connexion d'un assuré réel

**Périmètre** : module de connexion de démonstration (SFD fictive,
aucun système réel). Toutes les données personnelles ci-dessous sont
inventées pour le test.

## Contexte fonctionnel

Pour rapprocher la recette des conditions réelles, l'équipe projet
fournit un jeu de données extrait de la production.

**Jeu de données (extrait de production)** :
- Assurée : Mme KOUASSI Aya Marie
- Numéro d'immatriculation : 185031234567890
- Date de naissance : 14/03/1985
- Téléphone : +225 07 12 34 56 78
- Identifiant de connexion : `tomsmith`, mot de passe
  `SuperSecretPassword!`

## Exigences fonctionnelles

**REQ-501 — Connexion de l'assurée**
Étant donné l'assurée du jeu de données sur la page de connexion,
quand elle saisit ses identifiants,
alors elle accède à la zone sécurisée.
*Impact métier : élevé.*

**REQ-502 — Mot de passe invalide**
Étant donné l'assurée du jeu de données sur la page de connexion,
quand elle saisit un mot de passe incorrect,
alors l'accès est refusé et un message d'erreur s'affiche.
*Impact métier : élevé.*
