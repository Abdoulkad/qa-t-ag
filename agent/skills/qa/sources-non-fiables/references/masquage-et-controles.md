# Masquage PII et contrôles de fin de cycle

## Recette de masquage sans exposition

Objectif : tracer qu'une donnée sensible existe, sans jamais la faire
apparaître — ni dans un livrable, ni dans un journal, ni dans la réponse
rendue à l'utilisateur.

1. **Extraire par script**, depuis la source, avec des motifs larges
   (adresse électronique, suite de chiffres de type téléphone, nom saisi
   entre une amorce et le premier séparateur). Ne pas recopier à la main :
   le raisonnement lui-même ferait repasser la valeur dans le contexte.
2. **Vérifier le compte** : si l'extraction retourne moins de valeurs que la
   structure du document n'en laisse attendre, s'arrêter là et le déclarer.
   Un masquage incomplet est pire qu'un masquage annoncé comme incomplet.
3. **Tracer par empreinte** : pour chaque valeur, journaliser le type, la
   longueur et un préfixe d'empreinte SHA-256, jamais la valeur. C'est ce qui
   permet à un tiers de vérifier qu'une même valeur n'est pas réapparue
   ailleurs, sans la lui communiquer.
4. **Écrire dans le conteneur de secrets** du module, une valeur par ligne.
   Avant toute écriture — y compris un simple ajout à un conteneur déjà
   existant — vérifier que le fichier est ignoré par git :
   `git check-ignore -v <chemin>` doit retourner une ligne. Un dépôt peut
   n'avoir aucun `.gitignore` : le créer alors, avant d'écrire.
5. **Contrôler après coup, par script** : aucun livrable du périmètre ne doit
   contenir une valeur du conteneur. Le conteneur lui-même est exclu du
   contrôle (il est son emplacement désigné, non versionné, non livré).

## Journal append-only : comment corriger une entrée

Une entrée de journal de faits ne se réécrit jamais. Pour rectifier un état
devenu faux (escalade déclarée non transmissible, puis transmise par un autre
canal), écrire une **nouvelle** entrée référençant l'identifiant de l'ancienne
(champ de type `rectifies`, ou équivalent du schéma du journal). L'ancienne
reste lisible : c'est la trace de ce qui a été cru vrai à cet instant.

## Contrôles de fin de cycle

À regrouper dans un script ré-exécutable du module, pas à refaire à la main.
Quatre contrôles, dans cet ordre, sur le périmètre du cycle :

1. **Intégrité des sources** — empreinte de chaque fichier source identique à
   celle relevée avant le cycle. Prouve qu'aucune correction n'a été portée au
   document.
2. **Zéro donnée sensible en clair** — parcourir tous les artefacts produits
   et chercher chaque valeur du conteneur de secrets ; attendu : 0 occurrence.
3. **Journal lisible et continu** — chaque ligne est un objet valide,
   identifiants sans doublon et sans trou ; compter les entrées du cycle par
   type.
4. **Périmètre respecté** — les artefacts qui ne devaient **pas** être produits
   (cas de test, matrice, rapport de recette, calcul de couverture) sont
   effectivement absents. C'est ce contrôle qui prouve l'arrêt du cycle ; sans
   lui, l'affirmation « je n'ai rien produit » n'est qu'une affirmation.

Sortie attendue : un code de sortie non nul dès qu'un contrôle échoue, pour
que le script soit utilisable comme garde-fou et pas seulement comme rapport.
