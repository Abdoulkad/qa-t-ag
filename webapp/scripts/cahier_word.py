#!/usr/bin/env python3
"""Cahier de test Word (AG-06) — remplit le gabarit DSI sans reformuler.

Recopie le fichier des cas (12 colonnes) dans le gabarit Word, un bloc par CT,
en cochant priorité et type (☒). Script déterministe : aucun modèle.

Usage : python cahier_word.py <modele.docx> <cas.csv> <sortie.docx>
Codes : 0 = écrit, 2 = entrée inexploitable, 3 = défaut du script.
Auto-test : python cahier_word.py --selftest <modele.docx>
"""

import copy
import csv
import os
import sys
import tempfile

import docx
from docx.text.paragraph import Paragraph
from docx.table import Table

ORGANISATION = "CNPS — Direction du Système d'Information"

EN_TETE_CAS = [
    "ID", "Titre", "Objectif", "Exigence", "Technique", "Priorité", "Type",
    "Préconditions", "Données de test", "Étapes", "Résultat attendu",
    "Statut livrable",
]
PRIO_TOK = {"Critique": "P1", "Haute": "P2", "Moyenne": "P3"}
TYPE_TOK = {"Fonctionnel": "T1", "Sécurité/Habilitation": "T2", "Interface utilisateur": "T3"}


def _remplacer_paragraphe(p, mapping):
    plein = p.text
    for tok, val in mapping.items():
        plein = plein.replace(tok, val)
    if plein != p.text:
        runs = p.runs
        if runs:
            runs[0].text = plein
            for r in runs[1:]:
                r._element.getparent().remove(r._element)
        else:
            p.add_run(plein)


def _mapping_ct(cols):
    m = {
        "{{ID}}": cols[0].strip(),
        "{{TITRE}}": cols[1].strip(),
        "{{OBJECTIF}}": cols[2].strip(),
        "{{EXIGENCE}}": cols[3].strip(),
        "{{PRECONDITIONS}}": cols[7].strip(),
        "{{DONNEES}}": cols[8].strip(),
        "{{ETAPE}}": cols[9].strip(),
        "{{RESULTAT}}": cols[10].strip(),
    }
    statut = cols[11].strip()
    m["{{COMMENTAIRE}}"] = "À_CLARIFIER" if statut == "À_CLARIFIER" else ""
    sel_p = PRIO_TOK.get(cols[5].strip())
    for k in ("P1", "P2", "P3"):
        m["{{%s}}" % k] = "☒" if k == sel_p else "☐"
    sel_t = TYPE_TOK.get(cols[6].strip())
    for k in ("T1", "T2", "T3"):
        m["{{%s}}" % k] = "☒" if k == sel_t else "☐"
    return m


def _remplir_bloc(paragraphe, table, mapping):
    _remplacer_paragraphe(paragraphe, mapping)
    for row in table.rows:
        for cell in row.cells:
            for p in cell.paragraphs:
                _remplacer_paragraphe(p, mapping)


def _trouver_bloc(doc):
    paragraphe = None
    for p in doc.paragraphs:
        if "{{ID}}" in p.text:
            paragraphe = p
            break
    table = None
    for t in doc.tables:
        txt = "\n".join(c.text for row in t.rows for c in row.cells)
        if "{{OBJECTIF}}" in txt:
            table = t
            break
    return paragraphe, table


