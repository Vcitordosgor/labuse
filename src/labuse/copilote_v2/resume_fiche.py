"""COPILOTE-2 lot 1 — LE CHEMIN FICHE : un résumé DÉTERMINISTE d'une parcelle (ou d'une commune),
lu des MÊMES déclarations et ids que la fiche écran et le Dossier. Le Copilote ne calcule ni ne
choisit aucun chiffre : il lit `_q_v2_fiche` (la fiche premium servie à l'écran), passe les valeurs
au robinet (`exports.robinet_fiche.collecte` — id du registre → valeur), et réutilise les verdicts
de section du Dossier (`exports.verdicts` + `exports.miroir._verdict_factuel`). Le modèle, s'il est
appelé, ne fait que TOURNER la phrase ; en mode dégradé (clé absente), le résumé se construit
INTÉGRALEMENT sans lui — la preuve du mandat.

Deux entrées :
- `resume_parcelle(db, idu)` : les six chiffres du bandeau + le verdict-phrase de chacune des 11
  sections. `phrase(resume)` en fait le texte déterministe.
- `champ_precis(db, idu, message)` : une question sur UN champ (propriétaire, taxe, zone, risques,
  pente…) répond avec la LIGNE DÉCLARÉE et son id — plus de champ jeté par l'outil (COPILOTE-AUDIT-1).
"""
from __future__ import annotations

import html
import re
from typing import Any

from sqlalchemy.orm import Session

from .. import runs
from .outils import _fold_py

# Les SIX chiffres du bandeau (declarations/fiche/entete_tuiles.yaml — l'ordre de la maquette v4).
# (id du registre, libellé, fmt) — fmt appliqué à la valeur BRUTE, jamais recalculée.
_TUILES = [
    ("surface_parcelle_m2", "Surface", "m2"),
    ("zone_plu_famille", "Zone", "classe"),
    ("pente_deg", "Pente", "degre"),
    ("exposition_versant", "Exposition", "classe"),
    ("tfpb_taux_pct", "Taxe foncière", "pct"),
    ("sdp_residuelle_m2", "SDP restante", "m2"),
]

_TAG = re.compile(r"<[^>]+>")


def _plain(html_txt: str) -> str:
    """Le texte d'un verdict du Dossier est du HTML (<strong>…) : on le rend en clair pour le chat."""
    return html.unescape(_TAG.sub("", html_txt or "")).strip()


def _scalaire(valeur: Any) -> Any:
    """Un extracteur peut rendre un dict {taux, valeur, median…} : on en tire le scalaire à afficher.
    None si rien de numérique (la tuile est alors omise, jamais un crash ni un JSON brut à l'écran)."""
    if isinstance(valeur, dict):
        for k in ("taux", "taux_communal_pct", "valeur", "median", "pct", "m2", "moy"):
            if isinstance(valeur.get(k), (int, float)):
                return valeur[k]
        return None
    return valeur if isinstance(valeur, (int, float, str)) else None


def _fmt(valeur: Any, kind: str) -> str | None:
    v = _scalaire(valeur)
    if v is None:
        return None
    from ..exports.registre_fmt import fmt_m2, fmt_pct
    try:
        if kind == "m2":
            return fmt_m2(v)
        if kind == "pct":
            return fmt_pct(v)
        if kind == "degre":
            return f"{str(v).replace('.', ',')}°"
        return str(v)
    except (TypeError, ValueError):
        return None


def _fiche(db: Session, idu: str) -> dict | None:
    from fastapi import HTTPException

    from ..api.app import _q_v2_fiche
    try:
        f = _q_v2_fiche(db, idu, run_label=runs.current())
    except HTTPException:
        return None                     # parcelle absente du run servi → pas de résumé (jamais un 500)
    return f if f and f.get("commune") is not None else None


def _valeurs(db: Session, idu: str, fiche: dict) -> dict:
    """{id → Valeur} pour TOUS les ids câblés au robinet : le résumé lit exactement ce que le Dossier lit."""
    from ..exports import robinet_fiche
    return robinet_fiche.collecte(db, idu, list(robinet_fiche.EXTRACTEURS.keys()), fiche=fiche)


