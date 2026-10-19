# QA-T-AG — Spécifications de l'application web (refonte)

Version 1.0 — 19/10/2026 — Lot 1

Ce document fixe les règles de l'application web QA-T-AG (FastAPI + React +
PostgreSQL). Chaque règle porte un identifiant **RA-xx** (Règle Application)
pour ne pas se confondre avec les règles RG-xx des skills. Le tableau de
traçabilité en fin de document indique quel test automatisé couvre chaque
règle.

**Principe directeur, appliqué à l'application elle-même :** chaque règle est
appliquée par le serveur. Un bouton grisé ne suffit pas, l'API refuse
l'action et explique pourquoi.

Sources : retour d'exploration d'un testeur expérimenté sur la maquette
Lovable (oct. 2026), arbitrages de BAMK du 19/10/2026, scripts déterministes
existants (`webapp/scripts/`).

---

## 1. Acteurs et rôles

| Rôle | Code | Peut | Ne peut pas |
|---|---|---|---|
| Analyste QA | `ANALYSTE` | Créer une mission, lancer l'analyse, répondre aux questions, consulter les cas, saisir la recette, exporter le cahier | Décider à un Human Gate (sauf RA-12), gérer les comptes |
| Superviseur | `SUPERVISEUR` | Tout ce que fait l'Analyste, plus décider aux Human Gates PV-1 et PV-2 | Gérer les comptes ou la configuration |
| Administrateur | `ADMIN` | Gérer les comptes, les rôles et la configuration IA | Agir sur les missions s'il n'a que ce rôle |

- **RA-01** Les rôles se cumulent. Un utilisateur a au moins un rôle.
- **RA-02** Le premier compte créé dans une organisation reçoit les trois rôles.
  Les comptes suivants reçoivent `ANALYSTE`.
- **RA-03** Seul un `ADMIN` attribue ou retire des rôles. Un `ADMIN` ne peut
  pas retirer son propre rôle `ADMIN` s'il est le dernier de l'organisation.
- **RA-04** Un compte désactivé ne peut plus se connecter. Ses actions passées
  restent dans le journal.
- **RA-05** Toutes les données sont cloisonnées par organisation : un
  utilisateur ne voit jamais les données d'une autre organisation.
- **RA-40** Un Superviseur voit toutes les missions de son organisation ; un
  Analyste ne voit que les missions dont il est participant.

## 2. Authentification

- **RA-06** Connexion par e-mail et mot de passe. Mot de passe de 8 caractères
  minimum, stocké haché (bcrypt), jamais en clair ni dans les journaux.
- **RA-07** Session par jeton signé à durée limitée (8 h par défaut,
  configurable).

## 3. Missions et versions

Une **mission** porte une exigence (SFD ou User Story) à analyser. Chaque
modification du texte crée une **version** ; les versions précédentes restent
consultables en lecture seule.

- **RA-08** Chaque version porte l'empreinte SHA-256 de son texte, calculée
  par script (`empreinte.py`), jamais par l'IA.
- **RA-09** Une mission a des **participants**. Son créateur en fait partie
  d'office.
- **RA-10** Une version validée (PV-1) ou rejetée n'est plus modifiable :
  texte, réponses et critères sont figés. Corriger revient à créer une
  nouvelle version. Les cas de test restent corrigeables jusqu'à PV-2.

### Statuts de mission

```
ANALYSE_EN_COURS → CLARIFICATION → REECRITURE → ATTENTE_PV1
      → CONCEPTION → ATTENTE_PV2 → VALIDEE → EN_RECETTE → CLOTUREE
Rejet à PV-1 ou PV-2 → A_CORRIGER → (nouvelle version) → ANALYSE_EN_COURS
```

- **RA-11** Les transitions hors de ce schéma sont refusées par le serveur.

## 4. Human Gates (PV-1, PV-2)

- **RA-12** Une décision à un Human Gate exige le rôle `SUPERVISEUR`, **sauf**
  si la mission n'a qu'un seul participant : celui-ci peut alors décider seul
  (auto-validation).
