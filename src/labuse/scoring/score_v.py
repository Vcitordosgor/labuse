"""Score V (Vendabilité) — moteur de calcul (Stage 3 ADDITIF, mandat SPEC-LABUSE-SCORE-V).

V (0-100) = accumulation de signaux PUBLICS indiquant que le propriétaire a des raisons
objectives de vendre. Barème VERROUILLÉ : score_v_constants.py (D1). Ce module ne touche
ni la cascade, ni Q/A, ni la matrice — il PEUPLE `parcel_v_score`, point.

Architecture : précalculs SET-BASED (une requête par source de signal), assemblage Python
par parcelle, écriture COPY (idempotent : la table dérivée est reconstruite à chaque run,
`computed_at` horodate). Relançable à volonté — aucune donnée source n'est modifiée.

Matching propriétaire (§4.2) : SIREN direct (confiance 1.0) → fallback dénomination
normalisée (0.8, points A/B/C × 0.7) → ambigu = matching_review_queue, pas de match.
Typage (§4.3) : public/bailleur → V NULL + badge (D4) ; copro → calculé + flag.

Choix documentés :
 - Âge dirigeant = MAX des âges des dirigeants personnes physiques (mandat §5.2) — source
   v_pm_propension_vendre (RNE depth-0 + gigogne), fallback dirigeants recherche-entreprises.
 - « En cours » (LJ/RJ/sauvegarde) = aucun jugement de clôture POSTÉRIEUR pour ce SIREN
   (date_annonce, la seule date fiable — cf. Vague A1).
 - SCI dormante : nature juridique 6540 / forme DGFiP SCI, créée ≥ 20 ans, et aucune mise à
   jour RNE < 5 ans (proxy : date_mise_a_jour_rne de recherche-entreprises — on n'a pas
   l'historique d'événements RNE ; documenté au rapport).
 - Cession de fonds : retenue si le SIREN propriétaire est le CÉDANT (listeprecedentproprietaire
   / listeprecedentexploitant), ou annonce mono-SIREN le concernant.
 - DVF_TENURE_OBS5 (variante dégradée validée au GO Phase 0) : aucune mutation sur la fenêtre
   observable 2021-2025 (millésimes antérieurs retirés de la distribution DGFiP).
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..connectors.recherche_entreprises import normalize_denomination, parse_result
from . import score_v_constants as C

BODACC_SRC = "BODACC"
RE_SRC = "Recherche d'entreprises (DINUM)"
RNE_SRC = "INPI RNE"
CARTOFRICHES_URL = "https://cartofriches.cerema.fr/cartofriches/"


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _months_ago(months: int) -> date:
    return _today() - timedelta(days=round(months * 30.44))


def _signal(code: str, *, points: int | None = None, source: str, ref: str | None = None,
            url: str | None = None, date_evenement: str | None = None,
            match: dict | None = None) -> dict:
    famille, base_pts, label = C.SIGNALS[code]
    return {
        "code": code, "famille": famille, "label": label,
        "points": base_pts if points is None else points,
        "source": source, "ref": ref, "url": url,
        "date_evenement": date_evenement, "match": match,
    }


# ─────────────────────────── précalculs set-based ───────────────────────────

def _load_owner_links(session: Session) -> list[dict]:
    rows = session.execute(text(
        "SELECT idu, regexp_replace(COALESCE(siren,''), '[^0-9]', '', 'g') AS siren, "
        "       COALESCE(denomination,''), groupe, COALESCE(forme_juridique,'') "
        "FROM parcelle_personne_morale")).all()
    return [{"idu": r[0], "siren": r[1] if len(r[1]) == 9 else None,
             "denomination": r[2], "groupe": r[3], "forme": r[4]} for r in rows]


def _load_denom_lookups(session: Session) -> dict[str, dict]:
    rows = session.execute(text(
        "SELECT denomination_norm, status, siren, candidats FROM owner_denom_lookup")).all()
    return {r[0]: {"status": r[1], "siren": r[2], "candidats": r[3]} for r in rows}


def _load_enrichments(session: Session) -> dict[str, dict]:
    """siren → fiche PARSÉE (None si SIREN inconnu de recherche-entreprises)."""
    out: dict[str, dict] = {}
    for siren, payload in session.execute(text(
            "SELECT siren, payload FROM owner_enrichment")).all():
        if payload and not payload.get("not_found"):
            out[siren] = parse_result(payload)
    return out


def _load_dirigeant_ages(session: Session) -> dict[str, int]:
    """siren → âge de l'aîné des dirigeants PHYSIQUES (RNE depth-0 + gigogne)."""
    rows = session.execute(text(
        "SELECT siren, age_max_dirigeant FROM v_pm_propension_vendre "
        "WHERE age_max_dirigeant IS NOT NULL")).all()
    return {r[0]: int(r[1]) for r in rows}


