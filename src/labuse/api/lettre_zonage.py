"""M22-B — LETTRE DE VÉRIFICATION DE ZONAGE : l'attestation courte que personne ne fait.

2-3 pages print, sobres (briques M22-0, thème clair) — une ATTESTATION, pas une plaquette :
 · identification : parcelle (IDU, adresse BAN, surface, commune), date d'édition ;
 · zonage : zone(s) du PLU applicables, intitulé exact + référence du document d'urbanisme
   (nom du PLU, date d'approbation quand elle est calibrée, identifiant GPU sinon) ;
 · règles principales de la zone, CHACUNE AVEC SON ARTICLE (hauteur, emprise, reculs,
   pleine terre, stationnement) — telles que calibrées (`config/plu_<commune>.yaml`,
   clés `*_src`). RÈGLE D'OR : une règle sans article ne s'imprime PAS ;
 · servitudes et prescriptions cartographiées touchant la parcelle — celles EN BASE
   uniquement (jamais « aucune servitude » : on n'affirme pas l'absence du non-modélisé) ;
 · encadré de LIMITES : la lettre n'est pas un certificat d'urbanisme (art. L.410-1,
   seul opposable) ; la taille minimale de lot n'est pas modélisée → « non vérifiée ».

Interdits (mandat) : affirmer l'absence d'une contrainte non modélisée ; le mot
« opposable » appliqué à la lettre elle-même ; toute règle sans son article.
Quota : hors périmètre M22 — point de branchement documenté dans le rapport
(plans.acces("dossier_parcelle") + usage_compteurs, comme api/dossier.py).
"""
from __future__ import annotations

import logging
from datetime import date

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from . import briques_pdf as bq
from .briques_pdf import esc

log = logging.getLogger("labuse.lettre_zonage")
router = APIRouter(prefix="/lettre-zonage", tags=["lettre-zonage"])

LIBELLE = ("Lettre de vérification de zonage établie à partir des documents d'urbanisme tels que "
           "numérisés (GPU / PLU calibré LABUSE) — ne constitue pas un certificat d'urbanisme "
           "(art. L.410-1 du code de l'urbanisme). À vérifier en mairie.")

LIMITES = ("Cette lettre reflète les documents d'urbanisme tels que numérisés à la date d'édition. "
           "Elle ne constitue pas un certificat d'urbanisme au sens de l'art. L.410-1 du code de "
           "l'urbanisme, seul opposable. La taille minimale de lot n'est pas une donnée "
           "modélisée : non vérifiée.")


def get_db():
    from .app import get_db as _g
    yield from _g()


# ───────────────────────── règles calibrées → lignes (article OBLIGATOIRE) ─────────────────────────

def _fmt_regle(valeur, unite: str, src: str | None) -> tuple[str, str] | None:
    """(valeur affichée, article) ou None si la ligne ne DOIT pas s'imprimer.
    - nombre → « 12 m » ; texte (ex. stationnement) → tel quel ;
    - 'a_verifier' → « à vérifier — règlement ambigu pour cette sous-zone » ;
    - None AVEC source → « non réglementé » (l'article le dit, ex. Art. 9 « il n'est pas
      fixé de règle ») ; None SANS source → pas de ligne (on n'invente ni règle ni article)."""
    from ..faisabilite.plu_rules import A_VERIFIER
    if not src:
        return None
    if valeur == A_VERIFIER:
        return ("à vérifier — règlement ambigu pour cette sous-zone", src)
    if valeur is None:
        return ("non réglementé", src)
    if isinstance(valeur, (int, float)):
        v = f"{valeur:g}{(' ' + unite) if unite else ''}"
    else:
        v = str(valeur)
    return (v, src)


