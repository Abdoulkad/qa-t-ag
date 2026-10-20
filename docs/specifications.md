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
   Une section « Alerte sécurité » omise par l'IA (faute d'alerte) est
   ajoutée vide et la correction est tracée ; une section de fond manquante
   (Inventaire, Défauts) fait échouer l'analyse, avec la raison affichée.
2. **Clarifier** : un humain répond à chaque question.
3. **Réécrire** : l'IA propose une exigence réécrite avec des critères
   d'acceptation testables.
4. **Valider (PV-1)** : l'humain compare l'original et la réécriture, puis
   décide.

- **RA-17** Le **score de clarté** (0-100) est calculé par script à partir du
  nombre et de la gravité des défauts, jamais noté par l'IA. Formule :
  `100 − 25 × bloquants − 10 × majeurs − 3 × mineurs`, borné à [0, 100]. Il
  porte sur les défauts retenus : un défaut écarté n'y compte plus, un défaut
  requalifié y compte avec sa nouvelle criticité (RA-50).
- **RA-49** **Revue AG-01, grille QA-REV-02.** Chaque défaut porte une citation
  exacte, un constat (le problème, sans reformuler l'exigence), une catégorie
  parmi : contradiction certaine, contradiction apparente, ambiguïté, terme non
  défini, exigence non testable, règle manquante, cas limite à confirmer, règle
  sans exigence, incohérence avec les user stories ; une criticité selon
  l'impact démontré et une question neutre. « Certaine » est réservée à deux
  règles impossibles à satisfaire ensemble ; une exception possible fait une
  contradiction « apparente ». Le script refuse une contradiction non qualifiée
  et une criticité `Bloquante` sans justification, et signale les doublons
  (même citation, même catégorie). Les règles absentes du texte font l'objet de
  **questions complémentaires**, sans citation : elles ne comptent pas dans le
  score, ne bloquent pas la réécriture, et leurs réponses sont des sources.
- **RA-50** **Validation humaine des défauts.** La revue est une aide : chaque
  défaut peut être confirmé, écarté comme faux positif (motif obligatoire ; sa
  question sans réponse passe hors périmètre avec ce motif, ce qu'une
  annulation défait) ou requalifié (motif obligatoire ; la criticité de l'agent
  est conservée, la question devient bloquante ou non). Confirmer et écarter se
  font par lot. Le score est recalculé, la réécriture ignore les défauts
  écartés, chaque décision est journalisée, et PV-1 montre les défauts jamais
  examinés et ceux écartés.
- **RA-18** Une réponse à une question métier enregistre son auteur et sa date.
- **RA-19** Chaque règle métier et chaque critère d'acceptation réécrit **cite
  au moins une source** : une phrase de l'exigence d'origine (citée mot pour
  mot ; seuls les blancs multiples et la casse sont tolérés) ou une réponse de
  l'étape Clarifier. Un critère peut aussi s'appuyer sur les règles qu'il
  vérifie. Un script le vérifie.
- **RA-20** Une règle ou un critère sans source vérifiable est marqué
  `HYPOTHESE`. Il l'est aussi dès qu'**une** de ses sources est rejetée
  (citation introuvable, question sans réponse ou décidée, règle inconnue ou
  elle-même hypothèse), même si une autre est valide : la partie qui en dépend
  ne repose sur rien. PV-1 est refusé tant qu'il reste une
  hypothèse : l'IA n'invente pas de règle métier.
- **RA-21** La réécriture n'est possible qu'une fois toutes les questions
  bloquantes **traitées** : répondues, ou déclarées hors périmètre ou
  reportées (RA-42).
- Pour lever une hypothèse avant PV-1, l'humain peut : répondre à une question
  ou ajouter une **précision** (question + réponse, numérotée Q-n comme les
  autres) puis relancer la réécriture ; ou **écarter** le critère avec un
  motif obligatoire, inscrit au journal.
- **RA-42** Une question sans réponse peut recevoir une **décision humaine
  motivée** : `HORS_PERIMETRE` (l'agent n'écrit rien dessus) ou `REPORTEE`
  (le sujet devient un point ouvert). Le motif est obligatoire ; l'auteur et la
  date sont enregistrés. Une question déjà répondue ne peut pas être décidée ;
  répondre plus tard à une question décidée annule la décision. Une question
  décidée n'est **jamais** une source de critère (RA-19 reste entière).
- **RA-43** La réécriture peut comporter une section « Points ouverts » : les
  sujets non tranchés, sans source, qui ne deviennent pas des critères. Ils ne
  bloquent pas PV-1 mais sont affichés au décideur avec les questions décidées
  et leur motif, avant qu'il approuve.
- **RA-44** Les décisions sur les questions, l'écart des règles et des critères
  et la justification des phrases non reprises peuvent être faits **par lot**,
  avec un motif commun. Chaque élément garde sa propre ligne
  dans le journal QA. Le lot est refusé en entier si un seul élément est
  invalide.
- **RA-47** La réécriture **sépare** la User Story réécrite (même besoin, même
  intention), les **règles métier** RG-n (ce que le métier impose, chacune
  sourcée) et les **critères d'acceptation** CA-n (ce qu'on vérifie, chacun
  lié aux règles qu'il vérifie). La section des règles est obligatoire
  (« Aucune » si besoin). PV-1 est refusé tant qu'une règle n'est vérifiée par
  aucun critère, ou qu'un critère vérifie une règle écartée. Écarter une règle
  est motivé et journalisé. La traçabilité suit la chaîne RG → CA → CT, et le
  taux de couverture compte les règles.
- **RA-48** **Couverture du texte d'origine** : le texte est découpé en phrases
  numérotées. Les titres et identifiants sont ignorés, comme les phrases de
  **cadrage** de la User Story : rôle (« En tant que… ») et bénéfice
  (« Afin de… », « Pour que… »), reprises par la User Story réécrite. La phrase
  qui porte le besoin (« je veux… ») reste toujours contrôlée. Chaque phrase doit être
  reprise par au moins une citation valide d'une règle ou d'un critère restant.
  Sinon, PV-1 est refusé jusqu'à ce que l'humain relance la réécriture ou
  déclare la phrase « non reprise volontairement », avec un motif. Cette
  justification survit aux réécritures de la même version et est montrée au
  décideur de PV-1. La couverture est recalculée à chaque lecture : écarter une
  règle peut découvrir une phrase.

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

## 7 bis. Cahier des cas de test (export Word, avant recette)

Document distinct du cahier de recette : il décrit les cas à exécuter,
zones d'exécution laissées vides, au gabarit DSI `webapp/modele-cahier-cas.docx`.

- **RA-46** Le cahier des cas s'exporte dès que les cas sont conçus (statut
  `ATTENTE_PV2` ou suivant), sur la version courante, **depuis la base** et par
  `cahier_word.py`, sans reformulation. Un bandeau identifie la mission, la
  version et son empreinte. Avant PV-2, le document porte la mention
  « DOCUMENT DE TRAVAIL — cas non validés » et le nom de fichier se termine
  par `_brouillon` ; après PV-2, il indique la date, le décideur et
  l'auto-validation éventuelle. Un cas dont la priorité ou le type ne
  correspond à aucune case du gabarit bloque l'export. Chaque export est
  inscrit au journal avec l'empreinte SHA-256 du fichier remis.

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
  (sauf Ollama). Tant qu'aucune IA n'est choisie, la création
  d'une mission est refusée avec un message qui l'explique.