def _verdict_section(sec_id: str, valeurs: dict) -> tuple[str, str] | None:
    """Le verdict-phrase d'une section, en CLAIR — les MÊMES moteurs que le Dossier (parité garantie).
    Rend (texte, ton) ou None (pas de verdict pour cette section : pas de ligne vide)."""
    from ..exports.verdicts import verdict_potentiel, verdict_reseaux, verdict_zonage
    if sec_id == "urbanisme":
        v = verdict_zonage(valeurs)
        return (_plain(v[0]), v[1]) if v else None
    if sec_id == "potentiel":
        v = verdict_potentiel(valeurs)
        return (_plain(v[0]), v[1]) if v else None
    if sec_id == "reseaux":
        v = verdict_reseaux(valeurs)
        return (_plain(v[0]), v[1]) if v else None
    if sec_id == "risques":
        av = valeurs.get("aleas_parcelle_liste")
        liste = (av.valeur if av else None) or []
        rouges = [a for a in liste if isinstance(a, dict) and a.get("redhibitoire")]
        if rouges:
            return (_plain(rouges[0].get("libelle") or "Aléa rédhibitoire relevé."), "warn")
        if av is not None:
            return ("Aléas relevés — aucun rédhibitoire.", "neutral")
        return None
    from ..exports.miroir import _verdict_factuel
    fx = _verdict_factuel(sec_id, valeurs)
    return (_plain(fx[0]), fx[1]) if fx else None


def resume_parcelle(db: Session, idu: str) -> dict | None:
    """Le résumé déterministe d'une parcelle : bandeau (6 chiffres) + verdict des 11 sections.
    Aucun modèle. None si la parcelle est absente du run servi."""
    fiche = _fiche(db, idu)
    if fiche is None:
        return None
    valeurs = _valeurs(db, idu, fiche)
    tuiles = []
    for cid, lib, kind in _TUILES:
        v = valeurs.get(cid)
        rendu = _fmt(v.valeur, kind) if v is not None else None
        if rendu is not None:
            tuiles.append({"id": cid, "libelle": lib, "valeur": rendu})
    from ..registre.declarations import sections_fiche
    sections = []
    for s in sections_fiche():
        sid = s["id"]
        if sid == "entete":
            continue
        vd = _verdict_section(sid, valeurs)
        if vd is not None:
            sections.append({"id": sid, "titre": s["titre"], "verdict": vd[0], "ton": vd[1]})
    return {"idu": idu, "commune": fiche.get("commune"), "tuiles": tuiles, "sections": sections,
            "source": "fiche LABUSE (run servi)", "millesime": runs.current()}


def phrase(resume: dict) -> str:
    """Le texte du résumé, déterministe — servi tel quel en mode dégradé, ou passé au modèle à
    reformuler (le modèle ne choisit ni ne calcule aucun chiffre : ils sont ici)."""
    idu = resume["idu"]
    tete = f"Parcelle {idu} à {resume['commune']}"
    bandeau = " · ".join(f"{t['libelle']} {t['valeur']}" for t in resume["tuiles"])
    lignes = [f"{tete} — {bandeau}." if bandeau else f"{tete}."]
    for sec in resume["sections"]:
        marque = "⚠ " if sec["ton"] == "warn" else ""
        lignes.append(f"• {sec['titre']} : {marque}{sec['verdict']}")
    return "\n".join(lignes)


