"""Cahier de recette Word (RA-32, RA-33).

Même gabarit DSI que le cahier des cas : cahier_word.py recopie les cas sans les
reformuler, puis ce module remplit les zones d'exécution depuis la base
(résultat observé, statut coché, captures, testeur et date, commentaires et
anomalies) et ajoute une synthèse en tête. Le fichier produit est ensuite relu :
chaque cas doit y porter le statut enregistré en base, sinon rien n'est remis.
"""
import hashlib
import io
import json
import os
import tempfile

import docx
from docx.shared import Cm
from sqlalchemy import select
from sqlalchemy.orm import Session, undefer

from . import journal, scripts_qa
from .missions import lignes_cahier, version_courante
from .models import (Anomalie, ClotureRecette, DecisionPorte, Execution, Mission, Preuve,
                     Utilisateur)
from .recette import dernieres_executions
from .regles import RegleViolee

STATUTS_EXPORT = ("EN_RECETTE", "CLOTUREE")
# Statut en base -> libellé de la case à cocher du gabarit
CASES = {"PASS": "PASS", "FAIL": "FAIL", "BLOCKED": "BLOQUÉ", "NOT_RUN": "NON EXÉCUTÉ"}
LIGNE_STATUTS = "☐  PASS        ☐  FAIL        ☐  BLOQUÉ        ☐  NON EXÉCUTÉ"
LIBELLES_ANOMALIE = {"OUVERTE": "ouverte", "CORRIGEE": "corrigée, à retester",
                     "FERMEE": "fermée", "REJETEE": "rejetée"}


class ControleEchoue(Exception):
    """RA-33 : le fichier produit ne correspond pas à la base."""


def _nom(db: Session, uid: int) -> str:
    p = db.get(Utilisateur, uid)
    return (p.nom or p.email) if p else "?"


def _ligne(table, debut: str):
    """Ligne du bloc de cas dont la première cellule commence par `debut`."""
    for row in table.rows:
        if row.cells[0].text.strip().startswith(debut):
            return row
    raise ControleEchoue("gabarit inattendu : ligne « %s » absente" % debut)


def _ecrire(cellule, texte: str) -> None:
    """Remplace le contenu de la cellule (premier paragraphe), vide les suivants."""
    paragraphes = cellule.paragraphs
    lignes = texte.split("\n")
    paragraphes[0].text = lignes[0]
    for i, p in enumerate(paragraphes[1:], start=1):
        p.text = lignes[i] if i < len(lignes) else ""
    for reste in lignes[len(paragraphes):]:
        cellule.add_paragraph(reste)


def _blocs(doc) -> list[tuple[str, object]]:
    """(code du cas, table) pour chaque bloc de cas, dans l'ordre du document."""
    blocs = []
    for t in doc.tables:
        if not any(r.cells[0].text.strip().startswith("Statut d'exécution") for r in t.rows):
            continue
        precedent = t._element.getprevious()
        texte = "".join(precedent.itertext()) if precedent is not None else ""
        blocs.append((texte.split(" : ")[0].strip(), t))
    return blocs


def _statut_coche(table) -> str | None:
    texte = _ligne(table, "Statut d'exécution").cells[-1].text
    coches = [code for code, libelle in CASES.items() if "☒  %s" % libelle in texte]
    return coches[0] if len(coches) == 1 else None


