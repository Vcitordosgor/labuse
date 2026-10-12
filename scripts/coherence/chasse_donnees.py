"""CHASSE-DONNEES-1 — le banc des écarts (docs/audit-2026-10/chasse-donnees-1/ECARTS.md).

Une garde par écart REPRODUCTIBLE de la chasse : aujourd'hui elle MORD (les écarts
sont ouverts) ; après CHASSE-DONNEES-FIX-1 elle doit passer au vert et devenir la
garde automatique. Lecture seule stricte (statement_timeout posé, aucun INSERT).

Usage :
    PYTHONPATH=src .venv/bin/python -m scripts.coherence.chasse_donnees \
        [--api http://127.0.0.1:8740]

Sortie : une ligne [OK]/[ECART]/[SKIP] par garde, bilan final, exit 1 si ECART.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import urllib.request

import psycopg

RACINE = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "scripts"))
from coherence.lib import _dsn_defaut  # noqa: E402 — même DSN que le banc COHERENCE-1

API = "http://127.0.0.1:8740"

# Témoins du lot B (docs/audit-2026-10/chasse-donnees-1/TEMOINS.md)
CW0658 = "97415000CW0658"   # contenance 25 633 ≠ dessin 27 156 (+5,9 %)
AV2114 = "97418000AV2114"   # disparue du cadastre 01/09/2026, encore en CRM
BZ0005 = "97415000BZ0005"   # bizone A 70 % / N 28 %
DR0219 = "97411000DR0219"   # SCI HOSSEIN ROY 414234526, cessée le 08/07/2026
IC0434 = "97411000IC0434"   # bâtie (3 bâtiments) mais taux_emprise_pct NULL → badge « Nu »


def _api(path: str):
    import time
    import urllib.error
    for essai in range(5):
        try:
            with urllib.request.urlopen(API + path, timeout=60) as r:
                corps = r.read()
            break
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and essai < 4:      # rate-limit local : on attend, on réessaie
                time.sleep(3 * (essai + 1))
                continue
            raise
    try:
        return json.loads(corps)
    except ValueError:
        return corps.decode("utf-8", "replace")


def _db():
    cx = psycopg.connect(_dsn_defaut())
    cx.read_only = True          # AVANT toute requête (sinon transaction déjà ouverte)
    cx.execute("SET statement_timeout = '20s'")
    return cx


def _manifest() -> dict:
    return json.loads((RACINE / "config" / "served_manifest.json").read_text())


def _chercher(obj, pred, chemin=""):
    """Balaie récursivement un JSON et rend [(chemin, valeur)] où pred(clé, valeur)."""
    trouvees = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{chemin}.{k}" if chemin else k
            if pred(k, v):
                trouvees.append((p, v))
            trouvees.extend(_chercher(v, pred, p))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            trouvees.extend(_chercher(v, pred, f"{chemin}[{i}]"))
    return trouvees


# ---------------------------------------------------------------- les gardes

def g01_tuile_surface():
    """C : la tuile bake parcels.surface_m2 (dessin) quand la fiche sert la contenance
    (tiles.py CREATE TABLE mvt_parcels vs builder fiche surface_terrain)."""
    fiche = _api(f"/parcels/{CW0658}")
    servi = _chercher(fiche, lambda k, v: k == "surface_terrain_m2" and isinstance(v, (int, float)))
    if not servi:
        return "SKIP", "fiche sans surface_terrain_m2"
    with _db() as cx:
        tuile = cx.execute(
            "SELECT round(surface_m2) FROM mvt_parcels WHERE idu = %s", (CW0658,)).fetchone()
    if tuile is None:
        return "SKIP", "CW0658 absente de mvt_parcels"
    f, t = round(servi[0][1]), int(tuile[0])
    return ("OK", f"fiche=tuile={f}") if abs(f - t) <= 1 else \
        ("ECART", f"fiche {f} m² (contenance) vs tuile {t} m² (dessin)")


def g02_export_surface():
    """C : l'export md/html imprime le dessin brut comme « Surface » (app.py export)."""
    texte = str(_api(f"/parcels/{CW0658}/export"))
    if "25633" in texte or "25 633" in texte:
        return "OK", "export sert la contenance 25 633"
    if "27156" in texte or "27 156" in texte:
        return "ECART", "export sert le dessin 27 156 m², fiche = contenance 25 633"
    return "SKIP", "aucune des deux surfaces repérée dans l'export"


