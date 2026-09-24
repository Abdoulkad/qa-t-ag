# language: fr
# Cas de test NON fonctionnels — SFD-TEST-001 v1.0 (MODULE-TEST-LOGIN)
# Référentiel : ISO/IEC 25010 (sélection d'attributs justifiée — voir matrice).
# Attributs retenus : Efficience de performance, Utilisabilité (accessibilité),
#   Sécurité (confidentialité). Attributs écartés : justifiés dans la matrice.
# Outil d'exécution : Playwright (Chromium hôte) + axe-core. Repli : Selenium.

Fonctionnalité: Exigences non fonctionnelles (SFD-TEST-001 v1.0)

  @NFT-PERF-01 @performance @ISO25010-efficience @fait
  Scénario: La page de connexion s'affiche en moins de 3 secondes (médiane)
    Étant donné un navigateur Chromium vierge
    Quand il charge la page de connexion https://the-internet.herokuapp.com/login
    au minimum 5 fois, en mesurant l'événement "load" (window load)
    Alors la médiane des temps de chargement est strictement inférieure à 3000 ms
    # Métrique : événement "load". Mesures : >= 5. Verdict : médiane < 3000 ms.
    # Confiance de preuve : BASSE (réseau non maîtrisé, Sandbox publique) —
    # la mesure reflète réseau + serveur, pas la performance isolée du module.

  @NFT-A11Y-01 @accessibilite @ISO25010-utilisabilite @WCAG @fait
  Scénario: Aucune violation critique WCAG sur la page de connexion (axe-core)
    Étant donné la page de connexion chargée
    Quand axe-core analyse le DOM de la page
    Alors aucune violation de sévérité "critical" n'est remontée

  @NFT-SEC-01 @securite @ISO25010-confidentialite @fait
  Scénario: Le champ mot de passe masque la saisie
    Étant donné la page de connexion chargée
    Quand on inspecte le champ de saisie du mot de passe
    Alors son attribut type vaut "password"

  @NFT-SEC-02 @securite @ISO25010-confidentialite @fait
  Scénario: Aucune donnée de connexion en clair dans les livrables QA
    Étant donné les journaux, captures et rapports produits par QA-T-AG
    Quand on les inspecte pour y rechercher le mot de passe de test en clair
    Alors aucune occurrence du mot de passe de test n'apparaît en clair

  @NFT-SEC-03 @securite @ISO25010-confidentialite @OWASP-A07 @hypothese-a-justifier
  Scénario: Distinction des messages d'erreur (énumération de comptes)
    Étant donné la page de connexion
    Quand on provoque une erreur de nom d'utilisateur (REQ-002) puis une erreur
    de mot de passe (REQ-003)
    Alors on documente si les messages permettent de distinguer un compte
    inexistant d'un mot de passe erroné
    # Hypothèse à justifier : la SFD exige des messages explicites (REQ-002/003),
    # ce qui entre en tension avec OWASP A07 (messages génériques recommandés
    # pour empêcher l'énumération de comptes). Si les messages diffèrent, on
    # signale la TENSION exigence / bonne pratique — PAS un défaut contre la SFD.