def _regles_zone(code: str, commune: str | None) -> dict:
    """Règles calibrées d'une zone, chacune avec son article — via le MÊME resolver que la
    faisabilité (`resolve_zone`, YAML `*_src`). `calibree=False` → repli honnête (pas de règles)."""
    from ..faisabilite.plu_rules import resolve_zone
    r = resolve_zone(code, commune)
    if r is None or not r.calibree:
        return {"calibree": False, "code": code, "lignes": [], "notes": [], "prospect": False,
                "gel": False}
    src = r.sources or {}
    lignes: list[tuple[str, str, str]] = []          # (règle, valeur, article)
    hauteur = None
    if r.he_m is not None or r.hf_m is not None:
        parts = []
        if r.he_m is not None:
            parts.append(f"égout {r.he_m:g} m" if isinstance(r.he_m, (int, float)) else f"égout {r.he_m}")
        if r.hf_m is not None:
            parts.append(f"faîtage {r.hf_m:g} m" if isinstance(r.hf_m, (int, float)) else f"faîtage {r.hf_m}")
        hauteur = _fmt_regle(" · ".join(parts), "", src.get("hauteur"))
    for label, item in [
        ("Hauteur maximale", hauteur),
        ("Emprise au sol", _fmt_regle(r.emprise_sol_pct, "%", src.get("emprise"))),
        ("Recul / voirie", _fmt_regle(r.recul_voirie_m, "m", src.get("recul_voirie"))),
        ("Recul / limites séparatives", _fmt_regle(r.recul_limites_sep_m, "m", src.get("recul_limites"))),
        ("Pleine terre", _fmt_regle(r.pleine_terre_pct, "%", src.get("pleine_terre"))),
        ("Stationnement", _fmt_regle(r.stat_logement, "", src.get("stat"))),
    ]:
        if item:
            lignes.append((label, item[0], item[1]))
    # M147 L1 : PAS de notes.insert(hauteur_note) — ZoneRules.notes contient DÉJÀ toute clé finissant
    # par `_note` (dont hauteur_note). L'insertion la dupliquait, et le `[:2]` de _regles (supprimé
    # aussi) faisait alors tomber toute note suivante — le GEL de Us, l'alignement de Ua, le retrait
    # ZAC de AU3a. Aucune note matérielle ne doit disparaître pour une raison de gabarit.
    notes = list(r.notes or [])
    # M147 L2 : le GEL (construction neuve non autorisée : Us, 2AU) est remonté STRUCTURELLEMENT, plus
    # seulement via une note en prose — la condition gouverne le chiffre (doctrine M143 L1 / M145 B.1.4).
    return {"calibree": True, "code": code, "lignes": lignes, "notes": notes,
            "prospect": r.hauteur_mode == "prospect", "gel": not r.constructible_neuf}


# ───────────────────────── référence d'attestation (C8) ─────────────────────────

def _ref_attestation(db: Session, idu: str) -> str:
    """M22-F C8 — numéro de référence UNIQUE de l'attestation, LZ-AAAA-NNNN, stocké en base
    (table `lettre_zonage_refs`, additive). Une référence par ÉDITION : chaque génération
    est tracée. Petit retry sur collision (concurrence faible, contrainte UNIQUE fait foi)."""
    from sqlalchemy import text as _t
    db.execute(_t(
        "CREATE TABLE IF NOT EXISTS lettre_zonage_refs ("
        "  id serial PRIMARY KEY, ref text UNIQUE NOT NULL, idu text NOT NULL,"
        "  created_at timestamptz NOT NULL DEFAULT now())"))
    annee = date.today().year
    for _essai in range(3):
        n = db.execute(_t(
            "SELECT count(*) FROM lettre_zonage_refs WHERE ref LIKE :p"),
            {"p": f"LZ-{annee}-%"}).scalar() or 0
        ref = f"LZ-{annee}-{n + 1:04d}"
        try:
            db.execute(_t("INSERT INTO lettre_zonage_refs (ref, idu) VALUES (:r, :i)"),
                       {"r": ref, "i": idu})
            db.commit()
            return ref
        except Exception:  # noqa: BLE001 — collision UNIQUE : on recompte
            db.rollback()
    return f"LZ-{annee}-XXXX"  # repli improbable : la lettre sort, la réf est dégradée


# ───────────────────────── sections HTML (layout attestation) ─────────────────────────

def _identification(p: dict, rap: dict, ref: str, marque: dict | None = None) -> str:
    """Couverture d'ATTESTATION (C8) : marque, titre, RÉFÉRENCE et DATE D'ÉDITION en tête,
    identification, plan cadastral clair (C2).

    M31 PC1 : `marque` ET `_marque_bloc` étaient référencés sans être en portée (régression
    M23-A 98363d7). Aucun test ne couvrait _identification/_build_pdf → NameError latent en
    prod (tout PDF Lettre de zonage plantait). marque threadée + import local ici."""
    from ..marque import bloc_html as _marque_bloc
    edition = date.today().strftime("%d/%m/%Y")
    rows = [("Références cadastrales", f"{p['idu']} · section {p['section']} n° {p['numero']}"),
            ("Commune", p["commune"]),
            ("Surface du terrain (cadastre)", f"{p['surface_m2']:.0f} m²")]
    if rap.get("adresse"):
        rows.append(("Adresse (Base Adresse Nationale)", rap["adresse"]))
    table = "".join(f"<tr><td style='width:38%'>{esc(k)}</td><td>{esc(v)}</td></tr>" for k, v in rows)
    return (f"<section class='garde'>"
            f"{_marque_bloc(marque)}{bq.wordmark_html('LETTRE DE VÉRIFICATION DE ZONAGE · attestation documentaire')}"
            f"<h1>Lettre de vérification de zonage</h1>"
            f"<div class='refs'>Référence <b>{esc(ref)}</b> · éditée le <b>{esc(edition)}</b> · "
            f"parcelle <b>{esc(p['idu'])}</b> — {esc(p['commune'])}</div>"
            f"<div class='bandeau'>{LIBELLE}</div>"
            f"<h2>1 · Identification</h2><table>{table}</table>"
            f"{bq.map_html(p['geojson'])}</section>")