def _age_from_enrichment(fiche: dict, today: date) -> int | None:
    """Fallback âge : dirigeants recherche-entreprises (YYYY-MM ou année seule)."""
    best: int | None = None
    for d in fiche.get("dirigeants") or []:
        if (d.get("type") or "").lower() == "personne morale":
            continue
        naissance = d.get("date_de_naissance") or d.get("annee_de_naissance")
        if not naissance:
            continue
        m = re.match(r"^(\d{4})(?:-(\d{2}))?", str(naissance))
        if not m:
            continue
        y = int(m.group(1))
        mo = int(m.group(2) or 12)          # année seule → plancher prudent (fin d'année)
        if y < 1900 or y > today.year:
            continue
        age = today.year - y - (1 if today.month < mo else 0)
        if 0 <= age <= 130 and (best is None or age > best):
            best = age
    return best


def _load_bodacc(session: Session) -> dict[str, list[dict]]:
    """siren → annonces Score V triées par date (nature, famille, refs)."""
    rows = session.execute(text(
        "SELECT siren, famille, COALESCE(nature,''), date_annonce, id, "
        "       payload->>'url_complete' AS url, "
        "       COALESCE(payload->>'listeprecedentproprietaire','') || ' ' || "
        "       COALESCE(payload->>'listeprecedentexploitant','') AS cedants, "
        "       payload->>'registre' AS registre "
        "FROM bodacc_annonces_owner ORDER BY siren, date_annonce")).all()
    out: dict[str, list[dict]] = {}
    for r in rows:
        out.setdefault(r[0], []).append({
            "famille": r[1], "nature": r[2].lower(), "date": r[3],
            "annonce_id": r[4].split(":")[0], "url": r[5], "cedants": r[6] or "",
            "registre": r[7] or ""})
    return out


def _load_friches(session: Session) -> dict[str, dict]:
    """idu → friche (rattachement EXACT refcad ∪ intersection géométrique)."""
    out: dict[str, dict] = {}
    for idu, nom, sid in session.execute(text(
            "SELECT r.value, f.attrs->>'site_nom', f.attrs->>'site_id' "
            "FROM spatial_layers f, jsonb_array_elements_text(f.attrs->'refcad') r "
            "WHERE f.kind='friche' AND f.attrs ? 'refcad'")).all():
        out.setdefault(idu, {"nom": nom, "site_id": sid})
    for idu, nom, sid in session.execute(text(
            "SELECT DISTINCT ON (p.idu) p.idu, f.attrs->>'site_nom', f.attrs->>'site_id' "
            "FROM parcels p JOIN spatial_layers f "
            "  ON f.kind='friche' AND ST_Intersects(f.geom_2975, p.geom_2975) "
            "ORDER BY p.idu")).all():
        out.setdefault(idu, {"nom": nom, "site_id": sid})
    return out


def _load_dvf(session: Session) -> dict[str, dict]:
    """idu → dernière mutation observée {date, nature, valeur} (fenêtre 2021-2025)."""
    rows = session.execute(text(
        "SELECT DISTINCT ON (id_parcelle) id_parcelle, date_mutation, nature_mutation, "
        "       valeur_fonciere, id_mutation "
        "FROM dvf_mutations_parcelle WHERE date_mutation IS NOT NULL "
        "ORDER BY id_parcelle, date_mutation DESC")).all()
    return {r[0]: {"date": r[1], "nature": r[2], "valeur": r[3], "id_mutation": r[4]}
            for r in rows}


