#!/usr/bin/env python3
"""QA-T-AG — application web (MVP Streamlit).

Écrans : SFD → Revue (PV-1) → Cas de test (PV-2) → Cahier Word.
Le LLM (DeepSeek) fait l'analyse ; les scripts déterministes contrôlent ;
les Human Gates sont des boutons.
"""
import csv
import os
import re
import subprocess
import sys
import tempfile

import streamlit as st

import agent_ia

RACINE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(RACINE, "scripts")
GABARIT_DEF = os.path.join(RACINE, "modele-cahier-cas.docx")
DEMO = os.path.join(RACINE, "demo")


def _projet(nom):
    base = os.path.splitext(nom or "projet")[0].lower()
    base = re.sub(r"[^a-z0-9]+", "-", base).strip("-")
    return base or "projet"


def _app_log(msg):
    import datetime
    with open(os.path.join(RACINE, "app.log"), "a", encoding="utf-8") as f:
        f.write(datetime.datetime.now().strftime("%H:%M:%S") + " " + msg + "\n")


def _nettoyer_cas(contenu):
    """Extrait le CSV du contenu LLM (préambule, bloc code) et normalise."""
    TECH = {
        "partitions d'équivalence": "partitions d'équivalence",
        "partitions d'equivalence": "partitions d'équivalence",
        "valeurs limites": "valeurs limites",
        "table de décision": "table de décision",
        "table de decision": "table de décision",
        "transitions d'état": "transitions d'état",
        "transitions d'etat": "transitions d'état",
        "transition d'état": "transitions d'état",
    }
    lignes = contenu.splitlines()
    start = None
    for i, l in enumerate(lignes):
        if l.strip().startswith("ID;Titre;Objectif;Exigence;Technique"):
            start = i
            break
    if start is None:
        return contenu
    lignes = lignes[start:]
    out = []
    for l in lignes:
        s = l.strip()
        if not s or s.startswith("```"):
            continue
        parts = s.split(";")
        if len(parts) != 12:
            continue
        parts[4] = TECH.get(parts[4].strip().lower(), parts[4].strip())
        st = parts[11].strip().lower()
        if st in ("prêt", "pret", "ok", "conforme", "valide"):
            parts[11] = "OK"
        elif st in ("à_clarifier", "à clarifier", "a_clarifier", "a clarifier"):
            parts[11] = "À_CLARIFIER"
        out.append(";".join(parts))
    return "\n".join(out) if out else contenu

st.set_page_config(page_title="QA-T-AG", layout="wide", page_icon="🛡️")

# ---------- état de session ----------
for k in ("workdir", "sfd_text", "sfd_nom", "revue", "revue_mode",
          "revue_ctrl", "revue_code", "cas_path", "cas_mode", "cas_ctrl",
          "cas_code", "matrice", "pv1", "pv2", "cahier_path"):
    if k not in st.session_state:
        st.session_state[k] = None
st.session_state.setdefault("pv1", False)
st.session_state.setdefault("pv2", False)

# ---------- sidebar ----------
st.sidebar.header("⚙️ Configuration")
cle = st.sidebar.text_input("Clé API DeepSeek", type="password",
                            help="Stockée en mémoire uniquement, jamais écrite.")
os.environ["DEEPSEEK_API_KEY"] = (cle.strip() if cle
                                  else os.environ.get("DEEPSEEK_API_KEY", ""))
gabarit = st.sidebar.text_input("Gabarit Word (.docx)", value=GABARIT_DEF)
if agent_ia.cle_disponible():
    st.sidebar.success("✅ Mode IA (DeepSeek) actif")
else:
    st.sidebar.warning("⚠️ Mode démo — sans clé, seule la SFD fictive est analysée")
if st.sidebar.button("🔌 Tester la clé DeepSeek"):
    ok, msg = agent_ia.tester_cle()
    if ok:
        st.sidebar.success(msg)
    else:
        st.sidebar.error(msg)
st.sidebar.caption("Sans clé → le bouton d'analyse bascule en mode démo.")


def run(script, *args):
    return subprocess.run(
        [sys.executable, os.path.join(SCRIPTS, script)] + list(args),
        capture_output=True, text=True)


def workdir():
    if not st.session_state.workdir:
        st.session_state.workdir = tempfile.mkdtemp(prefix="qatag_")
    return st.session_state.workdir


st.title("🛡️ QA-T-AG — Agent QA/BA autonome")
st.caption("Le script calcule · l'agent analyse · l'humain arbitre")

