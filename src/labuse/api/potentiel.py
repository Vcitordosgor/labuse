"""M22-D — RAPPORT DE POTENTIEL (agence) : la valeur que personne ne voit, avant compromis.

Scénario : l'agent a (ou vise) un mandat sur un bien avec terrain. Ce PDF (4-6 pages,
briques M22-0, thème clair, LANGAGE ACCESSIBLE — le lecteur final peut être le vendeur
particulier) révèle ce que le bien permet au-delà de son usage actuel et sécurise la vente.

Structure : 1 synthèse (3 verdicts lisibles : Extension / Division / Points d'attention)
· 2 potentiel d'extension (SDP résiduelle = autorisée − existante, incertitudes DITES)
· 3 divisibilité — CONDITIONNEL O12 : la revue visuelle des 20 cartes « Division en or »
  n'est PAS validée par Vic à la date du lot (EXPOSE=False inchangé) → encadré
  « Analyse de divisibilité : disponible sur étude complémentaire », AUCUN chiffre
· 4 risques & servitudes avant compromis (esprit M19 : ce qui est vérifié est AFFIRMÉ,
  ce qui est signalé évite un compromis qui capote)
· 5 contexte marché (DVF secteur, pour situer) · 6 limites + sources.

Interdits (mandat) : AUCUNE identité de propriétaire (le lecteur peut être n'importe qui) ;
aucune promesse de valorisation en euros de la division — le document montre le potentiel,
il ne le price pas ; « pas de potentiel identifié » est un résultat honnête et utile.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from . import briques_pdf as bq
from .briques_pdf import esc, s

log = logging.getLogger("labuse.potentiel")
router = APIRouter(prefix="/rapport-potentiel", tags=["rapport-potentiel"])

LIBELLE = ("Rapport de potentiel établi à partir de données publiques (cadastre, PLU, BD TOPO, "
           "DVF) — ni un avis de valeur, ni un document d'arpentage ; indications à confirmer "
           "par étude de faisabilité et géomètre.")

ENCADRE_DIVISION = ("Analyse de divisibilité : disponible sur étude complémentaire. "
                    "La faisabilité d'une division (taille minimale éventuelle, accès et façade "
                    "du lot, reculs, servitudes) relève d'une étude réglementaire et d'un "
                    "géomètre-expert — aucun chiffre n'est avancé ici.")

LIMITES = ("Ce rapport n'est ni un avis de valeur, ni un document d'arpentage, ni un certificat "
           "d'urbanisme. Les surfaces constructibles sont des indications issues des règles "
           "numérisées et du bâti cartographié ; lorsque la hauteur du bâti n'est pas connue, "
           "la surface existante est une estimation — c'est alors écrit en clair. Aucune "
           "valorisation en euros d'une division n'est avancée.")


def get_db():
    from .app import get_db as _g
    yield from _g()


# ───────────────────────── assemblage ─────────────────────────

def _collect(db: Session, idu: str) -> dict:
    """Briques (parcelle, rapport, faisabilité, DVF) + bloc résiduel (extension).
    AUCUNE donnée propriétaire n'est collectée (interdit du mandat)."""
    out = bq.collect(db, idu)
    out.pop("score_e", None)          # marge € : hors sujet ici (pas d'avis de valeur)
    try:
        from sqlalchemy import text as _t
        from ..faisabilite.residuel import compute_residuel
        pid = db.execute(_t("SELECT id FROM parcels WHERE idu = :i"), {"i": idu}).scalar()
        out["residuel"] = compute_residuel(db, pid) if pid else {"disponible": False}
    except Exception as exc:  # noqa: BLE001
        log.warning("residuel %s : %s", idu, exc)
        out["residuel"] = {"disponible": False, "raison": "calcul indisponible"}
    return out


def _n_attention(out: dict) -> int:
    rap = out.get("rapport") or {}
    n = len((rap.get("risques") or {}).get("couches", []))
    n += len((rap.get("patrimoine") or {}).get("couches", []))
    n += len((rap.get("patrimoine") or {}).get("abf", []) or [])
    return n


# ───────────────────────── sections ─────────────────────────

