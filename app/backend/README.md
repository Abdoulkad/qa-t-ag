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
| `qatag/ia/fournisseurs.py` | Connecteur DeepSeek, OpenAI, Mistral, Ollama, Anthropic |
| `migrations/` | Évolutions du schéma PostgreSQL (Alembic) |
