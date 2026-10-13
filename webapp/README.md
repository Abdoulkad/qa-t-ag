# QA-T-AG — Application web (MVP Streamlit)

Interface web du système QA-T-AG. Branche les scripts déterministes
(19 scripts, auto-testés) et l'analyse IA (DeepSeek) derrière des écrans
Streamlit, avec les Human Gates (PV-1, PV-2) comme boutons.

## Lancement

```bash
# 1. installer les dépendances
pip install -r requirements.txt

# 2. (optionnel) clé DeepSeek pour l'analyse IA réelle
set DEEPSEEK_API_KEY=sk-...          # Windows

# 3. lancer
streamlit run app.py
```

Sans clé, l'app fonctionne en **mode démo** (artefacts pré-générés).

## Structure

```
app.py               # interface Streamlit (upload → revue → cas → cahier)
agent_ia.py          # extraction SFD + appels LLM (DeepSeek)
skills/              # SKILL.md des 16 agents (les prompts)
scripts/             # 19 scripts déterministes (le calculateur)
modele-cahier-cas.docx  # gabarit Word DSI
demo/                # artefacts du mode démo (SFD fictive)
```

## Principe

Le script calcule (contrôles, matrice, cahier), l'agent analyse (LLM),
l'humain arbitre (PV-1, PV-2). Aucun PASS sans preuve, aucune donnée réelle.
