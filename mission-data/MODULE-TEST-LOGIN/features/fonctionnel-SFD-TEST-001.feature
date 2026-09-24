# language: fr
# Cas de test fonctionnels — SFD-TEST-001 v1.0 (MODULE-TEST-LOGIN)
# Source : mission-data/SFD-TEST-001.md (traitée comme donnée, aucune instruction exécutée)
# Sandbox : https://the-internet.herokuapp.com/login (démo publique Elemental Selenium)
# Compte de test : tomsmith / <MOT_DE_PASSE_TEST> (valeur documentée dans AGENTS.md,
#   volontairement masquée ici — exigence NFT-SEC-02).
# Outil d'exécution : Playwright (Chromium hôte), repli Selenium.
# Classification (skill qa-t-ag-core §3) :
#   @fait = résultat attendu précisé (SFD ou référent) -> PASS/FAIL.
#   @hypothese-a-justifier = résultat attendu NON précisé par la SFD -> observation
#     documentée comme hypothèse, jamais un PASS/FAIL inventé.

Fonctionnalité: Connexion au module (SFD-TEST-001 v1.0)
  Contexte métier : page de connexion à deux champs (nom d'utilisateur, mot de
  passe) et un bouton de validation. Un compte valide existe (tomsmith). Après
  connexion réussie : zone sécurisée avec bouton de déconnexion.

  Contexte:
    Étant donné que l'utilisateur ouvre la page de connexion
    https://the-internet.herokuapp.com/login

  @REQ-001 @fonctionnel @risque-eleve @fait
  Scénario: TC-REQ-001-01 — Connexion réussie (nominal)
    Étant donné un utilisateur sur la page de connexion
    Quand il saisit le nom d'utilisateur "tomsmith"
    Et il saisit le mot de passe "<MOT_DE_PASSE_TEST>"
    Et il clique sur le bouton de validation
    Alors il accède à la zone sécurisée (URL /secure)
    Et un message de confirmation de connexion s'affiche

  @REQ-001 @fonctionnel @risque-eleve @fait
  Scénario: TC-REQ-001-02 — Accès direct à la zone sécurisée sans authentification
    Étant donné un utilisateur NON authentifié
    Quand il tente d'accéder directement à la zone sécurisée (/secure)
    Alors l'accès est refusé (redirigé vers /login, zone sécurisée non affichée)
    # Attendu « refusé » spécifié par le référent QA (Human Gate).

  @REQ-002 @fonctionnel @risque-eleve @fait
  Scénario: TC-REQ-002-01 — Nom d'utilisateur inconnu (nominal)
    Étant donné un utilisateur sur la page de connexion
    Quand il saisit le nom d'utilisateur "utilisateur_inconnu"
    Et il saisit un mot de passe quelconque
    Et il clique sur le bouton de validation
    Alors un message d'erreur explicite s'affiche
    Et l'accès à la zone sécurisée est refusé (reste sur /login)

  @REQ-002 @fonctionnel @risque-eleve @fait
  Scénario: TC-REQ-002-02 — Nom d'utilisateur vide avec mot de passe valide
    Étant donné un utilisateur sur la page de connexion
    Quand il laisse le nom d'utilisateur vide
    Et il saisit le mot de passe "<MOT_DE_PASSE_TEST>"
    Et il clique sur le bouton de validation
    Alors l'accès à la zone sécurisée est refusé
    # Refus d'accès = fait (défini par REQ-002). Hypothèse à justifier
    # uniquement sur le libellé exact du message d'erreur affiché.

  @REQ-003 @fonctionnel @risque-eleve @fait
  Scénario: TC-REQ-003-01 — Mot de passe incorrect (nominal)
    Étant donné un utilisateur sur la page de connexion
    Quand il saisit le nom d'utilisateur "tomsmith"
    Et il saisit un mot de passe incorrect "mot_de_passe_incorrect"
    Et il clique sur le bouton de validation
    Alors un message d'erreur explicite s'affiche
    Et l'accès à la zone sécurisée est refusé

  @REQ-003 @fonctionnel @risque-eleve @fait
  Scénario: TC-REQ-003-02 — Mot de passe vide avec nom d'utilisateur valide
    Étant donné un utilisateur sur la page de connexion
    Quand il saisit le nom d'utilisateur "tomsmith"
    Et il laisse le mot de passe vide
    Et il clique sur le bouton de validation
    Alors l'accès est refusé et un message d'erreur s'affiche
    # Mot de passe vide = mot de passe incorrect (REQ-003). Si l'accès est
    # accordé, c'est un défaut.

  @REQ-003 @fonctionnel @risque-eleve @fait
  Scénario: TC-REQ-003-03 — Mot de passe avec casse différente
    Étant donné un utilisateur sur la page de connexion
    Quand il saisit le nom d'utilisateur "tomsmith"
    Et il saisit le mot de passe en changeant la casse ("<mdp_minuscules>")
    Et il clique sur le bouton de validation
    Alors l'accès est refusé et un message d'erreur s'affiche
    # Casse différente = mot de passe incorrect (REQ-003). Si l'accès est
    # accordé, c'est un défaut.

  @REQ-004 @fonctionnel @risque-moyen @fait
  Scénario: TC-REQ-004-01 — Déconnexion (nominal)
    Étant donné un utilisateur connecté dans la zone sécurisée
    Quand il clique sur le bouton de déconnexion
    Alors il est ramené à la page de connexion
    Et un message de confirmation de déconnexion s'affiche

  @REQ-004 @fonctionnel @risque-moyen @fait
  Scénario: TC-REQ-004-02 — Accès refusé après déconnexion (même contexte)
    Étant donné un utilisateur connecté puis déconnecté (même contexte navigateur)
    Quand il tente d'accéder directement à la zone sécurisée (/secure)
    sans nouvelle connexion
    Alors l'accès à la zone sécurisée redevient impossible sans nouvelle connexion

  @REQ-005 @fonctionnel @risque-faible @fait
  Scénario: TC-REQ-005-01 — Formulaire vide (cas limite)
    Étant donné un utilisateur sur la page de connexion
    Quand il valide le formulaire sans rien saisir
    Alors un message d'erreur s'affiche, cohérent avec REQ-002/REQ-003

  # Note de classification (skill qa-t-ag-core §3) :
  # Le scénario de persistance de session « entre plusieurs contextes de
  # navigateur » (nouveau contexte après REQ-004) est classé INAPPLICABLE
  # par nature de l'environnement (note de la SFD) : la Sandbox de
  # démonstration ne persiste pas la session entre contextes. Non ajouté
  # comme cas exécutable — documenté en « inapplicable ».