def _load_dpe(session: Session) -> dict[str, dict]:
    rows = session.execute(text(
        "SELECT parcelle_idu, count(*) FILTER (WHERE etiquette_dpe='G') AS g, "
        "       count(*) FILTER (WHERE etiquette_dpe='F') AS f, "
        "       max(date_etablissement) AS d, min(numero_dpe) AS num "
        "FROM dpe_records WHERE parcelle_idu IS NOT NULL AND etiquette_dpe IN ('F','G') "
        "GROUP BY parcelle_idu")).all()
    return {r[0]: {"g": r[1], "f": r[2], "date": r[3], "numero": r[4]} for r in rows}


def _load_nu_parcelles(session: Session, idus: list[str]) -> set[str]:
    """Parcelles « terrain nu » (ratio bâti < 5 %, aligné bati.py) parmi les candidates."""
    nu: set[str] = set()
    for k in range(0, len(idus), 5000):
        chunk = idus[k:k + 5000]
        rows = session.execute(text(
            "SELECT p.idu, COALESCE(LEAST(1.0, "
            "  (SELECT SUM(ST_Area(ST_Intersection(b.geom_2975, p.geom_2975))) "
            "   FROM spatial_layers b "
            "   WHERE b.kind='batiment' AND ST_Intersects(b.geom_2975, p.geom_2975)) "
            "  / NULLIF(ST_Area(p.geom_2975), 0)), 0) AS ratio "
            "FROM parcels p WHERE p.idu = ANY(:idus)"), {"idus": chunk}).all()
        nu.update(idu for idu, ratio in rows if (ratio or 0.0) < C.NU_RATIO_MAX)
    return nu


# ─────────────────────────── matching & typage (§4.2, §4.3) ───────────────────────────

_BAILLEUR_RX = re.compile(C.BAILLEUR_DENOM_PATTERN)


def resolve_owner(link: dict, lookups: dict[str, dict]) -> dict:
    """Un lien DGFiP → {siren, confiance, ambiguous_candidats}. §4.2."""
    if link["siren"]:
        return {"siren": link["siren"], "confiance": C.CONF_SIREN_DIRECT, "candidats": None}
    norm = normalize_denomination(link["denomination"])
    lk = lookups.get(norm)
    if lk and lk["status"] == "found" and lk["siren"]:
        return {"siren": lk["siren"], "confiance": C.CONF_DENOMINATION, "candidats": None}
    if lk and lk["status"] == "ambiguous":
        return {"siren": None, "confiance": None, "candidats": lk["candidats"]}
    return {"siren": None, "confiance": None, "candidats": None}


def classify_owner(link: dict, siren: str | None, fiche: dict | None) -> str:
    """owner_type Score V (§4.3) : public | bailleur | copro | pm."""
    groupe = link["groupe"]
    mapped = C.DGFIP_GROUPE_OWNER_TYPE.get(groupe) if groupe is not None else None
    denom_norm = normalize_denomination(link["denomination"])
    if siren in C.BAILLEURS_SOCIAUX_SIREN or _BAILLEUR_RX.search(denom_norm or ""):
        return "bailleur"
    if mapped:
        return mapped
    nat = str((fiche or {}).get("nature_juridique") or "")
    if nat.startswith("7"):        # catégories juridiques 7xxx = personne morale de droit public
        return "public"
    if nat == "9110" or "SYNDIC" in denom_norm and "COPROPRI" in denom_norm:
        return "copro"
    return "pm"


# ─────────────────────────── extracteurs de signaux ───────────────────────────

_RX_CLOTURE = re.compile(r"cl[oô]ture")
_RX_LJ = re.compile(r"liquidation judiciaire")
_RX_RJ = re.compile(r"redressement judiciaire")
_RX_SAUV = re.compile(r"sauvegarde")
_RX_PLAN = re.compile(r"plan de (redressement|sauvegarde|continuation)")


