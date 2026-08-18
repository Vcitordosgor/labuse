"""M78 · Phase 3 — VÉRIFICATION (3a) + PROJET (3b).

3a VÉRIFICATION : IDU + prix demandé → instruction à charge et à décharge depuis les MÊMES points de
calcul (fiche + marché), confrontation au prix (prix probable vs demandé), avis final en UNE phrase
avec ses réserves et le MÊME verrou anti-invention que le héros (§2e). DVF sous le seuil M79 →
« échantillon insuffisant », jamais une médiane sur 1 vente.

3b PROJET : « j'ai un projet : résidence 12 lots à Bras-Panon » → fiche de cadrage (vocabulaire fermé
FICHE_SCHEMA) construite depuis le brief. La CRÉATION RÉELLE passe par l'API projets existante (au
niveau de l'endpoint, avec le compte) — JAMAIS d'écriture directe en base ici.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from . import outils


def _eur(n: float | int) -> str:
    return f"{round(n):,}".replace(",", " ") + " €"


def _m2(n: float | int | None) -> str:
    return (f"{round(n):,}".replace(",", " ") + " m²") if n is not None else "surface inconnue"


# ───────────────────────── 3b — PROJET (préparation de la fiche) ─────────────────────────
def preparer_projet(params: dict, message: str) -> dict:
    """Construit la fiche de cadrage (FICHE_SCHEMA) depuis les paramètres extraits. L'écriture réelle
    est faite par l'endpoint (API projets). Retourne {fiche, nom, idu}."""
    fiche: dict = {"type_programme": "logements"}
    ampleur: dict = {}
    if params.get("programme_logements") is not None:
        ampleur["logements"] = int(params["programme_logements"])
    if ampleur:
        fiche["ampleur"] = ampleur
    if params.get("commune"):
        fiche["perimetre"] = {"mode": "communes", "communes": [params["commune"]]}
    if params.get("budget_eur") is not None:
        fiche["budget_foncier_eur"] = float(params["budget_eur"])
    return {"fiche": fiche, "nom": None, "idu": params.get("idu")}   # nom None → l'API le dérive


# ───────────────────────── 4 — VEILLE (préparation) ─────────────────────────
def preparer_veille(db: Session, params: dict, message: str = "") -> dict:
    """Parse la demande de veille (type + commune). ARBITRAGE Vic : on ne POSE que les types BRANCHÉS
    (une veille qui ne se déclencherait jamais est pire qu'un refus honnête). Un type connu mais non
    branché → refus honnête + demande MESURÉE en télémétrie (on capte le signal sans fausse veille).
    Type inconnu → DIT. Le modèle ne sert QU'ICI (à la création)."""
    from . import telemetrie
    from .veilles import TYPES, EVALUABLES
    vt = params.get("veille_type")
    commune = params.get("commune") or (params.get("perimetre") if isinstance(params.get("perimetre"), str) else None)
    actifs = " · ".join(TYPES[t] for t in EVALUABLES)
    if vt in TYPES and vt not in EVALUABLES:
        telemetrie.critere_non_traduisible(db, f"veille:{vt}", message)   # mesurer la demande, sans poser
        return {"text": f"La veille « {TYPES[vt]} » n'est pas encore active : sa source n'est pas branchée, "
                f"et je ne pose pas une veille qui ne se déclencherait jamais. Pour l'instant je pose : "
                f"{actifs}. Ce type suivra.", "intent": "VEILLE", "refus": "type_pas_encore_actif"}
    if vt not in TYPES:
        return {"text": f"Je ne sais pas poser ce type de veille. Types actifs : {actifs}.",
                "intent": "VEILLE", "refus": "type_non_couvert"}
    if not commune:
        return {"text": f"Sur quelle commune veiller les {TYPES[vt]} ?", "intent": "VEILLE",
                "clarification": True}
    # M112 P2.2 — porte cliquable vers la SECTION Surveillance (volet Secteurs) : jamais un
    # « rendez-vous dans X » sans bouton. Le volet où la veille posée devient visible/réglable.
    return {"text": "Pose de la veille…", "intent": "VEILLE",
            "surveillance": {"volet": "secteurs"},
            "_action": {"type": "veille", "veille_type": vt, "commune": commune}}