def _zonage(zones: list[dict], commune: str | None, rnu: dict | None = None) -> str:
    from ..plu_reglement import resolve_reglement
    # M147 L3 — RNU : une commune au règlement national n'a PAS de PLU local. Dire le RNU (statut
    # légal), pas « zonage non résolu » (qui imputerait à un défaut de numérisation un fait de droit).
    # rnu.rnu_block existait mais n'était jamais appelé (constat M146 §B3).
    if rnu:
        verif = f" (statut vérifié le {esc(rnu['verifie_le'])})" if rnu.get("verifie_le") else ""
        return (f"<h2>2 · Zonage applicable</h2>"
                f"<div class='bandeau'><b>{esc(rnu['libelle'])}.</b> {esc(rnu['detail'])}</div>"
                f"<p class='note'>Commune : {esc(rnu.get('commune_nom') or commune)}{verif}. "
                f"Il n'existe donc pas de zone ni de règlement de PLU à attester pour cette "
                f"parcelle — les règles nationales d'urbanisme s'appliquent.</p>")
    if not zones:
        return ("<h2>2 · Zonage applicable</h2><p class='note'>Zonage non résolu dans les couches "
                "numérisées (GPU) à la date d'édition — vérification en mairie indispensable.</p>")
    def _approb_fr(iso: str | None) -> str | None:
        try:
            return date.fromisoformat(iso).strftime("%d/%m/%Y") if iso else None
        except ValueError:
            return iso
    rows, fichiers = [], {}
    for z in zones:
        code = z.get("libelle") or z.get("classe") or "—"
        reg = resolve_reglement(commune, str(code), z.get("idurba")) or {}
        fichier = reg.get("document")                  # nom du PDF règlement (calibré) ou None
        if fichier:
            # C3 — nom LISIBLE du document en tableau ; le nom de fichier part en note.
            approb = _approb_fr(reg.get("approbation"))
            ref_doc = f"PLU de {commune}" + (f", approuvé le {approb}" if approb else "")
            fichiers[fichier] = ref_doc
        else:
            ref_doc = f"GPU {z['idurba']}" if z.get("idurba") else "document non calibré"
        rows.append(f"<tr><td><b>{esc(code)}</b></td><td class='n'>{esc(z.get('pct'))} %</td>"
                    f"<td>{esc(ref_doc)}</td></tr>")
    body = (f"<h2>2 · Zonage applicable</h2>"
            f"<table><tr><th>Zone (intitulé du règlement)</th><th class='n'>Part de la parcelle</th>"
            f"<th>Document d'urbanisme</th></tr>{''.join(rows)}</table>")
    for fichier, lisible in fichiers.items():
        body += (f"<p class='note'>{esc(lisible)} — fichier du règlement écrit : "
                 f"{esc(fichier)}.</p>")
    body += ("<p class='note'>Source zonage : Géoportail de l'urbanisme (GPU), couche numérisée "
             "intersectée avec la géométrie cadastrale de la parcelle.</p>")
    return body


def _est_zone_au(z: dict) -> bool:
    """Zone d'urbanisation future (AU) : ouverture conditionnée à une opération d'aménagement
    d'ensemble (M147 L4). Détectée sur le SUBTYPE GPU (`classe` = 'AUc', 'AU3a'…) — pas sur le
    libellé, pour ne pas confondre 'Uav' (zone U) avec de l'AU."""
    classe = str(z.get("classe") or "")
    return classe.upper().startswith("AU")


