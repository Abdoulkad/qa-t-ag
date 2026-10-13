# Grille de revue SFD — 7 catégories

Appliquée dans cet ordre fixe. Un DEF cite toujours le passage mot pour mot,
la section, une catégorie, une gravité proposée et une question au rédacteur.

## 1. Ambiguïté

**Définition** : un passage qui peut se lire de plusieurs façons, sans qu'on
puisse décider laquelle est la bonne.

**Signaux** : pronoms sans référent (« il », « ce montant »), « environ »,
« notamment », « en général », « si nécessaire », une condition non explicitée.

**Question type** : « Faut-il lire A, B, ou autre chose ? »

## 2. Contradiction

**Définition** : deux passages incompatibles sur la même grandeur (même délai,
même transition, même condition, même montant décrits différemment à deux
endroits).

**Signaux** : deux seuils différents pour la même règle, deux statuts
contradictoires, un délai qui change d'une section à l'autre. Se détecte en
croisant les trois tableaux du workflow.

**Question type** : « Quel passage fait foi ? »

## 3. Cas oublié

**Définition** : une situation possible que la SFD ne traite pas. Le
comportement n'est pas décrit : ce n'est pas une ambiguïté, c'est un trou.

**Signaux** : un délai sans règle pour « en retard / en avance / jamais », une
valeur hors bornes non traitée, une transition d'état manquante, un acteur
sans règle pour un cas particulier.

**Question type** : « Que se passe-t-il si <cas> ? »

## 4. Exigence non testable

**Définition** : une exigence sans critère observable ni mesurable — on ne
peut pas écrire un résultat attendu.

**Signaux** : « performant », « convivial », « sécurisé », « rapide » sans
seuil ; « réduit de moitié » sans ligne de base.

**Question type** : « Quel critère observable permet de vérifier cette
exigence ? »

## 5. Règle sans exigence

**Définition** : une règle de gestion (ou une exigence) qui ne se rattache à
rien : règle sans exigence qui la porte, ou exigence sans règle qui la rend
concrète.

**Signaux** : un BR cité mais jamais appelé par une REQ, une REQ qui n'impose
aucun comportement vérifiable.

**Question type** : « À quelle exigence cette règle se rattache-t-elle (ou
inversement) ? »

## 6. Terme non défini

**Définition** : un terme métier ou technique utilisé sans définition, dont le
sens n'est pas évident pour le lecteur.

**Signaux** : sigle jamais développé, notion métier propre au domaine,
grandeur sans unité.

**Question type** : « Quelle est la définition de <terme> ? »

## 7. Incohérence avec les user stories

**Définition** : un écart entre ce que dit la SFD et ce que disent les user
stories jointes (périmètre, acteur, résultat attendu).

**Signaux** : une user story qui décrit un parcours absent de la SFD, ou
l'inverse ; des acteurs différents pour le même cas.

**Question type** : « La SFD ou la user story fait-elle foi pour <point> ? »
