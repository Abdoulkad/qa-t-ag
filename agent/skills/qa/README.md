# QA-T-AG — Skills Hermès (16 skills, 19 scripts déterministes)

Implémentation sous **Hermès** du système QA-T-AG (13 agents IA d'assurance
qualité pour la DSI de la CNPS), migré depuis Claude Code. Principe directeur :
**« Le script calcule, l'agent analyse, l'humain arbitre. »**

## Socle déterministe (Phase 0/1)

`qa-t-ag-socle/` — briques déterministes (7 scripts, tous auto-testés) :
statuts normalisés (`statuts.py`), empreinte SHA-256 (`empreinte.py`),
contrats JSON Schema (`contrats.py` + `schemas/`), journal append-only
(`journal.py`), transitions de campagne à 2 portes (`etat_chaine.py`),
manifeste (`manifeste.py`), portes de validation PV-1/PV-2 (`pv.py`).

## Agents V1 (conception de la chaîne)

| Agent | Skill | Script |
|---|---|---|
| AG-01 Revue SFD | `qa-revue-sfd` | `controler_revue.py` |
| AG-02 Conception des cas | `qa-conception` | `controler_cas.py` |
| AG-03 Traçabilité | `qa-tracabilite` | `tracer.py` |
| AG-04 Données de test | `qa-donnees` | `donnees.py` |
| AG-05 Relecteur critique | `qa-relecteur` | `verifier_relecture.py` |
| AG-06 Cahier Word | `qa-cahier` | `cahier_word.py` |
| AG-07 Orchestrateur | `qa-orchestrateur` | (procédure) |

## V2 (exécution) et V3 (non fonctionnel)

| Agent | Skill | Script |
|---|---|---|
| AG-08 Exécution | `qa-execution` | `resultats.py` |
| AG-09 Anomalies | `qa-anomalies` | `controler_anomalies.py` |
| AG-10 Régression | `qa-regression` | `impact.py` |
| AG-11 Performance | `qa-performance` | `controler_scenarios.py` |
| AG-12 Sécurité | `qa-securite` | `controler_securite.py` |
| AG-13 Ergonomie/accessibilité | `qa-ergonomie` | `controler_ergonomie.py` |

## Méthode et sécurité

- `qa-t-ag-migration/` — méthode de construction/extension de QA-T-AG sous Hermès.
- `sources-non-fiables/` — immunité aux injections indirectes, masquage PII.

## Vérification

Chaque script déterministe embarque un auto-test : `python <script> --selftest`
(`cahier_word.py` requiert le gabarit : `--selftest <modele.docx>`).
Aucun `PASS` n'est émis sans sortie d'exécution qui le prouve.
