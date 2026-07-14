"""M-VIA — Indicateur de VIABILISATION & RACCORDEMENT (eau · assainissement · élec).

LABUSE ne peut PAS afficher le tracé des réseaux (donnée sensible Vigipirate,
rediffusion interdite). Ce module ne touche JAMAIS à cette donnée verrouillée :
il construit une PROBABILITÉ de viabilisation par FAISCEAU DE PREUVES, à partir de
signaux DÉJÀ en base (permis Sitadel, voirie/bâti BD TOPO, zonage PLU, poste source
S3REnR). C'est un INDICATEUR, jamais une certitude ni un verrou de constructibilité.
Disclaimer « à confirmer auprès du gestionnaire / DT-DICT » obligatoire partout.

Traçabilité = produit : chaque contribution dit POURQUOI (« 6 permis accordés < 100 m ·
façade sur voie urbanisée · zone U »), comme le bloc P v2.

────────────────────────────── Calibration (M-VIA lot 2) ──────────────────────────────
Seuils CALIBRÉS sur données réelles (échantillon stratifié 4000 parcelles/famille PLU,
seed 974), jamais décrétés. Détail dans reports/m-via/SYNTHESE-M-VIA.md.

  · Distance au permis autorisé le plus proche (médiane / p90) :
        U 28/87 m · AU 22/118 m · A 116/372 m · N 120/910 m
    → rayon primaire 100 m = échelle « même rue / îlot mitoyen » : capte 93 % des
      parcelles U et 87 % des AU, contre ~45 % en A/N. Discriminant net.
  · Nb de permis < 100 m (médiane) : U 4 · AU 5 · A 0 · N 0.
  · Façade sur voirie SEULE (≤ 5 m) : ~75 % partout (BD TOPO inclut les chemins
    ruraux) → NON discriminant seul. Le mandat exige « voie URBANISÉE » : proxy =
    voirie au contact (≤ 10 m) ET bâti riverain (≤ 30 m) → U 89 % vs N 39 %.
  · Bâti mitoyen ≤ 10 m : U 98 % · AU 76 % · A 62 % · N 38 % → signal moyen.

Distribution du score obtenue (bandes) :
  U   : 87 % confirmée / 13 % probable                 (moy. 88)
  AU  : 75 % confirmée / 20 % probable / 6 % autres    (moy. 78)
  A   : 16 % confirmée / 34 % probable / 50 % à étudier (moy. 47)
  N   : 11 % confirmée / 20 % probable / 70 % à étudier (moy. 31)
Comportement voulu : le faisceau de preuves PRIME sur l'étiquette de zone quand les
faits la contredisent (parcelle N enclavée dans un secteur bâti = viabilisée).
"""
from __future__ import annotations

from typing import Any

from .. import config

# ─────────────────────────── Poids calibrés (somme = 100) ───────────────────────────
# S1 permis proximité = LE signal le plus fort (preuve factuelle qu'on construit et
# raccorde dans le secteur). S4 zone = pondération de fond.
W_PERMIS = 40      # S1 — permis autorisés < 100 m (mandat 2.1)
W_FACADE = 25      # S2 — façade sur voie publique urbanisée (mandat 2.2)
W_BATI = 15        # S3 — adjacence au bâti existant (mandat 2.3)
W_ZONE = 20        # S4 — zone urbanisée PLU (mandat 2.4)

# Rayons/fenêtres calibrés.
R_PRIMAIRE_M = 100          # rayon primaire "même rue"
R_SECTEUR_M = 200           # rayon "secteur"
ANNEE_RECENTE = 2022        # permis récents = secteur en développement actif

# Bandes de score → libellé (mandat 2.6).
BANDES = [
    (70, "confirmee",   "Viabilisation confirmée par les faits"),
    (45, "probable",    "Viabilisation probable"),
    (25, "incertaine",  "Viabilisation incertaine — à vérifier"),
    (0,  "lourde",      "Viabilisation lourde probable"),
]

DISCLAIMER = (
    "Indicateur de PROBABILITÉ de viabilisation (faisceau de preuves), pas une "
    "certitude ni un droit à construire. Aucun tracé de réseau (donnée sensible). "
    "À confirmer auprès des gestionnaires et via DT-DICT (reseaux-et-canalisations.gouv.fr)."
)