def g03_export_cascade():
    """C : l'export lit dryrun_cascade_results au run SCORING (0 ligne) au lieu du run
    cascade → « Ont répondu : — » alors que la fiche a une cascade peuplée."""
    texte = str(_api(f"/parcels/{CW0658}/export")).replace("*", "")
    if "Ont répondu : —" in texte or "Ont répondu: —" in texte or "Ont répondu :  —" in texte:
        return "ECART", "export « Ont répondu : — » (cascade vide, mauvais run)"
    if "Ont répondu" in texte:
        return "OK", "export sert une cascade peuplée"
    return "SKIP", "section cascade introuvable dans l'export"


def g04_export_disparue():
    """C : la fiche d'une parcelle disparue porte la mention, l'export l'ignore."""
    fiche = json.dumps(_api(f"/parcels/{AV2114}"), ensure_ascii=False).lower()
    if "disparu" not in fiche:
        return "SKIP", "la fiche ne mentionne plus la disparition (recadastrage ?)"
    texte = str(_api(f"/parcels/{AV2114}/export")).lower()
    return ("OK", "export mentionne la disparition") if "disparu" in texte else \
        ("ECART", "fiche dit « disparue », export muet")


def g05_partner_statut():
    """C (C-11) : /api/v1/parcels joignait parcel_p_score_v2 sur runs.cascade() (q_v18_sources,
    0 ligne) au lieu du run SCORING → statut null partout. Après FIX-1 la jointure est au run
    scoring : on teste la SORTIE RÉELLE de l'API (statut non-null servi)."""
    rep = _api("/api/v1/parcels?key=demo-labuse-partner-key&commune=Cilaos&limit=50")
    if not isinstance(rep, dict):
        return "SKIP", "endpoint partenaire indisponible"
    items = rep.get("items") or []
    if not items:
        return "SKIP", "aucun item partenaire (commune vide ?)"
    statuts = [it.get("statut") for it in items]
    non_null = [s for s in statuts if s is not None]
    return ("OK", f"{len(non_null)}/{len(items)} items avec statut servi") if non_null else \
        ("ECART", f"statut null sur {len(items)}/{len(items)} items (jointure au mauvais run)")


def g06_courrier_zone():
    """C : le Courrier lit parcel_zone_plu.zone_lib en direct (1re ligne) quand la fiche
    sert la zone DOMINANTE — divergence sur bizone (courrier_compose._synthese)."""
    fiche = _api(f"/parcels/{BZ0005}")
    dom = _chercher(fiche, lambda k, v: k in ("zone_dominante", "zone") and isinstance(v, str))
    if not dom:
        return "SKIP", "fiche sans zone_dominante"
    zone_fiche = dom[0][1]
    with _db() as cx:
        brut = cx.execute(
            "SELECT zone_lib FROM parcel_zone_plu WHERE idu = %s LIMIT 1", (BZ0005,)).fetchone()
    if brut is None:
        return "SKIP", "BZ0005 sans ligne parcel_zone_plu"
    return ("OK", f"zone unique « {zone_fiche} »") if brut[0] == zone_fiche else \
        ("ECART", f"lecture directe courrier « {brut[0]} » vs fiche dominante « {zone_fiche} »")


def g07_compteurs_commune():
    """C (invariant qui TIENT) : /filtre compte == len(idus) == /stats, 3 communes."""
    run = _manifest()["scoring_run"]
    ecarts = []
    for insee in ("97411", "97415", "97416"):
        f = _api(f"/filtre?source={run}&commune={insee}&idus=1&limit=0")
        compte = f.get("compte")
        idus = f.get("idus") or []
        tronque = f.get("idus_tronque")
        s = _api(f"/stats?source={run}&commune={insee}")
        total_stats = (_chercher(s, lambda k, v: k in ("total", "n", "compte")
                                 and isinstance(v, int)) or [(None, None)])[0][1]
        if not tronque and compte != len(idus):
            ecarts.append(f"{insee}: compte {compte} ≠ idus {len(idus)}")
        if total_stats is not None and compte != total_stats:
            ecarts.append(f"{insee}: filtre {compte} ≠ stats {total_stats}")
    return ("OK", "compte = idus = stats sur 3 communes") if not ecarts else \
        ("ECART", " ; ".join(ecarts))


