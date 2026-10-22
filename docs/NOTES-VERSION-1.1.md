# QA-T-AG — Application web v1.1.0 (recette)

*L'IA au service de la qualité logicielle.*

La v1.1 ajoute la **recette** au cycle de la v1.0 : après PV-2, les cas validés
sont exécutés, les échecs deviennent des anomalies qualifiées, la recette est
clôturée et le cahier de recette Word sort de la base. Elle intègre aussi les
lots de sécurité S1 et S2.

Principe inchangé : **le script calcule · l'agent analyse · l'humain arbitre.**

## Recette

- **Exécution manuelle** des cas, passage par passage, historique conservé :
  statut (Succès, Échec, Non testable, Non exécuté), résultat obtenu,
  commentaire, captures (bouton ou Ctrl+V).
- **Règles serveur** : résultat obtenu et au moins une capture exigés pour
  Succès et Échec, commentaire exigé pour Non testable et Non exécuté.
- **Captures en base** avec empreinte SHA-256, PNG ou JPEG reconnus à leur
  signature, couvertes par la sauvegarde.
- **Anomalies ANO-nnn** ouvertes par chaque échec, sans doublon au nouvel échec.
- **AG-09** propose titre, gravité, reproductibilité et justification
  (`controler_qualification.py` contrôle le format) ; l'humain confirme ou
  requalifie avec motif. Sans IA, qualification manuelle.
- **Cycle de vie** : corrigée → fermée par un passage réussi, rejetée ou
  rouverte avec motif.
- **Clôture** sans réserve, ou avec réserves motivées et figées ; mêmes règles
  d'habilitation que les Human Gates.
- **Suivi et levée des réserves** : après une clôture avec réserves, les seuls
  cas en réserve restent rejouables et leurs anomalies suivies ; la levée des
  réserves est une décision distincte (statut « Réserves levées »).
- **Cahier de recette Word** au gabarit DSI du rapport de test : contexte,
  objectifs, un bloc par cas avec captures, comptage, récapitulatif,
  synthèse, conclusion ; relu et comparé à la base avant d'être remis (RA-33).
- **AG-11** rédige contexte, objectifs, synthèse, recommandations, conclusion
  et avis sur la mise en production (`controler_rapport.py` vérifie chiffres,
  références et avis) ; l'humain corrige et valide ; seul le texte validé
  entre dans le cahier, recontrôlé à l'export.

## Sécurité (lots S1 et S2)

Inscription fermée après le premier compte, limitation des tentatives de
connexion, en-têtes HTTP, sauvegardes vérifiées, mots de passe provisoires à
changer à la première connexion, réinitialisation par l'administrateur,
sessions fermées après un changement de mot de passe.

## Règles et tests

- Règles RA-01 à RA-68 dans `docs/specifications.md`, reliées à leurs tests (§ 12).
- 215 tests automatiques côté serveur.
- Migrations 0001 à 0009, applicables sur une base existante.

## Mettre à jour

`git pull`, puis dans `app\backend` : `pip install -r requirements.txt` et
`alembic upgrade head` ; dans `app\frontend` : `npm install` et `npm run build` ;
redémarrer le serveur.

## Limites connues

- **Exécution automatique (AG-08) et régression (AG-10)** : prévues après
  l'évaluation des agents, sur un environnement de recette isolé.
- **Confidentialité** : avec un fournisseur d'IA en ligne, le texte des
  exigences et des anomalies quitte le poste. Pour des données réelles,
  privilégier Ollama (local) ou anonymiser.
- **HTTPS** à mettre en place avant toute utilisation depuis un autre poste.