# ───────────────────────────────── Scoring (S1–S4) ─────────────────────────────────
def _pts_permis(c100: int, c200: int) -> int:
    if c100 >= 6:
        return W_PERMIS
    if c100 >= 3:
        return 30
    if c100 >= 1:
        return 18
    if c200 >= 3:
        return 8
    return 0


def _pts_facade(voie10: bool, bati30: bool, voie75: bool) -> int:
    if voie10 and bati30:
        return W_FACADE          # façade sur voie urbanisée (bâti riverain)
    if voie10:
        return 8                 # voie au contact mais non bâtie → urbanisation incertaine
    if voie75:
        return 4
    return 0


def _pts_bati(bati10: bool, bati30: bool, bati75: bool) -> int:
    if bati10:
        return W_BATI
    if bati30:
        return 9
    if bati75:
        return 3
    return 0


def _pts_zone(zone_fam: str | None) -> int:
    return {"U": W_ZONE, "AU": 13, "A": 4, "N": 0}.get(zone_fam or "", 0)


def compute_score(sig: dict[str, Any]) -> int:
    """Score 0-100 déterministe (identique au batch SQL)."""
    return (
        _pts_permis(sig.get("c100", 0) or 0, sig.get("c200", 0) or 0)
        + _pts_facade(bool(sig.get("voie10")), bool(sig.get("bati30")), bool(sig.get("voie75")))
        + _pts_bati(bool(sig.get("bati10")), bool(sig.get("bati30")), bool(sig.get("bati75")))
        + _pts_zone(sig.get("zone_fam"))
    )


def band(score: int) -> tuple[str, str]:
    for seuil, code, libelle in BANDES:
        if score >= seuil:
            return code, libelle
    return "lourde", BANDES[-1][2]


# ─────────────────────────── Contributions tracées (fiche) ───────────────────────────
def contributions(sig: dict[str, Any]) -> list[dict[str, Any]]:
    """Liste lisible « pourquoi ce score », triée par poids décroissant."""
    out: list[dict[str, Any]] = []
    c100 = sig.get("c100", 0) or 0
    c200 = sig.get("c200", 0) or 0
    p = _pts_permis(c100, c200)
    if p:
        recent = sig.get("c100_recent", 0) or 0
        acheve = sig.get("c100_acheve", 0) or 0
        det = f"{c100} permis autorisé(s) < 100 m"
        extra = []
        if recent:
            extra.append(f"{recent} depuis {ANNEE_RECENTE} (secteur en développement actif)")
        if acheve:
            extra.append(f"{acheve} achevé(s) — raccordements réalisés (DAACT)")
        if extra:
            det += " · " + " · ".join(extra)
        out.append({"libelle": "Permis accordés à proximité", "points": p, "detail": det, "signe": "+"})
    elif c200:
        out.append({"libelle": "Activité de permis dans le secteur", "points": 0,
                    "detail": f"{c200} permis < 200 m, aucun < 100 m", "signe": "·"})
    else:
        out.append({"libelle": "Aucun permis à proximité", "points": 0,
                    "detail": "aucun permis autorisé < 200 m", "signe": "−"})

    f = _pts_facade(bool(sig.get("voie10")), bool(sig.get("bati30")), bool(sig.get("voie75")))
    if f == W_FACADE:
        out.append({"libelle": "Façade sur voie publique urbanisée", "points": f,
                    "detail": "voie au contact + bâti riverain → réseaux enterrés sous voirie", "signe": "+"})
    elif f:
        out.append({"libelle": "Voie publique à proximité", "points": f,
                    "detail": "voie proche mais urbanisation incertaine", "signe": "+"})
    else:
        out.append({"libelle": "Pas de voie urbanisée à proximité", "points": 0,
                    "detail": "aucune voirie < 75 m", "signe": "−"})

    b = _pts_bati(bool(sig.get("bati10")), bool(sig.get("bati30")), bool(sig.get("bati75")))
    if b:
        dist = "≤ 10 m" if sig.get("bati10") else ("≤ 30 m" if sig.get("bati30") else "≤ 75 m")
        out.append({"libelle": "Adjacence au bâti existant", "points": b,
                    "detail": f"bâti {dist} (le bâti voisin est raccordé)", "signe": "+"})

    z = _pts_zone(sig.get("zone_fam"))
    zf = sig.get("zone_fam")
    if zf:
        libz = {"U": "Zone urbaine (U)", "AU": "Zone à urbaniser (AU)",
                "A": "Zone agricole (A)", "N": "Zone naturelle (N)"}.get(zf, f"Zone {zf}")
        out.append({"libelle": libz, "points": z, "detail": "pondération de fond (zonage PLU)",
                    "signe": "+" if z >= 13 else ("·" if z else "−")})

    out.sort(key=lambda c: -c["points"])
    return out