def _synthese(doc, premier, compte: dict, anomalies: list[Anomalie], codes: dict,
              etat: str, reserves: list[str]) -> None:
    """Synthèse insérée avant le premier cas : compteurs, anomalies, clôture."""
    def paragraphe(texte, gras=False):
        run = premier.insert_paragraph_before().add_run(texte)
        run.bold = gras
        return run

    paragraphe("Synthèse de la recette", gras=True)
    paragraphe(etat)
    paragraphe("Cas : %d · réussis : %d · en échec : %d · non testables : %d · "
               "non exécutés : %d" % (compte["total"], compte["PASS"], compte["FAIL"],
                                      compte["BLOCKED"], compte["NOT_RUN"] + compte["aucun"]))
    if anomalies:
        paragraphe("Anomalies (%d)" % len(anomalies), gras=True)
        table = doc.add_table(rows=1, cols=5)
        if "Table Grid" in [st.name for st in doc.styles]:
            table.style = doc.styles["Table Grid"]
        for cellule, titre in zip(table.rows[0].cells,
                                  ("Anomalie", "Cas", "Gravité", "Statut", "Titre")):
            cellule.text = titre
        for a in anomalies:
            r = table.add_row().cells
            r[0].text, r[1].text = a.code, codes.get(a.cas_id, "")
            r[2].text = a.gravite or "À qualifier"
            r[3].text = LIBELLES_ANOMALIE[a.statut]
            r[4].text = a.titre
        premier._p.addprevious(table._tbl)
    else:
        paragraphe("Aucune anomalie.")
    if reserves:
        paragraphe("Réserves (%d)" % len(reserves), gras=True)
        for r in reserves:
            paragraphe("• " + r)
    premier.insert_paragraph_before("")