def famille_a(siren: str, annonces: list[dict], match: dict) -> list[dict]:
    """Candidats famille A (détresse juridique BODACC) — le MAX sera retenu."""
    cands: list[dict] = []
    pcl = [a for a in annonces if a["famille"] == "pcl"]

    def _after(kind_rx, ref_date) -> bool:
        return any(kind_rx.search(a["nature"]) and a["date"] and ref_date
                   and a["date"] > ref_date for a in pcl)

    lj_open = [a for a in pcl if _RX_LJ.search(a["nature"]) and not _RX_CLOTURE.search(a["nature"])]
    if lj_open:
        last = max(lj_open, key=lambda a: a["date"] or date.min)
        cloturee = _after(_RX_CLOTURE, last["date"])
        code = "BODACC_LJ_CLOT" if cloturee else "BODACC_LJ"
        cands.append(_signal(code, source=BODACC_SRC, ref=f"Avis n° {last['annonce_id']}",
                             url=last["url"], date_evenement=str(last["date"] or ""), match=match))
    rj_open = [a for a in pcl if _RX_RJ.search(a["nature"])
               and not _RX_CLOTURE.search(a["nature"]) and not _RX_PLAN.search(a["nature"])]
    if rj_open:
        last = max(rj_open, key=lambda a: a["date"] or date.min)
        if not (_after(_RX_CLOTURE, last["date"]) or _after(_RX_PLAN, last["date"])
                or _after(_RX_LJ, last["date"])):
            cands.append(_signal("BODACC_RJ", source=BODACC_SRC,
                                 ref=f"Avis n° {last['annonce_id']}", url=last["url"],
                                 date_evenement=str(last["date"] or ""), match=match))
    sv_open = [a for a in pcl if _RX_SAUV.search(a["nature"])
               and not _RX_CLOTURE.search(a["nature"]) and not _RX_PLAN.search(a["nature"])]
    if sv_open:
        last = max(sv_open, key=lambda a: a["date"] or date.min)
        if not (_after(_RX_CLOTURE, last["date"]) or _after(_RX_PLAN, last["date"])):
            cands.append(_signal("BODACC_SAUVEGARDE", source=BODACC_SRC,
                                 ref=f"Avis n° {last['annonce_id']}", url=last["url"],
                                 date_evenement=str(last["date"] or ""), match=match))
    rads = [a for a in annonces if a["famille"] == "radiation" and a["date"]
            and a["date"] >= _months_ago(C.RADIATION_WINDOW_MONTHS)]
    if rads:
        last = max(rads, key=lambda a: a["date"])
        cands.append(_signal("BODACC_RADIATION", source=BODACC_SRC,
                             ref=f"Avis n° {last['annonce_id']}", url=last["url"],
                             date_evenement=str(last["date"]), match=match))
    ventes = [a for a in annonces if a["famille"] == "vente_cession" and a["date"]
              and a["date"] >= _months_ago(C.CESSION_FONDS_WINDOW_MONTHS)]
    for a in ventes:
        # `registre` duplique chaque SIREN (formaté + brut) → set pour compter les entités.
        seul = len(set(re.findall(r"\d{9}", re.sub(r"\s", "", a["registre"])))) <= 1
        cedant = siren in re.sub(r"\s", "", a["cedants"])
        if cedant or seul:
            cands.append(_signal("BODACC_CESSION_FONDS", source=BODACC_SRC,
                                 ref=f"Avis n° {a['annonce_id']}", url=a["url"],
                                 date_evenement=str(a["date"]), match=match))
            break
    return cands


