---
name: qa-t-ag-migration
description: "Use when building or extending QA-T-AG under Hermes."
version: 0.2.0
metadata:
  hermes:
    tags: [qa, qa-t-ag, migration, multi-agent, hermes]
    category: qa
---

# QA-T-AG — Construction & migration sous Hermes

Méthode pour transformer la SFD `QA-T-AG_SFD_Hermes_V2.0.md` (13 agents
AG-01..AG-13) en système opérationnel sous Hermes, dans le bon ordre, sans
produire « 13 processus autonomes ayant tous accès à tous les outils »
(SFD §4.2).

## Correspondance SFD → Hermes (fixe)

| Concept SFD | Mécanisme Hermes | Précision |
|---|---|---|
| Procédure réutilisable | **Skill** | une skill = une méthode, jamais une frontière de sécurité |
| Agent spécialisé | **Profil / Bot Mode** | bot nommé : chat, rôle, modèle, mémoire, skills propres |
| Orchestrateur (AG-07) | **`delegate_task`** ou **Kanban** | décision ouverte : délégation ≠ file durable |
| Script déterministe | `scripts/*.py` dans une skill | « le script calcule, l'agent analyse, l'humain arbitre » |

## Ordre de construction (SFD §5.2 / §13)

1. **Socle déterministe d'abord** — contrats JSON Schema, statuts
   normalisés, empreintes SHA-256, journal append-only, transitions de
   campagne, manifeste. Construit : skill `qa-t-ag-socle`.
2. AG-01 (revue SFD) puis AG-02 (conception), lecture seule.
3. AG-03 (traçabilité) / AG-04 (données) / AG-05 (relecteur), scripts.
4. AG-06 (cahier Word), script sans modèle.
5. AG-08 (exécution), sandbox obligatoire, non destructif d'abord.
6. AG-10..AG-13 en dernier, permissions dédiées.

## Pièges

- **`skills.write_approval: true` met toute écriture de skill en attente.**
  `skill_manage` renvoie `staged` + `pending_id` et n'écrit RIEN : la
  payload part dans `<HERMES_HOME>/pending/skills/<id>.json`. L'humain
  approuve avec `/skills approve <id>` (ou `/skills pending`). Ne jamais
  s'auto-approuver — lancer soi-même l'approbation détruit le Human Gate que
  ce réglage instaure. Après approbation, vérifier que le répertoire du
  skill existe réellement avant d'y écrire les fichiers de support.
- **`/skills approve` n'est pas câblé dans le chat de l'app desktop**
  (CLI et gateway seulement) : si la commande « ne fait rien » dans l'app,
  passer par un terminal `hermes -p <profil>` puis `/skills approve <id>`,
  ou désactiver temporairement le garde-fou (`hermes config set
  skills.write_approval false`) avec l'accord explicite de l'humain, puis
  le réactiver en fin de construction.
- **La description d'un skill ne doit pas dépasser ~57 caractères.**
  Au-delà, `skill_manage` refuse (l'index tronque à 57 + « ... »). Mettre
  le déclencheur « Use when … » d'abord, le détail dans le corps.
- **Le `category` de `skill_manage` détermine le sous-dossier** :
  `category: "qa"` crée `skills/qa/<nom>/`, pas `skills/<nom>/`. Vérifier
  le chemin réel avant d'y écrire les fichiers de support.
- **`qa-t-ag-core` est user-owned : ne pas le patcher.** Le patch est refusé
  (pas simplement ignoré). Construire dans de nouveaux skills, ou demander
  `hermes curator adopt qa-t-ag-core` si une modification y est réellement
  nécessaire.
- **Ne jamais déclarer un script « fait » sans sortie d'exécution.** Chaque
  script du socle embarque un auto-test (`python <script>.py` → code 0). Le
  lancer depuis son emplacement final : c'est la preuve, pas la lecture.
