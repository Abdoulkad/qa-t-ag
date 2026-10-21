# QA-T-AG — Application web v1.0.0 (conception)

*L'IA au service de la qualité logicielle.*

Première version de l'application web QA-T-AG (FastAPI + React +
PostgreSQL). Elle couvre le cycle de **conception des tests**, de
l'exigence jusqu'aux cas validés : Analyser → Clarifier → Réécrire →
**PV-1** → Concevoir → **PV-2**. La recette (exécution, preuves,
anomalies, cahier de recette) est prévue pour la version suivante.

Principe : **le script calcule · l'agent analyse · l'humain arbitre.**
Les règles sont appliquées par le serveur ; l'interface ne fait que les
refléter.

## Ce que fait la v1.0

**Analyser (AG-01, grille QA-REV-02)**
- Revue d'une SFD ou d'une User Story, saisie ou déposée (.txt, .md, .docx, .pdf ; 10 Mo).
- Neuf catégories de défauts, dont contradiction certaine / apparente et cas limite à confirmer.
- Chaque défaut : citation vérifiée mot pour mot par script, constat, criticité justifiée, question neutre.
- Questions complémentaires sur les règles absentes du texte.
- Validation humaine de chaque défaut : confirmer, écarter (motif), requalifier (motif).
- Score de clarté calculé par script sur les défauts retenus.

**Clarifier**
- Réponses métier tracées (auteur, date), précisions humaines.
- Questions déclarées hors périmètre ou reportées, avec motif ; traitement par lot.

**Réécrire**
- User Story réécrite, **règles métier** (RG-n) et **critères d'acceptation** (CA-n) séparés.
- Aucune règle inventée : toute source est vérifiée ; une seule source non valable fait une hypothèse.
- Contrôle de couverture : chaque phrase du texte d'origine doit être reprise ou justifiée.
- Points ouverts affichés au décideur de PV-1.

**Concevoir (AG-02, AG-03)**
- Cas de test au format 12 colonnes, technique justifiée, statut calculé (prêt, incomplet, à clarifier).
- Traçabilité RG → CA → CT et taux de couverture.
- Export Word du cahier des cas au gabarit DSI (brouillon avant PV-2, validé après), empreinte au journal.

**Human Gates et traçabilité**
- PV-1 et PV-2 avec règles de décision (auto-validation tracée quand on est seul sur la mission).
- Journal QA chaîné (SHA-256), en ajout seul, protégé par la base ; auteur de chaque action.
- Trois rôles cumulables : Analyste QA, Superviseur, Administrateur.

**IA configurable**
- DeepSeek, OpenAI, Mistral, Anthropic, Ollama (local, sans clé) ; choix dans la configuration.
- Réponses en continu, nouvelles tentatives sur coupure, longueur de réponse réglable (`IA_MAX_TOKENS`).

**Interface**
- Mission découpée en étapes, colonne « Prochaine étape », vue de pilotage, suivi des cas,
  barre d'en-tête avec fil d'Ariane et profil, logo et identité visuelle.

## Règles et tests

- 50 règles métier (RA-01 à RA-50) dans `docs/specifications.md`, chacune reliée à ses tests (§ 12).
- 122 tests automatiques côté serveur, auto-tests des scripts de contrôle.
- 5 migrations de base de données (0001 à 0005), applicables sur une base existante.

## Installer ou mettre à jour

Voir `app/backend/README.md` (installation Windows pas à pas, mises à jour, tests).
Depuis une installation précédente : `git pull`, `alembic upgrade head`, `npm run build`,
puis redémarrer le serveur.

## Limites connues

- **Recette absente** : exécution des cas, preuves, anomalies et cahier de recette arrivent en v1.1.
- **Confidentialité** : avec un fournisseur d'IA en ligne, le texte des exigences quitte le poste.
  Pour des exigences réelles, privilégier Ollama (local) ou un fournisseur validé, ou anonymiser.
- **Sécurité avant partage** : en-têtes HTTP de sécurité (CSP, X-Frame-Options), limitation des
  tentatives de connexion, HTTPS et sauvegardes restent à mettre en place avant un déploiement multi-utilisateur.
- **Qualité des agents non mesurée** : les tests vérifient l'application des règles, pas la
  pertinence des défauts trouvés ; un jeu d'évaluation sur des exigences réelles anonymisées est prévu.
- **Pas de mot de passe oublié** ni de connexion Google ou de compte de démonstration.
- Scripts et skills encore en double entre `agent/` (agent Hermes) et `webapp/`.
- L'ancienne application Streamlit (`webapp/app.py`) n'est plus maintenue.
