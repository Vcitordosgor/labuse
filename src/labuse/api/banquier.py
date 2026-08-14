"""O1 — DOSSIER BANQUIER : le PDF qu'un porteur pose sur le bureau de son financeur.

6-8 pages print, sobres, TOUT sourcé. Réutilise l'existant (aucune donnée nouvelle) :
 · identité + photo aérienne IGN (BD ORTHO, Géoplateforme) + plan de situation ;
 · les 11 steps de faisabilité (moteur déterministe `parcel_faisabilite`) ;
 · bilan promoteur & charge foncière (`compute_bilan`) + **Score É V2** (marge € O0) ;
 · comparables DVF (`sector_price`) + permis SITADEL voisins (`nearby_permits`) ;
 · risques / servitudes / zonage (`collect_report_data`) + ZAN si dispo (guardé) ;
 · **synthèse exécutive narrée par le socle IA (sonnet, strict_numbers)** — elle raconte les
   étapes, n'invente AUCUN chiffre ; repli déterministe honnête si pas de clé.

M22-0 : les sections HTML, le CSS print, la collecte et les helpers vivent dans
`briques_pdf.py` (partagés avec les exports M22). Ici ne restent que le spécifique
banquier : libellé légal, synthèse exécutive IA, assemblage, endpoints + cache async.

Doctrine : jamais un RR ni un score interne en vitrine ; chaque chiffre porte Sourcé/Estimé ;
« non estimable » quand une donnée manque, jamais un chiffre fabriqué ; particulier jamais nommé.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from .. import plans
from . import briques_pdf as bq
from .briques_pdf import esc as _esc, eur as _eur

log = logging.getLogger("labuse.banquier")
router = APIRouter(prefix="/dossier-banquier", tags=["dossier-banquier"])

LIBELLE = ("Dossier de présentation établi à partir de données publiques (cadastre, DVF, SITADEL, PLU) — "
           "estimations indicatives, ni un prix ni une promesse ; ne remplace pas une étude de faisabilité "
           "ni une expertise. À vérifier par le porteur et ses conseils.")


def _strip_md(t: str) -> str:
    """M73 C3 — retire le markdown d'une sortie LLM avant impression PDF (gras, titres, puces),
    et un titre « SYNTHÈSE EXÉCUTIVE » redondant en tête (le <h2> du bloc existe déjà)."""
    import re
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", t)          # **gras**
    t = re.sub(r"\*(.+?)\*", r"\1", t)              # *italique*
    t = re.sub(r"(?m)^#{1,6}\s*", "", t)            # # titres
    t = re.sub(r"(?m)^\s*[-*]\s+", "• ", t)         # - puces → •
    t = re.sub(r"(?i)^\s*synth[èe]se\s+ex[ée]cutive\s*:?\s*", "", t.strip())
    return t.strip()


def get_db():
    from .app import get_db as _g
    yield from _g()


# ───────────────────────── synthèse exécutive (socle IA, strict_numbers) ─────────────────────────

_SYSTEM_SYNTHESE = (
    "Tu es analyste foncier. Rédige une SYNTHÈSE EXÉCUTIVE de 4 à 6 phrases pour un dossier de "
    "présentation à un banquier, à partir des SEULS faits fournis (chacun avec sa provenance). "
    "Règles ABSOLUES : n'invente AUCUN chiffre ni fait absent du contexte ; ne cite pas de score "
    "interne ni de classement ; reste factuel et prudent ; qualifie les estimations d'« estimé ». "
    "Structure : le foncier et son potentiel, la charge foncière supportable, le marché de comparaison, "
    "les points de vigilance. Pas de listes, un paragraphe."
)


def _facts_synthese(out: dict, core_mod):
    F = core_mod.Fact
    facts: dict = {}
    p = out["parcelle"]
    facts["parcelle"] = F(f"parcelle {p['idu']} à {p['commune']}, {p['surface_m2']} m² de terrain", "SOURCE")
    fais = out.get("faisabilite")
    if fais is not None:
        fo = fais.fourchette or {}
        if fo.get("shab_vendable_m2"):
            facts["capacite"] = F(f"surface habitable vendable estimée ~{fo['shab_vendable_m2']} m² "
                                  f"(zone {fais.zone_resolue or fais.zone})", "ESTIME")
        if fo.get("logements_au_sol"):
            lo, hi = fo["logements_au_sol"]
            # M54-AB F10 : borner quand min = max (« ~2 à 2 » → « ~2 »).
            lg = f"~{lo}" if lo == hi else f"{lo} à {hi}"
            facts["logements"] = F(f"potentiel indicatif {lg} logements", "ESTIME")
    bilan = out.get("bilan")
    if bilan is not None and bilan.charge_fonciere:
        cf = bilan.charge_fonciere
        facts["charge_fonciere"] = F(
            f"charge foncière supportable estimée {_eur(cf.get('central'))} "
            f"(~{cf.get('par_m2_terrain')} €/m² de terrain), fiabilité {bilan.fiabilite}", "ESTIME")
    prix = out.get("prix_dvf")
    if prix and prix.get("median"):
        # MANDAT PRIX SORTIE CONSOMMATEURS (Vic 28/07/2026) — `sector_price` est le prix des
        # COMPARABLES (existant), PAS le prix de sortie du bilan (neuf). Distingués pour ne pas
        # servir deux « prix de sortie » incohérents dans le même dossier.
        # M54-AB C5 : la synthèse IA ne cite plus de n divergent (« 54 ventes » vs tableau 51) —
        # le n des comparables reste dans le TABLEAU, les n de marché dans le bloc commune M-U.
        facts["marche"] = F(f"comparables DVF du secteur {prix.get('median')} €/m² (existant, "
                            f"fiabilité {prix.get('fiabilite')})",
                            "SOURCE" if prix.get("fiabilite") == "fiable" else "ESTIME")
    label_neuf = out.get("prix_neuf_label")
    if label_neuf:
        import re
        # retire tout « , N ventes » du label : le n divergent ne doit pas entrer dans la prose IA.
        label_neuf = re.sub(r",?\s*\d[\d\s]*ventes", "", label_neuf).strip(" ·—,")
        facts["prix_sortie_neuf"] = F(f"prix de sortie neuf retenu pour le bilan — {label_neuf}", "ESTIME")
    # M54-AB C3 : la marge SYNTHÉTISÉE découle de la charge du bilan à rebours (point de calcul
    # unique), jamais de la charge Score É recalculée à 21 % — sinon la synthèse cite -18 k€ et le
    # bloc Score É -19 k€ dans le même dossier.
    from .briques_pdf import score_e_affiche
    sa = score_e_affiche(out)
    if sa:
        facts["marge"] = F(f"marge foncière estimée {_eur(sa['marge'])} "
                           f"(prix de sortie neuf, niveau {sa['niveau_prix']})", "ESTIME")
    perm = out.get("permits")
    if perm and perm.get("n"):
        facts["permis_voisins"] = F(f"{perm['n']} permis de construire dans le voisinage récent", "SOURCE")
    # points de vigilance : servitudes/risques
    rap = out.get("rapport") or {}
    vig = []
    for sec in ("risques", "patrimoine"):
        for it in (rap.get(sec) or {}).get("couches", []):
            vig.append(it["label"])
    if (rap.get("patrimoine") or {}).get("abf"):
        vig.append("abords de monument historique (avis ABF probable)")
    if vig:
        facts["vigilance"] = F("points de vigilance : " + ", ".join(sorted(set(vig))[:6]), "SOURCE")
    return facts


def _synthese_html(db: Session, out: dict) -> str:
    """Synthèse exécutive narrée par le socle (sonnet, strict_numbers). Repli déterministe si pas de clé."""
    from ..ai import core
    from ..ai.avis import AVIS_IA
    facts = _facts_synthese(out, core)
    txt = None
    try:
        ctx = core.build_context(facts, allowed_fields=set(facts))
        res = core.complete(db, kind="synthese-banquier", model=core.MODEL_REASONING, max_tokens=600,
                            system=_SYSTEM_SYNTHESE, context=ctx, validate=True,
                            require_sources=False, strict_numbers=True)
        if not res.degraded and not res.rejected and res.text:
            txt = res.text
    except Exception as exc:  # noqa: BLE001
        log.warning("synthèse IA : %s", exc)
    ai_used = txt is not None
    if not txt:
        # repli déterministe : concatène les faits (aucun chiffre inventé)
        txt = " · ".join(f.value for f in facts.values())
    # EXPRESS-01 · Volet B : l'avis IA n'apparaît QUE si la synthèse a été générée par le
    # LLM (jamais sur le repli déterministe — critère : uniquement là où l'IA s'exprime).
    # M54-AB F10 : le cartouche « L'IA ne juge pas… » passe APRÈS la synthèse (il la commente,
    # il ne l'introduit pas).
    avis = f"<div class='avis-ia'>{_esc(AVIS_IA)}</div>" if ai_used else ""
    # M73 C3 : le LLM renvoie du markdown (**gras**, titres, puces) — jamais imprimé tel quel dans
    # un PDF client. On dé-markdownise + on retire un titre « SYNTHÈSE EXÉCUTIVE » redondant (le <h2>
    # existe déjà). Défaut corrigé à l'écran en M61, il subsistait dans le banquier.
    return f"<div class='exec'>{_esc(_strip_md(txt)) if txt else '—'}</div>{avis}"


# ───────────────────────── endpoints ─────────────────────────

# BLOC B (B1.5) — génération ASYNCHRONE + cache par (idu, run servi). La génération
# (collecte + weasyprint) prenait 9,3 s BLOQUANTS au clic : désormais le front lance
# `POST /{idu}/prepare` (202, thread avec SA PROPRE session DB), sonde `GET /{idu}/statut`,
# puis ouvre le PDF — servi du cache en ~ms. Le GET direct .pdf reste synchrone (compat
# liens/QA) mais profite du même cache. Cache mémoire LRU (32 dossiers ≈ qq Mo), vidé au
# redémarrage — le run servi ne change qu'avec un restart (bascule) : la clé (idu, run)
# est une ceinture-bretelles documentée.
from collections import OrderedDict as _OD
from threading import Lock as _Lock, Thread as _Thread

from ..scoring.score_v_constants import Q_A_RUN_LABEL as _RUN

_PDF_CACHE: _OD[tuple[str, str], bytes] = _OD()
_PDF_CACHE_MAX = 32
_PDF_JOBS: dict[tuple[str, str], dict] = {}
_PDF_LOCK = _Lock()


def _build_pdf(db: Session, idu: str, marque: dict | None = None) -> bytes:
    out = bq.collect(db, idu)
    out["_synthese"] = _synthese_html(db, out)   # synthèse d'abord (utilisée en couverture)
    sections = [bq.cover(out, marque=marque, titre="Dossier banquier", bandeau=LIBELLE,
                         produit_sous_titre="DOSSIER BANQUIER · présentation financeur"),
                bq.identite(out), bq.faisabilite(out),
                bq.bilan(out), bq.comparables(out), bq.risques(out),
                bq.assainissement_rehab(out),        # M73-D — ANC + réhab (rendu partagé, jamais masqué)
                bq.limites_section("banquier")]      # M73 §5 — « Ce que ce document ne peut pas dire »
    # C7 : bandeau de contexte sur chaque page (produit · IDU — commune)
    pdf = bq.render_pdf(sections, LIBELLE, produit="Dossier banquier",
                        idu=idu, commune=out["parcelle"].get("commune") or "")
    log.info("dossier banquier %s généré (%d ko)", idu, len(pdf) // 1024)
    return pdf


def _cache_put(key: tuple[str, str], pdf: bytes) -> None:
    with _PDF_LOCK:
        _PDF_CACHE[key] = pdf
        _PDF_CACHE.move_to_end(key)
        while len(_PDF_CACHE) > _PDF_CACHE_MAX:
            _PDF_CACHE.popitem(last=False)


def _job_worker(idu: str) -> None:
    """Thread de génération — session DB PROPRE (jamais celle de la requête, fermée à la réponse)."""
    from ..db import session_scope
    key = (idu, _RUN)
    try:
        with session_scope() as s:
            pdf = _build_pdf(s, idu)
        _cache_put(key, pdf)
        with _PDF_LOCK:
            _PDF_JOBS[key] = {"etat": "pret"}
    except Exception as e:                                    # noqa: BLE001 — l'état porte l'erreur
        log.warning("dossier banquier %s : échec génération (%s)", idu, e)
        with _PDF_LOCK:
            _PDF_JOBS[key] = {"etat": "erreur", "detail": "Génération impossible — réessayez."}


@router.post("/{idu}/prepare", status_code=202)
def dossier_banquier_prepare(idu: str) -> dict:
    """Lance (ou constate) la génération asynchrone. Réponses : pret | en_cours."""
    if not plans.acces("dossier_parcelle"):
        raise HTTPException(403, detail=plans.refus("dossier_parcelle"))
    key = (idu, _RUN)
    with _PDF_LOCK:
        if key in _PDF_CACHE:
            _PDF_JOBS[key] = {"etat": "pret"}
            return {"etat": "pret"}
        if _PDF_JOBS.get(key, {}).get("etat") == "en_cours":
            return {"etat": "en_cours"}
        _PDF_JOBS[key] = {"etat": "en_cours"}
    _Thread(target=_job_worker, args=(idu,), daemon=True).start()
    return {"etat": "en_cours"}


@router.get("/{idu}/statut")
def dossier_banquier_statut(idu: str) -> dict:
    """État de la génération asynchrone : pret | en_cours | erreur | inconnu."""
    key = (idu, _RUN)
    with _PDF_LOCK:
        if key in _PDF_CACHE:
            return {"etat": "pret"}
        return dict(_PDF_JOBS.get(key, {"etat": "inconnu"}))


@router.get("/{idu}.pdf")
def dossier_banquier_pdf(idu: str, request: Request, ign: bool = True,
                         db: Session = Depends(get_db)) -> Response:
    """Sert le Dossier banquier — du cache si prêt, sinon génération synchrone (compat liens)."""
    if not plans.acces("dossier_parcelle"):
        raise HTTPException(403, detail=plans.refus("dossier_parcelle"))
    # M23-E : PORTE DE QUOTA abonné (30/j Intégral · 200/j Illimité usage loyal ;
    # Flash HORS quota) — 429 honnête au dépassement, passant sans session (pilote).
    from ..quota import porte_export
    porte_export(request, db)
    from ..marque import charger as _charger_marque
    marque = _charger_marque(db, request)

    key = (idu, _RUN)
    with _PDF_LOCK:
        pdf = _PDF_CACHE.get(key)
        if pdf is not None:
            _PDF_CACHE.move_to_end(key)
    if pdf is None:
        pdf = _build_pdf(db, idu, marque=marque)
        _cache_put(key, pdf)
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="dossier_banquier_{idu}.pdf"'})