# ───────────────────────── 3a — VÉRIFICATION ─────────────────────────
def verification(db: Session, params: dict) -> dict:
    """IDU + prix demandé → avis instruit. Une seule question si l'un manque (le Copilote demande)."""
    idu = params.get("idu")
    prix = params.get("prix_eur") or params.get("budget_eur")
    if not idu:
        return {"text": "Quelle parcelle dois-je vérifier ? Donnez-moi son IDU (14 caractères).",
                "intent": "VERIFICATION", "clarification": True}
    f = outils.fiche_parcelle(db, idu=idu)
    if not f.ok:
        return {"text": f"Parcelle {idu} introuvable.", "intent": "VERIFICATION", "refus": "donnee_absente"}
    if not prix:
        return {"text": f"À quel prix la parcelle {idu} vous est-elle proposée ?",
                "intent": "VERIFICATION", "clarification": True}
    d = f.data
    commune = d.get("commune")
    surface = d.get("surface_m2")
    # marché du secteur — MÊME point de calcul que la fiche (build_marche_commune, DVF terrain nu M79).
    # Prix terrain nu par ZONE (€/m²) × surface ; sous le seuil M79 (n ventes) → échantillon insuffisant.
    from ..faisabilite.marche_commune import build_marche_commune
    z = (d.get("zone") or "").upper()
    fam = "AU" if z.startswith("AU") else (z[:1] if z else "")
    terrain_m2 = n_ventes = None
    insuffisant = False
    if commune:
        for l in build_marche_commune(db, commune).get("lignes", []):
            if isinstance(l, dict) and l.get("cle") == "prix_terrain_nu_par_zone":
                pz = ((l.get("valeurs") or {}).get("par_zone") or {}).get(fam)
                if pz and pz.get("calculable"):
                    terrain_m2, n_ventes = pz.get("median_eur_m2"), pz.get("n")
                    insuffisant = n_ventes is not None and n_ventes < 5   # seuil M79
                break
    # AVIS DÉTERMINISTE (arbitrage Vic) — la mission la plus exposée : on ne laisse PAS le modèle
    # s'enthousiasmer sur une parcelle qui a peut-être un défaut invisible. Trois règles gravées :
    #  1. JAMAIS « estimée à X € » pour une médiane × surface — c'est une PROJECTION arithmétique.
    #  2. La réserve de MÉTHODE est TOUJOURS dite (le calcul ignore config/accès/topo/état/bâti).
    #  3. Écart > 2× → mention explicite « l'écart est important, à vérifier sur place ».
    lignes: list[str] = [f"Parcelle {idu} à {commune}, {_m2(surface)} en zone "
                         f"{d.get('zone') or fam or '?'}, proposée à {_eur(prix)}."]
    if terrain_m2 and surface and not insuffisant:
        projection = round(terrain_m2 * surface)
        lignes.append(f"À ce prix médian de zone ({_eur(terrain_m2)}/m², {n_ventes} ventes DVF), "
                      f"{_m2(surface)} représenteraient {_eur(projection)} — une projection arithmétique, "
                      f"PAS une valeur vénale.")
        ecart = projection / prix if prix and prix < projection else (prix / projection if prix else None)
        sens = "sous" if prix < projection else "au-dessus de"
        if ecart:
            lignes.append(f"Le prix demandé est {ecart:.1f}× {sens} cette projection.")
            if ecart >= 2:
                lignes.append("L'écart est important — il tient peut-être à des caractéristiques que "
                              "ce calcul ne mesure pas (un prix très inférieur au marché a généralement une "
                              "raison). À vérifier sur place.")
    elif insuffisant:
        lignes.append(f"Échantillon DVF insuffisant en zone {fam} ({n_ventes} vente(s)) : pas de repère "
                      f"de prix terrain fiable — jamais une médiane sur si peu.")
    else:
        lignes.append("Pas de repère de prix terrain DVF pour cette zone.")
    lignes.append("Réserve de méthode : ce calcul ne tient compte ni de la configuration du terrain, ni "
                  "de son accès, ni de la topographie, ni de l'état du sol ou du bâti — tout ce qui fait "
                  "qu'une parcelle vaut moins que la médiane de sa zone.")
    return {"text": " ".join(lignes), "intent": "VERIFICATION", "tool": "verification", "idu": idu,
            "sources": [f.source, "DVF (prix terrain nu par zone)"],
            # sorties : ouvrir la fiche, exporter le dossier, écrire au propriétaire (PM → sinon SPF)
            "actions": ["ouvrir_fiche", "exporter_dossier", "ecrire_proprietaire"]}