def famille_b(siren: str, fiche: dict | None, age: int | None, forme_dgfip: str,
              match: dict, today: date) -> list[dict]:
    """Candidats famille B (cycle de vie propriétaire)."""
    cands: list[dict] = []
    if fiche and fiche.get("etat_administratif") == "C":
        cands.append(_signal("RNE_CESSATION", source=RE_SRC,
                             ref=f"SIREN {siren} — état administratif « cessée »",
                             url=f"https://annuaire-entreprises.data.gouv.fr/entreprise/{siren}",
                             date_evenement=fiche.get("date_fermeture"), match=match))
    if age is not None:
        code = ("RNE_DIRIGEANT_75" if age >= 75 else
                "RNE_DIRIGEANT_70" if age >= 70 else
                "RNE_DIRIGEANT_65" if age >= 65 else None)
        if code:
            cands.append(_signal(code, source=RNE_SRC,
                                 ref=f"Aîné des dirigeants personnes physiques : {age} ans",
                                 url=f"https://data.inpi.fr/entreprises/{siren}", match=match))
    est_sci = "SCI" in forme_dgfip.upper() or str((fiche or {}).get("nature_juridique")) == "6540"
    if est_sci and fiche and fiche.get("date_creation"):
        try:
            creation = date.fromisoformat(fiche["date_creation"])
        except ValueError:
            creation = None
        maj = (fiche.get("date_mise_a_jour_rne") or "")[:10]
        try:
            maj_d = date.fromisoformat(maj) if maj else None
        except ValueError:
            maj_d = None
        vieille = creation and creation <= today.replace(year=today.year - C.SCI_DORMANTE_AGE_ANS)
        inactive = maj_d is None or maj_d <= today.replace(year=today.year - C.SCI_DORMANTE_INACTIVITE_ANS)
        if vieille and inactive:
            cands.append(_signal("RNE_SCI_DORMANTE", source=RE_SRC,
                                 ref=f"SCI créée le {creation}, aucune mise à jour RNE récente",
                                 url=f"https://data.inpi.fr/entreprises/{siren}", match=match))
    return cands


def famille_c(idu: str, fiche: dict | None, match: dict) -> list[dict]:
    """Candidats famille C (détachement géographique du siège)."""
    if not fiche:
        return []
    siege = fiche.get("siege") or {}
    dept, commune = siege.get("departement"), siege.get("commune_insee")
    adresse = siege.get("adresse") or siege.get("libelle_commune") or "?"
    if siege.get("code_pays_etranger") or (dept and dept != "974"):
        return [_signal("GEO_HORS_ILE", source=RE_SRC, ref=f"Siège : {adresse}", match=match)]
    if commune and commune != idu[:5]:
        return [_signal("GEO_AUTRE_COMMUNE", source=RE_SRC, ref=f"Siège : {adresse}", match=match)]
    return []


# ─────────────────────────── moteur ───────────────────────────

def _tenure_qualifiee(cands: list[dict]) -> bool:
    """v1.1 : la tenure OBS5 ne compte que combinée à un signal A/B/C, FRICHE ou DPE (famille E).
    NU_PM_HORS_IMMO ne qualifie pas (deux signaux de dormance passive ne se valident pas entre eux)."""
    return any(s["famille"] in C.TENURE_QUALIFYING_FAMILIES
               or s["code"] in C.TENURE_QUALIFYING_CODES for s in cands)


def _retain(cands: list[dict], factor_families: set[str] | None) -> tuple[list[dict], int]:
    """Applique MAX (A/B/C/E) ou SOMME plafonnée (D) + facteur fallback ; retourne
    (signaux retenus toutes familles, total points)."""
    retained: list[dict] = []
    total = 0
    by_fam: dict[str, list[dict]] = {}
    for s in cands:
        by_fam.setdefault(s["famille"], []).append(s)
    for fam, sigs in by_fam.items():
        cap = C.FAMILY_CAPS[fam]
        if factor_families and fam in factor_families:
            for s in sigs:
                s["points"] = round(s["points"] * C.FALLBACK_FAMILY_FACTOR)
        if fam in C.SUM_FAMILIES:
            sigs = sorted(sigs, key=lambda s: -s["points"])
            fam_total = 0
            for s in sigs:
                pts = min(s["points"], cap - fam_total)
                if pts <= 0:
                    break
                s["points"] = pts
                retained.append(s)
                fam_total += pts
            total += fam_total
        else:
            best = max(sigs, key=lambda s: s["points"])
            best["points"] = min(best["points"], cap)
            retained.append(best)
            total += best["points"]
    return retained, total


