#!/usr/bin/env python3
"""QA-T-AG — application web (MVP Streamlit).

Écrans : Tableau de bord · Revue SFD (PV-1) · Cas de test (PV-2) · Cahier Word.
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


CAMPAGNES = os.path.join(RACINE, "campagnes")
HISTORIQUE = os.path.join(CAMPAGNES, "historique.csv")


def _parser_defauts(revue):
    defs = []
    for m in re.finditer(r"^###\s+(DEF-\d+)\s*[-—–]\s*(.+?)\s*[-—–]\s*(.+?)\s*$",
                         revue or "", re.MULTILINE):
        defs.append({"categorie": m.group(2).strip(),
                     "gravite": m.group(3).strip()})
    return defs


def _metrics():
    par_gravite, par_categorie, par_priorite, par_type = {}, {}, {}, {}
    defs = _parser_defauts(st.session_state.revue) if st.session_state.revue else []
    for d in defs:
        par_gravite[d["gravite"]] = par_gravite.get(d["gravite"], 0) + 1
        par_categorie[d["categorie"]] = par_categorie.get(d["categorie"], 0) + 1
    ct_rows = []
    if st.session_state.cas_path and os.path.isfile(st.session_state.cas_path):
        with open(st.session_state.cas_path, encoding="utf-8-sig") as f:
            rows = list(csv.reader(f, delimiter=";"))
        ct_rows = [r for r in rows[1:] if len(r) >= 7]
        for r in ct_rows:
            par_priorite[r[5]] = par_priorite.get(r[5], 0) + 1
            par_type[r[6]] = par_type.get(r[6], 0) + 1
    return {"nb_defauts": len(defs), "nb_ct": len(ct_rows),
            "par_gravite": par_gravite, "par_categorie": par_categorie,
            "par_priorite": par_priorite, "par_type": par_type}


def _charger_historique():
    if not os.path.isfile(HISTORIQUE):
        return []
    with open(HISTORIQUE, encoding="utf-8-sig") as f:
        return list(csv.reader(f, delimiter=";"))


def _sauvegarder_campagne():
    import datetime
    m = _metrics()
    os.makedirs(CAMPAGNES, exist_ok=True)
    nouveau = not os.path.isfile(HISTORIQUE) or os.path.getsize(HISTORIQUE) == 0
    with open(HISTORIQUE, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        if nouveau:
            w.writerow(["SFD", "Date", "Défauts", "Cas", "Statut"])
        w.writerow([st.session_state.sfd_nom or "—",
                    datetime.date.today().isoformat(),
                    m["nb_defauts"], m["nb_ct"], "A_CLARIFIER"])


def _metrics_dashboard():
    hist = _charger_historique()
    rows = hist[1:] if len(hist) > 1 else []

    def _somme(i):
        return sum(int(r[i]) for r in rows if len(r) > i and str(r[i]).strip().isdigit())

    sfds_hist = len(rows)
    defauts_hist = _somme(2)
    cas_hist = _somme(3)
    m = _metrics()
    courant = bool(st.session_state.sfd_text) and not st.session_state.get("campagne_sauvegardee")
    en_attente = m["nb_defauts"] if (st.session_state.revue and not st.session_state.pv1) else 0
    return {
        "sfd_analysees": sfds_hist + (1 if courant else 0),
        "defauts_detectes": defauts_hist + (m["nb_defauts"] if courant else 0),
        "cas_generes": cas_hist + (m["nb_ct"] if courant else 0),
        "en_attente": en_attente,
    }


PALETTE = ["#e74c3c", "#f39c12", "#27ae60"]  # rouge, orange, vert (3 couleurs max)


def _chart_barre(donnees, couleurs_fixes=None):
    import pandas as pd
    import altair as alt
    labels = list(donnees.keys())
    valeurs = list(donnees.values())
    if couleurs_fixes:
        couleurs = [couleurs_fixes.get(l, PALETTE[0]) for l in labels]
    else:
        couleurs = [PALETTE[i % len(PALETTE)] for i in range(len(labels))]
    df = pd.DataFrame({"label": labels, "valeur": valeurs, "couleur": couleurs})
    return alt.Chart(df).mark_bar().encode(
        x=alt.X("label:N", sort="-y", title=None),
        y=alt.Y("valeur:Q", title=None),
        color=alt.Color("couleur:N", scale=None, legend=None),
    ).properties(height=220)


st.set_page_config(page_title="QA-T-AG", layout="wide", page_icon="🛡️")

# ---------- style : barre latérale bleu marine ----------
st.markdown("""
<style>
section[data-testid="stSidebar"] {
    background-color: #0f1729;
}
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] .stCaption,
section[data-testid="stSidebar"] .stMarkdown {
    color: #e2e8f0 !important;
    font-size: 1.05rem !important;
}
section[data-testid="stSidebar"] [data-testid="stRadio"] label {
    font-size: 1.25rem !important;
}
section[data-testid="stSidebar"] hr {
    border-color: #334155;
}
</style>
""", unsafe_allow_html=True)

# ---------- état de session ----------
for k in ("workdir", "sfd_text", "sfd_nom", "revue", "revue_mode",
          "revue_ctrl", "revue_code", "cas_path", "cas_mode", "cas_ctrl",
          "cas_code", "matrice", "pv1", "pv2", "cahier_path"):
    if k not in st.session_state:
        st.session_state[k] = None
st.session_state.setdefault("pv1", False)
st.session_state.setdefault("pv2", False)

# ---------- sidebar : navigation + configuration ----------
with st.sidebar:
    st.markdown("## 🛡️ QA-T-AG")
    st.markdown("**Bonjour BAMK** 👋")
    page = st.radio("Navigation", [
        "📊 Tableau de bord",
        "📄 Revue SFD",
        "📝 Cas de test",
        "📘 Cahier de recette",
    ], label_visibility="collapsed")
    st.markdown("---")
    st.markdown("**⚙️ Configuration**")
    cle = st.text_input("Clé API DeepSeek", type="password",
                        help="Stockée en mémoire uniquement, jamais écrite.")
    os.environ["DEEPSEEK_API_KEY"] = (cle.strip() if cle
                                      else os.environ.get("DEEPSEEK_API_KEY", ""))
    gabarit = st.text_input("Gabarit Word (.docx)", value=GABARIT_DEF)
    if agent_ia.cle_disponible():
        st.success("✅ Mode IA (DeepSeek) actif")
    else:
        st.warning("⚠️ Mode démo — sans clé, seule la SFD fictive est analysée")
    if st.button("🔌 Tester la clé DeepSeek"):
        ok, msg = agent_ia.tester_cle()
        if ok:
            st.success(msg)
        else:
            st.error(msg)
    st.caption("Sans clé → le bouton d'analyse bascule en mode démo.")


def run(script, *args):
    return subprocess.run(
        [sys.executable, os.path.join(SCRIPTS, script)] + list(args),
        capture_output=True, text=True)


def workdir():
    if not st.session_state.workdir:
        st.session_state.workdir = tempfile.mkdtemp(prefix="qatag_")
    return st.session_state.workdir


def _charger_sfd(text, nom):
    st.session_state.sfd_text = text
    st.session_state.sfd_nom = nom
    for k in ("revue", "cas_path", "cahier_path", "matrice"):
        st.session_state[k] = None
    st.session_state.pv1 = st.session_state.pv2 = False
    st.session_state.pop("campagne_sauvegardee", None)


def _carte_metric(label, valeur, couleur):
    st.markdown(
        '<div style="border:2px solid %s;border-radius:12px;padding:16px;'
        'background:#ffffff;box-shadow:0 1px 4px rgba(15,23,41,0.08);'
        'min-height:100px;">'
        '<div style="font-size:0.78rem;color:#64748b;text-transform:uppercase;'
        'letter-spacing:0.4px;font-weight:600;">%s</div>'
        '<div style="font-size:2.1rem;font-weight:700;color:#0f1729;'
        'margin-top:4px;">%s</div>'
        '</div>' % (couleur, label, valeur),
        unsafe_allow_html=True)


st.title("🛡️ QA-T-AG — Agent QA/BA autonome")
st.caption("Le script calcule · l'agent analyse · l'humain arbitre")

# ======================================================================
# PAGE : Tableau de bord
# ======================================================================
if page == "📊 Tableau de bord":
    st.header("📊 Tableau de bord")
    md = _metrics_dashboard()
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        _carte_metric("SFD ANALYSEES", md["sfd_analysees"], "#3b82f6")
    with c2:
        _carte_metric("DEFAUTS DETECTES", md["defauts_detectes"], "#e74c3c")
    with c3:
        _carte_metric("CAS DE TEST GENERES", md["cas_generes"], "#27ae60")
    with c4:
        _carte_metric("EN ATTENTE DE VOTRE DECISION", md["en_attente"], "#f39c12")

    st.markdown("---")
    st.subheader("📁 Charger une SFD")
    col_up, col_ta = st.columns(2)
    with col_up:
        up_dash = st.file_uploader("Joindre une SFD (.docx ou .md)",
                                   type=["docx", "md"], key="up_dash")
    with col_ta:
        texte_colle = st.text_area("…ou coller le contenu de la SFD ici",
                                   height=120, key="ta_dash")
        if st.button("📥 Charger ce texte", width="stretch"):
            if texte_colle.strip():
                _charger_sfd(texte_colle.strip(), "SFD collée")
                st.rerun()
            else:
                st.warning("Zone vide — collez le texte de la SFD d'abord.")

    if up_dash is not None:
        digest = ("dash", up_dash.name, up_dash.size)
        if st.session_state.get("upload_digest_dash") != digest:
            wd = workdir()
            p = os.path.join(wd, up_dash.name)
            with open(p, "wb") as f:
                f.write(up_dash.getbuffer())
            _charger_sfd(agent_ia.extraire_sfd_texte(p), up_dash.name)
            st.session_state.upload_digest_dash = digest
            st.rerun()

    if st.session_state.sfd_text:
        st.success("SFD chargée : %s — passez à « 📄 Revue SFD » pour lancer la revue."
                   % st.session_state.sfd_nom)

    m = _metrics()
    if m["par_gravite"] or m["par_categorie"] or m["par_priorite"] or m["par_type"]:
        GRAV = {"Bloquante": "#e74c3c", "Majeure": "#f39c12", "Mineure": "#27ae60"}
        a, b = st.columns(2)
        if m["par_gravite"]:
            a.subheader("Défauts par gravité")
            a.altair_chart(_chart_barre(m["par_gravite"], GRAV), width="stretch")
        if m["par_categorie"]:
            b.subheader("Défauts par catégorie")
            b.altair_chart(_chart_barre(m["par_categorie"]), width="stretch")
        c, d = st.columns(2)
        if m["par_priorite"]:
            c.subheader("Cas par priorité")
            c.altair_chart(_chart_barre(m["par_priorite"]), width="stretch")
        if m["par_type"]:
            d.subheader("Cas par type")
            d.altair_chart(_chart_barre(m["par_type"]), width="stretch")
    hist = _charger_historique()
    if len(hist) > 1:
        st.subheader("Historique des campagnes")
        import pandas as pd
        dfh = pd.DataFrame(hist[1:], columns=hist[0])
        st.dataframe(dfh, width="stretch")
    if not st.session_state.sfd_text and len(hist) <= 1:
        st.info("Commencez par charger une SFD dans « 📄 Revue SFD ».")

# ======================================================================
# PAGE : Revue SFD (① SFD + ② Revue + PV-1)
# ======================================================================
elif page == "📄 Revue SFD":
    st.header("① Charger la SFD")
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
            st.session_state.pop("campagne_sauvegardee", None)
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
            st.session_state.pop("campagne_sauvegardee", None)

    if st.session_state.sfd_text:
        st.success("SFD chargée : %s — %d caractères"
                   % (st.session_state.sfd_nom, len(st.session_state.sfd_text)))
        with st.expander("Aperçu de la SFD"):
            st.text(st.session_state.sfd_text[:1500])

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
            st.rerun()

    if st.session_state.revue:
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
            st.success("PV-1 validé ✔ — la revue est acceptée. Passez à « 📝 Cas de test ».")
    elif not st.session_state.sfd_text:
        st.info("Chargez une SFD ci-dessus (ou cliquez « Démo ») pour lancer la revue.")

# ======================================================================
# PAGE : Cas de test (③ + PV-2)
# ======================================================================
elif page == "📝 Cas de test":
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
            st.success("PV-2 validé ✔ — les cas sont validés. Passez à « 📘 Cahier de recette ».")
    else:
        st.info("Validez la revue (PV-1) dans « 📄 Revue SFD » pour concevoir les cas.")

# ======================================================================
# PAGE : Cahier de recette (④)
# ======================================================================
elif page == "📘 Cahier de recette":
    st.header("④ Cahier de recette (AG-06)")
    if st.session_state.pv2:
        if st.button("📘 Générer le cahier Word"):
            wd = workdir()
            out = os.path.join(wd, "cahier.docx")
            r = run("cahier_word.py", gabarit, st.session_state.cas_path, out)
            if r.returncode == 0:
                st.session_state.cahier_path = out
                if not st.session_state.get("campagne_sauvegardee"):
                    _sauvegarder_campagne()
                    st.session_state.campagne_sauvegardee = True
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
    elif not st.session_state.pv2:
        st.info("Validez les cas (PV-2) dans « 📝 Cas de test » pour générer le cahier.")
