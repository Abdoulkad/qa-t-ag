#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""3e exécution de NFT-PERF-01 pour classification instable/flaky (skill §3)."""
import time, statistics
from playwright.sync_api import sync_playwright

BASE = "https://the-internet.herokuapp.com/login"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=CHROME, headless=True)
    samples = []
    for i in range(5):
        ctx = browser.new_context()
        page = ctx.new_page()
        t0 = time.perf_counter()
        page.goto(BASE, wait_until="load", timeout=30000)
        t1 = time.perf_counter()
        nav = page.evaluate("() => { const n = performance.getEntriesByType('navigation')[0]; return n ? (n.loadEventEnd - n.startTime) : null; }")
        samples.append({"wall_ms": round((t1-t0)*1000.0, 1), "load_event_ms": round(nav, 1) if nav else None})
        ctx.close()
    browser.close()

load_vals = [s["load_event_ms"] for s in samples if s["load_event_ms"] is not None]
med = statistics.median(load_vals)
print("samples:", samples)
print(f"médiane load = {med:.1f} ms ; verdict = {'PASS' if med < 3000 else 'FAIL'}")
