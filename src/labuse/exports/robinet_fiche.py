"""EXPORTS-REBRANCHEMENT-1 lot 1 — LE ROBINET FICHE : id du registre → valeur du payload
`/parcels/{idu}` (la MÊME fiche que l'écran). Remplace l'ancienne `collecte.py` : il n'existe
plus de collecte « parallèle » propre aux documents — la LISTE de ce qu'un document affiche
vient des déclarations (`declarations/fiche/`), et chaque valeur vient d'ICI, au même robinet
que l'écran. Un id sans extracteur n'est pas rendu (listé par le builder comme non câblé) ;
un extracteur qui rend None = donnée absente → le document dit la phrase d'absence DÉCLARÉE.

Règles : les extracteurs lisent la FICHE (payload), jamais la base — sauf `n_permis_proximite`
(même moteur `nearby_permits` que l'écran, compte live 500 m/24 mois). `None`/''/[]/{} = absent.
"""
from __future__ import annotations

from typing import Any, Callable

from ..registre.valeur import Valeur, valeurs_pour

EXTRACTEURS: dict[str, Callable[[Any, str, dict], Any]] = {}


def extracteur(*ids: str):
    def deco(fn: Callable[[Any, str, dict], Any]):
        for cid in ids:
            EXTRACTEURS[cid] = fn
        return fn
    return deco


def collecte(db, idu: str, ids: list[str], *, fiche: dict | None = None) -> dict[str, Valeur]:
    """{id → Valeur} pour les ids demandés qui ont un extracteur et une valeur servie.
    Même contrat que l'ancienne collecte (Financier/Apporteur la consomment aussi)."""
    f = fiche or {}
    brut: dict[str, Any] = {}
    for cid in ids:
        fn = EXTRACTEURS.get(cid)
        if fn is None:
            continue
        try:
            val = fn(db, idu, f)
        except Exception:  # noqa: BLE001 — un extracteur qui échoue OMET sa donnée, jamais un 500
            val = None
        if val is not None:
            brut[cid] = val
    return valeurs_pour(db, brut)


def _nz(v):
    """None / '' / [] / {} → None (donnée non servie) ; sinon la valeur."""
    return v if v not in (None, "", [], {}) else None


# ══ Identité ═══════════════════════════════════════════════════════════════════════════════

@extracteur("surface_parcelle_m2")
def _c_surface(db, idu, f):
    s = f.get("surface_m2")
    return round(float(s)) if s is not None else None


@extracteur("adresse_ban")
def _c_adresse(db, idu, f):
    return _nz(f.get("adresse"))


@extracteur("type_proprietaire")
def _c_proprietaire(db, idu, f):
    pm = f.get("proprietaire_moral")
    if not isinstance(pm, dict):
        return None
    denom, siren = pm.get("denomination"), pm.get("siren")
    if denom and siren:
        return f"Personne morale — {denom} (SIREN {siren})"
    if denom:
        return f"Personne morale — {denom}"
    return "Personne morale"


@extracteur("proprietaire_timeline_liste")
def _c_prop_histo(db, idu, f):
    h = f.get("proprietaire_historique") or {}
    return _nz(h.get("millesimes"))


@extracteur("pente_deg")
def _c_pente(db, idu, f):
    return _nz((f.get("terrain") or {}).get("pente_moy_deg"))


@extracteur("exposition_versant")
def _c_exposition(db, idu, f):
    t = f.get("terrain") or {}
    return _nz(t.get("exposition") or t.get("exposition_versant"))


@extracteur("prix_achat_historique_eur")
def _c_prix_achat(db, idu, f):
    # dernière mutation DVF SUR la parcelle (souvent absente : parcelle jamais mutée seule).
    m = (f.get("dvf_parcelle") or {}).get("derniere_mutation")
    return m if isinstance(m, dict) and m.get("valeur") else None


@extracteur("coproprietes_liste")
def _c_copro(db, idu, f):
    return _nz(f.get("coproprietes"))


@extracteur("filiation_parcelle")
def _c_filiation(db, idu, f):
    return _nz(f.get("filiation"))


@extracteur("historique_permis_liste")
def _c_permis_parcelle(db, idu, f):
    d = f.get("depots") or {}
    return _nz(d.get("parcelle"))


# ══ Urbanisme ══════════════════════════════════════════════════════════════════════════════

def _famille_zone(code: str) -> str | None:
    """U1a → U · AUx → AU · Nh → N · A → A."""
    c = (code or "").strip().upper()
    if c.startswith("AU"):
        return "AU"
    if c[:1] in ("U", "A", "N"):
        return c[:1]
    return None