# ───────────────────────── commune ─────────────────────────
def resume_commune(db: Session, commune: str) -> dict | None:
    """Résumé déterministe d'une commune : le bandeau (chiffres servis à la fiche commune) + une
    ligne factuelle par carte. Mêmes valeurs que `commune_contexte` (la fiche commune écran) —
    aucun calcul, aucune invention. None si la commune est inconnue au contexte."""
    from .outils import resoudre_commune
    resolue = resoudre_commune(commune)
    if resolue is None:
        return None
    from ..api.app import commune_contexte
    c = commune_contexte(resolue, db=db)
    if not c or not (c.get("population") or c.get("foncier")):
        return None

    def g(bloc, cle):
        b = c.get(bloc) or {}
        return b.get(cle) if isinstance(b, dict) else None

    tuiles = []
    for lib, val in (
        ("Habitants", g("population", "habitants")),
        ("Logements", g("population", "logements")),
        ("Parcelles", g("foncier", "n_parcelles")),
        ("Prix ancien", g("comparable", "ancien_median_eur_m2")),
        ("Permis / an", g("permis_bloc", "permis_12m")),
    ):
        if isinstance(val, (int, float)):
            rendu = (f"{val:,}".replace(",", " ") + (" €/m²" if lib == "Prix ancien" else ""))
            tuiles.append({"libelle": lib, "valeur": rendu})
    plu = (c.get("plu_statut") or {}).get("libelle")
    if plu:
        tuiles.append({"libelle": "PLU", "valeur": str(plu)})

    cartes = []

    def carte(titre, txt):
        if txt:
            cartes.append({"titre": titre, "verdict": txt})

    sru = c.get("sru") or {}
    if sru.get("taux_lls") is not None:
        carte("Logement social (SRU)", f"Taux LLS {str(sru['taux_lls']).replace('.', ',')} % — {sru.get('statut') or 'statut non précisé'}.")
    risq = c.get("risques") or {}
    if risq.get("ppr_pct") is not None:
        carte("Risques", f"PPR sur {str(risq['ppr_pct']).replace('.', ',')} % des parcelles de la commune.")  # CHASSE-FIX-1 (C14)
    fisc = c.get("fiscalite") or {}
    # RETOUCHES-1 point 2 — la MÊME ligne que la fiche et le Dossier (producteur unique
    # fiscalite_libelle, déjà calculée dans le bloc fiscalité servi).
    _lignes_tf = fisc.get("lignes") or []
    if _lignes_tf:
        carte("Fiscalité", _lignes_tf[0]["ligne"] + ".")
    comp = c.get("comparable") or {}
    if comp.get("delai_median_mois") is not None:
        carte("Instruction", f"Délai médian d'instruction {comp['delai_median_mois']} mois.")
    fonc = c.get("foncier") or {}
    if fonc.get("classement"):
        carte("Foncier", f"Classement du foncier : {fonc['classement']}.")
    zabc = (c.get("zonage_abc") or {}).get("zone")
    if zabc:
        carte("Zonage A/B/C", f"Commune en zone {zabc} (investissement locatif).")

    return {"commune": resolue, "tuiles": tuiles, "cartes": cartes,
            "source": "fiche commune LABUSE", "millesime": runs.current()}


def phrase_commune(resume: dict) -> str:
    tete = f"Commune de {resume['commune']}"
    bandeau = " · ".join(f"{t['libelle']} {t['valeur']}" for t in resume["tuiles"])
    lignes = [f"{tete} — {bandeau}." if bandeau else f"{tete}."]
    for c in resume["cartes"]:
        lignes.append(f"• {c['titre']} : {c['verdict']}")
    return "\n".join(lignes)


# ───────────────────────── champ précis (ligne déclarée + id) ─────────────────────────
# mot-clé (folded) → (id du registre, libellé). La réponse cite la ligne et son id : plus de champ
# jeté par l'outil (le trou d'outillage constaté à COPILOTE-AUDIT-1 point 3).
_CHAMPS = [
    (("proprietaire", "proprio", "a qui appartient", "qui possede", "qui detient"),
     ("type_proprietaire", "Propriétaire")),
    (("taxe d'amenagement", "taxe damenagement", "taxe amenagement", "ta communale", "taux de ta"),
     ("taxe_amenagement_estimee_eur", "Taxe d'aménagement")),
    (("taxe fonciere", "tfpb", "taxe fonciere batie"), ("tfpb_taux_pct", "Taxe foncière (bâti)")),
    (("zone", "zonage", "plu"), ("zone_plu_famille", "Zone PLU")),
    (("risque", "risques", "alea", "aleas", "ppr", "inondation"), ("aleas_parcelle_liste", "Risques et aléas")),
    (("pente", "denivele"), ("pente_deg", "Pente")),
    (("exposition", "versant", "orientation"), ("exposition_versant", "Exposition")),
    (("surface", "superficie", "taille"), ("surface_parcelle_m2", "Surface")),
    (("sdp", "surface de plancher", "constructible restant", "capacite"),
     ("sdp_residuelle_m2", "SDP résiduelle")),
]


