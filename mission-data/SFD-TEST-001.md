---
id: SFD-TEST-001
version: 1.0
module: MODULE-TEST-LOGIN
statut: validée
---

# SFD-TEST-001 — Module de connexion (module de test QA-T-AG)

**Périmètre** : ceci est une SFD fictive, sur un module de démonstration
public (pas un système CNPS), utilisée uniquement pour valider le
fonctionnement de QA-T-AG avant de le brancher sur un vrai module.

## Contexte fonctionnel

Le module fournit une page de connexion avec deux champs (nom
d'utilisateur, mot de passe) et un bouton de validation. Un compte de
test valide existe : utilisateur `tomsmith`, mot de passe
`SuperSecretPassword!`. Après connexion réussie, l'utilisateur accède à
une zone sécurisée avec un bouton de déconnexion.

## Exigences fonctionnelles

**REQ-001 — Connexion réussie**
Étant donné un utilisateur sur la page de connexion,
quand il saisit un nom d'utilisateur et un mot de passe valides et
valide le formulaire,
alors il accède à la zone sécurisée et un message de confirmation
s'affiche.
*Impact métier : élevé (fonctionnalité d'entrée du module).*

**REQ-002 — Nom d'utilisateur invalide**
Étant donné un utilisateur sur la page de connexion,
quand il saisit un nom d'utilisateur inconnu (mot de passe quelconque)
et valide le formulaire,
alors un message d'erreur explicite s'affiche et l'accès est refusé.
*Impact métier : élevé (contrôle d'accès).*

**REQ-003 — Mot de passe invalide**
Étant donné un utilisateur sur la page de connexion, avec un nom
d'utilisateur valide,
quand il saisit un mot de passe incorrect et valide le formulaire,
alors un message d'erreur explicite s'affiche et l'accès est refusé.
*Impact métier : élevé (contrôle d'accès).*

**REQ-004 — Déconnexion**
Étant donné un utilisateur connecté dans la zone sécurisée,
quand il clique sur le bouton de déconnexion,
alors il est ramené à la page de connexion avec un message de
confirmation, et l'accès à la zone sécurisée redevient impossible sans
nouvelle connexion.
*Impact métier : moyen.*

**REQ-005 — Formulaire vide**
Étant donné un utilisateur sur la page de connexion,
quand il valide le formulaire sans rien saisir,
alors un message d'erreur s'affiche, cohérent avec REQ-002/REQ-003.
*Impact métier : faible (cas limite).*

## Exigences non fonctionnelles attendues

- **Performance** : la page de connexion doit s'afficher en moins de
  3 secondes.
- **Accessibilité** : aucune violation critique WCAG sur la page de
  connexion (axe-core).
- **Sécurité** : le champ mot de passe doit masquer la saisie
  (`type="password"`), aucune donnée de connexion ne doit apparaître en
  clair dans les journaux ou captures produits par QA-T-AG.

## Note connue sur l'environnement

Ce module de démonstration ne persiste pas la session entre plusieurs
contextes de navigateur — un scénario qui rouvrirait une nouvelle
session pour vérifier la persistance après REQ-004 échouera par nature
de l'environnement, pas par défaut du module. Si QA-T-AG rencontre ce
cas, il doit le classer **inapplicable**, avec cette explication —
c'est un bon test de la classification fait/hypothèse/inapplicable/
instable (skill `qa-t-ag-core`, section 3).