@extracteur("zone_plu_famille")
def _c_zone_fam(db, idu, f):
    zones = (f.get("reglement_plu") or {}).get("zones") or []
    return _famille_zone(zones[0].get("zone")) if zones else None


@extracteur("reglement_plu_bloc")
def _c_reglement(db, idu, f):
    zones = (f.get("reglement_plu") or {}).get("zones") or []
    if not zones:
        return None
    z = dict(zones[0])   # y porter le drapeau Q12 (prescriptions non vérifiables sur la commune)
    z["_prescriptions_verifiables"] = f.get("prescriptions_verifiables", True)
    z["_prescriptions_motif"] = f.get("prescriptions_non_verifiables_motif")
    return z


@extracteur("er_emplacement_reserve")
def _c_er(db, idu, f):
    return _nz((f.get("dispositifs") or {}).get("er"))


@extracteur("ebc_classe")
def _c_ebc(db, idu, f):
    return _nz((f.get("dispositifs") or {}).get("ebc"))


@extracteur("dpu_perimetre")
def _c_dpu(db, idu, f):
    d = (f.get("dispositifs") or {}).get("dpu")
    return d if isinstance(d, dict) and d.get("etat") == "servi" else None


@extracteur("peb_zone")
def _c_peb(db, idu, f):
    d = (f.get("dispositifs") or {}).get("peb")
    if not isinstance(d, dict):
        return None
    return d if d.get("zone") and d.get("zone") != "hors" else None


@extracteur("dispositifs_parcelle")
def _c_dispositifs_sup(db, idu, f):
    # ER/EBC/DPU/PEB ont chacun leur ligne déclarée : cette ligne sert le RESTE du droit des
    # sols — les servitudes d'utilité publique (SUP) par catégorie.
    return _nz((f.get("dispositifs") or {}).get("sup"))


@extracteur("statut_plu")
def _c_plu_fraicheur(db, idu, f):
    return _nz(f.get("plu_fraicheur"))


@extracteur("sar_divergence")
def _c_sar(db, idu, f):
    ligne = next((l for l in (f.get("lines") or [])
                  if isinstance(l, dict) and l.get("layer") == "sar"
                  and l.get("result") not in (None, "PASS")), None)
    return ligne.get("detail") if ligne else None


@extracteur("mixite_clause")
def _c_mixite(db, idu, f):
    return _nz(f.get("mixite_clause"))


@extracteur("rtaa_exigences")
def _c_rtaa(db, idu, f):
    return _nz(f.get("rtaa_exigences"))


# ══ Bâti / Terrain ═════════════════════════════════════════════════════════════════════════

@extracteur("emprise_batie_m2")
def _c_emprise(db, idu, f):
    return _nz((f.get("le_bien") or {}).get("emprise_batie_m2"))


@extracteur("hauteur_bati_m")
def _c_hauteur(db, idu, f):
    return _nz((f.get("le_bien") or {}).get("hauteur_bati_m"))


@extracteur("n_batiments")
def _c_nbat(db, idu, f):
    return _nz((f.get("le_bien") or {}).get("nb_batiments"))


@extracteur("surface_libre_sol_m2")
def _c_libre(db, idu, f):
    return _nz((f.get("le_bien") or {}).get("surface_libre_m2"))


@extracteur("cosia_detecte_m2")
def _c_cosia(db, idu, f):
    return _nz((f.get("le_bien") or {}).get("cosia_detecte_m2"))


@extracteur("part_artificialisee_pct")
def _c_artif(db, idu, f):
    o = (f.get("le_bien") or {}).get("ocsge") or {}
    return _nz(o.get("artif_pct") if isinstance(o, dict) else None)


@extracteur("usage_sol_dominant")
def _c_usage_sol(db, idu, f):
    o = (f.get("le_bien") or {}).get("ocsge") or {}
    return _nz((o.get("usage_libelle") or o.get("usage")) if isinstance(o, dict) else None)


@extracteur("pente_toit_deg")
def _c_pente_toit(db, idu, f):
    t = (f.get("le_bien") or {}).get("toit") or {}
    return _nz(t.get("pente_deg") if isinstance(t, dict) else None)


@extracteur("nature_toit")
def _c_nature_toit(db, idu, f):
    t = (f.get("le_bien") or {}).get("toit") or {}
    return _nz((t.get("forme_libelle") or t.get("forme")) if isinstance(t, dict) else None)


@extracteur("dpe_connu")
def _c_dpe(db, idu, f):
    return _nz(f.get("dpe_connu"))


@extracteur("rnb_batiments_liste")
def _c_rnb(db, idu, f):
    return _nz((f.get("le_bien") or {}).get("rnb"))