def _regles(zones: list[dict], commune: str | None, rnu: dict | None = None) -> str:
    body = "<h2>3 · Règles principales des zones (avec leurs articles)</h2>"
    # M147 L3 — RNU : pas de règlement de zone à servir (les règles nationales s'appliquent au cas
    # par cas). Mention explicite plutôt qu'un en-tête vide (wording rnu.NON_APPLICABLE_RNU).
    if rnu:
        from ..rnu import NON_APPLICABLE_RNU
        return (body + f"<p class='note'>Règles de zone du PLU : {esc(NON_APPLICABLE_RNU)}. "
                f"En l'absence de document local, la constructibilité relève des règles nationales "
                f"d'urbanisme (parties actuellement urbanisées, appréciation au cas par cas du service "
                f"instructeur) — non couverte par la présente lettre.</p>")
    imprimees = 0
    for z in zones[:3]:
        code = z.get("libelle") or z.get("classe")
        if not code:
            continue
        rz = _regles_zone(str(code), commune)
        if not rz["calibree"]:
            body += (f"<h3>Zone {esc(code)}</h3><p class='note'>Règlement non calibré pour cette "
                     f"zone/commune : règles non vérifiées — se reporter au règlement écrit "
                     f"(consultable sur le Géoportail de l'urbanisme).</p>")
            continue
        if not rz["lignes"]:
            continue
        # M147 L2 — GEL : la condition AVANT le chiffre. Le tableau est présenté pour ce qu'il est —
        # la règle applicable SI la zone s'ouvre, jamais une autorisation de construire.
        titre_valeur = "Valeur calibrée"
        if rz["gel"]:
            body += (f"<h3>Zone {esc(code)} — zone gelée</h3>"
                     f"<div class='bandeau'>⚠ <b>Zone gelée à la date d'édition : construction neuve "
                     f"non autorisée.</b> Les valeurs ci-dessous sont les règles qui s'appliqueraient "
                     f"<b>si</b> la zone était ouverte à l'urbanisation ; elles ne valent pas "
                     f"autorisation de construire.</div>")
            titre_valeur = "Règle si ouverture"
        else:
            body += f"<h3>Zone {esc(code)}</h3>"
        rows = "".join(f"<tr><td>{esc(l)}</td><td>{esc(v)}</td><td class='note'>{esc(a)}</td></tr>"
                       for l, v, a in rz["lignes"])
        body += (f"<table><tr><th>Règle</th><th>{titre_valeur}</th><th>Article / page du règlement</th></tr>"
                 f"{rows}</table>")
        if rz["prospect"]:
            body += ("<p class='note'>Hauteur en prospect : la hauteur admissible dépend de la largeur "
                     "de la voie au droit de la parcelle (L ≥ H) — valeur par parcelle, pas par zone.</p>")
        # M147 L1 — TOUTES les notes matérielles (plus de coupe [:2] : fpdf2 pagine, ne tronque pas).
        for n in rz["notes"]:
            body += f"<p class='note'>{esc(n)}</p>"
        # M147 L4 — caveat ZAC générique et VRAI sur zone AU (aucune couche ZAC : dette M144, on
        # n'affirme rien par parcelle, on rappelle le régime).
        if _est_zone_au(z):
            body += ("<p class='note'>Zone d'urbanisation future : l'ouverture à la construction est "
                     "conditionnée à une opération d'aménagement d'ensemble. Un périmètre d'aménagement "
                     "(ZAC) peut s'y appliquer, avec un règlement propre — à vérifier auprès de la "
                     "commune ; il n'est pas modélisé dans la présente lettre.</p>")
        imprimees += 1
    if imprimees:
        body += ("<p class='note'>Valeurs calibrées par LABUSE depuis le règlement écrit cité — le "
                 "règlement complet (dispositions générales, renvois, annexes) peut les compléter.</p>")
    return body


def _servitudes(rap: dict) -> str:
    items: list[tuple[str, str, str]] = []
    for it in (rap.get("identite") or {}).get("prescriptions", []):
        items.append(("Prescription PLU", it.get("libelle") or "—", it.get("code") or ""))
    for it in (rap.get("risques") or {}).get("couches", []):
        items.append(("Risque cartographié", it.get("label") or "—", it.get("detail") or ""))
    for it in (rap.get("patrimoine") or {}).get("couches", []):
        items.append(("Servitude / protection", it.get("label") or "—", it.get("detail") or ""))
    for m in (rap.get("patrimoine") or {}).get("abf", []) or []:
        items.append(("Patrimoine", "Abords de monument historique (~500 m) — avis ABF probable",
                      m.get("name") or ""))
    body = "<h2>4 · Servitudes et prescriptions cartographiées</h2>"
    if items:
        rows = "".join(f"<tr><td>{esc(t)}</td><td>{esc(l)}</td><td>{esc(d)}</td></tr>"
                       for t, l, d in items)
        body += f"<table><tr><th>Nature</th><th>Élément</th><th>Détail</th></tr>{rows}</table>"
        body += ("<p class='note'>Liste limitée aux couches numérisées en base à la date d'édition "
                 "— elle ne vaut pas état exhaustif des servitudes.</p>")
    else:
        body += ("<p class='note'>Aucun élément dans les couches numérisées en base à la date "
                 "d'édition — ce constat ne vaut pas absence de servitude : seules les servitudes "
                 "cartographiées et ingérées sont vérifiées ici.</p>")
    return body