- **RA-13** Dès que la mission a deux participants ou plus, l'auteur de la
  version (celui qui a lancé l'analyse) ne peut pas décider à son Human Gate.
- **RA-14** Une auto-validation est marquée comme telle dans la décision, dans
  le journal et dans le cahier de recette (« validé par l'unique acteur de la
  mission »).
- **RA-15** Un rejet exige un commentaire non vide. Il fait passer la mission
  en `A_CORRIGER` *(retour testeur : impossible de corriger et resoumettre)*.
- **RA-16** Après un rejet, plus aucune action n'est possible sur la version
  rejetée ; seule la création d'une nouvelle version est permise.

## 5. Cycle Analyser → Clarifier → Réécrire → Valider

*(Retour testeur : « aucune fonctionnalité ne permet de proposer une version
améliorée de la User Story avec des critères d'acceptation testables ».)*

1. **Analyser (AG-01)** : l'IA relève les défauts (ambiguïtés, contradictions,
   cas oubliés…) et formule des questions métier. `controler_revue.py`
   contrôle le rapport : chaque citation doit exister mot pour mot.
2. **Clarifier** : un humain répond à chaque question.
3. **Réécrire** : l'IA propose une exigence réécrite avec des critères
   d'acceptation testables.
4. **Valider (PV-1)** : l'humain compare l'original et la réécriture, puis
   décide.

- **RA-17** Le **score de clarté** (0-100) est calculé par script à partir du
  nombre et de la gravité des défauts, jamais noté par l'IA. Formule :
  `100 − 25 × bloquants − 10 × majeurs − 3 × mineurs`, borné à [0, 100].
- **RA-18** Une réponse à une question métier enregistre son auteur et sa date.
- **RA-19** Chaque critère d'acceptation réécrit **cite au moins une source** :
  une phrase de l'exigence d'origine (citée mot pour mot) ou une réponse de
  l'étape Clarifier. Un script le vérifie.
- **RA-20** Un critère sans source vérifiable est marqué `HYPOTHESE`. PV-1 est
  refusé tant qu'il reste une hypothèse : l'IA n'invente pas de règle métier.
- **RA-21** La réécriture n'est possible qu'une fois toutes les questions
  bloquantes répondues.
- Pour lever une hypothèse avant PV-1, l'humain peut : répondre à une question
  ou ajouter une **précision** (question + réponse, numérotée Q-n comme les
  autres) puis relancer la réécriture ; ou **écarter** le critère avec un
  motif obligatoire, inscrit au journal.

## 6. Conception des cas de test (AG-02 à AG-05)

- **RA-22** Un cas porte une **technique** (partitions d'équivalence, valeurs
  limites, table de décision, transitions d'état) **et sa justification** :
  quelle partition, quelle limite, quelle règle de la table *(retour testeur :
  techniques annoncées mais pas démontrées)*.
- **RA-23** Un cas est `PRET` seulement s'il a des préconditions, des données de
  test concrètes et un résultat attendu. Sinon il est `INCOMPLET` *(retour
  testeur : statut « OK » sans données de test)*. Ne sont **pas** concrètes :
  une variable `{…}`, « à définir », « TBD », ou une description de classe
  sans valeur précise (« mot de passe valide », « un e-mail existant »).
  « Sans objet » est accepté quand le cas ne demande aucune donnée. Le statut
  est calculé par le serveur, jamais recopié de l'IA.
- **RA-24** Un cas lié à un point non résolu est `A_CLARIFIER`.
- **RA-25** Chaque cas est tracé vers au moins une exigence ou un critère
  (matrice calculée par `tracer.py`).
- **RA-26** PV-2 est **refusé** tant qu'un cas est `A_CLARIFIER` ou
  `INCOMPLET`. La réponse liste les cas qui bloquent *(retour testeur : clôture
  PV-2 possible avec des critères « À clarifier »)*.
- **RA-41** PV-2 est aussi refusé tant qu'un critère d'acceptation n'est couvert
  par aucun cas.
- Un cas se corrige champ par champ avant PV-2 ; son statut est recalculé. Un
  cas signalé « À clarifier » par l'agent ne devient `PRET` qu'après une
  confirmation humaine explicite, tracée au journal.

## 7. Recette (exécution)

Statuts canoniques (`statuts.py`) et libellés affichés :

| Code | Libellé |
|---|---|
| `PASS` | Succès |
| `FAIL` | Échec |
| `BLOCKED` | Non testable |
| `NOT_RUN` | Non exécuté |

- **RA-27** La recette n'est ouverte qu'après PV-2.
- **RA-28** Sur un cas sans résultat attendu complet, seuls `BLOCKED` et
  `NOT_RUN` sont acceptés par le serveur *(retour testeur : PASS/FAIL possible
  sans résultat attendu défini)*.
- **RA-29** `PASS` et `FAIL` exigent un résultat obtenu saisi.
- **RA-30** Un `FAIL` ouvre une anomalie liée au cas (AG-09).
- **RA-31** Une preuve (capture) est stockée sur disque ; la base garde son
  chemin, son type et son empreinte SHA-256. PNG ou JPEG, 10 Mo maximum.

## 8. Cahier de recette (export Word)

- **RA-32** Le cahier est généré **uniquement depuis la base**, à partir du
  gabarit Word de l'organisation (`cahier_word.py`).
- **RA-33** Après génération, un contrôle relit le fichier produit et vérifie
  que chaque cas et chaque statut correspondent à la base *(retour testeur :
  cohérence entre statuts de recette et export Word)*. L'empreinte du fichier
  est inscrite au journal.

## 9. Journal QA

- **RA-34** Le journal est en ajout seul : aucune route ne permet de modifier
  ou supprimer une entrée. Chaque entrée porte l'horodatage UTC, l'acteur,
  l'événement et la mission.
- **RA-35** Chaque entrée porte l'empreinte de l'entrée précédente (chaînage) :
  une modification directe en base est détectable par vérification de la
  chaîne.

## 10. IA configurable

| Fournisseur | Protocole | Point d'accès (vérifié dans la doc éditeur, oct. 2026) |
|---|---|---|
| DeepSeek | compatible OpenAI | `https://api.deepseek.com/chat/completions` |
| OpenAI | OpenAI | `https://api.openai.com/v1/chat/completions` |
| Mistral | compatible OpenAI | `https://api.mistral.ai/v1/chat/completions` |
| Ollama (local) | compatible OpenAI | `http://localhost:11434/v1/chat/completions`, sans clé |
| Anthropic (Claude) | Messages API | `https://api.anthropic.com/v1/messages` |

- **RA-36** Les clés d'API sont lues dans le fichier `.env` du serveur. Elles
  ne sont jamais stockées en base, jamais renvoyées par l'API, jamais
  affichées.
- **RA-37** Le fournisseur et le modèle actifs sont choisis par un `ADMIN` dans
  la configuration. Le choix est refusé si la clé du fournisseur est absente
  (sauf Ollama).
- **RA-38** Chaque version analysée enregistre le fournisseur et le modèle
  utilisés.
- **RA-39** Les appels IA s'exécutent en tâche de fond ; leur état
  (`EN_ATTENTE`, `EN_COURS`, `TERMINEE`, `ECHEC`) est consultable.

## 11. Modèle de données

| Table | Contenu |
|---|---|
| `organisation` | Nom, gabarit Word |
| `utilisateur` | E-mail, nom, hash du mot de passe, rôles, actif |
| `mission` | Référence (M-001…), titre, statut, organisation, créateur |
| `participant` | Mission ↔ utilisateur |
| `version_exigence` | Texte, n° de version, empreinte, auteur, fournisseur et modèle IA, score de clarté |
| `defaut` | DEF-xx : catégorie, gravité, citation, description (AG-01) |
| `question_metier` | Question, réponse, auteur et date de la réponse, bloquante |
| `critere_acceptation` | Texte, sources, statut (`SOURCE` / `HYPOTHESE`) |
| `cas_test` | Les 12 colonnes du CSV + justification de technique + statut |
| `trace` | Cas ↔ exigence ou critère |
| `decision_porte` | PV-1/PV-2, décision, commentaire, décideur, auto-validation |
| `execution` | Statut, résultat obtenu, commentaire, testeur, date |
| `preuve` | Fichier, type, taille, empreinte |
| `anomalie` | Cas, description, gravité, statut |
| `journal` | Entrées chaînées en ajout seul |
| `tache_ia` | Type, état, erreur, horodatages |
| `config_ia` | Fournisseur et modèle actifs par organisation |

## 12. Traçabilité règles ↔ tests

Tenue à jour à chaque lot. Les tests sont dans `app/backend/tests/`.

| Règles | Test | Lot |
|---|---|---|
| RA-01 à RA-05 | `test_comptes.py` | 1 |
| RA-06, RA-07 | `test_auth.py` | 1 |
| RA-08 à RA-11, RA-40 | `test_missions.py` | 1 |
| RA-12 à RA-16 | `test_portes.py` | 1 |
| RA-20, RA-26 (blocage des portes) | `test_portes.py` | 1 |
| RA-17 | `test_clarte.py` | 1 |
| RA-34, RA-35 | `test_journal.py` | 1 |
| RA-36 à RA-39 | `test_ia.py` | 1 |
| RA-18 à RA-21 | `test_clarification.py` | 2 |
| RA-22 à RA-26, RA-41 | `test_conception.py` | 2 |
| RA-27 à RA-33 | à venir (recette, export Word) | 3 |

La protection du journal (RA-34) est assurée par la base elle-même : un
déclencheur PostgreSQL refuse `UPDATE`, `DELETE` et `TRUNCATE` sur la table.
