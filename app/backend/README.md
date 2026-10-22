# QA-T-AG — Application web (FastAPI + React + PostgreSQL)

API de l'application web QA-T-AG. Les règles appliquées sont décrites dans
[`docs/specifications.md`](../../docs/specifications.md) ; chaque règle
(RA-xx) est couverte par un test dans `tests/`.

Le backend réutilise les scripts déterministes de `webapp/scripts` et les
prompts des agents de `webapp/skills`, sans les modifier.

## Installation sur Windows

Prérequis : Python 3.11 ou plus récent, PostgreSQL 14 ou plus récent.

### 1. Créer la base et son utilisateur

Dans **SQL Shell (psql)** ou dans l'outil de requête de **pgAdmin**,
connecté avec le compte `postgres` :

```sql
CREATE USER qatag WITH PASSWORD 'choisissez-un-mot-de-passe';
CREATE DATABASE qatag OWNER qatag;
```

### 2. Installer le backend

Dans un terminal PowerShell, depuis le dossier du dépôt :

```powershell
cd app\backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Si PowerShell refuse d'exécuter `Activate.ps1`, utilisez l'invite de
commandes classique (`cmd`) avec `.venv\Scripts\activate.bat`.

### 3. Configurer `.env`

Ouvrez `app\backend\.env` et renseignez :

- `DATABASE_URL` avec le mot de passe choisi à l'étape 1 ;
- `SECRET_KEY` : générez-la avec
  `python -c "import secrets; print(secrets.token_urlsafe(48))"` ;
- la clé d'API du fournisseur IA que vous utilisez (par exemple
  `DEEPSEEK_API_KEY`).

Le serveur refuse de démarrer si `SECRET_KEY` est absente ou fait moins de
32 caractères.

### 4. Créer les tables puis lancer

Toujours depuis `app\backend`, environnement activé :

```powershell
alembic upgrade head
uvicorn qatag.main:app --reload
```

L'API répond sur http://localhost:8000. La documentation interactive de
toutes les routes est sur http://localhost:8000/docs.

### 5. Construire l'interface (une fois, puis à chaque mise à jour)

Prérequis : Node.js 22.12 ou plus récent (ou 20.19 minimum). Dans un second
terminal, depuis le dossier du dépôt :

```powershell
cd app\frontend
npm install
npm run build
```

Relancez ensuite `uvicorn` : le même serveur sert l'API et l'interface sur
http://localhost:8000.

### 6. Premier compte

Ouvrez http://localhost:8000 et cliquez sur **Créer un compte**. Le premier
compte devient Analyste, Superviseur et Administrateur (RA-02). Choisissez
ensuite l'IA dans **Configuration IA**.

Les comptes suivants sont créés par un administrateur, page **Utilisateurs** :
après le premier compte, l'inscription libre est fermée (RA-51). Le mot de
passe choisi (bouton **Générer**) est provisoire : la personne le remplace à
sa première connexion. En cas d'oubli, **Réinitialiser le mot de passe**
attribue un nouveau mot de passe provisoire.

### Développer l'interface

Pour modifier l'interface avec rechargement instantané, lancez `npm run dev`
dans `app\frontend` et ouvrez http://localhost:5173 (le backend doit tourner
sur le port 8000).

## Mises à jour

Après chaque récupération d'une nouvelle version du code :

```powershell
cd app\backend
pip install -r requirements.txt
alembic upgrade head
cd ..\frontend
npm install
npm run build
```

## Recette (v1.1)

Après PV-2, l'étape **Recette** de la mission liste les cas à exécuter. Pour
chaque cas : choisissez le statut (Succès, Échec, Non testable, Non exécuté),
saisissez le résultat obtenu et joignez vos captures (bouton ou Ctrl+V dans
le formulaire). Succès et échec exigent au moins une capture ; un échec ouvre
une anomalie ; l'agent
AG-09 en propose la qualification, que vous confirmez ou modifiez (motif à
l'appui). Déclarez une anomalie corrigée à la livraison du correctif, puis
rejouez le cas : un passage réussi la ferme. Clôturez enfin la recette, sans
réserve ou avec réserves motivées, et exportez le cahier de recette Word.
L'onglet **Rapport** rédige les parties d'interprétation du cahier
(contexte, objectifs, synthèse, recommandations, conclusion, avis) : faites-
les proposer par l'agent AG-11, corrigez-les, puis validez-les ; seul le
texte validé entre dans le cahier.
Après une clôture avec réserves, seuls les cas en réserve se rejouent ; quand
ils sont tous réussis et leurs anomalies résolues, **Lever les réserves**
termine le suivi.
Les captures sont enregistrées dans la base : la sauvegarde les inclut.

## Évaluation des agents

La campagne suit le protocole d'évaluation : chaque exigence du corpus est
analysée trois fois par configuration d'IA, puis comparée au corrigé des
relecteurs. Les classeurs de la campagne contiennent des exigences réelles :
les fichiers `.xlsx` de `app\backend` (et le dossier `app\evaluation`) sont
ignorés par Git ; ne les copiez pas ailleurs dans le dépôt.

**1. Une base dédiée, jamais la base de travail.** Une fois, dans psql :

```sql
CREATE DATABASE qatag_eval OWNER qatag;
```

Puis, dans une fenêtre PowerShell réservée à la campagne (la variable ne vaut
que pour cette fenêtre et prime sur `.env`) :

```powershell
cd app\backend
.venv\Scripts\Activate.ps1
$env:DATABASE_URL = "postgresql+psycopg://qatag:VOTRE_MOT_DE_PASSE@localhost:5432/qatag_eval"
alembic upgrade head
uvicorn qatag.main:app --port 8001
```

L'application d'évaluation répond sur http://localhost:8001, avec ses propres
comptes et sa propre configuration IA.

**2. Le corrigé.** `python -m qatag.evaluation modele-corrige corrige.xlsx`
crée le classeur à remplir par les deux relecteurs : corpus (EX-01…), défauts
(VT-01…), règles (RC-01…), seuils validés par la DSI, signature.

**3. Les passages.** Une mission par exigence, configuration et passage,
titrée `EVAL-EX-01-DeepSeek-P1`. Pour changer de configuration, changez l'IA
active dans Configuration IA, puis ne la touchez plus jusqu'à la fin de ses
passages.

**4. L'export.** Dans la même fenêtre (même `DATABASE_URL`) :

```powershell
python -m qatag.evaluation exporter campagne.xlsx --corrige corrige.xlsx
```

Le classeur reprend ce que les agents ont réellement produit, défauts écartés
compris, avec une proposition d'appariement par citation. Le relecteur
remplit les colonnes jaunes : décision VP, FP, Doublon ou Trouvaille et VT,
règle du corrigé ou règle inventée, quatre conditions par cas. Après de
nouveaux passages, un nouvel export garde les saisies :
`exporter campagne-2.xlsx --corrige corrige.xlsx --reprendre campagne.xlsx`.

**5. La consolidation.**

```powershell
python -m qatag.evaluation consolider campagne.xlsx synthese.xlsx --corrige corrige.xlsx
```

Le calcul est refusé tant qu'une décision manque ; la liste dit quoi
compléter. La synthèse donne les indicateurs I1 à I13 par configuration, la
décision (apte, apte sous réserve, non apte), les bloquants oubliés, les
trouvailles, les catégories confondues et la stabilité par exigence.

## Sécurité

- **Comptes** : après le premier compte, seul un administrateur crée les comptes
  (`INSCRIPTION_LIBRE=false`, RA-51).
- **Connexion** : après 5 échecs en 15 minutes sur un même e-mail (20 depuis une
  même adresse IP), la connexion est refusée jusqu'à la fin de la fenêtre, même
  avec le bon mot de passe. Le blocage d'un compte existant est inscrit au
  journal (RA-52). Seuils réglables dans `.env`.
- **Mots de passe** : provisoire pour tout compte créé ou réinitialisé par un
  administrateur, à changer avant toute action ; changement libre via
  **Mot de passe** (barre latérale) ; chaque changement ferme les autres
  sessions du compte (RA-55 à RA-58).
- **En-têtes HTTP** : politique de sécurité du contenu stricte, interdiction
  d'affichage dans un cadre, pas de mise en cache des réponses de l'API (RA-53).
- **HTTPS** : indispensable dès que l'application est utilisée depuis un autre
  poste que le serveur. Placez-la derrière un serveur web qui gère le certificat
  (IIS, Nginx, Caddy…) ; l'en-tête HSTS est alors envoyé automatiquement.
  Uvicorn fait confiance par défaut aux en-têtes `X-Forwarded-*` venant de la
  même machine (127.0.0.1) : l'adresse IP réelle des utilisateurs sert alors à
  la limitation des connexions. Si le serveur web est sur une autre machine,
  lancez uvicorn avec `--forwarded-allow-ips=<adresse du serveur web>`, sinon
  tous les utilisateurs partageraient la même adresse et le même compteur.

## Sauvegardes

Toutes les données sont dans la base : une sauvegarde PostgreSQL suffit.
Depuis `app\backend`, environnement activé :

```powershell
python -m qatag.sauvegarde              # crée une sauvegarde dans app\sauvegardes
python -m qatag.sauvegarde --lister     # liste les sauvegardes
```

Chaque sauvegarde est relue après création pour vérifier qu'elle est
exploitable. Les 14 plus récentes sont conservées (`SAUVEGARDES_CONSERVEES`).
Si `pg_dump` est introuvable, indiquez dans `.env` le dossier `bin` de
PostgreSQL, par exemple `PG_BIN=C:\Program Files\PostgreSQL\16\bin`.

Les sauvegardes contiennent toutes vos données : copiez régulièrement le
dossier `app\sauvegardes` sur un autre support (disque externe, partage
réseau). Une sauvegarde restée sur le même disque ne protège pas d'une panne
de ce disque.

**Sauvegarde automatique.** `sauvegarder.bat` lance la sauvegarde et note le
résultat dans `app\backend\sauvegarde.log`. Lancez-le d'abord une fois à la
main (double-clic) et vérifiez le journal, puis programmez-le chaque jour avec
le Planificateur de tâches Windows, par exemple à 20 h :

```powershell
schtasks /create /tn "QA-T-AG sauvegarde" /tr "C:\chemin\vers\qa-t-ag\app\backend\sauvegarder.bat" /sc daily /st 20:00
```

Remplacez le chemin par celui de votre dépôt. S'il contient des espaces,
créez plutôt la tâche dans l'interface du Planificateur de tâches (action :
démarrer le programme `sauvegarder.bat`).

**Restaurer.** Arrêtez le serveur, puis :

```powershell
python -m qatag.sauvegarde --restaurer qatag-20261021-200000.dump
```

La commande demande de taper `RESTAURER` pour confirmer. Le contenu actuel de
la base est remplacé en une seule transaction : en cas d'erreur, la base
reste dans son état précédent.

## Lancer les tests

Les tests utilisent une **base séparée**, `qatag_test`, qu'ils vident
entièrement. Ne pointez jamais `TEST_DATABASE_URL` vers votre base de
travail.

```sql
CREATE DATABASE qatag_test OWNER qatag;
```

```powershell
$env:TEST_DATABASE_URL = "postgresql+psycopg://qatag:VOTRE_MOT_DE_PASSE@localhost:5432/qatag_test"
python -m pytest -q
```

Aucun test n'appelle une vraie IA : les réponses sont simulées.

## Organisation du code

| Fichier | Rôle |
|---|---|
| `qatag/regles.py` | Règles métier pures (transitions, habilitation aux portes, score de clarté) |
| `qatag/missions.py` | Missions, versions, Human Gates |
| `qatag/taches.py` | Analyses IA en tâche de fond |
| `qatag/journal.py` | Journal chaîné en ajout seul |
| `qatag/scripts_qa.py` | Pont vers les scripts déterministes existants |
| `qatag/evaluation.py` | Campagne d'évaluation des agents : export, appariement, indicateurs |
| `qatag/ia/fournisseurs.py` | Connecteur DeepSeek, OpenAI, Mistral, Ollama, Anthropic |
| `migrations/` | Évolutions du schéma PostgreSQL (Alembic) |