def _limites(rap: dict) -> str:
    src_rows = "".join(
        f"<tr><td>{esc(s.get('source'))}</td><td>{esc(s.get('millesime'))}</td></tr>"
        for s in (rap.get("sources") or [])
        if s.get("section") in ("identite", "risques", "patrimoine", "adresse"))
    body = (f"<h2>5 · Limites de la présente lettre</h2>"
            f"<div class='bandeau'>{LIMITES}</div>")
    if src_rows:
        body += (f"<h3>Sources et millésimes</h3>"
                 f"<table><tr><th>Source</th><th>Millésime / synchronisation</th></tr>{src_rows}</table>")
    return body


def _cloture(ref: str) -> str:
    """C8 — bloc de clôture d'attestation : qui édite, sous quelle référence, quand.
    Codes d'un document formel — aucun engagement au-delà du libellé légal du pied."""
    edition = date.today().strftime("%d/%m/%Y")
    return (f"<div class='hyp-encadre' style='margin-top:6mm'>"
            f"<span class='titre'>Édité par LABUSE</span>"
            f"Attestation documentaire n° <b>{esc(ref)}</b>, éditée le <b>{esc(edition)}</b> "
            f"par LABUSE (radar foncier — La Réunion) sur données publiques numérisées. "
            f"Document généré électroniquement, valable en l'état de ses sources ; la référence "
            f"ci-dessus est enregistrée par LABUSE et permet de vérifier l'authenticité de "
            f"l'édition sur simple demande.</div>")


# ───────────────────────── endpoint ─────────────────────────

def _build_pdf(db: Session, idu: str, marque: dict | None = None) -> bytes:
    # M31 PC1 : import _marque_bloc retiré d'ici (mort — utilisé dans _identification qui
    # l'importe désormais localement, avec `marque` reçue en paramètre).
    from ..flash.data import collect_report_data
    from sqlalchemy import text as _t
    row = db.execute(_t(
        "SELECT idu, commune, section, numero, round(surface_m2) AS surface_m2, "
        "ST_AsGeoJSON(geom, 7) AS geojson FROM parcels WHERE idu = :i"), {"i": idu}).mappings().first()
    if not row:
        from fastapi import HTTPException
        raise HTTPException(404, f"Parcelle {idu} inconnue.")
    p = dict(row)
    rap = collect_report_data(db, idu) or {}
    zones = (rap.get("identite") or {}).get("zones", [])
    # M147 L3 — RNU : bloc calculé une fois (None hors commune RNU), gouverne les sections 2 et 3.
    from ..rnu import rnu_block
    rnu = rnu_block(idu, db)
    ref = _ref_attestation(db, idu)                      # C8 : référence unique, tracée
    sections = [
        _identification(p, rap, ref, marque),
        _zonage(zones, p.get("commune"), rnu),
        _regles(zones, p.get("commune"), rnu),
        _servitudes(rap),
        _limites(rap),
        _cloture(ref),
    ]
    # C7 : bandeau de contexte sur chaque page
    pdf = bq.render_pdf(sections, LIBELLE, produit="Lettre de zonage",
                        idu=idu, commune=p.get("commune") or "")
    log.info("lettre zonage %s générée (%s, %d ko)", idu, ref, len(pdf) // 1024)
    return pdf


@router.get("/{idu}.pdf")
def lettre_zonage_pdf(idu: str, request: Request, db: Session = Depends(get_db)) -> Response:
    """Sert la lettre de vérification de zonage (synchrone : document court)."""
    # M23-E : PORTE DE QUOTA abonné (30/j Intégral · 200/j Illimité usage loyal ;
    # Flash HORS quota) — 429 honnête au dépassement, passant sans session (pilote).
    from ..quota import porte_export
    porte_export(request, db)
    from ..marque import charger as _charger_marque
    pdf = _build_pdf(db, idu, marque=_charger_marque(db, request))
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="lettre_zonage_{idu}.pdf"'})