@extracteur("ban_plus_adresses_bati")
def _c_ban_plus(db, idu, f):
    v = (f.get("le_bien") or {}).get("adresses_bati")
    if isinstance(v, dict):
        return _nz(v.get("liens"))
    if isinstance(v, list):
        return len(v) or None
    return _nz(v)


@extracteur("piscine_m2")
def _c_piscine(db, idu, f):
    lb = f.get("le_bien") or {}
    return _nz(lb.get("piscine_m2") or (f.get("piscine") or {}).get("surface_m2")
               if isinstance(f.get("piscine"), dict) or lb.get("piscine_m2") else None)


# ══ Potentiel ══════════════════════════════════════════════════════════════════════════════

@extracteur("potentiel_verdict")
def _c_potentiel(db, idu, f):
    return _nz(f.get("potentiel_transformation"))


@extracteur("sdp_residuelle_m2")
def _c_sdp(db, idu, f):
    p = f.get("potentiel_transformation") or {}
    v = p.get("sdp_residuelle_m2")
    return round(float(v)) if v is not None else None


@extracteur("capacite_logements")
def _c_capacite(db, idu, f):
    p = f.get("potentiel_transformation") or {}
    return p.get("capacite_estimee") if p.get("capacite_estimee") else None


@extracteur("surface_plancher_m2")
def _c_plancher(db, idu, f):
    p = f.get("potentiel_transformation") or {}
    return _nz(p.get("surface_plancher_m2"))


@extracteur("surface_vendable_m2")
def _c_vendable(db, idu, f):
    p = f.get("potentiel_transformation") or {}
    return _nz(p.get("surface_vendable_m2"))


@extracteur("marge_surelevation_m")
def _c_marge_surel(db, idu, f):
    # RECETTE-7 (E1)/RECETTE-10 (T1) — la marge n'est servie que quand la base la rend comparable
    # (faîtage BD TOPO, ou LiDAR HD mesuré : la contrainte la plus serrée est déjà appariée).
    p = f.get("potentiel_transformation") or {}
    base = str(p.get("hauteur_base") or "")
    if base.startswith("faîtage") or "mesuré (LiDAR HD)" in base:
        return p.get("hauteur_marge_m")
    return None


# ══ Risques ════════════════════════════════════════════════════════════════════════════════

@extracteur("aleas_parcelle_liste")
def _c_aleas(db, idu, f):
    return _nz((f.get("aleas") or {}).get("liste"))


@extracteur("n_vigilances")
def _c_vigilances(db, idu, f):
    n = sum(1 for l in (f.get("flags") or [])
            if isinstance(l, dict) and l.get("result") in ("SOFT_FLAG", "HARD_EXCLUDE"))
    return n or None


@extracteur("sis_classe")
def _c_sis(db, idu, f):
    v = (f.get("sols") or {}).get("sis_classe")
    return v if v and v != "hors" else None


@extracteur("casias_statut")
def _c_casias(db, idu, f):
    v = (f.get("sols") or {}).get("casias_statut")
    return v if v and v != "hors" else None


@extracteur("sols_parcelle")
def _c_sols(db, idu, f):
    s = f.get("sols") or {}
    touche = {k: v for k, v in s.items() if v not in (None, "hors")}
    return touche or None


@extracteur("endiguement_zone_protegee")
def _c_endiguement(db, idu, f):
    ligne = next((l for l in (f.get("lines") or [])
                  if isinstance(l, dict) and l.get("layer") == "endiguement"
                  and l.get("result") not in (None, "PASS")), None)
    return ligne.get("detail") if ligne else None


# ══ Réseaux / desserte ═════════════════════════════════════════════════════════════════════

@extracteur("viabilisation_verdict")
def _c_viab(db, idu, f):
    return _nz(f.get("viabilisation"))


@extracteur("distance_arret_m")
def _c_arret(db, idu, f):
    return _nz(f.get("proximites"))     # dict {arret, axe, pole, tcsp} — le rendeur dit la desserte


@extracteur("tcsp_stationnement_allege")
def _c_tcsp(db, idu, f):
    t = (f.get("proximites") or {}).get("tcsp")
    return t if isinstance(t, dict) and (t.get("sous_800m") or t.get("distance_m")) else None


@extracteur("part_logements_egout_pct")
def _c_anc(db, idu, f):
    return _nz(f.get("anc"))            # dict {statut, libelle, phrase, …}


@extracteur("fibre_parcelle")
def _c_fibre(db, idu, f):
    fi = f.get("fibre")
    return fi if isinstance(fi, dict) and fi.get("etat") else None


@extracteur("prod_spec_kwh_kwc")
def _c_solaire(db, idu, f):
    a = f.get("aper")
    if isinstance(a, dict):
        return _nz(a.get("prod_spec_kwh_kwc") or a.get("productible_kwh_kwc"))
    return None