# ---------- ① SFD ----------
st.header("① SFD")
c1, c2 = st.columns([3, 1])
with c1:
    up = st.file_uploader("Déposer la SFD (.docx ou .md)", type=["docx", "md"])
with c2:
    st.write("")
    if st.button("🧪 Démo (SFD fictive)", width="stretch"):
        st.session_state.sfd_text = open(os.path.join(DEMO, "SFD-demo.md"),
                                          encoding="utf-8").read()
        st.session_state.sfd_nom = "SFD-demo (fictive)"
        for k in ("revue", "cas_path", "cahier_path", "matrice"):
            st.session_state[k] = None
        st.session_state.pv1 = st.session_state.pv2 = False
        st.rerun()

if up is not None:
    digest = (up.name, up.size)
    if st.session_state.get("upload_digest") != digest:
        wd = workdir()
        p = os.path.join(wd, up.name)
        with open(p, "wb") as f:
            f.write(up.getbuffer())
        st.session_state.sfd_text = agent_ia.extraire_sfd_texte(p)
        st.session_state.sfd_nom = up.name
        st.session_state.upload_digest = digest
        for k in ("revue", "cas_path", "cahier_path", "matrice"):
            st.session_state[k] = None
        st.session_state.pv1 = st.session_state.pv2 = False

if st.session_state.sfd_text:
    st.success("SFD chargée : %s — %d caractères"
               % (st.session_state.sfd_nom, len(st.session_state.sfd_text)))
    with st.expander("Aperçu de la SFD"):
        st.text(st.session_state.sfd_text[:1500])

# ---------- ② Revue (PV-1) ----------
st.header("② Revue SFD (AG-01) — Human Gate PV-1")
if st.session_state.sfd_text and not st.session_state.revue:
    if st.button("🔍 Lancer la revue"):
        wd = workdir()
        sfd_path = os.path.join(wd, "sfd.md")
        with open(sfd_path, "w", encoding="utf-8") as f:
            f.write(st.session_state.sfd_text)
        try:
            with st.spinner("🔍 Analyse IA de la revue en cours…"):
                revue = agent_ia.generer_revue(st.session_state.sfd_text)
            mode = "IA (DeepSeek)"
        except RuntimeError:
            if st.session_state.sfd_nom.startswith("SFD-demo"):
                revue = open(os.path.join(DEMO, "revue-demo.md"),
                             encoding="utf-8").read()
                mode = "démo"
            else:
                st.error("Aucune clé DeepSeek détectée. Pour analyser **votre** SFD, "
                         "collez votre clé dans la barre latérale (⚙️ Configuration), "
                         "puis relancez — ou cliquez « Démo » pour un exemple.")
                st.stop()
        except Exception as e:
            st.warning("Analyse IA en échec (%s)." % e)
            st.stop()
        if "## Statut du livrable" not in revue:
            revue = revue.rstrip() + "\n\n## Statut du livrable\nA_CLARIFIER\n"
        revue_path = os.path.join(wd, "revue.md")
        with open(revue_path, "w", encoding="utf-8") as f:
            f.write(revue)
        r = run("controler_revue.py", sfd_path, revue_path)
        _app_log("controler exit=%d | revue=%d chars | ctrl_out=%d chars"
                 % (r.returncode, len(revue), len(r.stdout) + len(r.stderr)))
        st.session_state.revue = revue
        st.session_state.revue_mode = mode
        st.session_state.revue_ctrl = r.stdout + r.stderr
        st.session_state.revue_code = r.returncode
        _app_log("avant st.rerun, revue en session=%d chars"
                 % len(st.session_state.revue))
        st.rerun()

if st.session_state.revue:
    _app_log("AFFICHAGE revue : len=%d | mode=%s | code=%d"
             % (len(st.session_state.revue), st.session_state.revue_mode,
                st.session_state.revue_code))
    st.info("Analyse : %s" % st.session_state.revue_mode)
    st.caption("Contrôle déterministe (`controler_revue.py`) :")
    st.code(st.session_state.revue_ctrl)
    if st.session_state.revue_code == 2:
        st.warning("La revue est mal formée (section manquante). Relancez la génération.")
        if st.button("🔁 Régénérer la revue"):
            st.session_state.revue = None
            st.session_state.pv1 = False
            st.rerun()
    elif st.session_state.revue_code == 1:
        st.warning("La revue est complète, mais certaines citations sont reformulées "
                   "(pas mot pour mot). Vérifiez-les avant de valider PV-1.")
    with st.expander("Voir la revue complète"):
        st.markdown(st.session_state.revue)
    col_v, col_r = st.columns(2)
    with col_v:
        if st.button("✅ Valider la revue (PV-1)", width="stretch"):
            st.session_state.pv1 = True
            st.rerun()
    with col_r:
        if st.button("❌ Rejeter", width="stretch"):
            st.session_state.revue = None
            st.session_state.pv1 = False
            st.rerun()
    if st.session_state.pv1:
        st.success("PV-1 validé ✔ — la revue est acceptée.")

