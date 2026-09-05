"""M54-AB F6 (C5) — présentation CONDENSÉE du bloc Marché commune (M-U) dans les exports.

On CONSOMME `build_marche_commune` (lecture seule, jamais modifié) et on rend, pour chaque
export, une poignée de lignes CLIENT déjà datées (chaque ligne porte SA date amont, jamais un
millésime unique). Point de présentation UNIQUE partagé par dossier/flash, banquier et premium
— les n cités viennent d'ICI, plus de « 54 ventes » d'un côté et « 51 » de l'autre.
"""
from __future__ import annotations

from sqlalchemy.orm import Session


def _grp(n) -> str:
    return f"{int(round(n)):,}".replace(",", " ")


def phrase_ligne(lg: dict) -> str | None:
    """Une ligne M-U → phrase client DATÉE, ou None si non calculable (le bloc condensé n'affiche
    que le calculable ; le bloc complet, avec motifs, reste servi par l'outil Marché M-U)."""
    if not lg or not lg.get("calculable"):
        return None
    v = lg.get("valeurs") or {}
    date = lg.get("date_amont")
    d = f" — {date}" if date else ""
    cle = lg["cle"]
    # EXPORTS-1 (1.2) : la clé `prix_ancien_median` (ligne1, médiane autour du centroïde de la
    # commune, « n 11 ») n'existe plus — le prix de l'ancien est parcellaire
    # (`marche_service.phrase_prix_ancien`).
    if cle == "prix_sortie_neuf":
        return f"Prix de sortie neuf {_grp(v['prix_eur_m2'])} €/m² (niveau {v.get('niveau')}, n {v.get('n')}){d}"
    if cle == "tendance_12m":
        # EXPORTS-1 (1.6) : « n 218/583 » n'était expliqué nulle part — les deux effectifs sont dits.
        return (f"Tendance {v['sens']} {v['delta_pct']:+.1f} % sur 12 mois "
                f"({_grp(v['median_12m'])} vs {_grp(v['median_prec'])} €/m² — {v['n12']} ventes "
                f"sur 12 mois, {v['nprev']} sur les 12 mois précédents){d}")
    if cle == "liquidite":
        dl = v.get("delta_pct_an")
        dtxt = f", {dl:+d} % vs an−1" if dl is not None else ""
        return f"Liquidité {v['mutations_dernier_trim']} ventes au dernier trimestre{dtxt}{d}"
    if cle == "offre_engagee":
        return (f"Offre engagée {v['logements_12m']} logements autorisés / 12 mois "
                f"({v['permis_12m']} permis){d}")
    if cle == "gisement_constructible":
        return f"Gisement {_grp(v['sdp_residuelle_m2'])} m² SDP résiduelle sur {_grp(v['parcelles'])} parcelles servables{d}"
    if cle == "loyer_median":
        return f"Loyer médian {v['loyer_eur_m2']} €/m² ({v.get('type', '')}){d}"
    return None


def bloc_condense(db: Session, commune: str, cles: list[str]) -> list[dict]:
    """Rend les lignes M-U demandées (dans l'ordre) en phrases client datées.
    Chaque item : {cle, phrase, fiabilite}. Les lignes non calculables sont omises."""
    from ..faisabilite.marche_commune import build_marche_commune
    try:
        # SAVEPOINT : une requête M-U qui échoue (table absente en base de test…) est annulée
        # SEULE — sans poisonner la transaction appelante (qui rend le reste du document).
        with db.begin_nested():
            mc = build_marche_commune(db, commune)
    except Exception:  # noqa: BLE001 — marché indisponible → bloc omis, jamais un 500
        return []
    par = {lg["cle"]: lg for lg in mc.get("lignes", [])}
    out = []
    for c in cles:
        ph = phrase_ligne(par.get(c))
        if ph:
            out.append({"cle": c, "phrase": ph, "fiabilite": (par[c] or {}).get("fiabilite")})
    return out