def g08_accueil_totaux():
    """C : /accueil/chiffres (run servi, 433 229) vs /accueil/fraicheur (parcs bruts,
    434 582 — disparues incluses) sur le même écran (accueil.py)."""
    chiffres = _api("/accueil/chiffres")
    parcelles = (_chercher(chiffres, lambda k, v: k == "parcelles" and isinstance(v, int))
                 or [(None, None)])[0][1]
    if parcelles is None:
        return "SKIP", "chiffres sans champ parcelles"
    fraicheur = _api("/accueil/fraicheur")
    gros = [v for _, v in _chercher(fraicheur, lambda k, v: isinstance(v, int) and v > 100_000)]
    if not gros:
        return "SKIP", "fraicheur sans compteur de parcelles"
    autres = sorted({v for v in gros if v != parcelles})
    return ("OK", f"accueil cohérent ({parcelles})") if not autres else \
        ("ECART", f"chiffres {parcelles} vs fraicheur {autres} (disparues non filtrées)")


def g09_prix_ancien_unique():
    """C (C-20) : deux formules de €/m² ancien étaient servies — fiche commune/baromètre
    (moteurs.prix_ancien_communes : Vente stricte, [100,12000], ≥100 ventes) vs kanban/repères
    projets (toutes natures VEFA, [200,8000], sans seuil). Après FIX-1, le kanban/les repères LISENT
    la source UNIQUE. On teste la SORTIE SERVIE : /projets/reperes.dvf_median_eur_m2 == baromètre.
    La formule de référence reste calculée ici pour prouver que la VALEUR SERVIE la suit."""
    with _db() as cx:
        bar = {c: int(v) for c, v in cx.execute(
            "SELECT commune, round(percentile_cont(0.5) WITHIN GROUP ("
            "  ORDER BY valeur_fonciere / NULLIF(surface_reelle_bati,0))) "
            "FROM dvf_mutations WHERE nature_mutation = 'Vente' "
            "  AND valeur_fonciere > 1000 AND surface_reelle_bati > 0 "
            "  AND valeur_fonciere / surface_reelle_bati BETWEEN 100 AND 12000 "
            "GROUP BY commune HAVING count(*) >= 100").fetchall() if v}
    rep = _api("/projets/reperes?dimension=commune")
    options = rep.get("options") if isinstance(rep, dict) else None
    if not options:
        return "SKIP", "repères projets indisponibles"
    servi = {o["key"]: o.get("dvf_median_eur_m2") for o in options if o.get("dvf_median_eur_m2")}
    communs = sorted(set(bar) & set(servi))
    if not communs:
        return "SKIP", "aucune commune comparable servie"
    divergents = [f"{c}: baromètre {bar[c]} vs projets {servi[c]}"
                  for c in communs if abs(bar[c] - servi[c]) / bar[c] > 0.02]
    return ("OK", f"projets = baromètre sur {len(communs)} communes (source unique)") if not divergents else \
        ("ECART", f"{len(divergents)}/{len(communs)} communes divergent — " + " ; ".join(divergents[:3]))


def g10_sirene_etat():
    """D : SCI 414234526 servie « active » alors que l'unité légale est CESSÉE le
    08/07/2026 (état jamais raccordé au stock géolocalisé)."""
    fiche = json.dumps(_api(f"/parcels/{DR0219}"))
    if "414234526" not in fiche:
        return "SKIP", "SCI 414234526 absente de la fiche DR0219"
    actifs = _chercher(json.loads(fiche), lambda k, v: k in ("actif", "active") and v is True)
    return ("OK", "plus d'« actif » servi pour la SCI cessée") if not actifs else \
        ("ECART", f"SCI cessée 08/07/2026 servie active ({actifs[0][0]})")


def g11_bodacc_fraicheur():
    """D (D-47/D-51) : la fiche lisait bodacc_annonces_owner (gelée au 09/07) → état société en
    retard de 22 mois (SCI FREYNEAU 820034122 : « dernière annonce 2024-10-08 »). Après FIX-1 la
    fiche lit bodacc_procedures (vivante). On teste la SORTIE SERVIE : la date d'annonce servie =
    la plus récente de bodacc_procedures (2026-08-21), pas la date figée de la table owner."""
    with _db() as cx:
        proc = cx.execute(
            "SELECT max(date_annonce)::text FROM bodacc_procedures WHERE siren = '820034122'").fetchone()[0]
    if proc is None:
        return "SKIP", "FREYNEAU absente de bodacc_procedures"
    fiche = json.dumps(_api("/parcels/97409000BO0383"), ensure_ascii=False)
    if "820034122" not in fiche:
        return "SKIP", "SCI FREYNEAU absente de la fiche BO0383"
    # la fiche doit servir la date VIVANTE (procedures), plus la date gelée 2024-10-08.
    if proc[:7] in fiche:
        return "OK", f"fiche sert l'annonce vivante ({proc}) de bodacc_procedures"
    if "2024-10-08" in fiche or "2024" in json.dumps(_api("/parcels/97409000BO0383")).split("etat_societe")[-1][:200]:
        return "ECART", "fiche sert encore la date gelée (bodacc_annonces_owner)"
    return "ECART", f"fiche ne porte pas l'annonce vivante {proc}"


