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
import json
import time
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


# Coupures réseau passagères : on retente. Une erreur d'authentification ou de
# requête (4xx hors 408/429) n'est jamais retentée, elle ne changerait pas.
ERREURS_TRANSITOIRES = (httpx.RemoteProtocolError, httpx.ConnectError, httpx.ConnectTimeout,
                        httpx.ReadError, httpx.ReadTimeout, httpx.WriteError, httpx.PoolTimeout)
CODES_TRANSITOIRES = {408, 429, 500, 502, 503, 504, 529}
PAUSES_SECONDES = (5, 20)     # avant la 2e puis la 3e tentative
attendre = time.sleep         # remplacé dans les tests

LIBELLES_ERREUR = {
    "RemoteProtocolError": "connexion coupée par le serveur avant la fin de la réponse",
    "ConnectError": "connexion impossible (réseau ou adresse)",
    "ConnectTimeout": "délai de connexion dépassé",
    "ReadTimeout": "aucune donnée reçue pendant %d s" % DELAI_SECONDES,
    "ReadError": "lecture de la réponse interrompue",
}


class _Transitoire(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


def _client() -> httpx.Client:
    return httpx.Client(timeout=DELAI_SECONDES, transport=transport_http)


def _requete(f: Fournisseur, modele: str, systeme: str, utilisateur: str,
             max_tokens: int) -> tuple[dict, dict]:
    if f.protocole == "anthropic":
        return ({"x-api-key": f.cle(), "anthropic-version": "2023-06-01",
                 "content-type": "application/json"},
                {"model": modele, "max_tokens": max_tokens, "system": systeme, "stream": True,
                 "messages": [{"role": "user", "content": utilisateur}]})
    return ({"Authorization": "Bearer " + (f.cle() or "ollama")},
            {"model": modele, "max_tokens": max_tokens, "stream": True,
             "messages": [{"role": "system", "content": systeme},
                          {"role": "user", "content": utilisateur}]})


def _lire_flux(f: Fournisseur, lignes) -> tuple[str, str | None]:
    """Lit une réponse en continu (SSE). Les lignes vides et les commentaires
    « : keep-alive » envoyés pendant l'attente sont ignorés."""
    morceaux, fin = [], None
    for ligne in lignes:
        ligne = ligne.strip()
        if not ligne.startswith("data:"):
            continue                       # vide, commentaire ou « event: »
        donnee = ligne[5:].strip()
        if donnee == "[DONE]":
            break
        try:
            obj = json.loads(donnee)
        except ValueError:
            continue
        if obj.get("error") or obj.get("type") == "error":
            erreur = obj.get("error") or {}
            raise ErreurIA("%s a signalé une erreur : %s" % (
                f.libelle, str(erreur.get("message", erreur))[:300]))
        if f.protocole == "anthropic":
            if obj.get("type") == "content_block_delta":
                morceaux.append((obj.get("delta") or {}).get("text", ""))
            elif obj.get("type") == "message_delta":
                fin = (obj.get("delta") or {}).get("stop_reason") or fin
        else:
            for choix in obj.get("choices") or []:
                morceaux.append(((choix.get("delta") or {}).get("content")) or "")
                fin = choix.get("finish_reason") or fin
    return "".join(morceaux), fin


def _lire_json(f: Fournisseur, donnees: dict) -> tuple[str, str | None]:
    """Repli : certains serveurs compatibles ignorent « stream » et renvoient du JSON."""
    try:
        if f.protocole == "anthropic":
            return ("".join(b.get("text", "") for b in donnees["content"]
                            if b.get("type") == "text"), donnees.get("stop_reason"))
        choix = donnees["choices"][0]
        return choix["message"]["content"], choix.get("finish_reason")
    except (KeyError, IndexError, TypeError) as e:
        raise ErreurIA("Réponse inattendue de %s" % f.libelle) from e


def _une_tentative(f: Fournisseur, entetes: dict, corps: dict) -> str:
    try:
        with _client() as c, c.stream("POST", f.url(), headers=entetes, json=corps) as r:
            if r.status_code != 200:
                r.read()
                message = "%s a répondu HTTP %s : %s" % (f.libelle, r.status_code, r.text[:300])
                if r.status_code in CODES_TRANSITOIRES:
                    raise _Transitoire(message)
                # le corps d'erreur des éditeurs ne contient pas la clé ; on le tronque
                raise ErreurIA(message)
            if "text/event-stream" in r.headers.get("content-type", ""):
                texte, fin = _lire_flux(f, r.iter_lines())
            else:
                r.read()
                try:
                    texte, fin = _lire_json(f, json.loads(r.text))
                except ValueError as e:
                    raise ErreurIA("Réponse illisible de %s" % f.libelle) from e
    except ERREURS_TRANSITOIRES as e:
        nom = type(e).__name__
        raise _Transitoire("%s injoignable : %s (%s)" % (
            f.libelle, LIBELLES_ERREUR.get(nom, nom), nom)) from e
    except httpx.HTTPError as e:
        raise ErreurIA("%s injoignable : %s" % (f.libelle, type(e).__name__)) from e
    if fin in ("length", "max_tokens"):
        raise ErreurIA("%s a tronqué sa réponse : limite de %d tokens atteinte"
                       % (f.libelle, corps["max_tokens"]))
    return texte


def generer(code_fournisseur: str, modele: str, systeme: str, utilisateur: str,
            max_tokens: int = 8192) -> str:
    f = FOURNISSEURS.get(code_fournisseur)
    if f is None:
        raise ErreurIA("Fournisseur inconnu : %s" % code_fournisseur)
    if not f.disponible():
        raise ErreurIA("Clé d'API absente pour %s (fichier .env)" % f.libelle)
    entetes, corps = _requete(f, modele, systeme, utilisateur, max_tokens)
    tentatives = len(PAUSES_SECONDES) + 1
    for n in range(tentatives):
        try:
            return _une_tentative(f, entetes, corps)
        except _Transitoire as e:
            if n == tentatives - 1:
                raise ErreurIA("%s — échec après %d tentatives" % (e.message, tentatives)) from e
            attendre(PAUSES_SECONDES[n])
    raise AssertionError("inatteignable")