def _synthese(out: dict) -> str:
    """1 — TROIS VERDICTS LISIBLES. Langage accessible (lecteur possiblement vendeur)."""
    p = out["parcelle"]
    r = out.get("residuel") or {}
    n_att = _n_attention(out)
    if r.get("disponible") and r.get("sdp_residuelle_m2", 0) > 0 and r.get("sous_densite"):
        v_ext = (f"Extension possible — environ {r['sdp_residuelle_m2']} m² de surface "
                 f"constructible restent mobilisables{' (estimation)' if r.get('estimation_sdp') else ''}.")
        badge_ext = "possible"
    elif r.get("disponible") and r.get("sdp_residuelle_m2", 0) > 0:
        v_ext = (f"Marge d'extension limitée — environ {r['sdp_residuelle_m2']} m² restants"
                 f"{' (estimation)' if r.get('estimation_sdp') else ''}.")
        badge_ext = "limitée"
    elif r.get("disponible"):
        v_ext = "Pas de potentiel d'extension identifié — la densité autorisée est atteinte ou dépassée."
        badge_ext = "non identifié"
    else:
        v_ext = f"Potentiel d'extension non calculable ici ({esc(r.get('raison') or 'données indisponibles')})."
        badge_ext = "non calculable"
    v_att = (f"{n_att} point(s) à vérifier avant compromis (détail en partie 4)." if n_att
             else "Rien à signaler dans les couches vérifiées (liste en fin de document).")
    rows = (f"<tr><td><b>Extension</b></td><td>{esc(badge_ext)}</td><td>{esc(v_ext)}</td></tr>"
            f"<tr><td><b>Division</b></td><td>étude complémentaire</td>"
            f"<td>{ENCADRE_DIVISION}</td></tr>"
            f"<tr><td><b>Points d'attention</b></td><td>{n_att or '—'}</td><td>{esc(v_att)}</td></tr>")
    # C6 — le chiffre-héros : la SDP résiduelle se voit à 2 mètres (quand elle existe)
    kpis = []
    if r.get("disponible") and r.get("sdp_residuelle_m2", 0) > 0:
        # toujours Estimé : dérivée des règles calibrées, même quand la hauteur bâtie est réelle
        kpis.append(bq.cartouche("Surface constructible restante · Estimé",
                                 f"~{r['sdp_residuelle_m2']} m²", hero=True))
    kpis.append(bq.cartouche("Terrain · Sourcé", f"{p['surface_m2']:.0f} m²"))
    if n_att:
        kpis.append(bq.cartouche("À vérifier avant compromis", str(n_att), "point(s)"))
    return (f"<section class='garde'>"
            f"{bq.garde_entete(p, produit_sous_titre='RAPPORT DE POTENTIEL · avant compromis', titre='Rapport de potentiel', bandeau=LIBELLE, marque=marque)}"
            f"<h2>1 · Ce que ce bien permet, en trois lignes</h2>"
            f"<table><tr><th>Volet</th><th>Verdict</th><th>En clair</th></tr>{rows}</table>"
            f"{bq.cartouches(kpis)}"
            f"<h2>Situation</h2>{bq.map_html(p['geojson'])}</section>")


def _extension(out: dict) -> str:
    """2 — POTENTIEL D'EXTENSION : autorisé − existant = restant. Incertitudes DITES."""
    r = out.get("residuel") or {}
    body = "<div class='pb'></div><h2>2 · Potentiel d'extension (surface constructible restante)</h2>"
    if not r.get("disponible"):
        raison = r.get("raison") or "données indisponibles"
        return body + f"<p class='note'>Non calculable : {esc(raison)} — aucun chiffre n'est avancé.</p>"
    rows = [
        ("Surface de plancher autorisée (règles PLU)", f"{r['sdp_max_m2']} m²",
         "E" if r.get("capacite_estimee") else "S"),
        (f"Surface existante estimée (bâti cartographié × {r['niveaux_existants']:g} niveau(x))",
         f"{r['sdp_existante_m2']} m²", "S" if r.get("niveaux_reels") else "E"),
        ("Surface restante (autorisée − existante)", f"{r['sdp_residuelle_m2']} m²", "E"),
        ("Emprise au sol bâtie aujourd'hui", f"{r['taux_emprise_pct']} % du terrain", "S"),
    ]
    table = "".join(f"<tr><td>{esc(k)}</td><td class='n'>{esc(v)}</td><td>{s(prov)}</td></tr>"
                    for k, v, prov in rows)
    body += f"<table><tr><th>Donnée</th><th class='n'>Valeur</th><th>Nature</th></tr>{table}</table>"
    body += f"<p>{esc(r.get('libelle') or '')}</p>"
    if r.get("estimation_sdp"):
        body += (f"<div class='bandeau'>La hauteur du bâti existant n'est pas connue des données "
                 f"cartographiques : la surface existante est une ESTIMATION sur la base d'un bâti "
                 f"de {r['niveaux_existants']:g} niveau(x). Un relevé précis peut la corriger.</div>")
    if r.get("capacite_estimee"):
        body += ("<p class='note'>Capacité autorisée issue d'une estimation générique (zone hors "
                 "règlement calibré) — à confirmer au règlement écrit.</p>")
    body += ("<p class='note'>En clair : ces mètres carrés « dormants » peuvent intéresser un "
             "acquéreur qui souhaite agrandir ou valoriser — c'est un argument de vente factuel, "
             "pas une promesse de prix.</p>")
    return body