def compute_all(session: Session, limit: int | None = None, log=print) -> dict:
    """Batch complet : calcule V pour TOUTES les parcelles → parcel_v_score (reconstruite)."""
    today = _today()
    log("Score V — précalculs…")
    links = {lk["idu"]: lk for lk in _load_owner_links(session)}
    lookups = _load_denom_lookups(session)
    fiches = _load_enrichments(session)
    ages = _load_dirigeant_ages(session)
    bodacc = _load_bodacc(session)
    friches = _load_friches(session)
    dvf = _load_dvf(session)
    dpe = _load_dpe(session)
    log(f"  liens PM {len(links)}, fiches {len(fiches)}, âges {len(ages)}, "
        f"bodacc sirens {len(bodacc)}, friches {len(friches)}, dvf {len(dvf)}, dpe {len(dpe)}")

    # Review queue (matchs ambigus) — reconstruite (idempotent).
    session.execute(text("DELETE FROM matching_review_queue"))
    n_review = 0

    # Pré-résolution des propriétaires (owner_type, siren, confiance) par idu PM.
    owners: dict[str, dict] = {}
    for idu, lk in links.items():
        res = resolve_owner(lk, lookups)
        fiche = fiches.get(res["siren"]) if res["siren"] else None
        otype = classify_owner(lk, res["siren"], fiche)
        owners[idu] = {**res, "owner_type": otype, "denomination": lk["denomination"],
                       "forme": lk["forme"]}
        if res["candidats"]:
            session.execute(text(
                "INSERT INTO matching_review_queue (parcelle_id, denomination, candidats) "
                "VALUES (:idu, :denom, CAST(:cands AS jsonb))"),
                {"idu": idu, "denom": lk["denomination"],
                 "cands": json.dumps(res["candidats"], ensure_ascii=False)})
            n_review += 1

    # Terrain nu : seulement pour les parcelles PM matchées dont le NAF est HORS immo/construction.
    nu_candidates = []
    for idu, ow in owners.items():
        if ow["owner_type"] != "pm" or not ow["siren"]:
            continue
        fiche = fiches.get(ow["siren"])
        naf = (fiche or {}).get("activite_principale") or ""
        if naf and not naf.startswith(C.NAF_IMMO_PREFIXES):
            nu_candidates.append(idu)
    log(f"  terrain nu : {len(nu_candidates)} candidates (PM hors NAF immo/construction)…")
    nu = _load_nu_parcelles(session, nu_candidates)
    log(f"  terrain nu : {len(nu)} parcelles nues")

    parcels = session.execute(text("SELECT idu FROM parcels ORDER BY idu")).all()
    if limit:
        parcels = parcels[:limit]
    log(f"Score V — assemblage {len(parcels)} parcelles…")

    achat_recent_seuil = _months_ago(C.ACHAT_RECENT_WINDOW_MONTHS)
    rows: list[tuple] = []
    counts = {"full": 0, "partial": 0, "na": 0, "review": n_review,
              "direct": 0, "fallback": 0}

    for (idu,) in parcels:
        ow = owners.get(idu)
        otype = ow["owner_type"] if ow else "pp"
        siren = ow["siren"] if ow else None
        denom = (ow["denomination"] or None) if ow else None
        conf = ow["confiance"] if ow else None

        if otype in ("public", "bailleur"):
            # D4 : V = NULL + badge. Aucun signal calculé.
            rows.append((idu, None, "na", "full", conf, otype, siren, denom, "[]"))
            counts["na"] += 1
            continue

        cands: list[dict] = []
        matched = bool(siren and conf)
        factor = (C.FALLBACK_AFFECTED_FAMILIES
                  if (matched and conf == C.CONF_DENOMINATION) else None)
        if matched:
            match = {"type": "siren" if conf == C.CONF_SIREN_DIRECT else "denomination",
                     "valeur": siren, "confiance": conf}
            fiche = fiches.get(siren)
            a_cands = famille_a(siren, bodacc.get(siren, []), match)
            cands += a_cands
            age = ages.get(siren)
            if age is None and fiche:
                age = _age_from_enrichment(fiche, today)
            b_cands = famille_b(siren, fiche, age, ow["forme"], match, today)
            # Dédup D6 : radiation (A) retenue == cessation (B) → même événement, deux sources.
            a_ret = max(a_cands, key=lambda s: s["points"], default=None)
            if a_ret and a_ret["code"] == "BODACC_RADIATION":
                b_cands = [s for s in b_cands if s["code"] != "RNE_CESSATION"]
            cands += b_cands
            cands += famille_c(idu, fiche, match)

        pmatch = {"type": "parcelle", "valeur": idu, "confiance": 1.0}
        fr = friches.get(idu)
        if fr:
            cands.append(_signal("FRICHE", source="Cartofriches (Cerema)",
                                 ref=fr["nom"] or f"Site {fr['site_id']}",
                                 url=CARTOFRICHES_URL, match=pmatch))
        if idu in nu:
            cands.append(_signal("NU_PM_HORS_IMMO", source="BD TOPO IGN + recherche-entreprises",
                                 ref="Parcelle nue, NAF propriétaire hors construction/immobilier",
                                 match=pmatch))
        d = dpe.get(idu)
        if d:
            code = "DPE_G_MULTI" if d["g"] >= 2 else "DPE_G" if d["g"] == 1 else "DPE_F"
            cands.append(_signal(code, source="ADEME (DPE logements existants)",
                                 ref=f"DPE n° {d['numero']}" + (f" (+{d['g'] + d['f'] - 1})"
                                                                if d["g"] + d["f"] > 1 else ""),
                                 date_evenement=str(d["date"] or ""), match=pmatch))
        # v1.1 : tenure CONDITIONNELLE, évaluée APRÈS la collecte des autres signaux — seule,
        # la détention longue est du bruit (backtest v1 : 0.89× sur 81k parcelles) ; combinée
        # (A/B/C, friche, DPE), elle raconte la dormance/succession.
        mut = dvf.get(idu)
        if mut is None and _tenure_qualifiee(cands):
            cands.append(_signal("DVF_TENURE_OBS5", source="DVF (géo-DVF)",
                                 ref="Aucune mutation 2021-2025 (fenêtre observable)",
                                 match=pmatch))

        retained, total = _retain(cands, factor)
        # v1.1 : malus neutralisé (constante à 0) → plus émis ; le garde ci-dessous conserve le
        # circuit si un futur re-calibrage lui redonne un poids.
        if C.MALUS_ACHAT_RECENT[1] and mut and mut["date"] and mut["date"] >= achat_recent_seuil:
            code, pts, label = C.MALUS_ACHAT_RECENT
            retained.append({
                "code": code, "famille": "malus", "label": label, "points": pts,
                "source": "DVF (géo-DVF)", "ref": f"Mutation {mut['nature'] or ''} du {mut['date']}",
                "url": None, "date_evenement": str(mut["date"]), "match": pmatch})
            total += pts
        score = max(0, min(100, total))
        band = next(b for floor, b in C.V_BANDS if score >= floor)
        coverage = "full" if matched else "partial"
        confidence = conf if matched else 1.0
        counts[coverage] += 1
        if matched:
            counts["direct" if conf == C.CONF_SIREN_DIRECT else "fallback"] += 1
        rows.append((idu, score, band, coverage, confidence, otype, siren, denom,
                     json.dumps(retained, ensure_ascii=False)))

    log("Score V — écriture parcel_v_score (COPY)…")
    session.execute(text("DELETE FROM parcel_v_score"))
    session.commit()
    raw = session.connection().connection.driver_connection
    now = datetime.now(timezone.utc).isoformat()
    with raw.cursor() as cur:
        with cur.copy(
            "COPY parcel_v_score (parcelle_id, v_score, v_band, v_coverage, v_confidence, "
            "owner_type, owner_siren, owner_denomination, signals, computed_at) FROM STDIN"
        ) as cp:
            for r in rows:
                cp.write_row((*r[:8], r[8], now))
    session.commit()
    counts["parcelles"] = len(rows)
    return counts
