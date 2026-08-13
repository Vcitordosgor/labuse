"""M78 · Phase 3 — VÉRIFICATION (3a) + PROJET (3b).

3a VÉRIFICATION : IDU + prix demandé → instruction à charge et à décharge depuis les MÊMES points de
calcul (fiche + marché), confrontation au prix (prix probable vs demandé), avis final en UNE phrase
avec ses réserves et le MÊME verrou anti-invention que le héros (§2e). DVF sous le seuil M79 →
« échantillon insuffisant », jamais une médiane sur 1 vente.

3b PROJET : « j'ai un projet : résidence 12 lots à Bras-Panon » → fiche de cadrage (vocabulaire fermé
FICHE_SCHEMA) construite depuis le brief. La CRÉATION RÉELLE passe par l'API projets existante (au
niveau de l'endpoint, avec le compte) — JAMAIS d'écriture directe en base ici.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from .heros import _phrase_ok, _valeurs
from . import outils
from ..ai import core

# ───────────────────────── 3b — PROJET (préparation de la fiche) ─────────────────────────
def preparer_projet(params: dict, message: str) -> dict:
    """Construit la fiche de cadrage (FICHE_SCHEMA) depuis les paramètres extraits. L'écriture réelle
    est faite par l'endpoint (API projets). Retourne {fiche, nom, idu}."""
    fiche: dict = {"type_programme": "logements"}
    ampleur: dict = {}
    if params.get("programme_logements") is not None:
        ampleur["logements"] = int(params["programme_logements"])
    if ampleur:
        fiche["ampleur"] = ampleur
    if params.get("commune"):
        fiche["perimetre"] = {"mode": "communes", "communes": [params["commune"]]}
    if params.get("budget_eur") is not None:
        fiche["budget_foncier_eur"] = float(params["budget_eur"])
    return {"fiche": fiche, "nom": None, "idu": params.get("idu")}   # nom None → l'API le dérive


# ───────────────────────── 3a — VÉRIFICATION ─────────────────────────
AVIS_SYSTEM = """Tu es le copilote foncier de LABUSE. En UNE phrase française (30 mots max), donne un AVIS à
charge et à décharge sur l'achat de cette parcelle au prix demandé, à partir du JSON fourni UNIQUEMENT.
Dis l'essentiel (le prix demandé face au prix probable, la contrainte majeure), Y COMPRIS la réserve.
N'invente AUCUN chiffre : tout nombre vient du JSON. Pas de conseil juridique. Réponds la phrase seule."""


def _avis(db: Session | None, ctx: dict) -> str:
    autor = _valeurs({k: v for k, v in ctx.items() if isinstance(v, (int, float))}, None)
    for _ in range(2):
        r = core.complete(db, kind="copilote-avis", model=core.MODEL_REASONING, max_tokens=120,
                          system=AVIS_SYSTEM, context=ctx)
        if r.degraded:
            break
        p = (r.text or "").strip().strip('"').strip()
        if p and _phrase_ok(p, autor):
            return p
    # gabarit déterministe
    g = f"Parcelle {ctx.get('idu')} à {ctx.get('commune')}"
    if ctx.get("prix_demande_eur") and ctx.get("prix_probable_eur"):
        ecart = "au-dessus" if ctx["prix_demande_eur"] > ctx["prix_probable_eur"] else "sous"
        g += f" : demandé {ctx['prix_demande_eur']} €, prix probable {ctx['prix_probable_eur']} € ({ecart})."
    else:
        g += " : instruite (voir la fiche pour le détail sourcé)."
    return g


def verification(db: Session, params: dict) -> dict:
    """IDU + prix demandé → avis instruit. Une seule question si l'un manque (le Copilote demande)."""
    idu = params.get("idu")
    prix = params.get("prix_eur") or params.get("budget_eur")
    if not idu:
        return {"text": "Quelle parcelle dois-je vérifier ? Donnez-moi son IDU (14 caractères).",
                "intent": "VERIFICATION", "clarification": True}
    f = outils.fiche_parcelle(db, idu=idu)
    if not f.ok:
        return {"text": f"Parcelle {idu} introuvable.", "intent": "VERIFICATION", "refus": "donnee_absente"}
    if not prix:
        return {"text": f"À quel prix la parcelle {idu} vous est-elle proposée ?",
                "intent": "VERIFICATION", "clarification": True}
    d = f.data
    commune = d.get("commune")
    surface = d.get("surface_m2")
    # marché du secteur — MÊME point de calcul que la fiche (build_marche_commune, DVF terrain nu M79).
    # Prix terrain nu par ZONE (€/m²) × surface ; sous le seuil M79 (n ventes) → échantillon insuffisant.
    from ..faisabilite.marche_commune import build_marche_commune
    z = (d.get("zone") or "").upper()
    fam = "AU" if z.startswith("AU") else (z[:1] if z else "")
    terrain_m2 = n_ventes = None
    insuffisant = False
    if commune:
        for l in build_marche_commune(db, commune).get("lignes", []):
            if isinstance(l, dict) and l.get("cle") == "prix_terrain_nu_par_zone":
                pz = ((l.get("valeurs") or {}).get("par_zone") or {}).get(fam)
                if pz and pz.get("calculable"):
                    terrain_m2, n_ventes = pz.get("median_eur_m2"), pz.get("n")
                    insuffisant = n_ventes is not None and n_ventes < 5   # seuil M79
                break
    prix_probable = round(terrain_m2 * surface) if (terrain_m2 and surface and not insuffisant) else None
    ctx = {"idu": idu, "commune": commune, "surface_m2": surface, "zone": d.get("zone"),
           "verdict": d.get("verdict"), "prix_demande_eur": float(prix),
           "prix_probable_eur": prix_probable, "terrain_eur_m2": None if insuffisant else terrain_m2,
           "n_ventes": n_ventes,
           "reserve": (f"Échantillon insuffisant ({n_ventes} vente(s)) : pas de prix terrain fiable."
                       if insuffisant else None)}
    avis = _avis(db, ctx)
    sources = [f.source, "DVF terrains (marché commune)"]
    return {"text": avis, "intent": "VERIFICATION", "tool": "verification",
            "idu": idu, "sources": sources,
            # sorties : ouvrir la fiche, exporter le dossier, écrire au propriétaire (PM → sinon SPF)
            "actions": ["ouvrir_fiche", "exporter_dossier", "ecrire_proprietaire"]}