# ══ Fiscalité ══════════════════════════════════════════════════════════════════════════════

@extracteur("perimetres_dispositifs_liste")
def _c_fiscal(db, idu, f):
    return _nz(f.get("territoire_fiscal"))


@extracteur("taxe_amenagement_estimee_eur")
def _c_taxe(db, idu, f):
    return _nz(f.get("taxe_amenagement"))


@extracteur("tfpb_taux_pct")
def _c_tfpb(db, idu, f):
    fi = f.get("fiscalite") or {}
    return fi if isinstance(fi, dict) and fi.get("tfpb_commune_pct") is not None else None


# ══ Marché ═════════════════════════════════════════════════════════════════════════════════

@extracteur("prix_sortie_bati_eur_m2")
def _c_prix_ancien(db, idu, f):
    # la distribution du secteur (médiane + points retenus/écartés) — le rendeur en tire le nuage.
    pa = f.get("prix_ancien") or {}
    return pa if pa.get("median") is not None else None


@extracteur("prix_terrain_secteur_eur_m2")
def _c_terrain(db, idu, f):
    tn = (f.get("mode_b") or {}).get("terrain_nu")
    return tn if isinstance(tn, dict) and tn.get("prix_m2") else None


@extracteur("ventes_retenues_n")
def _c_retenues(db, idu, f):
    n = (f.get("prix_ancien") or {}).get("n")
    return {"n": n, "non_couvert": False} if n is not None else None


@extracteur("ventes_ecartees_n")
def _c_ecartees(db, idu, f):
    pa = f.get("prix_ancien") or {}
    n = pa.get("n_exclus")
    return {"n": n, "non_couvert": False} if n is not None else None


@extracteur("dvf_parcelle_liste")
def _c_dvf_secteur(db, idu, f):
    return _nz((f.get("dvf_parcelle") or {}).get("secteur"))


@extracteur("prix_neuf_vefa_acte_eur_m2")
def _c_vefa(db, idu, f):
    ms = f.get("marche_secteur") or {}
    v = ms.get("neuf_vefa") or ms.get("vefa")
    return _nz(v)


@extracteur("radar_annonces_liste")
def _c_radar(db, idu, f):
    return _nz(f.get("radar_annonces"))


@extracteur("ventes_100m_n")
def _c_ventes_100m(db, idu, f):
    v = f.get("voisinage_proche") or {}
    return v if v.get("ventes_dvf") is not None else None


@extracteur("voisinage_100m_liste")
def _c_voisinage(db, idu, f):
    return _nz(f.get("voisinage_proche"))


# ══ Quartier ═══════════════════════════════════════════════════════════════════════════════

@extracteur("iris_quartier")
def _c_iris(db, idu, f):
    iq = f.get("iris_quartier")
    return iq if isinstance(iq, dict) and iq.get("habitants") is not None else None


@extracteur("equipements_proximite_liste")
def _c_equip(db, idu, f):
    return _nz((f.get("proximites_equipements") or {}).get("items"))


@extracteur("n_permis_proximite")
def _c_permis(db, idu, f):
    # RECETTE-12 D1 — permis autorisés dans un RAYON de 500 m / 24 mois (même moteur que l'écran :
    # nearby_permits). Seul extracteur qui lit la base (compte live, non porté par le payload).
    from sqlalchemy import text
    from ..ingestion.permits import nearby_permits
    pid = db.execute(text("SELECT id FROM parcels WHERE idu = :i"), {"i": idu}).scalar()
    if pid is None:
        return None
    dyn = (nearby_permits(db, pid, radius_m=500, fenetre_mois=24) or {}).get("dynamique") or {}
    n = dyn.get("permis_recents")
    return ({"n": n, "non_couvert": False, "rayon_m": 500, "fenetre_mois": 24} if n else None)


# ══ Score / en-tête ════════════════════════════════════════════════════════════════════════

@extracteur("tier_opportunite")
def _c_tier(db, idu, f):
    sv = f.get("score_v2") or {}
    return _nz(sv.get("label"))          # le LIBELLÉ humain, jamais le code (verrou libellés)


@extracteur("rang_tier")
def _c_rang(db, idu, f):
    sv = f.get("score_v2") or {}
    if sv.get("rang") is None:
        return None
    return {"rang": sv.get("rang"), "total": sv.get("rang_total")}


# ══ Sources (section de clôture, hors miroir) ═════════════════════════════════════════════

@extracteur("run_label_servi")
def _c_sources(db, idu, f):
    return _nz(f.get("data_sources"))   # liste {nom, fournisseur, millesime, categorie}
