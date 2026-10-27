# app/qa — scripts, consignes des agents et gabarits

Ce dossier porte la partie « métier QA » de l'application. Le backend
(`app/backend`) l'utilise tel quel : **le script calcule · l'agent analyse ·
l'humain arbitre.**

| Dossier | Contenu |
|---|---|
| `scripts/` | Scripts déterministes : ils contrôlent les sorties des agents, jamais ne les estiment. La plupart s'auto-testent : `python <script>.py --selftest` (pour `cahier_word.py`, ajouter le chemin du gabarit). |
| `skills/` | Consignes (prompts) des agents IA, une par dossier, au format SKILL.md. |
| `modeles/` | Gabarits Word de la DSI : cahier de cas de test et rapport de test après exécution. |

## Utilisés par l'application

| Étape | Agent | Consigne (`skills/`) | Contrôle (`scripts/`) |
|---|---|---|---|
| Analyser | AG-01 | `qa-revue-sfd` | `controler_revue.py` |
| Réécrire | Réécriture | `qa-reecriture` | `verifier_reecriture.py` |
| Concevoir | AG-02 | `qa-conception` | `controler_cas.py` |
| Recette | AG-09 qualification des anomalies | `qa-qualification-anomalie` | `controler_qualification.py` |
| Recette | AG-11 rédaction du rapport de test | `qa-redaction-rapport` | `controler_rapport.py` |
| Export | — | — | `cahier_word.py` (cahier de cas), `empreinte.py` (SHA-256), `statuts.py` |

Gabarits : `modeles/modele-cahier-cas.docx` (export après PV-2) et
`modeles/modele-rapport-test.docx` (cahier de recette).

## En réserve

Les autres skills et scripts viennent de la première version de QA-T-AG,
un agent Hermes autonome. L'application ne les appelle pas encore ; ils
servent de base aux agents prévus (exécution AG-08, régression AG-10, sécurité,
performance, ergonomie, traçabilité, données de test, relecture). Leur
numérotation d'origine (AG-09 Anomalies, AG-11 Performance…) ne correspond
plus à celle de l'application, et certaines mentions (`AGENTS.md`, Sandbox)
renvoient à l'ancien agent. Ils seront revus au moment de leur intégration.

L'état complet de l'agent Hermes et de l'ancienne application Streamlit est
conservé dans la branche `archive/hermes-streamlit`.