def cahier(modele_path, cas_path, sortie_path):
    for p in (modele_path, cas_path):
        if not os.path.isfile(p):
            return 2, "fichier introuvable : %s" % p
    try:
        doc = docx.Document(modele_path)
        with open(cas_path, "r", encoding="utf-8-sig") as f:
            lignes = list(csv.reader(f, delimiter=";"))
    except Exception as e:
        return 3, "défaut du script : %s" % e
    if not lignes or lignes[0] != EN_TETE_CAS:
        return 2, "en-tête du fichier des cas non conforme"
    cts = [l for l in lignes[1:] if l and any(c.strip() for c in l)]
    if not cts:
        return 2, "fichier des cas vide"

    for p in doc.paragraphs:
        if "{{ORGANISATION}}" in p.text:
            _remplacer_paragraphe(p, {"{{ORGANISATION}}": ORGANISATION})

    paragraphe, table = _trouver_bloc(doc)
    if paragraphe is None or table is None:
        return 2, "gabarit sans bloc de cas de test"

    # captures des originaux AVANT remplissage (pour cloner encore avec jetons)
    p_original = copy.deepcopy(paragraphe._element)
    t_original = copy.deepcopy(table._element)

    # premier CT : remplit le bloc existant
    _remplir_bloc(paragraphe, table, _mapping_ct(cts[0]))

    # CT suivants : cloner le bloc original, remplir, insérer après
    ancre = table._element
    for cols in cts[1:]:
        m = _mapping_ct(cols)
        new_p_el = copy.deepcopy(p_original)
        new_t_el = copy.deepcopy(t_original)
        ancre.addnext(new_p_el)
        new_p_el.addnext(new_t_el)
        new_p = Paragraph(new_p_el, paragraphe._parent)
        new_t = Table(new_t_el, table._parent)
        _remplir_bloc(new_p, new_t, m)
        ancre = new_t_el

    try:
        doc.save(sortie_path)
    except Exception as e:
        return 3, "échec d'écriture : %s" % e
    return 0, "Écrit : %s — Cahier : %d CT écrits" % (sortie_path, len(cts))


def _auto_test(modele_path):
    if not os.path.isfile(modele_path):
        return [("gabarit introuvable", modele_path)]
    echecs = []
    rep = tempfile.mkdtemp()
    fcas = os.path.join(rep, "cas-demo.csv")
    fout = os.path.join(rep, "cahier-demo.docx")
    cts = [
        ["CT-001", "Calcul du montant", "Vérifier le calcul", "REQ-001",
         "valeurs limites", "Critique", "Fonctionnel", "pré", "données",
         "Saisir 100 001", "montant refusé", "OK"],
        ["CT-002", "Ouverture du droit", "Vérifier l'ouverture", "REQ-002",
         "transitions d'état", "Haute", "Sécurité/Habilitation", "pré", "d",
         "Valider", "droit ouvert", "À_CLARIFIER"],
    ]
    try:
        with open(fcas, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(EN_TETE_CAS)
            for l in cts:
                w.writerow(l)
        code, msg = cahier(modele_path, fcas, fout)
        if code != 0:
            echecs.append(("code %d" % code, msg))
        else:
            d = docx.Document(fout)
            texte = "\n".join(p.text for p in d.paragraphs)
            texte += "\n" + "\n".join(c.text for t in d.tables for r in t.rows for c in r.cells)
            if "{{" in texte:
                echecs.append(("jetons non remplacés restants", ""))
            for ct_id in ("CT-001", "CT-002"):
                if ct_id not in texte:
                    echecs.append(("CT manquant", ct_id))
            if "À_CLARIFIER" not in texte:
                echecs.append(("commentaire À_CLARIFIER absent", ""))
            # un bloc par CT : compter les tables « Cas de test »
            n_blocs = sum(1 for t in d.tables
                          if "Cas de test" in (t.rows[0].cells[0].text if t.rows else ""))
            if n_blocs != 2:
                echecs.append(("nombre de blocs != 2", n_blocs))
    finally:
        import shutil
        shutil.rmtree(rep, ignore_errors=True)
    return echecs


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "--selftest":
        modele = sys.argv[2] if len(sys.argv) >= 3 else "modele-cahier-cas.docx"
        e = _auto_test(modele)
        if e:
            for x in e:
                print("ÉCHEC:", x)
            sys.exit(1)
        print("Auto-test cahier_word.py : OK (blocs par CT, jetons remplis, ☒)")
        sys.exit(0)
    if len(sys.argv) != 4:
        print("Usage : python cahier_word.py <modele.docx> <cas.csv> <sortie.docx>",
              file=sys.stderr)
        sys.exit(3)
    code, msg = cahier(sys.argv[1], sys.argv[2], sys.argv[3])
    print(msg)
    sys.exit(code)