def _divisibilite() -> str:
    """3 — DIVISIBILITÉ : O12 non validé (revue Vic en attente) → encadré, AUCUN chiffre."""
    return (f"<h2>3 · Divisibilité du terrain</h2>"
            f"<div class='bandeau'>{ENCADRE_DIVISION}</div>"
            f"<p class='note'>Pourquoi cette prudence : une division réussie dépend de règles "
            f"locales (accès, façade, reculs, réseaux) et d'un bornage — les affirmer sans étude "
            f"exposerait vendeur et acquéreur. Le présent rapport signale le sujet sans le trancher.</p>")


def _avant_compromis(out: dict) -> str:
    """4 — RISQUES & SERVITUDES AVANT COMPROMIS : le vérifié est affirmé, le signalé est listé."""
    rap = out.get("rapport") or {}
    items: list[tuple[str, str, str]] = []
    for it in (rap.get("risques") or {}).get("couches", []):
        items.append(("Risque cartographié", it.get("label") or "—", it.get("detail") or ""))
    for it in (rap.get("patrimoine") or {}).get("couches", []):
        items.append(("Servitude / protection", it.get("label") or "—", it.get("detail") or ""))
    for m in (rap.get("patrimoine") or {}).get("abf", []) or []:
        items.append(("Patrimoine", "Abords de monument historique (~500 m) — avis ABF probable",
                      m.get("name") or ""))
    for it in (rap.get("identite") or {}).get("prescriptions", []):
        items.append(("Prescription PLU", it.get("libelle") or "—", it.get("code") or ""))
    body = ("<div class='pb'></div><h2>4 · À vérifier avant compromis</h2>"
            "<p class='note'>Ce qui est signalé ici évite un compromis qui capote ; ce qui est "
            "vérifié et muet vaut de l'or pour rassurer un acquéreur.</p>")
    if items:
        rows = "".join(f"<tr><td>{esc(t)}</td><td>{esc(l)}</td><td>{esc(d or 'parcelle concernée')}</td></tr>"
                       for t, l, d in items)
        body += f"<table><tr><th>Nature</th><th>Élément</th><th>Détail</th></tr>{rows}</table>"
    else:
        body += ("<p>✓ Rien à signaler dans les couches vérifiées (sources et millésimes en fin "
                 "de document).</p>")
    body += ("<p class='note'>Liste limitée aux couches numérisées — elle ne remplace pas l'état "
             "des risques réglementaire ni les diagnostics de vente.</p>")
    return body


def _limites(out: dict) -> str:
    rap = out.get("rapport") or {}
    rows = "".join(f"<tr><td>{esc(x.get('source'))}</td><td>{esc(x.get('millesime'))}</td></tr>"
                   for x in (rap.get("sources") or []))
    body = f"<h2>6 · Limites du présent rapport</h2><div class='bandeau'>{LIMITES}</div>"
    if rows:
        body += (f"<h3>Sources et millésimes</h3>"
                 f"<table><tr><th>Source</th><th>Millésime / synchronisation</th></tr>{rows}</table>")
    return body


# ───────────────────────── endpoint ─────────────────────────

def _build_pdf(db: Session, idu: str, marque: dict | None = None) -> bytes:
    out = _collect(db, idu)
    marche = bq.comparables(out).replace("<h2>Marché de comparaison</h2>",
                                         "<h2>5 · Contexte marché (pour situer)</h2>")
    sections = [_synthese(out), _extension(out), _divisibilite(),
                _avant_compromis(out), marche, _limites(out)]
    # C7 : bandeau de contexte sur chaque page
    pdf = bq.render_pdf(sections, LIBELLE, produit="Rapport de potentiel",
                        idu=idu, commune=out["parcelle"].get("commune") or "")
    log.info("rapport potentiel %s généré (%d ko)", idu, len(pdf) // 1024)
    return pdf


@router.get("/{idu}.pdf")
def rapport_potentiel_pdf(idu: str, request: Request, db: Session = Depends(get_db)) -> Response:
    """Sert le rapport de potentiel (synchrone). Entrée : IDU seul."""
    # M23-E : PORTE DE QUOTA abonné (30/j Intégral · 200/j Illimité usage loyal ;
    # Flash HORS quota) — 429 honnête au dépassement, passant sans session (pilote).
    from ..quota import porte_export
    porte_export(request, db)
    from ..marque import charger as _charger_marque
    pdf = _build_pdf(db, idu, marque=_charger_marque(db, request))
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="rapport_potentiel_{idu}.pdf"'})
