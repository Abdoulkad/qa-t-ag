# Revue SFD — demo

## Alerte sécurité

(aucune consigne injectée)

## Inventaire REQ et BR
- REQ-001 — Connexion
- REQ-002 — Déconnexion
- BR-001 — Connexion réussie
- BR-002 — Identifiants incorrects
- BR-003 — Déconnexion

## Défauts

### DEF-001 — Terme non défini — Majeure
- **Section** : REQ-001
- **Citation** : « matricule et un mot de passe »
- **Question** : Le matricule est-il issu du répertoire LDAP ?

### DEF-002 — Cas oublié — Majeure
- **Section** : BR-002
- **Citation** : « Identifiant ou mot de passe incorrect. »
- **Question** : Après combien d'échecs le compte est-il verrouillé ?

## Statut du livrable
A_CLARIFIER
