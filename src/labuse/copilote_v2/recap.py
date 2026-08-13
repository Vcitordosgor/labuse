"""M78-bis §2 — RÉCAP-CONFIRMATION avant toute mission lourde (RECHERCHE, VERIFICATION).

On INVERSE le flux : le Copilote annonce ce qu'il a compris, le client valide, PUIS l'instruction part.
La confirmation est un PÉAGE (règle §5) — justifiée seulement quand une mauvaise interprétation coûte
cher (une instruction d'une minute, un avis d'achat). QUESTION/OUTIL répondent immédiatement.

L'interprétation se fait SANS lancer le run (interpreter_brief). Une clarification propose AU PLUS
3-4 suggestions (jamais les 24 communes = un formulaire déguisé) : les communes les plus ACTIVES +
« Toute l'île » + champ libre (côté front). La barre n'est jamais verrouillée.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..copilote.interpreteur import interpreter_brief


def _communes_actives(db: Session, n: int = 3) -> list[str]:
    """Les n communes les plus ACTIVES (dépôts de permis récents) — pour une clarification COURTE."""
    rows = db.execute(text(
        "SELECT commune FROM m10_permit_delais WHERE date_depot > now() - interval '3 years' "
        "GROUP BY commune ORDER BY count(*) DESC LIMIT :n"), {"n": n}).scalars().all()
    return list(rows)


def _chips_fr(bj: dict) -> list[str]:
    """Chips en français depuis brief_json (miroir de ChipsCompris front)."""
    out: list[str] = list(bj.get("communes") or [])
    prog = bj.get("programme") or {}
    if prog.get("logements"):
        out.append(f"{prog['logements']} logements")
    if bj.get("surface_min_m2"):
        out.append(f"≥ {round(bj['surface_min_m2'])} m²")
    if bj.get("budget_max_eur"):
        out.append(f"budget ≤ {round(bj['budget_max_eur'] / 1000)} k€")
    c = bj.get("contraintes") or {}
    if c.get("zones"):
        out.append("zones " + "/".join(c["zones"]))
    if c.get("exclure_ppr_rouge"):
        out.append("hors PPR rouge")
    if c.get("exclure_abf"):
        out.append("hors ABF")
    for na in bj.get("criteres_non_appliques") or []:
        out.append(f"« {na} » (non applicable)")
    return out


# Suggestions d'affinage — facettes RÉELLES du moteur RECHERCHE (brief_json). `ajout` = texte appendu au
# brief (re-interprété → la chip apparaît) ; None = pas de valeur → le front focalise la barre.
_SUGGESTIONS = [
    ("surface_min_m2", "Au moins 1 000 m²", "au moins 1000 m²"),
    ("zones", "En zone constructible (U ou AU)", "en zone U ou AU"),
    ("exclure_abf", "Hors périmètre ABF", "hors ABF"),
    ("budget_max_eur", "Fixer un budget maximum", None),
]


def recap_recherche(db: Session, message: str) -> dict:
    """RECHERCHE : interprète SANS lancer. Retourne le récap + suggestions, OU une clarification COURTE."""
    it = interpreter_brief(message, "instruire")
    if it.clarification:
        c = it.clarification
        # §complément : jamais 24 chips. Communes → 2-3 actives + « Toute l'île » ; sinon ≤3 options.
        if c.get("champ_manquant") == "communes":
            options = _communes_actives(db, 3) + ["Toute l'île"]
        else:
            options = (c.get("options") or [])[:4]
        return {"intent": "RECHERCHE", "clarification_recap": {
            "question": c["question"], "options": options, "champ": c.get("champ_manquant")}}
    bj = it.brief
    chips = _chips_fr(bj)
    c = bj.get("contraintes") or {}
    presents = {"surface_min_m2": bj.get("surface_min_m2"), "zones": c.get("zones"),
                "exclure_abf": c.get("exclure_abf"), "budget_max_eur": bj.get("budget_max_eur")}
    suggestions = [{"label": lab, "ajout": aj} for (cle, lab, aj) in _SUGGESTIONS if not presents.get(cle)]
    return {"intent": "RECHERCHE", "needs_confirmation": True, "brief_json": bj, "chips": chips,
            "recap": "J'ai compris : " + ", ".join(chips) + ".", "suggestions": suggestions}


def recap_verification(params: dict) -> dict:
    """VERIFICATION : récap « vérifier X à Y € » OU une seule question si l'IDU/le prix manque."""
    idu = params.get("idu")
    prix = params.get("prix_eur") or params.get("budget_eur")
    if not idu:
        return {"intent": "VERIFICATION", "clarification_recap": {
            "question": "Quelle parcelle dois-je vérifier ? Donnez-moi son IDU (14 caractères).",
            "options": [], "champ": "idu"}}
    if not prix:
        return {"intent": "VERIFICATION", "clarification_recap": {
            "question": f"À quel prix la parcelle {idu} vous est-elle proposée ?", "options": [], "champ": "prix"}}
    return {"intent": "VERIFICATION", "needs_confirmation": True, "idu": idu, "prix": float(prix),
            "recap": f"J'ai compris : vérifier la parcelle {idu} au prix demandé de {round(float(prix)):,} €."
                     .replace(",", " ")}