def g12_zero_menteur_nu():
    """E (E-67/68) : taux_emprise_pct NULL (jamais mesuré, cause écarte la parcelle) était rendu 0
    → badge « Nu » + filtre « Terrain nu » sur une parcelle bâtie (IC0434). Après FIX-1, l'absence
    de mesure = 'non_mesure' (jamais 'nu'), et le filtre etat_sol=nu NE renvoie PLUS IC0434.
    On teste la SORTIE SERVIE : le CASE _ETAT_BIEN_SQL + le prédicat du filtre."""
    with _db() as cx:
        taux = cx.execute(
            "SELECT r.taux_emprise_pct FROM parcel_residuel r "
            "JOIN parcels p ON p.id = r.parcel_id WHERE p.idu = %s", (IC0434,)).fetchone()
        if taux is None:
            return "SKIP", "IC0434 absente du résiduel"
        if taux[0] is not None:
            return "SKIP", f"taux_emprise désormais mesuré ({taux[0]}) — témoin obsolète"
        # l'état servi (même CASE que _ETAT_BIEN_SQL) : taux NULL → 'non_mesure', plus 'nu'.
        etat = cx.execute(
            "SELECT CASE WHEN r.taux_emprise_pct IS NULL THEN 'non_mesure' "
            "WHEN r.taux_emprise_pct < 5 THEN 'nu' ELSE 'bati' END "
            "FROM parcel_residuel r JOIN parcels p ON p.id = r.parcel_id "
            "WHERE p.idu = %s", (IC0434,)).fetchone()[0]
        # le filtre « Terrain nu » (etat_sol=nu) exige désormais taux NON NULL < 5 → IC0434 exclue.
        nu_match = cx.execute(
            "SELECT EXISTS (SELECT 1 FROM parcel_residuel rs JOIN parcels p ON p.id = rs.parcel_id "
            "WHERE p.idu = %s AND rs.taux_emprise_pct IS NOT NULL AND rs.taux_emprise_pct < 5)",
            (IC0434,)).fetchone()[0]
    if etat == "nu" or nu_match:
        return "ECART", f"IC0434 rendue « nu » (etat={etat}, filtre_nu={nu_match}) alors que taux non mesuré"
    return "OK", f"taux non mesuré → etat='{etat}', hors filtre « Terrain nu »"


def g13_cloche_fraicheur():
    """C : la cloche (event_log) n'a plus bougé depuis le 21/08 alors que le run servi
    a été promu le 11/10 — detect_events jamais rejoué."""
    run = _manifest()["scoring_run"]
    with _db() as cx:
        bascule = cx.execute(
            "SELECT max(ts) FROM event_log WHERE run_to = %s", (run,)).fetchone()[0]
        derniere = cx.execute(
            "SELECT run_to, max(ts) FROM event_log WHERE run_to IS NOT NULL "
            "GROUP BY run_to ORDER BY max(ts) DESC LIMIT 1").fetchone()
    if bascule is not None:
        return "OK", f"cloche rejouée pour {run} ({bascule:%d/%m})"
    detail = f"dernière bascule cloche : {derniere[0]} du {derniere[1]:%d/%m/%Y}" if derniere \
        else "aucun événement de bascule en cloche"
    return "ECART", f"detect_events jamais rejoué pour {run} — {detail}"


