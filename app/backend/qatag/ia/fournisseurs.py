"""Connecteur IA multi-fournisseurs (RA-36, RA-37).

Points d'accès vérifiés dans la documentation des éditeurs (oct. 2026) :
- DeepSeek : https://api.deepseek.com/chat/completions (compatible OpenAI)
- OpenAI   : https://api.openai.com/v1/chat/completions
- Mistral  : https://api.mistral.ai/v1/chat/completions (compatible OpenAI)
- Ollama   : <OLLAMA_BASE_URL>/chat/completions, sans clé (local)
- Anthropic: https://api.anthropic.com/v1/messages (Messages API)

Les clés viennent uniquement du fichier .env ; elles ne sont jamais
renvoyées par l'API ni écrites dans les journaux.
"""
from dataclasses import dataclass

import httpx

from ..config import parametres

DELAI_SECONDES = 300

# Permet aux tests d'injecter un faux transport HTTP (aucun appel réseau réel)
transport_http: httpx.BaseTransport | None = None


@dataclass(frozen=True)
class Fournisseur:
    code: str
    libelle: str
    protocole: str          # "openai" ou "anthropic"
    attribut_cle: str | None  # nom du paramètre .env portant la clé
    modele_par_defaut: str

    def url(self) -> str:
        if self.code == "ollama":
            return parametres().ollama_base_url.rstrip("/") + "/chat/completions"
        return URLS[self.code]

    def cle(self) -> str:
        if not self.attribut_cle:
            return ""
        return getattr(parametres(), self.attribut_cle, "").strip()

    def disponible(self) -> bool:
        return self.attribut_cle is None or bool(self.cle())


URLS = {
    "deepseek": "https://api.deepseek.com/chat/completions",
    "openai": "https://api.openai.com/v1/chat/completions",
    "mistral": "https://api.mistral.ai/v1/chat/completions",
    "anthropic": "https://api.anthropic.com/v1/messages",
}

# Les modèles par défaut ne sont qu'une suggestion : l'Administrateur saisit
# le modèle exact dans la configuration, selon son abonnement.
FOURNISSEURS = {f.code: f for f in (
    Fournisseur("deepseek", "DeepSeek", "openai", "deepseek_api_key", "deepseek-flash"),
    Fournisseur("openai", "OpenAI", "openai", "openai_api_key", "gpt-4o-mini"),
    Fournisseur("mistral", "Mistral", "openai", "mistral_api_key", "mistral-large-latest"),
    Fournisseur("ollama", "Ollama (local)", "openai", None, "llama3.1"),
    Fournisseur("anthropic", "Anthropic (Claude)", "anthropic", "anthropic_api_key",
                "claude-sonnet-5-5"),
)}


class ErreurIA(Exception):
    pass


def _client() -> httpx.Client:
    return httpx.Client(timeout=DELAI_SECONDES, transport=transport_http)


def generer(code_fournisseur: str, modele: str, systeme: str, utilisateur: str,
            max_tokens: int = 8192) -> str:
    f = FOURNISSEURS.get(code_fournisseur)
    if f is None:
        raise ErreurIA("Fournisseur inconnu : %s" % code_fournisseur)
    if not f.disponible():
        raise ErreurIA("Clé d'API absente pour %s (fichier .env)" % f.libelle)
    try:
        with _client() as c:
            if f.protocole == "anthropic":
                r = c.post(f.url(), headers={
                    "x-api-key": f.cle(), "anthropic-version": "2023-06-01",
                    "content-type": "application/json"},
                    json={"model": modele, "max_tokens": max_tokens, "system": systeme,
                          "messages": [{"role": "user", "content": utilisateur}]})
            else:
                entetes = {"Authorization": "Bearer " + (f.cle() or "ollama")}
                r = c.post(f.url(), headers=entetes, json={
                    "model": modele, "max_tokens": max_tokens,
                    "messages": [{"role": "system", "content": systeme},
                                 {"role": "user", "content": utilisateur}]})
    except httpx.HTTPError as e:
        raise ErreurIA("%s injoignable : %s" % (f.libelle, type(e).__name__)) from e
    if r.status_code != 200:
        # le corps d'erreur des éditeurs ne contient pas la clé ; on le tronque
        raise ErreurIA("%s a répondu HTTP %s : %s" % (f.libelle, r.status_code, r.text[:300]))
    donnees = r.json()
    try:
        if f.protocole == "anthropic":
            return "".join(b.get("text", "") for b in donnees["content"]
                           if b.get("type") == "text")
        return donnees["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise ErreurIA("Réponse inattendue de %s" % f.libelle) from e
