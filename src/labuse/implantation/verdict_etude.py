"""ETUDE-AUDIT-FIX-1 LOT 1 (défaut 1) — SOURCE UNIQUE du verdict AFFICHÉ et des RÉSERVES d'une étude
de faisabilité, lue À L'IDENTIQUE par l'écran (payload servi par `api/modules`) et par le PDF
(`exports/etude_faisabilite`).

Avant ce lot, l'écran affichait le verdict BRUT du moteur (« Exploitable sous hypothèses ») tandis
que le PDF appliquait, LUI SEUL, une garde d'honnêteté qui comparait le plancher du scénario — dessiné
sur TERRAIN NU (bâti supposé démoli, l'étude le décide déjà) — au plancher RÉSIDUEL d'UNE parcelle
calculé AVEC son bâti existant. D'où « Exploitable » à l'écran et « À vérifier » au PDF pour la même
étude (Étang-Salé AW : 2 730 m² dessinés opposés à 299 m² résiduels d'une seule parcelle bâtie).

Ici : le verdict et ses réserves sont calculés UNE fois. La comparaison de capacité se fait sur
TERRAIN NU — plancher du scénario vs meilleure capacité trouvée par le moteur sur l'assiette fusionnée
(`capacite_maximale`, terrain libéré), JAMAIS contre le résiduel avec bâti. `annoter()` pose
`verdict_affiche`, `verdict_classe` et `reserves` sur chaque variante présente.
"""
from __future__ import annotations

import re


def _art_label(art) -> str:
    return re.sub(r"^(?:article|art\.?)\s+", "", str(art or "").strip(), flags=re.I)


def _grp(n) -> str:
    try:
        return f"{int(round(float(n))):,}".replace(",", " ")
    except (TypeError, ValueError):
        return str(n)


def bareme_stationnement_absent(payload: dict) -> bool:
    """Le barème de stationnement de la zone n'est pas servi par LABUSE → places NON vérifiées
    (réserve honnête, jamais « 0 place exigée »). Même détection que l'ancien `_bareme_stationnement_absent`
    du PDF : source unique = le drapeau `validee` du régime général ; repli heuristique sinon."""
    reg = (payload.get("stationnement_regimes") or {}).get("general") or {}
    if "validee" in reg:
        return not bool(reg.get("validee"))
    _art = _art_label(reg.get("article"))
    return (reg.get("ratio_par_logement") is None and not reg.get("regle_courte")
            and not str(_art or "").upper().startswith("L151"))


def reserves_etude(payload: dict, retenu: dict) -> list[str]:
    """Les RÉSERVES qui rétrogradent « Exploitable » → « À vérifier » (identiques écran/PDF).

    DÉFAUT 1 — la comparaison de capacité se fait sur TERRAIN NU : plancher du scénario vs meilleure
    capacité trouvée par le moteur sur l'assiette (terrain libéré, bâti supposé démoli), et non contre
    le plancher résiduel d'une parcelle AVEC son bâti existant. Le scénario retenu ne dépasse jamais
    cette capacité par construction → plus de rétrogradation à tort sur une étude « terrain libéré »."""
    raisons: list[str] = []
    sdp_e = (retenu.get("resume") or {}).get("sdp_m2")
    sdp_nu = (payload.get("capacite_maximale") or {}).get("sdp_m2")
    if isinstance(sdp_e, (int, float)) and isinstance(sdp_nu, (int, float)) and sdp_e > sdp_nu + 1:
        raisons.append(
            f"Le plancher de cette étude ({_grp(sdp_e)} m²) dépasse la meilleure capacité trouvée sur "
            f"le terrain nu ({_grp(sdp_nu)} m², bâti supposé démoli) : à confronter avant de retenir ce "
            "programme.")
    if bareme_stationnement_absent(payload):
        raisons.append("La règle de stationnement de cette zone existe au PLU mais n'est pas ingérée "
                       "par LABUSE : le nombre de places n'est pas vérifié (stationnement non vérifié).")
    return raisons


def verdict_affiche(payload: dict, retenu: dict) -> tuple[str, str, list[str]]:
    """(label, classe ∈ ok|cp|no, reserves) AFFICHÉS — strictement identiques à l'écran et au PDF.
    Une réserve suffit à passer d'« Exploitable » à « À vérifier » ; sinon on traduit le verdict
    global du moteur (`verdict`), avec repli sur le statut de scénario."""
    reserves = reserves_etude(payload, retenu)
    vg = str(retenu.get("verdict") or "")
    if reserves:
        return "À vérifier", "cp", reserves
    if vg.startswith("Exploitable"):
        return "Exploitable", "ok", reserves
    if vg.startswith("Impossible"):
        return "Impossible", "no", reserves
    if vg:
        return "À compléter", "cp", reserves
    st = str(retenu.get("statut_etude") or "")
    if st.startswith("exploitable"):
        return "Exploitable", "ok", reserves
    if st == "à compléter":
        return "À compléter", "cp", reserves
    if st == "ne tient pas":
        return "Ne tient pas", "no", reserves
    return "Simulation impossible", "no", reserves


def annoter(payload: dict) -> dict:
    """Pose `verdict_affiche`, `verdict_classe`, `reserves` sur CHAQUE variante présente (écran). Le
    worker PDF lit EXACTEMENT les mêmes champs. Best-effort — n'échoue jamais l'étude."""
    if not isinstance(payload, dict):
        return payload
    for v in (payload.get("variantes") or []):
        if not isinstance(v, dict) or v.get("absente"):
            continue
        try:
            label, classe, reserves = verdict_affiche(payload, v)
            v["verdict_affiche"] = label
            v["verdict_classe"] = classe
            v["reserves"] = reserves
        except Exception:  # noqa: BLE001 — l'annotation ne casse jamais l'étude
            pass
    return payload
