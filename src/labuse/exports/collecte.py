"""EXPORTS-2 lot 1.1 — LA COLLECTE : le SEUL endroit qui touche la donnée. Elle produit
{id → Valeur} pour un IDU ; les blocs ne reçoivent QUE ces Valeur (ni calcul ni requête dedans).

Chaque id a un COLLECTEUR `(db, idu, fiche) → valeur brute | None`. `None` = donnée non servie :
l'id n'entre pas dans la map, le bloc OMET la ligne (aucun ◌, aucune valeur d'exemple — décision
Vic lot 2). On lit la fiche `/parcels/{idu}` (point d'appel unique) → « écran = PDF ». Une valeur
peut être structurée (dict/liste) quand le bloc en a besoin (règles PLU, aléas, distribution).
"""
from __future__ import annotations

from typing import Any, Callable

from ..registre.valeur import Valeur, valeurs_pour

COLLECTEURS: dict[str, Callable[[Any, str, dict], Any]] = {}


def collecteur(*ids: str):
    def deco(fn: Callable[[Any, str, dict], Any]):
        for cid in ids:
            COLLECTEURS[cid] = fn
        return fn
    return deco


def collecte(db, idu: str, ids: list[str], *, fiche: dict | None = None) -> dict[str, Valeur]:
    """Assemble {id → Valeur} pour les ids demandés qui ont un collecteur et une valeur servie."""
    f = fiche or {}
    brut: dict[str, Any] = {}
    for cid in ids:
        fn = COLLECTEURS.get(cid)
        if fn is None:
            continue
        try:
            val = fn(db, idu, f)
        except Exception:  # noqa: BLE001 — un collecteur qui échoue OMET sa donnée, jamais un 500
            val = None
        if val is not None:
            brut[cid] = val
    return valeurs_pour(db, brut)


def _nz(v):
    """None / '' / [] / {} → None (donnée non servie) ; sinon la valeur."""
    return v if v not in (None, "", [], {}) else None


# ══ Section 1 — Identité ═══════════════════════════════════════════════════════════════════

@collecteur("surface_parcelle_m2")
def _c_surface(db, idu, f):
    s = f.get("surface_m2")
    return round(float(s)) if s is not None else None


@collecteur("adresse_ban")
def _c_adresse(db, idu, f):
    return _nz(f.get("adresse"))


@collecteur("type_proprietaire")
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


@collecteur("pente_deg")
def _c_pente(db, idu, f):
    return _nz((f.get("terrain") or {}).get("pente_moy_deg"))


@collecteur("prix_achat_historique_eur")
def _c_prix_achat(db, idu, f):
    # D-a — dernière mutation DVF SUR la parcelle (souvent absente : parcelle jamais mutée seule).
    m = (f.get("dvf_parcelle") or {}).get("derniere_mutation")
    return m if isinstance(m, dict) and m.get("valeur") else None


@collecteur("coproprietes_liste")
def _c_copro(db, idu, f):
    return _nz(f.get("coproprietes"))


# ══ Section 2 — Zonage ═════════════════════════════════════════════════════════════════════

def _famille_zone(code: str) -> str | None:
    """U1a → U · AUx → AU · Nh → N · A → A."""
    c = (code or "").strip().upper()
    if c.startswith("AU"):
        return "AU"
    if c[:1] in ("U", "A", "N"):
        return c[:1]
    return None


@collecteur("zone_plu_famille")
def _c_zone_fam(db, idu, f):
    zones = (f.get("reglement_plu") or {}).get("zones") or []
    return _famille_zone(zones[0].get("zone")) if zones else None


@collecteur("reglement_plu_bloc")
def _c_reglement(db, idu, f):
    zones = (f.get("reglement_plu") or {}).get("zones") or []
    if not zones:
        return None
    z = dict(zones[0])   # y porter le drapeau Q12 (prescriptions non vérifiables sur la commune)
    z["_prescriptions_verifiables"] = f.get("prescriptions_verifiables", True)
    z["_prescriptions_motif"] = f.get("prescriptions_non_verifiables_motif")
    return z


@collecteur("er_emplacement_reserve")
def _c_er(db, idu, f):
    return _nz((f.get("dispositifs") or {}).get("er"))


@collecteur("ebc_classe")
def _c_ebc(db, idu, f):
    return _nz((f.get("dispositifs") or {}).get("ebc"))


@collecteur("dpu_perimetre")
def _c_dpu(db, idu, f):
    d = (f.get("dispositifs") or {}).get("dpu")
    return d if isinstance(d, dict) and d.get("etat") == "servi" else None


@collecteur("peb_zone")
def _c_peb(db, idu, f):
    d = (f.get("dispositifs") or {}).get("peb")
    if not isinstance(d, dict):
        return None
    return d if d.get("zone") and d.get("zone") != "hors" else None


@collecteur("statut_plu")
def _c_plu_fraicheur(db, idu, f):
    return _nz(f.get("plu_fraicheur"))


# ══ Section 3 — Potentiel ══════════════════════════════════════════════════════════════════

@collecteur("emprise_batie_m2")
def _c_emprise(db, idu, f):
    return _nz((f.get("le_bien") or {}).get("emprise_batie_m2"))