# ---------- ③ Cas de test (PV-2) ----------
st.header("③ Cas de test (AG-02/03) — Human Gate PV-2")
if st.session_state.pv1 and not st.session_state.cas_path:
    if st.button("📝 Concevoir les cas de test"):
        wd = workdir()
        try:
            with st.spinner("📝 Conception des cas en cours…"):
                contenu = agent_ia.generer_cas(st.session_state.sfd_text)
            mode = "IA (DeepSeek)"
        except RuntimeError:
            if st.session_state.sfd_nom.startswith("SFD-demo"):
                contenu = open(os.path.join(DEMO, "cas-demo.csv"),
                               encoding="utf-8").read()
                mode = "démo"
            else:
                st.error("Aucune clé DeepSeek détectée pour concevoir les cas. "
                         "Collez votre clé dans la barre latérale (⚙️ Configuration).")
                st.stop()
        except Exception as e:
            st.warning("Analyse IA en échec (%s)." % e)
            st.stop()
        contenu = _nettoyer_cas(contenu)
        cas_path = os.path.join(wd, "cas-%s.csv" % _projet(st.session_state.sfd_nom))
        with open(cas_path, "w", encoding="utf-8") as f:
            f.write(contenu)
        sfd_path = os.path.join(wd, "sfd.md")
        r = run("controler_cas.py", sfd_path, cas_path)
        t = run("tracer.py", sfd_path, cas_path)
        st.session_state.cas_path = cas_path
        st.session_state.cas_mode = mode
        st.session_state.cas_ctrl = r.stdout + r.stderr + "\n" + t.stdout + t.stderr
        st.session_state.cas_code = r.returncode
        st.rerun()

if st.session_state.cas_path:
    st.info("Analyse : %s" % st.session_state.cas_mode)
    st.caption("Contrôles (`controler_cas.py` + `tracer.py`) :")
    st.code(st.session_state.cas_ctrl)
    try:
        with open(st.session_state.cas_path, encoding="utf-8-sig") as f:
            rows = list(csv.reader(f, delimiter=";"))
        if rows:
            import pandas as pd
            df = pd.DataFrame(rows[1:], columns=rows[0])
            st.dataframe(df[["ID", "Titre", "Exigence", "Technique",
                             "Priorité", "Type", "Statut livrable"]],
                         width="stretch")
    except Exception:
        pass
    col_v, col_r = st.columns(2)
    with col_v:
        if st.button("✅ Valider les cas (PV-2)", width="stretch"):
            st.session_state.pv2 = True
            st.rerun()
    with col_r:
        if st.button("❌ Rejeter", width="stretch", key="rej_cas"):
            st.session_state.cas_path = None
            st.session_state.pv2 = False
            st.rerun()
    if st.session_state.pv2:
        st.success("PV-2 validé ✔ — les cas sont validés.")

# ---------- ④ Cahier ----------
st.header("④ Cahier de recette (AG-06)")
if st.session_state.pv2:
    if st.button("📘 Générer le cahier Word"):
        wd = workdir()
        out = os.path.join(wd, "cahier.docx")
        r = run("cahier_word.py", gabarit, st.session_state.cas_path, out)
        if r.returncode == 0:
            st.session_state.cahier_path = out
        else:
            st.error(r.stdout + r.stderr)
        st.rerun()

if st.session_state.cahier_path and os.path.isfile(st.session_state.cahier_path):
    st.success("Cahier généré ✔")
    with open(st.session_state.cahier_path, "rb") as f:
        st.download_button("⬇️ Télécharger le cahier Word",
                           f.read(), file_name="cahier-cas.docx",
                           mime="application/vnd.openxmlformats-officedocument."
                                "wordprocessingml.document",
                           width="stretch")

if not st.session_state.sfd_text:
    st.info("Commencez par charger une SFD (ou cliquez « Démo »).")