# ─────────────────────────── Lot 3 — Coût raccordement (qualitatif) ───────────────────────────
def cout_raccordement(sig: dict[str, Any], code_band: str) -> dict[str, str]:
    """Estimation QUALITATIVE (jamais chiffrée en euros — trop variable). Croise le
    faisceau + le zonage assainissement (M8) quand disponible."""
    assain = sig.get("assainissement_zonage")   # 'collectif' | 'anc' | None
    if code_band == "confirmee":
        base = ("Raccordement a priori SIMPLE : réseaux présumés en façade/voirie, "
                "secteur déjà desservi et construit.")
    elif code_band == "probable":
        base = ("Raccordement PROBABLE au coût standard : secteur partiellement desservi. "
                "À confirmer (longueur de branchement, capacité).")
    elif code_band == "incertaine":
        base = ("Viabilisation À ÉTUDIER : extension de réseau possible, surcoût — "
                "faire chiffrer le branchement auprès du gestionnaire.")
    else:  # lourde
        base = ("Extension de réseau PROBABLE, surcoût significatif : parcelle éloignée "
                "du secteur desservi (façade et/ou secteur non construits).")

    if assain == "anc":
        assain_txt = ("Zonage assainissement NON COLLECTIF ici → filière autonome à prévoir "
                      "(fosse/dispositif, surcoût + emprise).")
    elif assain == "collectif":
        assain_txt = "Zonage assainissement COLLECTIF sur ce secteur → raccordement au réseau à confirmer."
    elif code_band in ("incertaine", "lourde"):
        assain_txt = ("Zonage assainissement non disponible sur la commune → en secteur peu dense, "
                      "prévoir une probable filière autonome (ANC).")
    else:
        assain_txt = "Zonage assainissement non disponible sur la commune (M8)."

    return {"niveau": base, "assainissement": assain_txt,
            "disclaimer": "Estimation qualitative — jamais un chiffrage en euros (trop variable). À confirmer."}


# ─────────────────────────── Assemblage de l'indicateur (fiche) ───────────────────────────
def build_indicateur(sig: dict[str, Any], elec_pv: dict[str, Any] | None = None) -> dict[str, Any]:
    score = compute_score(sig)
    code, libelle = band(score)
    contribs = contributions(sig)
    out: dict[str, Any] = {
        "score": score,
        "band": code,
        "libelle": libelle,
        "contributions": contribs,
        "cout_raccordement": cout_raccordement(sig, code),
        "disclaimer": DISCLAIMER,
    }
    # S5 — capacité élec (S3REnR), volet PV : note SÉPARÉE (hors 0-100). Les postes
    # sources S3REnR ne sont PAS géolocalisés en base et la capacité est ÎLE-large →
    # note d'îlot honnête (pas d'attribution par parcelle fabriquée). Fournie par l'API.
    if elec_pv is not None:
        out["elec_pv"] = elec_pv
    return out


# ───────────────────────────── Lot 1 — Gestionnaires (fiche) ─────────────────────────────
def resolve_gestionnaires(commune: str) -> dict[str, Any] | None:
    """Bloc « Gestionnaires » (contact administratif uniquement, aucune donnée sensible)."""
    cfg = config.load_yaml_config("gestionnaires_via")
    c = (cfg.get("communes") or {}).get(commune)
    if not c:
        return None
    epci_code = c.get("epci")
    epci = (cfg.get("epci_competence") or {}).get(epci_code, {})
    meta = cfg.get("meta") or {}
    return {
        "commune": commune,
        "a_jour_au": meta.get("a_jour_au"),
        "epci": {"code": epci_code, "nom": epci.get("nom"), "contact": epci.get("contact")},
        "eau": c.get("eau"),
        "assainissement": c.get("assainissement"),
        "spanc": c.get("spanc"),
        "electricite": meta.get("electricite_partout"),
        "note": c.get("note") or None,
        "disclaimer": meta.get("disclaimer"),
    }
