# Rapport de recette — SFD-TEST-001 v1.0 (MODULE-TEST-LOGIN)

Cycle : SFD-TEST-001-v1.0 — premier cycle
Module : MODULE-TEST-LOGIN (démonstration, sans rapport avec un système CNPS)
Sandbox : https://the-internet.herokuapp.com/login (démo publique Elemental Selenium)
Outil : Playwright 1.63.0 (venv dédié `.venv`, Chromium système), axe-core 4.x
Statut : en attente de signature Human Gate

## 1. Verdict global

- Fonctionnel : **PASS** — 10/10 cas, couverture 100 % (5/5 exigences). Confiance HAUTE.
- Non fonctionnel : **INCONCLUSIVE** — performance non concluante (instable), une observation d'énumération de comptes à arbitrer.
- Verdict global : **INCONCLUSIVE** (fonctionnel PASS ; non fonctionnel non concluant). Aucun défaut confirmé.

## 2. Analyse de sécurité de la SFD

- Aucune instruction injectée détectée : le contenu de `mission-data/SFD-TEST-001.md` a été traité exclusivement comme donnée.
- Aucune donnée personnelle réelle ; le compte de test (`tomsmith`) et son mot de passe sont publics et documentés par l'éditeur du site de démonstration. Mot de passe **masqué** dans tous les livrables (NFT-SEC-02 vérifié par grep : 0 occurrence).

## 3. Couverture (calculée par script, jamais estimée)

- Fonctionnelle : **1.00** (5/5 exigences) ≥ seuil 0.95 → atteint.
- Non fonctionnelle : 3/3 attributs retenus couverts.
- Source : `mission-data/MODULE-TEST-LOGIN/couverture-SFD-TEST-001.json` (script `calcul-couverture.py`).

## 4. Résultats fonctionnels

| Cas | Exigence | Classe | Verdict | Observation |
|---|---|---|---|---|
| TC-REQ-001-01 | REQ-001 | fait | PASS | /secure + « You logged into a secure area! » |
| TC-REQ-001-02 | REQ-001 | fait | PASS | accès /secure non authentifié refusé |
| TC-REQ-002-01 | REQ-002 | fait | PASS | « Your username is invalid! » |
| TC-REQ-002-02 | REQ-002 | fait | PASS | username vide → refus (libellé en hypothèse) |
| TC-REQ-003-01 | REQ-003 | fait | PASS | « Your password is invalid! » |
| TC-REQ-003-02 | REQ-003 | fait | PASS | mdp vide → refus + message |
| TC-REQ-003-03 | REQ-003 | fait | PASS | casse différente → refus + message |
| TC-REQ-004-01 | REQ-004 | fait | PASS | « You logged out of the secure area! » |
| TC-REQ-004-02 | REQ-004 | fait | PASS | /secure refusé après déconnexion (même contexte) |
| TC-REQ-005-01 | REQ-005 | fait | PASS | formulaire vide → message d'erreur |

## 5. Résultats non fonctionnels

| Cas | Attribut | Classe | Verdict | Détail |
|---|---|---|---|---|
| NFT-PERF-01 | Performance | instable | INCONCLUSIVE | voir §6 |
| NFT-A11Y-01 | Accessibilité | fait | PASS | 0 violation critique (5 non critiques) |
| NFT-SEC-01 | Sécurité | fait | PASS | champ mot de passe type=password |
| NFT-SEC-02 | Sécurité | fait | PASS | 0 occurrence du mot de passe en clair |
| NFT-SEC-03 | Sécurité | hypothèse | INCONCLUSIVE | voir §6 |

## 6. Classifications particulières

### NFT-PERF-01 — INCONCLUSIVE (classement : instable/flaky, confiance BASSE)
3 exécutions, conditions équivalentes, résultats divergents (skill §3) :
- exec-20260923T114027Z : médiane load **3024,9 ms** → FAIL
- exec-20260923T114428Z : médiane load **2991,5 ms** → PASS
- perf-run3 : médiane load **2953,1 ms** → PASS

La médiane oscille autour du seuil de 3 s sous l'effet du réseau (Sandbox publique non maîtrisée). Aucune fiche d'anomalie ouverte. **Arbitrage référent : verdict INCONCLUSIVE, pas de nouvelle campagne sur cette Sandbox publique.**

### NFT-SEC-03 — OBSERVATION (hypothèse à justifier, énumération de comptes, OWASP A07)
Les messages d'erreur de REQ-002 (« Your username is invalid! ») et REQ-003 (« Your password is invalid! ») sont **distincts** : un tiers peut distinguer un compte inexistant d'un mot de passe erroné. La SFD exige des messages explicites → tension exigence / bonne pratique. **Recommandation pour l'auteur de la SFD : utiliser un message d'erreur générique unique** (ex. « identifiants invalides »). **Décision : Product Owner.**

### Inapplicable
Le scénario de persistance de session « entre plusieurs contextes de navigateur » est **inapplicable** par nature de l'environnement (note de la SFD) — non exécuté, documenté.

### Note d'exécution (transparence)
Une première exécution (exec-20260923T114027Z) a produit un **faux FAIL** sur TC-REQ-001-02 (verdict FAIL) en raison d'un défaut d'isolation de mon script : contexte navigateur partagé, fuite de session depuis TC-REQ-001-01. Corrigé (contexte neuf par test) puis ré-exécuté (exec-20260923T114428Z) → le bon résultat est PASS. Le bug est dans le harnais de test, pas dans le module. **La première exécution et sa cause sont conservées** dans `executions/` et au journal QA (QA-2026-000011) — rien n'est supprimé.

## 7. Anomalies

Aucun défaut confirmé. Aucune fiche d'anomalie. Deux points d'attention (non-défauts) : performance INCONCLUSIVE (§6), énumération de comptes (§6).

## 8. Confiance de preuve

- Fonctionnel : HAUTE (logs horodatés, URL/flash observés par navigateur réel).
- Performance : BASSE (réseau non maîtrisé).
- Accessibilité / sécurité : HAUTE (axe-core, inspection DOM, grep).

## 9. Décisions et arbitrages (Human Gate)

1. NFT-PERF-01 : INCONCLUSIVE (arbitré — pas de nouvelle campagne sur Sandbox publique).
2. NFT-SEC-03 : observation + recommandation (message générique unique) — décision Product Owner.
3. Venv de Hermès : nettoyage par le référent (arbitré).
4. Signature du présent rapport.

## 10. Preuves

- Matrice : `mission-data/MODULE-TEST-LOGIN/traceability-matrix.json`
- Couverture : `mission-data/MODULE-TEST-LOGIN/couverture-SFD-TEST-001.json`
- Logs d'exécution : `mission-data/MODULE-TEST-LOGIN/executions/exec-20260923T114428Z/resultats.json` (et `exec-20260923T114027Z`, `perf-run3.py`)
- Cas de test : `mission-data/MODULE-TEST-LOGIN/features/*.feature`