def _quel_champ(message: str) -> tuple[str, str] | None:
    m = _fold_py(message.lower())
    for kws, cible in _CHAMPS:
        if any(k in m for k in kws):
            return cible
    return None


def champ_precis(db: Session, idu: str, message: str) -> dict | None:
    """Une question sur UN champ de la fiche → la ligne DÉCLARÉE et son id (jamais un champ jeté).
    Rend {texte, champ_id, valeur, source} ou None si la demande ne vise pas un champ connu."""
    cible = _quel_champ(message)
    if cible is None:
        return None
    cid, libelle = cible
    fiche = _fiche(db, idu)
    if fiche is None:
        return None
    valeurs = _valeurs(db, idu, fiche)
    v = valeurs.get(cid)
    if v is None or v.valeur in (None, "", [], {}):
        return {"texte": f"{libelle} : non renseigné pour la parcelle {idu} (donnée absente au run servi).",
                "champ_id": cid, "valeur": None, "source": "fiche LABUSE"}
    texte = _rendre_champ(cid, libelle, v.valeur, valeurs)
    return {"texte": texte, "champ_id": cid, "valeur": v.valeur, "source": f"fiche LABUSE · {cid}"}


def _rendre_champ(cid: str, libelle: str, valeur: Any, valeurs: dict) -> str:
    """Rendu en clair d'un champ précis — lisible, jamais le JSON brut, et cite l'id du registre."""
    from ..exports.registre_fmt import fmt_m2, fmt_pct
    if cid == "type_proprietaire":
        return f"Propriétaire : {str(valeur).split(' (SIREN')[0]} ({cid})."
    if cid == "zone_plu_famille":
        from ..exports.verdicts import zone_libelle
        lib = zone_libelle(valeurs) or f"famille {valeur}"
        return f"Zone PLU : {lib} ({cid})."
    if cid == "aleas_parcelle_liste" and isinstance(valeur, list):
        red = [a for a in valeur if isinstance(a, dict) and a.get("redhibitoire")]
        if red:
            return f"Risques : {red[0].get('libelle')} — rédhibitoire ({cid})."
        libs = [a.get("libelle") for a in valeur if isinstance(a, dict) and a.get("libelle")]
        return f"Risques : {' ; '.join(libs[:3]) if libs else 'aucun aléa rédhibitoire relevé'} ({cid})."
    if cid == "taxe_amenagement_estimee_eur" and isinstance(valeur, dict):
        taux = valeur.get("taux_communal_pct")
        mill = valeur.get("taux_communal_millesime") or ""
        return (f"Taxe d'aménagement — taux communal {fmt_pct(taux)}" + (f" ({mill})" if mill else "")
                + f" ({cid}).")
    if cid in ("surface_parcelle_m2", "sdp_residuelle_m2"):
        return f"{libelle} : {fmt_m2(valeur)} ({cid})."
    if cid in ("tfpb_taux_pct",):
        # RETOUCHES-1 point 2 — la MÊME ligne canonique que la fiche et le Dossier (producteur unique).
        from ..fiscalite_libelle import lignes_taxe_fonciere
        _lignes = lignes_taxe_fonciere(valeur if isinstance(valeur, dict) else {})
        if _lignes:
            return f"{_lignes[0]['ligne']} ({cid})."
        return f"{libelle} : non renseigné ({cid})."
    if cid == "pente_deg":
        return f"Pente : {str(valeur).replace('.', ',')}° ({cid})."
    return f"{libelle} : {valeur} ({cid})."