@collecteur("hauteur_bati_m")
def _c_hauteur(db, idu, f):
    return _nz((f.get("le_bien") or {}).get("hauteur_bati_m"))


@collecteur("n_batiments")
def _c_nbat(db, idu, f):
    return _nz((f.get("le_bien") or {}).get("nb_batiments"))


@collecteur("surface_libre_sol_m2")
def _c_libre(db, idu, f):
    return _nz((f.get("le_bien") or {}).get("surface_libre_m2"))


@collecteur("potentiel_verdict")
def _c_potentiel(db, idu, f):
    return _nz(f.get("potentiel_transformation"))


@collecteur("sdp_residuelle_m2")
def _c_sdp(db, idu, f):
    p = f.get("potentiel_transformation") or {}
    v = p.get("sdp_residuelle_m2")
    return round(float(v)) if v is not None else None


@collecteur("capacite_logements")
def _c_capacite(db, idu, f):
    p = f.get("potentiel_transformation") or {}
    return p.get("capacite_estimee") if p.get("capacite_estimee") else None


@collecteur("marge_surelevation_m")
def _c_marge_surel(db, idu, f):
    p = f.get("potentiel_transformation") or {}
    return p.get("hauteur_marge_m") if p.get("hauteur_base") == "égout" else None


# ══ Section 4 — Risques ════════════════════════════════════════════════════════════════════

@collecteur("aleas_parcelle_liste")
def _c_aleas(db, idu, f):
    return _nz((f.get("aleas") or {}).get("liste"))


# ══ Section 5 — Marché ═════════════════════════════════════════════════════════════════════

@collecteur("prix_sortie_bati_eur_m2")
def _c_prix_ancien(db, idu, f):
    # la distribution du secteur (médiane + points retenus/écartés) — le bloc en tire le nuage.
    pa = f.get("prix_ancien") or {}
    return pa if pa.get("median") is not None else None


@collecteur("prix_terrain_secteur_eur_m2")
def _c_terrain(db, idu, f):
    tn = (f.get("mode_b") or {}).get("terrain_nu")
    return tn if isinstance(tn, dict) and tn.get("prix_m2") else None


@collecteur("ventes_retenues_n")
def _c_retenues(db, idu, f):
    n = (f.get("prix_ancien") or {}).get("n")
    return {"n": n, "non_couvert": False} if n is not None else None


@collecteur("ventes_ecartees_n")
def _c_ecartees(db, idu, f):
    pa = f.get("prix_ancien") or {}
    n = pa.get("n_exclus")
    return {"n": n, "non_couvert": False} if n is not None else None


@collecteur("dvf_parcelle_liste")
def _c_dvf_secteur(db, idu, f):
    return _nz((f.get("dvf_parcelle") or {}).get("secteur"))


@collecteur("n_permis_proximite")
def _c_permis(db, idu, f):
    dep = (f.get("depots") or {}).get("secteur") or {}
    n = dep.get("count")
    return {"n": n, "non_couvert": False} if n is not None else None


# ══ Section 6 — Réseaux ════════════════════════════════════════════════════════════════════

@collecteur("viabilisation_verdict")
def _c_viab(db, idu, f):
    return _nz(f.get("viabilisation"))


@collecteur("distance_arret_m")
def _c_arret(db, idu, f):
    return _nz(f.get("proximites"))     # dict {arret, axe, pole, tcsp} — le bloc rend la desserte


@collecteur("part_logements_egout_pct")
def _c_anc(db, idu, f):
    return _nz(f.get("anc"))            # dict {statut, libelle, phrase, …}


@collecteur("fibre_parcelle")
def _c_fibre(db, idu, f):
    fi = f.get("fibre")
    return fi if isinstance(fi, dict) and fi.get("etat") else None


# ══ Section 7 — Autour (maille RÉELLE : quartier IRIS ; jamais un isochrone non branché) ═════

@collecteur("iris_quartier")
def _c_iris(db, idu, f):
    iq = f.get("iris_quartier")
    return iq if isinstance(iq, dict) and iq.get("habitants") is not None else None


@collecteur("equipements_proximite_liste")
def _c_equip(db, idu, f):
    return _nz((f.get("proximites_equipements") or {}).get("items"))


# ══ Section 8 — Commune ════════════════════════════════════════════════════════════════════

@collecteur("perimetres_dispositifs_liste")
def _c_fiscal(db, idu, f):
    return _nz(f.get("territoire_fiscal"))


@collecteur("taxe_amenagement_estimee_eur")
def _c_taxe(db, idu, f):
    return _nz(f.get("taxe_amenagement"))


@collecteur("parc_social_rpls_logements")
def _c_parc_social(db, idu, f):
    rp = (f.get("marche_secteur") or {}).get("rpls_commune") or {}
    return rp.get("nb_logements") if rp.get("nb_logements") else None


# ══ Section 10 — Sources ═══════════════════════════════════════════════════════════════════

@collecteur("run_label_servi")
def _c_sources(db, idu, f):
    return _nz(f.get("data_sources"))   # liste {nom, fournisseur, millesime, categorie}