- **RA-38** Chaque version analysée enregistre le fournisseur et le modèle
  utilisés.
- **RA-39** Les appels IA s'exécutent en tâche de fond ; leur état
  (`EN_ATTENTE`, `EN_COURS`, `TERMINEE`, `ECHEC`) est consultable.
- **RA-45** Les réponses de l'IA sont reçues en continu (streaming). Une
  coupure réseau ou une surcharge passagère (HTTP 408, 429, 5xx) est retentée
  automatiquement, jusqu'à 3 tentatives, après 5 puis 20 secondes de pause.
  Une erreur définitive (clé refusée, requête invalide) ne l'est pas. Une
  réponse tronquée par la limite de tokens est signalée comme telle.
  La longueur de réponse demandée dépend du fournisseur (DeepSeek 32 768
  tokens, raisonnement compris ; OpenAI et Mistral 16 384 ; Anthropic 32 000 ;
  Ollama 8 192). Elle se règle avec `IA_MAX_TOKENS` dans le fichier `.env`.

## 11. Modèle de données

| Table | Contenu |
|---|---|
| `organisation` | Nom, gabarit Word |
| `utilisateur` | E-mail, nom, hash du mot de passe, rôles, actif |
| `mission` | Référence (M-001…), titre, statut, organisation, créateur |
| `participant` | Mission ↔ utilisateur |
| `version_exigence` | Texte, n° de version, empreinte, auteur, fournisseur et modèle IA, score de clarté, texte réécrit, points ouverts |
| `defaut` | DEF-xx : catégorie, criticité (et criticité initiale de l'agent), citation, constat, justification, validation (`CONFIRME` / `ECARTE`), motifs, auteur et date |
| `question_metier` | Question, nature (`DEFAUT` / `COMPLEMENTAIRE` / `PRECISION`), sujet et raison (complémentaire), réponse, auteur et date de la réponse, bloquante, décision (`HORS_PERIMETRE` / `REPORTEE`), motif, auteur et date de la décision |
| `regle_metier` | RG-n : texte, sources, sources rejetées, statut (`SOURCE` / `HYPOTHESE`) |
| `critere_acceptation` | Texte, sources, règles vérifiées (RG-n), statut (`SOURCE` / `HYPOTHESE`) |
| `phrase_source` | Phrase numérotée du texte d'origine, titre, motif de non-reprise, auteur et date |
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
| RA-36 à RA-39, RA-45 | `test_ia.py` | 1 |
| RA-18 à RA-21 | `test_clarification.py` | 2 |
| RA-22 à RA-26, RA-41 | `test_conception.py` | 2 |
| RA-20 (source rejetée), RA-21 (amendée), RA-42 à RA-44 | `test_decisions.py` | 2 |
| RA-46 | `test_cahier_cas.py` | 2 |
| RA-47, RA-48 | `test_regles_couverture.py` | 2 |
| RA-17 (défauts retenus), RA-49, RA-50 | `test_revue_v2.py` | 2 |
| RA-27 à RA-33 | à venir (recette, export Word) | 3 |

La protection du journal (RA-34) est assurée par la base elle-même : un
déclencheur PostgreSQL refuse `UPDATE`, `DELETE` et `TRUNCATE` sur la table.