def g15_courrier_surface():
    """Lot 1 (C-04/05) : le Courrier étiquetait « surface cadastrale » un dessin brut (27 156 m²
    pour CW0658 dont l'acte dit 25 633). Après FIX-1 le courrier sert la contenance."""
    import urllib.request
    import urllib.error
    req = urllib.request.Request(
        API + "/courrier/composer", data=json.dumps({"idu": CW0658}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            doc = json.loads(r.read())
    except (urllib.error.HTTPError, urllib.error.URLError, ValueError) as exc:
        return "SKIP", f"courrier indisponible ({type(exc).__name__})"
    texte = json.dumps(doc, ensure_ascii=False)
    if "27156" in texte.replace(" ", "") and "cadastrale" in texte:
        # le dessin 27 156 apparaît sous une étiquette « cadastrale »
        if "27156" in texte.replace(" ", "") and "25633" not in texte.replace(" ", ""):
            return "ECART", "courrier sert le dessin 27 156 m² (étiquette « cadastrale »)"
    if "25633" in texte.replace(" ", ""):
        return "OK", "courrier sert la contenance 25 633 m²"
    return "SKIP", "aucune des deux surfaces repérée dans le courrier"


def g16_disparue_documents():
    """Lot 2 (C-08) : une parcelle disparue du cadastre (AV2114) était composée comme vivante par
    le Courrier (« Surface cadastrale : 2 853 m², zone UB »). Après FIX-1 le courrier REFUSE."""
    import urllib.request
    import urllib.error
    fiche = json.dumps(_api(f"/parcels/{AV2114}"), ensure_ascii=False).lower()
    if "disparu" not in fiche:
        return "SKIP", "la fiche ne mentionne plus la disparition (recadastrage ?)"
    req = urllib.request.Request(
        API + "/courrier/composer", data=json.dumps({"idu": AV2114}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            doc = json.loads(r.read())
    except (urllib.error.HTTPError, urllib.error.URLError, ValueError) as exc:
        return "SKIP", f"courrier indisponible ({type(exc).__name__})"
    texte = json.dumps(doc, ensure_ascii=False).lower()
    if doc.get("bloque") and "disparu" in texte:
        return "OK", "courrier refuse une parcelle disparue"
    return "ECART", "courrier compose une parcelle disparue (pas de refus)"


def g17_comparatif_zone():
    """Lot 3 (C-06) : le Comparatif servait la sous-zone de CALCUL (Usdu 2,4 %) au lieu de la zone
    DOMINANTE de la fiche (A 70 %) sur la bizone BZ0005 → « Zone Usdu, constructible oui » à côté
    de « Zone A inconstructible ». Après FIX-1 : la dominante + parts, constructibilité cohérente."""
    rep = _api(f"/compare?idus=97415000BZ0007,{BZ0005}")
    if not isinstance(rep, dict):
        return "SKIP", "comparateur indisponible"
    row = next((p for p in (rep.get("parcels") or []) if p.get("idu") == BZ0005), None)
    if not row:
        return "SKIP", f"{BZ0005} absente du comparatif"
    zone = (row.get("zone") or "").upper()
    if zone.startswith("USDU"):
        return "ECART", f"comparatif sert la sous-zone de calcul « {row.get('zone')} » (pas la dominante)"
    if zone.startswith("A"):
        return "OK", f"comparatif sert la zone dominante « {row.get('zone')} » (constructible={row.get('zone_constructible')})"
    return "SKIP", f"zone comparatif inattendue « {row.get('zone')} »"


def g18_simulplu_non_calculable():
    """Lot 4 (E-83) : SimulPLU servait ratio 0.0 (percentile NULL) comme une estimation → « SDP
    estimée 0 m² » sur tout le listing. Après FIX-1 : calculable=False + ratio None quand aucune
    parcelle U comparable (Saint-Philippe Ub, RNU)."""
    rep = _api("/moteurs/simulplu?zone=Ub&commune=Saint-Philippe")
    if not isinstance(rep, dict):
        return "SKIP", "simulplu indisponible"
    if rep.get("ratio_analogie") == 0.0:
        return "ECART", "ratio_analogie servi 0.0 (absence présentée comme mesure)"
    if rep.get("calculable") is False and rep.get("ratio_analogie") is None:
        return "OK", "analogie non calculable servie comme telle (ratio None)"
    return "SKIP", f"corpus U présent (calculable={rep.get('calculable')}) — témoin obsolète"


def g19_catnat_source_vs_zero():
    """Lot 4 (E-82) : CatNat renvoyait disponible=False quand une commune avait 0 arrêté, confondu
    avec la source indisponible → front « aucun arrêté ». Après FIX-1 : source présente ⇒
    disponible=True (0 arrêté = vrai 0 mesuré), « disponible=False » réservé à la table absente."""
    fiche = _api(f"/parcels/{CW0658}")
    if not isinstance(fiche, dict):
        return "SKIP", "fiche indisponible"
    c = fiche.get("catnat")
    if not isinstance(c, dict):
        return "SKIP", "pas de bloc catnat"
    # la table existe (témoin à 23 arrêtés) → disponible doit être True (jamais False masquant un 0).
    if c.get("disponible") is True and (c.get("total") or 0) > 0:
        return "OK", f"source disponible, {c.get('total')} arrêtés (0 ne pourra plus être « indisponible »)"
    return "ECART", f"catnat disponible={c.get('disponible')} total={c.get('total')} (source présente)"


def g20_millesime_derive():
    """Lot 5 (D-54/D-57) : les millésimes servis sont DÉRIVÉS des tables, plus des littéraux figés.
    RPLS : l'année affichée (fiche commune) = l'année de rpls_commune.millesime. PM : le millésime
    servi (timeline) = max(parcelle_personne_morale.millesime)."""
    with _db() as cx:
        rpls_mill = cx.execute("SELECT max(millesime) FROM rpls_commune").fetchone()
        pm_mill = cx.execute("SELECT max(millesime) FROM parcelle_personne_morale").fetchone()
    annee_rpls = (rpls_mill[0] or "")[:4] if rpls_mill and rpls_mill[0] else None
    if not annee_rpls:
        return "SKIP", "rpls_commune sans millésime"
    fc = _api("/communes/Saint-Paul/contexte")
    servis = [v for _, v in _chercher(fc if isinstance(fc, dict) else {},
                                      lambda k, v: k == "millesime" and isinstance(v, str) and "RPLS" in v)]
    if not servis:
        return "SKIP", "millésime RPLS non trouvé dans le contexte commune"
    # aucun millésime RPLS servi ne doit contenir une AUTRE année que celle de la table.
    faux = [s for s in servis if annee_rpls not in s]
    return ("OK", f"RPLS servi dérivé de la table ({annee_rpls}) · PM max {pm_mill[0] if pm_mill else '—'}") \
        if not faux else ("ECART", f"millésime RPLS figé {faux} ≠ table {annee_rpls}")


def g21_regles_plu():
    """Lot 6 (D-48/50/52) : la fiche sert la règle PLU COMPLÈTE/EXACTE. Saint-Joseph U2 (BW2262) :
    la hauteur graduée est servie (exception) + le recul montre la formule « H/2 » (pas le seul
    plancher 3 m). L'Étang-Salé UC (AE1391) : le stationnement est le barème chiffré, plus « à vérifier »."""
    manques = []
    f1 = _api("/parcels/97412000BW2262")
    zones1 = (f1.get("reglement_plu") or {}).get("zones", []) if isinstance(f1, dict) else []
    rv1 = {rv["cle"]: rv for z in zones1 for rv in z.get("regles_valeurs", [])}
    h = rv1.get("hauteur") or {}
    if not any("gradu" in (e.get("texte") or "").lower() for e in h.get("exceptions", [])):
        manques.append("U2 hauteur sans gradation (D-48)")
    rl = rv1.get("recul_limites") or {}
    if "H/2" not in (rl.get("valeur") or ""):
        manques.append("U2 recul sans formule H/2 (D-50)")
    f2 = _api("/parcels/97404000AE1391")
    zones2 = (f2.get("reglement_plu") or {}).get("zones", []) if isinstance(f2, dict) else []
    stat = next((rv for z in zones2 for rv in z.get("regles_valeurs", []) if rv["cle"] == "stationnement"), {})
    if stat.get("etat") == "a_verifier" or "vérifier" in (stat.get("valeur") or ""):
        manques.append("UC stationnement « à vérifier » alors que le barème existe (D-52)")
    return ("OK", "règles PLU servies complètes (gradation + formule H/2 + barème stationnement)") \
        if not manques else ("ECART", " ; ".join(manques))


def g22_ventes_100m_nature():
    """Lot 7 (E-75) : « ventes < 100 m » comptait TOUTES les natures (échanges/adjudications) comme
    des ventes (AD0220 : « 1 vente » pour 1 échange). Après FIX-1 : nature ILIKE 'vente%'."""
    with _db() as cx:
        natures = cx.execute(
            "SELECT DISTINCT nature_mutation FROM dvf_mutations_parcelle m "
            "JOIN parcels dp ON dp.idu = m.id_parcelle "
            "JOIN parcels a ON a.idu = '97401000AD0220' "
            "WHERE m.date_mutation >= (now() - interval '36 months') AND m.id_parcelle <> '97401000AD0220' "
            "AND ST_DWithin(a.geom_2975, dp.geom_2975, 100)").fetchall()
    noms = {(n[0] or "").lower() for n in natures}
    f = _api("/parcels/97401000AD0220")
    vp = (f.get("voisinage_proche") or {}) if isinstance(f, dict) else {}
    n_servi = vp.get("ventes_dvf")
    # s'il n'y a QUE des non-ventes autour, le servi ne doit PAS afficher de vente (None/0).
    que_non_ventes = noms and not any(x.startswith("vente") for x in noms)
    if que_non_ventes and n_servi:
        return "ECART", f"{n_servi} « vente(s) » servie(s) alors que le voisinage ne porte que {noms}"
    return "OK", f"voisinage proche : natures {noms or '∅'}, ventes servies={n_servi}"


def g23_etude_zone_perimetre():
    """Lot 7 (E-69) : un rayon hors {0,5;1;2;5} km retombait sur l'isochrone mais le document
    affichait « Rayon N km ». Après FIX-1, le payload dit le périmètre RÉELLEMENT calculé."""
    import urllib.request
    import urllib.error
    req = urllib.request.Request(
        API + "/outils/etude-zone", data=json.dumps({"idu": CW0658, "rayon_km": 10}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            z = json.loads(r.read())
    except (urllib.error.HTTPError, urllib.error.URLError, ValueError) as exc:
        return "SKIP", f"étude-zone indisponible ({type(exc).__name__})"
    if z.get("entree") == "rayon" and z.get("rayon_km") == 10:
        return "SKIP", "rayon 10 km désormais accepté — témoin obsolète"
    if z.get("rayon_km") is None and z.get("isochrone_minutes"):
        return "OK", f"rayon 10 km non retenu → isochrone {z['isochrone_minutes']} min servie (périmètre honnête)"
    return "ECART", f"périmètre ambigu : entree={z.get('entree')} rayon_km={z.get('rayon_km')}"


def g24_ventes_12m_ancree():
    """Lot 7 (E-66) : « ventes / 12 mois » de l'Étude de zone était CALENDAIRE (now-12m) alors que
    DVF s'arrête fin 2025 → ~2,5 mois couverts (13 au lieu de 57). Après FIX-1 : fenêtre ancrée sur
    la dernière date de données (parasite D-65 exclu)."""
    import urllib.request
    import urllib.error
    req = urllib.request.Request(
        API + "/outils/etude-zone", data=json.dumps({"idu": CW0658, "rayon_km": 2}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            z = json.loads(r.read())
    except (urllib.error.HTTPError, urllib.error.URLError, ValueError) as exc:
        return "SKIP", f"étude-zone indisponible ({type(exc).__name__})"
    m = z.get("marche") or {}
    v = m.get("ventes_12m") or m.get("ventes")
    if v is None:
        return "SKIP", "ventes non servies"
    # la fenêtre calendaire donnait ~13 ; l'ancrée ~57. On exige nettement plus que le calendaire.
    return ("OK", f"fenêtre ancrée : {v} ventes (≫ 13 du calendaire)") if v >= 30 else \
        ("ECART", f"seulement {v} ventes — fenêtre probablement encore calendaire")


def g25_filtre_carte_page():
    """Lot 7 (C-12/C-29) : la liste d'IDU (ce que la CARTE peint) doit avoir le MÊME périmètre que
    la PAGE — hors étage 0 par défaut (C-12 : Le Port 205 écartées → idus=205 vs page=[]) et filtrée
    par bande/signal (C-29 : bande=A → toute la commune peinte). Après FIX-1 : idus = page."""
    # C-12 : commune 100 % écartée → idus (carte) vide comme la page
    f = _api("/filtre?source=%s&commune=Le+Port&surface_min=15&surface_max=19&limit=200&idus=1" % _manifest()["scoring_run"])
    if not isinstance(f, dict):
        return "SKIP", "filtre indisponible"
    page_n = len(f.get("page") or [])
    idus = f.get("idus")
    if idus is not None and len(idus) != page_n:
        return "ECART", f"C-12 : carte {len(idus)} ≠ page {page_n} (étage 0 peint par la carte seule)"
    # C-29 : bande=A → idus restreint à la bande, pas toute la commune
    fb = _api("/filtre?source=%s&commune=Saint-Andr%%C3%%A9&bande=A&idus=1&limit=0" % _manifest()["scoring_run"])
    if isinstance(fb, dict):
        bande_a = (fb.get("bandes") or {}).get("A")
        iv = fb.get("idus")
        if iv is not None and bande_a is not None and len(iv) != bande_a:
            return "ECART", f"C-29 : idus {len(iv)} ≠ bande A {bande_a} (bande non appliquée aux idus)"
    return "OK", f"carte = page (C-12 : idus={len(idus) if idus is not None else '—'}=page {page_n} ; C-29 : bande filtre les idus)"


def g14_digest_vs_cloche():
    """C (C-45) : le top digest est recalculé à l'ENVOI sur le run servi, quand la cloche relit
    event_log. Le symptôme de staleness était que la cloche vivait dans un AUTRE monde (dernière
    bascule q_v10) que le digest (q_v18). L'invariant SAIN n'est pas « les mêmes IDU » (le top =
    les plus chaudes, les bascules = celles qui ont CHANGÉ de tier : concepts distincts) mais « le
    MÊME monde » : la bascule cloche la plus récente porte sur le run servi (digest ⇄ cloche
    cohérents). Le recouvrement d'IDU, s'il existe, est un bonus."""
    run = _manifest()["scoring_run"]
    digest = _api("/events/digest")
    if not isinstance(digest, dict):
        return "SKIP", "digest non JSON"
    idus_digest = {v for _, v in _chercher(digest, lambda k, v: k == "idu" and isinstance(v, str))}
    if not idus_digest:
        return "SKIP", "digest sans IDU"
    with _db() as cx:
        dernier_run_to = cx.execute(
            "SELECT run_to FROM event_log WHERE kind = 'bascule' AND NOT demo AND run_to IS NOT NULL "
            "ORDER BY ts DESC LIMIT 1").fetchone()
        idus_cloche_run = {r[0] for r in cx.execute(
            "SELECT DISTINCT idu FROM event_log WHERE kind = 'bascule' AND run_to = %s "
            "AND idu IS NOT NULL", (run,)).fetchall()}
    if not dernier_run_to:
        return "ECART", "aucune bascule cloche — cloche muette"
    if dernier_run_to[0] != run:
        return "ECART", (f"cloche dans un autre monde : dernière bascule run_to={dernier_run_to[0]} "
                         f"≠ run servi {run}")
    commun = idus_digest & idus_cloche_run
    return "OK", (f"digest et cloche sur le même run servi {run} "
                  f"({len(idus_cloche_run)} bascules servies, {len(commun)} IDU communs au top)")


GARDES = [
    ("surface-tuile-vs-fiche", g01_tuile_surface),
    ("export-surface", g02_export_surface),
    ("export-cascade", g03_export_cascade),
    ("export-disparue", g04_export_disparue),
    ("partner-statut", g05_partner_statut),
    ("courrier-zone-bizone", g06_courrier_zone),
    ("compteurs-commune", g07_compteurs_commune),
    ("accueil-totaux", g08_accueil_totaux),
    ("prix-ancien-unique", g09_prix_ancien_unique),
    ("sirene-etat", g10_sirene_etat),
    ("bodacc-fraicheur", g11_bodacc_fraicheur),
    ("zero-menteur-nu", g12_zero_menteur_nu),
    ("cloche-fraicheur", g13_cloche_fraicheur),
    ("digest-vs-cloche", g14_digest_vs_cloche),
    ("courrier-surface", g15_courrier_surface),
    ("disparue-documents", g16_disparue_documents),
    ("comparatif-zone-dominante", g17_comparatif_zone),
    ("simulplu-non-calculable", g18_simulplu_non_calculable),
    ("catnat-source-vs-zero", g19_catnat_source_vs_zero),
    ("millesime-derive", g20_millesime_derive),
    ("regles-plu-completes", g21_regles_plu),
    ("ventes-100m-nature", g22_ventes_100m_nature),
    ("etude-zone-perimetre", g23_etude_zone_perimetre),
    ("ventes-12m-ancree", g24_ventes_12m_ancree),
    ("filtre-carte-page", g25_filtre_carte_page),
]


def main() -> int:
    global API
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--api", default=API)
    API = ap.parse_args().api
    bilan = {"OK": 0, "ECART": 0, "SKIP": 0}
    for nom, garde in GARDES:
        try:
            verdict, detail = garde()
        except Exception as exc:  # noqa: BLE001 — une garde qui plante ne tue pas le banc
            verdict, detail = "SKIP", f"erreur {type(exc).__name__}: {exc}"
        bilan[verdict] += 1
        print(f"[{verdict}] {nom} — {detail}")
    print(f"\nBilan : {bilan['OK']} OK · {bilan['ECART']} ECART · {bilan['SKIP']} SKIP "
          f"({len(GARDES)} gardes)")
    return 1 if bilan["ECART"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
