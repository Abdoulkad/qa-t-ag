#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exécution des tests QA — SFD-TEST-001 v1.0 (MODULE-TEST-LOGIN)
Outil : Playwright 1.63.0 (venv dédié .venv), Chromium système (Chrome installé).
Sandbox : https://the-internet.herokuapp.com/login (démo publique) — SEULE URL autorisée.
Verdicts calculés par ce script (jamais estimés). Mot de passe lu depuis la
variable d'environnement TEST_PASSWORD — jamais écrit en clair dans les sorties.
Isolation : un contexte navigateur NEUF par test (pas de fuite de session).
"""
import os, json, time, statistics, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "https://the-internet.herokuapp.com"
LOGIN = BASE + "/login"
SECURE = BASE + "/secure"
LOGOUT = BASE + "/logout"

USER = "tomsmith"
PASSWORD = os.environ.get("TEST_PASSWORD", "")
if not PASSWORD:
    print("ERREUR : variable d'environnement TEST_PASSWORD non définie.")
    sys.exit(2)

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
AXE_PATH = Path("node_modules/axe-core/axe.min.js")

EXEC_ID = "exec-" + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
OUT_DIR = Path("mission-data/MODULE-TEST-LOGIN/executions") / EXEC_ID
OUT_DIR.mkdir(parents=True, exist_ok=True)

results = []

def record(test_id, exigence, attribut, classe, verdict, confiance, detail, preuve):
    results.append({
        "test_id": test_id, "exigence": exigence, "attribut": attribut,
        "classe": classe, "verdict": verdict, "confiance": confiance,
        "detail": detail, "preuve": preuve,
    })
    print(f"[{verdict:12s}] {test_id} — {detail}")

def flash_text(page):
    el = page.query_selector("#flash")
    if not el:
        return None
    return (el.inner_text() or "").strip()

def secure_heading(page):
    el = page.query_selector("h2")
    if not el:
        return False
    return "Secure Area" in (el.inner_text() or "")

def refused(page):
    return "/secure" not in page.url and not secure_heading(page)

def do_login(page):
    page.goto(LOGIN, wait_until="load", timeout=30000)
    page.fill("#username", USER)
    page.fill("#password", PASSWORD)
    page.click("button[type=submit]")
    page.wait_for_load_state("load")

# ---------------------------------------------------------------------------
# Fonctionnels (contexte neuf par test)
# ---------------------------------------------------------------------------
def tc_req001_01(browser):
    ctx = browser.new_context()
    page = ctx.new_page()
    do_login(page)
    f = flash_text(page)
    ok = ("/secure" in page.url) and ("logged into a secure area" in (f or "").lower()) and secure_heading(page)
    record("TC-REQ-001-01", "REQ-001", None, "fait",
           "PASS" if ok else "FAIL", "HAUTE",
           "connexion avec identifiants valides",
           {"url_finale": page.url, "flash": f, "zone_sec": secure_heading(page)})
    ctx.close()

def tc_req001_02(browser):
    ctx = browser.new_context()
    page = ctx.new_page()
    page.goto(SECURE, wait_until="load", timeout=30000)
    page.wait_for_load_state("load")
    f = flash_text(page)
    ok = refused(page)
    record("TC-REQ-001-02", "REQ-001", None, "fait",
           "PASS" if ok else "FAIL", "HAUTE",
           "accès direct /secure sans authentification -> refusé",
           {"url_finale": page.url, "flash": f, "zone_sec": secure_heading(page)})
    ctx.close()

def tc_req002_01(browser):
    ctx = browser.new_context()
    page = ctx.new_page()
    page.goto(LOGIN, wait_until="load", timeout=30000)
    page.fill("#username", "utilisateur_inconnu")
    page.fill("#password", "nimporte")
    page.click("button[type=submit]")
    page.wait_for_load_state("load")
    f = flash_text(page)
    ok = refused(page) and ("Your username is invalid!" in (f or ""))
    record("TC-REQ-002-01", "REQ-002", None, "fait",
           "PASS" if ok else "FAIL", "HAUTE",
           "nom d'utilisateur inconnu -> message + refus",
           {"url_finale": page.url, "flash": f})
    ctx.close()

def tc_req002_02(browser):
    ctx = browser.new_context()
    page = ctx.new_page()
    page.goto(LOGIN, wait_until="load", timeout=30000)
    page.fill("#username", "")
    page.fill("#password", PASSWORD)
    page.click("button[type=submit]")
    page.wait_for_load_state("load")
    f = flash_text(page)
    ok = refused(page)
    record("TC-REQ-002-02", "REQ-002", None, "fait",
           "PASS" if ok else "FAIL", "HAUTE",
           "username vide + mdp valide -> accès refusé (libellé message en hypothèse)",
           {"url_finale": page.url, "flash": f, "note": "libellé exact du message observé, non spécifié par la SFD"})
    ctx.close()

def tc_req003_01(browser):
    ctx = browser.new_context()
    page = ctx.new_page()
    page.goto(LOGIN, wait_until="load", timeout=30000)
    page.fill("#username", USER)
    page.fill("#password", "mot_de_passe_incorrect")
    page.click("button[type=submit]")
    page.wait_for_load_state("load")
    f = flash_text(page)
    ok = refused(page) and ("Your password is invalid!" in (f or ""))
    record("TC-REQ-003-01", "REQ-003", None, "fait",
           "PASS" if ok else "FAIL", "HAUTE",
           "mot de passe incorrect -> message + refus",
           {"url_finale": page.url, "flash": f})
    ctx.close()

def tc_req003_02(browser):
    ctx = browser.new_context()
    page = ctx.new_page()
    page.goto(LOGIN, wait_until="load", timeout=30000)
    page.fill("#username", USER)
    page.fill("#password", "")
    page.click("button[type=submit]")
    page.wait_for_load_state("load")
    f = flash_text(page)
    refused_ok = refused(page)
    error_shown = bool(f)
    ok = refused_ok and error_shown
    record("TC-REQ-003-02", "REQ-003", None, "fait",
           "PASS" if ok else "FAIL", "HAUTE",
           "mot de passe vide -> refus + message (défaut si accordé)",
           {"url_finale": page.url, "flash": f, "refuse": refused_ok})
    ctx.close()

def tc_req003_03(browser):
    ctx = browser.new_context()
    page = ctx.new_page()
    page.goto(LOGIN, wait_until="load", timeout=30000)
    page.fill("#username", USER)
    page.fill("#password", PASSWORD.lower())
    page.click("button[type=submit]")
    page.wait_for_load_state("load")
    f = flash_text(page)
    refused_ok = refused(page)
    error_shown = bool(f)
    ok = refused_ok and error_shown
    record("TC-REQ-003-03", "REQ-003", None, "fait",
           "PASS" if ok else "FAIL", "HAUTE",
           "casse différente du mot de passe -> refus + message (défaut si accordé)",
           {"url_finale": page.url, "flash": f, "refuse": refused_ok})
    ctx.close()

def tc_req004(browser):
    ctx = browser.new_context()
    page = ctx.new_page()
    do_login(page)
    page.click("a[href='/logout']")
    page.wait_for_load_state("load")
    f = flash_text(page)
    ok1 = ("/login" in page.url) and ("logged out" in (f or "").lower())
    record("TC-REQ-004-01", "REQ-004", None, "fait",
           "PASS" if ok1 else "FAIL", "HAUTE",
           "déconnexion -> retour /login + confirmation",
           {"url_finale": page.url, "flash": f})
    page.goto(SECURE, wait_until="load", timeout=30000)
    page.wait_for_load_state("load")
    f2 = flash_text(page)
    ok2 = refused(page)
    record("TC-REQ-004-02", "REQ-004", None, "fait",
           "PASS" if ok2 else "FAIL", "HAUTE",
           "accès zone sécurisée refusé après déconnexion (même contexte)",
           {"url_finale": page.url, "flash": f2, "zone_sec": secure_heading(page)})
    ctx.close()

def tc_req005_01(browser):
    ctx = browser.new_context()
    page = ctx.new_page()
    page.goto(LOGIN, wait_until="load", timeout=30000)
    page.fill("#username", "")
    page.fill("#password", "")
    page.click("button[type=submit]")
    page.wait_for_load_state("load")
    f = flash_text(page)
    ok = refused(page) and bool(f)
    record("TC-REQ-005-01", "REQ-005", None, "fait",
           "PASS" if ok else "FAIL", "HAUTE",
           "formulaire vide -> message d'erreur",
           {"url_finale": page.url, "flash": f})
    ctx.close()

# ---------------------------------------------------------------------------
# Non fonctionnels
# ---------------------------------------------------------------------------
def nft_sec01(browser):
    ctx = browser.new_context()
    page = ctx.new_page()
    page.goto(LOGIN, wait_until="load", timeout=30000)
    ptype = page.get_attribute("#password", "type")
    ok = (ptype == "password")
    record("NFT-SEC-01", "SEC", "securite", "fait",
           "PASS" if ok else "FAIL", "HAUTE",
           "champ mot de passe type=password",
           {"type_observe": ptype})
    ctx.close()

def nft_perf01(browser):
    samples = []
    for i in range(5):
        ctx = browser.new_context()
        page = ctx.new_page()
        t0 = time.perf_counter()
        page.goto(LOGIN, wait_until="load", timeout=30000)
        t1 = time.perf_counter()
        nav = page.evaluate("() => { const n = performance.getEntriesByType('navigation')[0]; return n ? (n.loadEventEnd - n.startTime) : null; }")
        wall = (t1 - t0) * 1000.0
        samples.append({"wall_ms": round(wall, 1), "load_event_ms": round(nav, 1) if nav else None})
        ctx.close()
    load_vals = [s["load_event_ms"] for s in samples if s["load_event_ms"] is not None]
    if len(load_vals) < 5:
        record("NFT-PERF-01", "PERF", "performance", "fait",
               "BLOCKED", "BASSE", "mesures load insuffisantes", samples)
        return
    med = statistics.median(load_vals)
    ok = med < 3000
    record("NFT-PERF-01", "PERF", "performance", "fait",
           "PASS" if ok else "FAIL", "BASSE",
           f"médiane load = {med:.1f} ms (seuil 3000 ms, 5 mesures)",
           {"samples": samples, "mediane_ms": round(med, 1), "note_confiance": "réseau non maîtrisé (Sandbox publique)"})

def nft_a11y01(browser):
    ctx = browser.new_context()
    page = ctx.new_page()
    page.goto(LOGIN, wait_until="load", timeout=30000)
    try:
        axe_src = AXE_PATH.read_text(encoding="utf-8")
        page.add_script_tag(content=axe_src)
        res = page.evaluate("async () => { return await axe.run(); }")
        violations = res.get("violations", [])
        crit = [v for v in violations if v.get("impact") == "critical"]
        ok = len(crit) == 0
        detail = f"{len(violations)} violation(s) au total, {len(crit)} critique(s)"
        preuve = {"total_violations": len(violations),
                  "critical": [{"id": v["id"], "impact": v["impact"], "nodes": len(v["nodes"])} for v in crit]}
        record("NFT-A11Y-01", "A11Y", "accessibilite", "fait",
               "PASS" if ok else "FAIL", "HAUTE", detail, preuve)
    except Exception as e:
        record("NFT-A11Y-01", "A11Y", "accessibilite", "fait",
               "BLOCKED", "BASSE", "axe-core non exécutable: " + repr(e), {})
    ctx.close()

def nft_sec03(browser):
    ctx = browser.new_context()
    page = ctx.new_page()
    page.goto(LOGIN, wait_until="load", timeout=30000)
    page.fill("#username", "utilisateur_inconnu")
    page.fill("#password", "nimporte")
    page.click("button[type=submit]")
    page.wait_for_load_state("load")
    m_username = flash_text(page)
    page.fill("#username", USER)
    page.fill("#password", "mot_de_passe_incorrect")
    page.click("button[type=submit]")
    page.wait_for_load_state("load")
    m_password = flash_text(page)
    differ = (m_username != m_password)
    record("NFT-SEC-03", "SEC", "securite", "hypothese_a_justifier",
           "INCONCLUSIVE", "HAUTE",
           "messages REQ-002 vs REQ-003 distinguent-ils compte inexistant / mdp erroné ?",
           {"message_username": m_username, "message_password": m_password,
            "messages_distincts": differ,
            "note": "tension SFD (messages explicites) vs OWASP A07 (générique recommandé) — PAS un défaut contre la SFD"})
    ctx.close()

# ---------------------------------------------------------------------------
def main():
    print(f"=== QA-T-AG — exécution {EXEC_ID} ===\n")
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(executable_path=CHROME, headless=True)
        except Exception as e:
            try:
                browser = p.chromium.launch(headless=True)
            except Exception as e2:
                record("CYCLE", None, None, "fait", "BLOCKED", "BASSE",
                       "impossible de lancer Chromium", {"chrome": repr(e), "bundled": repr(e2)})
                _write()
                return

        try:
            nft_sec01(browser)
            nft_perf01(browser)
            tc_req001_01(browser)
            tc_req001_02(browser)
            tc_req002_01(browser)
            tc_req002_02(browser)
            tc_req003_01(browser)
            tc_req003_02(browser)
            tc_req003_03(browser)
            tc_req004(browser)
            tc_req005_01(browser)
            nft_a11y01(browser)
            nft_sec03(browser)
        except Exception as e:
            record("CYCLE", None, None, "fait", "BLOCKED", "BASSE",
                   "erreur d'exécution: " + repr(e), {})
        finally:
            browser.close()

    _write()

def _write():
    out = {
        "cycle": "SFD-TEST-001-v1.0",
        "module_id": "MODULE-TEST-LOGIN",
        "execution_id": EXEC_ID,
        "sandbox": LOGIN,
        "outil": "Playwright 1.63.0 (venv .venv, Chromium système)",
        "date_execution": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mot_de_passe_masque": "***",
        "resultats": results,
    }
    p = OUT_DIR / "resultats.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nÉvidence écrite : {p}")
    raw = json.dumps(out, ensure_ascii=False)
    leak = PASSWORD in raw
    print(f"NFT-SEC-02 (auto-contrôle) : fuite du mot de passe dans l'évidence = {leak}")

if __name__ == "__main__":
    main()
