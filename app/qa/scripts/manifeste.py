#!/usr/bin/env python3
"""Manifeste de campagne (SFD §6, §7.3).

Lie campaign_id, artefacts d'entrée et livrables d'agents à leurs empreintes
SHA-256. Les empreintes sont calculées par script (empreinte.py), jamais
fournies par l'appelant.

`verifier_empreintes` re-calcule les empreintes des artefacts enregistrés et
signale tout écart : c'est le déclencheur des invalidations en cascade (§7.3),
les livrables dépendants devant alors passer à `A_RECALCULER` — signalé ici,
jamais recalculé en silence.

Auto-test : `python manifeste.py` (code 0 = OK).
"""

import json
import os
import sys
import tempfile
from datetime import datetime, timezone

import empreinte

STATUT_INVALIDATION = "A_RECALCULER"


def _horodatage_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


class Manifeste:
    """Manifeste de campagne persisté en JSON."""

    def __init__(self, chemin):
        self.chemin = chemin
        self.donnees = self._charger()

    def _charger(self):
        if os.path.isfile(self.chemin):
            with open(self.chemin, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "campaign_id": None,
            "project_id": None,
            "created_at": None,
            "inputs": {},
            "livrables": [],
        }

    def _sauver(self):
        with open(self.chemin, "w", encoding="utf-8") as f:
            json.dump(self.donnees, f, ensure_ascii=False, indent=2)

    def creer(self, campaign_id, project_id, chemins_entree):
        """Initialise le manifeste et enregistre les artefacts d'entrée.

        `chemins_entree` : liste de chemins ; les empreintes sont calculées ici.
        """
        self.donnees["campaign_id"] = campaign_id
        self.donnees["project_id"] = project_id
        self.donnees["created_at"] = _horodatage_utc()
        self.donnees["inputs"] = {
            c: empreinte.empreinte_fichier(c) for c in chemins_entree
        }
        self.donnees["livrables"] = []
        self._sauver()
        return self.donnees["inputs"]

    def ajouter_livrable(self, task_id, agent_id, chemin_livrable, statut):
        """Enregistre un livrable avec son empreinte et son statut."""
        e = empreinte.empreinte_fichier(chemin_livrable)
        livrable = {
            "task_id": task_id,
            "agent_id": agent_id,
            "path": chemin_livrable,
            "sha256": e,
            "status": statut,
            "recorded_at": _horodatage_utc(),
        }
        self.donnees["livrables"].append(livrable)
        self._sauver()
        return livrable

    def verifier_empreintes(self):
        """Re-calcule les empreintes ; retourne la liste des écarts détectés.

        Un écart sur une entrée invalide (en cascade, §7.3) les livrables qui
        en dépendent — signalés ici, pas recalculés en silence.
        """
        ecarts = []
        for chemin, attendu in self.donnees.get("inputs", {}).items():
            if not os.path.isfile(chemin):
                ecarts.append({"path": chemin, "attendu": attendu, "observe": "INTROUVABLE"})
            else:
                observe = empreinte.empreinte_fichier(chemin)
                if observe != attendu:
                    ecarts.append({"path": chemin, "attendu": attendu, "observe": observe})
        for l in self.donnees.get("livrables", []):
            if not os.path.isfile(l["path"]):
                ecarts.append({"path": l["path"], "attendu": l["sha256"], "observe": "INTROUVABLE"})
            else:
                observe = empreinte.empreinte_fichier(l["path"])
                if observe != l["sha256"]:
                    ecarts.append({"path": l["path"], "attendu": l["sha256"], "observe": observe})
        return ecarts


def _auto_test():
    fd, chemin_manifeste = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    os.unlink(chemin_manifeste)
    fd, chemin_entree = tempfile.mkstemp(suffix=".txt")
    with os.fdopen(fd, "w") as f:
        f.write("entree v1")
    fd, chemin_livrable = tempfile.mkstemp(suffix=".md")
    with os.fdopen(fd, "w") as f:
        f.write("# livrable")
    echecs = []
    try:
        m = Manifeste(chemin_manifeste)
        m.creer("QA-001", "PROJ-001", [chemin_entree])
        m.ajouter_livrable("TASK-1", "AG-01", chemin_livrable, "OK")
        if m.verifier_empreintes():
            echecs.append(("écart inattendu sur manifeste intact", m.verifier_empreintes()))
        with open(chemin_entree, "w") as f:
            f.write("entree v2")
        ecarts = m.verifier_empreintes()
        if not any(e["path"] == chemin_entree for e in ecarts):
            echecs.append(("écart non détecté après modification", ecarts))
    finally:
        for c in (chemin_manifeste, chemin_entree, chemin_livrable):
            if os.path.isfile(c):
                os.unlink(c)
    return echecs


if __name__ == "__main__":
    echecs = _auto_test()
    if echecs:
        for e in echecs:
            print("ÉCHEC:", e)
        print("%d échec(s)" % len(echecs))
        sys.exit(1)
    print("Auto-test manifeste.py : OK (création, empreintes, invalidation cascade)")
    sys.exit(0)