def exporter(db: Session, u: Utilisateur, m: Mission) -> tuple[bytes, str]:
    if m.statut not in STATUTS_EXPORT:
        raise RegleViolee("RA-32", "Le cahier de recette s'exporte une fois la recette "
                                   "commencée (statut actuel : %s)" % m.statut)
    v = version_courante(m)
    cas, lignes = lignes_cahier(db, v, "RA-32")
    dernieres = dernieres_executions(db, [c.id for c in cas])
    passages = {c.id: 0 for c in cas}
    for (cas_id,) in db.execute(select(Execution.cas_id).where(
            Execution.cas_id.in_([c.id for c in cas]))):
        passages[cas_id] += 1
    preuves: dict[int, list[Preuve]] = {}
    for p in db.scalars(select(Preuve).options(undefer(Preuve.contenu)).where(
            Preuve.execution_id.in_([e.id for e in dernieres.values()])).order_by(Preuve.id)):
        preuves.setdefault(p.execution_id, []).append(p)
    anomalies = db.scalars(select(Anomalie).where(Anomalie.mission_id == m.id)
                           .order_by(Anomalie.code)).all()
    codes = {c.id: c.code for c in cas}
    cloture = db.scalar(select(ClotureRecette).where(ClotureRecette.mission_id == m.id))
    pv2 = db.scalar(select(DecisionPorte).where(DecisionPorte.version_id == v.id,
                                                DecisionPorte.porte == "PV-2",
                                                DecisionPorte.decision == "APPROUVE"))

    compte = {"PASS": 0, "FAIL": 0, "BLOCKED": 0, "NOT_RUN": 0, "aucun": 0, "total": len(cas)}
    for c in cas:
        e = dernieres.get(c.id)
        compte[e.statut if e else "aucun"] += 1
    if cloture:
        etat = "Recette clôturée %s le %s par %s%s." % (
            "avec réserves" if cloture.decision == "CLOTURE_AVEC_RESERVES" else "sans réserve",
            cloture.decide_le.strftime("%d/%m/%Y"), _nom(db, cloture.decideur_id),
            " (auto-validation)" if cloture.auto_validation else "")
        if cloture.commentaire:
            etat += " Motif : %s" % cloture.commentaire
        reserves = json.loads(cloture.reserves)
    else:
        etat = "DOCUMENT DE TRAVAIL — recette en cours, non clôturée."
        reserves = []
    entete = "Mission %s — %s · version %d · empreinte %s" % (
        m.reference, m.titre, v.numero, v.empreinte[:12])
    validation = ("Cas validés à PV-2 le %s par %s" % (pv2.decide_le.strftime("%d/%m/%Y"),
                                                        _nom(db, pv2.decideur_id))
                  if pv2 else "")
    bandeau = "CAHIER DE RECETTE\n%s · %d cas\n%s" % (entete, len(cas), validation)

    fd, chemin = tempfile.mkstemp(suffix=".docx")
    os.close(fd)
    try:
        scripts_qa.cahier_cas(lignes, bandeau, chemin)
        doc = docx.Document(chemin)
        for p in doc.paragraphs:
            if p.text.strip() == "CAS DE TEST":
                p.text = "CAHIER DE RECETTE"
        blocs = _blocs(doc)
        if [code for code, _ in blocs] != [c.code for c in cas]:
            raise ControleEchoue("blocs de cas inattendus dans le document produit")
        for c, (_, table) in zip(cas, blocs):
            e = dernieres.get(c.id)
            statut = e.statut if e else "NOT_RUN"
            ligne_statut = LIGNE_STATUTS.replace("☐  %s" % CASES[statut], "☒  %s" % CASES[statut])
            _ecrire(_ligne(table, "Statut d'exécution").cells[-1],
                    "Statut d'exécution :\n" + ligne_statut)
            observe = _ligne(table, "Résultat observé").cells[-1]
            capture = _ligne(table, "Capture d'écran").cells[-1]
            testeur = _ligne(table, "Testeur & Date").cells[-1]
            remarques = [a for a in anomalies if a.cas_id == c.id]
            commentaire = []
            if e is None:
                _ecrire(observe, "Cas non exécuté.")
                _ecrire(capture, "—")
                _ecrire(testeur, "Nom du testeur : —          Date : —")
            else:
                _ecrire(observe, "Passage %d du %s\n%s" % (
                    passages[c.id], e.execute_le.strftime("%d/%m/%Y %H:%M"),
                    e.resultat_obtenu or "—"))
                images = preuves.get(e.id, [])
                _ecrire(capture, "" if images else "Aucune capture.")
                for p in images:
                    run = capture.paragraphs[-1].add_run()
                    run.add_picture(io.BytesIO(p.contenu), width=Cm(12))
                    capture.add_paragraph("%s · SHA-256 %s" % (p.nom, p.empreinte[:16]))
                _ecrire(testeur, "Nom du testeur : %s          Date : %s" % (
                    _nom(db, e.testeur_id), e.execute_le.strftime("%d / %m / %Y")))
                if e.commentaire:
                    commentaire.append(e.commentaire)
            commentaire += ["%s (%s, %s) : %s" % (a.code, a.gravite or "à qualifier",
                                                  LIBELLES_ANOMALIE[a.statut], a.titre)
                            for a in remarques]
            _ecrire(_ligne(table, "Commentaires").cells[-1], "\n".join(commentaire) or "—")
        premier = next(p for p in doc.paragraphs if p.text.startswith(cas[0].code + " : "))
        _synthese(doc, premier, compte, anomalies, codes, etat, reserves)
        doc.save(chemin)

        # RA-33 : relecture du fichier produit, comparaison à la base
        relu = docx.Document(chemin)
        blocs_relus = _blocs(relu)
        if [code for code, _ in blocs_relus] != [c.code for c in cas]:
            raise ControleEchoue("les cas du document ne correspondent pas à la base")
        for c, (_, table) in zip(cas, blocs_relus):
            attendu = dernieres[c.id].statut if c.id in dernieres else "NOT_RUN"
            if _statut_coche(table) != attendu:
                raise ControleEchoue("statut de %s différent de la base" % c.code)
        texte = "\n".join(p.text for p in relu.paragraphs) + "\n".join(
            cell.text for t in relu.tables for row in t.rows for cell in row.cells)
        absentes = [a.code for a in anomalies if a.code not in texte]
        if absentes:
            raise ControleEchoue("anomalies absentes du document : %s" % ", ".join(absentes))
        with open(chemin, "rb") as f:
            contenu = f.read()
    finally:
        os.remove(chemin)
    nom = "Cahier_recette_%s_v%d%s.docx" % (m.reference, v.numero, "" if cloture else "_brouillon")
    journal.ajouter(db, m.organisation_id, "cahier_recette_exporte", mission_id=m.id,
                    acteur_id=u.id, details={
                        "version": v.numero, "cas": len(cas), "anomalies": len(anomalies),
                        "cloturee": bool(cloture), "fichier": nom, "controle": "conforme",
                        "empreinte": hashlib.sha256(contenu).hexdigest()})
    db.commit()
    return contenu, nom
