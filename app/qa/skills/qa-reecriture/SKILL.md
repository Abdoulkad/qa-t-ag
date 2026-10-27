---
name: qa-reecriture
description: "Use when rewriting an ambiguous requirement or User Story into a clear, testable one with sourced business rules and acceptance criteria, after the business questions have been answered."
version: 0.2.0
metadata:
  hermes:
    tags: [qa, qa-t-ag, reecriture, criteres-acceptation, ag01]
    category: qa
---

# Réécriture d'exigence — cycle Analyser → Clarifier → Réécrire → Valider

Tu réécris une exigence (SFD ou User Story) en une version claire et
testable, avec des critères d'acceptation. Tu travailles **après** la revue
AG-01 et **après** les réponses humaines aux questions métier.

## Ce que tu produis, séparément

1. **La User Story réécrite** : le même besoin et la même intention que
   l'original, rédigés clairement (« En tant que …, je veux …, afin de … »).
2. **Les règles métier** (RG-01, RG-02…) : ce que le métier impose (seuils,
   délais, formats, statuts, droits). C'est ce que le métier relit.
3. **Les critères d'acceptation** (CA-01…) : ce qu'on vérifie, en Gherkin.
   Chaque critère indique les règles qu'il vérifie (`Règles : RG-01`).

Chaque phrase de l'exigence d'origine doit être reprise par au moins une
règle ou un critère, cité mot pour mot entre « ». Une phrase que tu ne peux
pas reprendre faute de précision va dans les points ouverts. Le script
signale toute phrase oubliée.

## Règle absolue : tu n'inventes aucune règle métier

Chaque règle métier et chaque critère d'acceptation doit citer **au moins une
source** (un critère peut aussi s'appuyer sur les règles qu'il vérifie) :

- une citation **mot pour mot** de l'exigence d'origine, entre « » ;
- ou le code d'une réponse humaine, `Q-n`, fournie dans la consigne.

Un seuil, un délai, un format, un message, un rôle qui n'apparaît ni dans
l'exigence ni dans une réponse ne doit **pas** être inventé. Si un critère
te semble nécessaire mais qu'aucune source ne le justifie, écris-le quand
même et laisse ses sources vides : le script de contrôle le marquera
`HYPOTHESE` et l'humain tranchera. Ne maquille jamais une hypothèse en
citant une source qui ne la dit pas.

Une question restée sans réponse n'est pas une source. Ne bâtis **pas** de
critère dessus : range le sujet dans la section « ## Points ouverts » (voir
le format). Une question déclarée **hors périmètre** par l'humain ne donne
lieu à rien. Une question **reportée** va dans les points ouverts.

Chaque source citée doit être valable. Un critère qui cite **une seule**
source non valable (citation introuvable, question sans réponse) est marqué
`HYPOTHESE`, même si ses autres sources sont bonnes : la partie qui en dépend
ne repose sur rien. N'ajoute pas une question ouverte « pour faire bien ».

## Qualité des critères

- Forme Gherkin : « Étant donné …, quand …, alors … ».
- Un critère = un comportement observable et vérifiable.
- Valeurs exactes (nombres, unités, libellés) reprises des sources.
- Couvrir le cas nominal, les cas d'erreur et les limites que les sources
  permettent d'établir.

## Format de sortie (contrat, contrôlé par `verifier_reecriture.py`)

Rien avant, rien après :

```markdown
## User Story réécrite
<la User Story réécrite, claire, sans ambiguïté>

## Règles métier
### RG-01
- **Règle** : Le lien de réinitialisation expire 30 minutes après son envoi.
- **Sources** : « valide pendant une durée limitée » ; Q-1

## Critères d'acceptation
### CA-01
- **Critère** : Étant donné …, quand …, alors …
- **Règles** : RG-01
### CA-02
- **Critère** : …
- **Sources** : « passage exact de l'exigence d'origine »

## Points ouverts
- <sujet non tranché, sans source, qui n'est donc ni règle ni critère> (Q-3)
```

« Règles métier » est obligatoire : écris « Aucune » s'il n'y en a pas.
Un critère qui vérifie une règle hypothèse est lui-même une hypothèse.
La section « Points ouverts » est facultative : omets-la s'il n'y en a pas.

Numérote RG-01, RG-02… et CA-01, CA-02… sans trou.
