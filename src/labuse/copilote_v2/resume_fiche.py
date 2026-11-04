"""COPILOTE-2 lot 1 — LE CHEMIN FICHE : un résumé DÉTERMINISTE d'une parcelle (ou d'une commune),
lu des MÊMES déclarations et ids que la fiche écran et le Dossier. Le Copilote ne calcule ni ne
choisit aucun chiffre : il lit `_q_v2_fiche` (la fiche premium servie à l'écran), passe les valeurs
au robinet (`exports.robinet_fiche.collecte` — id du registre → valeur), et réutilise les verdicts
de section du Dossier (`exports.verdicts` + `exports.miroir._verdict_factuel`). Le modèle, s'il est
appelé, ne fait que TOURNER la phrase ; en mode dégradé (clé absente), le résumé se construit
INTÉGRALEMENT sans lui — la preuve du mandat.

Deux entrées :
- `resume_parcelle(db, idu)` : les six chiffres du bandeau + le verdict-phrase de chacune des 11
  sections. `phrase(resume)` en fait le texte déterministe.
- `champ_precis(db, idu, message)` : une question sur UN champ (propriétaire, taxe, zone, risques,
  pente…) répond avec la LIGNE DÉCLARÉE et son id — plus de champ jeté par l'outil (COPILOTE-AUDIT-1).
"""
from __future__ import annotations

import html
import re
from typing import Any

from sqlalchemy.orm import Session

from .. import runs
from .outils import _fold_py

# Les SIX chiffres du bandeau (declarations/fiche/entete_tuiles.yaml — l'ordre de la maquette v4).
# (id du registre, libellé, fmt) — fmt appliqué à la valeur BRUTE, jamais recalculée.
_TUILES = [
    ("surface_parcelle_m2", "Surface", "m2"),
    ("zone_plu_famille", "Zone PLU", "classe"),   # FIX-NU3-2 (M-T06) — un seul libellé « Zone PLU »
    ("pente_deg", "Pente", "degre"),
    ("exposition_versant", "Exposition", "classe"),
    ("tfpb_taux_pct", "Taxe foncière", "pct"),
    ("sdp_residuelle_m2", "SDP restante (bâti conservé)", "m2"),
]

_TAG = re.compile(r"<[^>]+>")


def _plain(html_txt: str) -> str:
    """Le texte d'un verdict du Dossier est du HTML (<strong>…) : on le rend en clair pour le chat."""
    return html.unescape(_TAG.sub("", html_txt or "")).strip()


def _scalaire(valeur: Any) -> Any:
    """Un extracteur peut rendre un dict {taux, valeur, median…} : on en tire le scalaire à afficher.
    None si rien de numérique (la tuile est alors omise, jamais un crash ni un JSON brut à l'écran)."""
    if isinstance(valeur, dict):
        for k in ("taux", "taux_communal_pct", "valeur", "median", "pct", "m2", "moy"):
            if isinstance(valeur.get(k), (int, float)):
                return valeur[k]
        return None
    return valeur if isinstance(valeur, (int, float, str)) else None


def _fmt(valeur: Any, kind: str) -> str | None:
    v = _scalaire(valeur)
    if v is None:
        return None
    from ..exports.registre_fmt import fmt_m2, fmt_pct
    try:
        if kind == "m2":
            return fmt_m2(v)
        if kind == "pct":
            return fmt_pct(v)
        if kind == "degre":
            return f"{str(v).replace('.', ',')}°"
        return str(v)
    except (TypeError, ValueError):
        return None


def _fiche(db: Session, idu: str) -> dict | None:
    from fastapi import HTTPException

    from ..api.app import _q_v2_fiche
    try:
        f = _q_v2_fiche(db, idu, run_label=runs.current())
    except HTTPException:
        return None                     # parcelle absente du run servi → pas de résumé (jamais un 500)
    return f if f and f.get("commune") is not None else None


def _valeurs(db: Session, idu: str, fiche: dict) -> dict:
    """{id → Valeur} pour TOUS les ids câblés au robinet : le résumé lit exactement ce que le Dossier lit."""
    from ..exports import robinet_fiche
    return robinet_fiche.collecte(db, idu, list(robinet_fiche.EXTRACTEURS.keys()), fiche=fiche)


def _verdict_section(sec_id: str, valeurs: dict) -> tuple[str, str] | None:
    """Le verdict-phrase d'une section, en CLAIR — les MÊMES moteurs que le Dossier (parité garantie).
    Rend (texte, ton) ou None (pas de verdict pour cette section : pas de ligne vide)."""
    from ..exports.verdicts import verdict_potentiel, verdict_reseaux, verdict_zonage
    if sec_id == "urbanisme":
        v = verdict_zonage(valeurs)
        return (_plain(v[0]), v[1]) if v else None
    if sec_id == "potentiel":
        v = verdict_potentiel(valeurs)
        return (_plain(v[0]), v[1]) if v else None
    if sec_id == "reseaux":
        v = verdict_reseaux(valeurs)
        return (_plain(v[0]), v[1]) if v else None
    if sec_id == "risques":
        av = valeurs.get("aleas_parcelle_liste")
        liste = (av.valeur if av else None) or []
        rouges = [a for a in liste if isinstance(a, dict) and a.get("redhibitoire")]
        if rouges:
            return (_plain(rouges[0].get("libelle") or "Aléa rédhibitoire relevé."), "warn")
        if av is not None:
            return ("Aléas relevés — aucun rédhibitoire.", "neutral")
        return None
    from ..exports.miroir import _verdict_factuel
    fx = _verdict_factuel(sec_id, valeurs)
    return (_plain(fx[0]), fx[1]) if fx else None


def resume_parcelle(db: Session, idu: str) -> dict | None:
    """Le résumé déterministe d'une parcelle : bandeau (6 chiffres) + verdict des 11 sections.
    Aucun modèle. None si la parcelle est absente du run servi."""
    fiche = _fiche(db, idu)
    if fiche is None:
        return None
    valeurs = _valeurs(db, idu, fiche)
    tuiles = []
    for cid, lib, kind in _TUILES:
        v = valeurs.get(cid)
        rendu = _fmt(v.valeur, kind) if v is not None else None
        if rendu is not None:
            # URGENCE-1 (NU-F-026) — on NE sérialise PLUS l'id de registre (`surface_parcelle_m2`,
            # `pente_deg`…) vers le client : il n'est lu ni par le front ni par `phrase()`, seul
            # libellé/valeur le sont. Surface client réduite au strict affichage.
            tuiles.append({"libelle": lib, "valeur": rendu})
    from ..registre.declarations import sections_fiche
    sections = []
    for s in sections_fiche():
        sid = s["id"]
        if sid == "entete":
            continue
        vd = _verdict_section(sid, valeurs)
        if vd is not None:
            # URGENCE-1 (NU-F-026) — id de section (registre) non sérialisé vers le client (non lu).
            sections.append({"titre": s["titre"], "verdict": vd[0], "ton": vd[1]})
    # FIX-PRIX-ET-OPPORTUNITES (lot 1) — commune OFFICIELLE dérivée de l'INSEE de l'IDU (jamais le
    # `parcels.commune` texte qui nommait « Saint-Denis » une parcelle de L'Étang-Salé).
    from ..communes import nom_officiel
    return {"idu": idu, "commune": nom_officiel(idu) or fiche.get("commune"), "tuiles": tuiles,
            "sections": sections, "source": "fiche LABUSE (run servi)", "millesime": runs.current()}


def phrase(resume: dict) -> str:
    """Le texte du résumé, déterministe — servi tel quel en mode dégradé, ou passé au modèle à
    reformuler (le modèle ne choisit ni ne calcule aucun chiffre : ils sont ici)."""
    idu = resume["idu"]
    tete = f"Parcelle {idu} à {resume['commune']}"
    bandeau = " · ".join(f"{t['libelle']} {t['valeur']}" for t in resume["tuiles"])
    lignes = [f"{tete} — {bandeau}." if bandeau else f"{tete}."]
    for sec in resume["sections"]:
        marque = "⚠ " if sec["ton"] == "warn" else ""
        lignes.append(f"• {sec['titre']} : {marque}{sec['verdict']}")
    return "\n".join(lignes)


# ───────────────────────── commune ─────────────────────────
def resume_commune(db: Session, commune: str) -> dict | None:
    """Résumé déterministe d'une commune : le bandeau (chiffres servis à la fiche commune) + une
    ligne factuelle par carte. Mêmes valeurs que `commune_contexte` (la fiche commune écran) —
    aucun calcul, aucune invention. None si la commune est inconnue au contexte."""
    from .outils import resoudre_commune
    resolue = resoudre_commune(commune)
    if resolue is None:
        return None
    from ..api.app import commune_contexte
    c = commune_contexte(resolue, db=db)
    if not c or not (c.get("population") or c.get("foncier")):
        return None

    def g(bloc, cle):
        b = c.get(bloc) or {}
        return b.get(cle) if isinstance(b, dict) else None

    tuiles = []
    for lib, val in (
        ("Habitants", g("population", "habitants")),
        ("Logements", g("population", "logements")),
        ("Parcelles", g("foncier", "n_parcelles")),
        ("Prix ancien", g("comparable", "ancien_median_eur_m2")),
        ("Permis / an", g("permis_bloc", "permis_12m")),
    ):
        if isinstance(val, (int, float)):
            rendu = (f"{val:,}".replace(",", " ") + (" €/m²" if lib == "Prix ancien" else ""))
            tuiles.append({"libelle": lib, "valeur": rendu})
    plu = (c.get("plu_statut") or {}).get("libelle")
    if plu:
        tuiles.append({"libelle": "PLU", "valeur": str(plu)})

    cartes = []

    def carte(titre, txt):
        if txt:
            cartes.append({"titre": titre, "verdict": txt})

    sru = c.get("sru") or {}
    if sru.get("taux_lls") is not None:
        carte("Logement social (SRU)", f"Taux LLS {str(sru['taux_lls']).replace('.', ',')} % — {sru.get('statut') or 'statut non précisé'}.")
    risq = c.get("risques") or {}
    if risq.get("ppr_pct") is not None:
        carte("Risques", f"PPR sur {str(risq['ppr_pct']).replace('.', ',')} % des parcelles de la commune.")  # CHASSE-FIX-1 (C14)
    fisc = c.get("fiscalite") or {}
    # RETOUCHES-1 point 2 — la MÊME ligne que la fiche et le Dossier (producteur unique
    # fiscalite_libelle, déjà calculée dans le bloc fiscalité servi).
    _lignes_tf = fisc.get("lignes") or []
    if _lignes_tf:
        carte("Fiscalité", _lignes_tf[0]["ligne"] + ".")
    comp = c.get("comparable") or {}
    if comp.get("delai_median_mois") is not None:
        carte("Instruction", f"Délai médian d'instruction {comp['delai_median_mois']} mois.")
    fonc = c.get("foncier") or {}
    if fonc.get("classement"):
        carte("Foncier", f"Classement du foncier : {fonc['classement']}.")
    zabc = (c.get("zonage_abc") or {}).get("zone")
    if zabc:
        carte("Zonage A/B/C", f"Commune en zone {zabc} (investissement locatif).")

    return {"commune": resolue, "tuiles": tuiles, "cartes": cartes,
            "source": "fiche commune LABUSE", "millesime": runs.current()}


def phrase_commune(resume: dict) -> str:
    tete = f"Commune de {resume['commune']}"
    bandeau = " · ".join(f"{t['libelle']} {t['valeur']}" for t in resume["tuiles"])
    lignes = [f"{tete} — {bandeau}." if bandeau else f"{tete}."]
    for c in resume["cartes"]:
        lignes.append(f"• {c['titre']} : {c['verdict']}")
    return "\n".join(lignes)


# ───────────────────────── champ précis (ligne déclarée + id) ─────────────────────────
# mot-clé (folded) → (id du registre, libellé). La réponse cite la ligne et son id : plus de champ
# jeté par l'outil (le trou d'outillage constaté à COPILOTE-AUDIT-1 point 3).
_CHAMPS = [
    (("proprietaire", "proprio", "a qui appartient", "appartient-elle", "appartient elle",
      "appartient a", "qui possede", "qui detient", "personne morale", "detenue par", "detenu par"),
     ("type_proprietaire", "Propriétaire")),
    # COPILOTE-5 — le STATUT du PLU AVANT la zone (« plu » nu est happé par la zone sinon).
    (("statut du plu", "plu a jour", "plu approuve", "plu opposable", "date du plu", "a jour",
      "document d'urbanisme opposable", "le plu est-il", "plu en vigueur", "opposable"),
     ("statut_plu", "Statut du PLU")),
    (("taxe d'amenagement", "taxe damenagement", "taxe amenagement", "ta communale", "taux de ta"),
     ("taxe_amenagement_estimee_eur", "Taxe d'aménagement")),
    (("taxe fonciere", "tfpb", "taxe fonciere batie"), ("tfpb_taux_pct", "Taxe foncière (bâti)")),
    (("zone", "zonage", "plu"), ("zone_plu_famille", "Zone PLU")),
    (("risque", "risques", "alea", "aleas", "ppr", "inondation"), ("aleas_parcelle_liste", "Risques et aléas")),
    # COPILOTE-5 — pollution des sols (CASIAS), distincte des aléas PPR.
    (("pollution", "pollue", "polluee", "site pollue", "sol pollue", "casias", "ancien site industriel"),
     ("casias_statut", "Pollution des sols (CASIAS)")),
    (("pente", "denivele"), ("pente_deg", "Pente")),
    (("exposition", "versant", "orientation"), ("exposition_versant", "Exposition")),
    # COPILOTE-5 — surface LIBRE au sol AVANT la surface de parcelle (« surface » happerait sinon).
    (("surface libre", "sol libre", "terrain libre", "espace libre", "surface disponible au sol"),
     ("surface_libre_sol_m2", "Surface libre au sol")),
    (("surface", "superficie", "taille"), ("surface_parcelle_m2", "Surface")),
    (("sdp", "surface de plancher", "constructible restant", "capacite"),
     ("sdp_residuelle_m2", "SDP restante")),  # NU-3-M-T01 : « SDP restante » partout (cf. :34)
    # ═══ COPILOTE-5 — COUVERTURE COMPLÈTE : chaque section de la fiche a son champ, LU du MÊME
    # robinet (robinet_fiche) que l'écran et le Dossier — jamais une 2e source. ═══
    # §1 Identité
    (("adresse", "ou se trouve", "localisation", "ou est-elle situee", "quelle adresse",
      "quelle est l'adresse"), ("adresse_ban", "Adresse")),
    # §3 Bâti
    (("emprise batie", "emprise du bati", "surface batie", "emprise bâtie", "surface au sol du bati"),
     ("emprise_batie_m2", "Emprise bâtie")),
    (("hauteur du bati", "hauteur du batiment", "hauteur existante", "hauteur construite",
      "hauteur batie"), ("hauteur_bati_m", "Hauteur du bâti")),
    (("combien de batiments", "nombre de batiments", "parcelle batie", "deja bati",
      "est-elle batie", "y a-t-il un batiment", "y a-t-il des batiments", "batie ou non"),
     ("n_batiments", "Bâti")),
    (("toiture", "nature du toit", "type de toit", "pente du toit", "toit en"), ("nature_toit", "Toiture")),
    (("piscine",), ("piscine_m2", "Piscine")),
    # §6 Réseaux et desserte
    (("fibre", "ftth", "internet", "tres haut debit"), ("fibre_parcelle", "Fibre optique")),
    (("viabilis", "raccord", "reseaux", "vrd", "eau potable", "assainissement", "electricite",
      "desserte en reseaux"), ("viabilisation_verdict", "Viabilisation / réseaux")),
    (("arret de bus", "transport en commun", "arret de transport", "tcsp", "ligne de bus",
      "transports en commun"), ("distance_arret_m", "Transport en commun")),
    # §4/7 Urbanisme — servitudes & dispositifs
    (("servitude", "dispositif", "emplacement reserve", "droit de preemption", "dpu",
      "monument historique", "batiment de france", "abf"), ("dispositifs_parcelle", "Dispositifs et servitudes")),
    (("rtaa", "reglementation thermique", "confort thermique dom"), ("rtaa_exigences", "RTAA DOM")),
    # §9 Marché
    (("prix du terrain", "prix au m2 du terrain", "valeur du terrain", "combien vaut le terrain",
      "prix du foncier", "prix du m2 de terrain"), ("prix_terrain_secteur_eur_m2", "Prix du terrain (secteur)")),
    (("derniere vente", "deja vendu", "ventes autour", "dvf", "prix du marche", "prix au m2",
      "prix de l'ancien", "transactions", "prix de vente"), ("dvf_parcelle_liste", "Marché — ventes")),
    (("prix d'achat", "achetee pour", "acquise pour", "dernier prix paye", "prix paye"),
     ("prix_achat_historique_eur", "Dernier prix d'achat")),
    # §11 Potentiel
    (("potentiel constructible", "potentiel de la parcelle", "capacite constructible",
      "capacite de la parcelle"), ("potentiel_verdict", "Potentiel constructible")),
    (("combien de logements", "capacite en logements", "nombre de logements constructibles",
      "combien de lots"), ("capacite_logements", "Capacité en logements")),
    # §10 Quartier
    (("quartier", "iris", "voisinage", "habitants du quartier", "population du quartier",
      "environnement urbain"), ("iris_quartier", "Quartier")),
    (("ecole", "commerce", "equipements a proximite", "commodites", "services a proximite",
      "a proximite", "autour de la parcelle"), ("equipements_proximite_liste", "Équipements à proximité")),
    # §3/9 DPE
    (("dpe", "diagnostic de performance", "classe energetique", "performance energetique"),
     ("dpe_connu", "DPE")),
]


# NU-E-048 — la VRAIE source de chaque champ qualitatif (un verdict de zone vient du PLU, pas du
# cadastre ; les aléas/PPR de la DEAL ; le propriétaire personne morale de la DGFiP). Défaut
# « fiche LABUSE » pour les champs mesurés sans source réglementaire distincte (pente, surface…).
_SOURCE_CHAMP = {
    "zone_plu_famille": "PLU — zonage (règlement communal)",
    "aleas_parcelle_liste": "DEAL Réunion — PPR / aléas",
    "type_proprietaire": "DGFiP — propriétaire (personnes morales : SIREN public)",
    "surface_parcelle_m2": "cadastre",
    "taxe_amenagement_estimee_eur": "barème taxe d'aménagement (service-public.gouv.fr)",
    # COPILOTE-5 — la vraie source de chaque section (le même producteur que la fiche écran).
    "statut_plu": "GPU — document d'urbanisme opposable",
    "casias_statut": "BASIAS / CASIAS — sites et sols pollués",
    "surface_libre_sol_m2": "LABUSE — surface libre au sol (CoSIA / BD TOPO)",
    "adresse_ban": "BAN — Base Adresse Nationale",
    "emprise_batie_m2": "BD TOPO / CoSIA — emprise bâtie",
    "hauteur_bati_m": "BD TOPO — hauteur du bâti",
    "n_batiments": "BD TOPO — bâti",
    "nature_toit": "CoSIA / BD ORTHO — toiture",
    "piscine_m2": "CoSIA — détection piscine",
    "fibre_parcelle": "ARCEP — déploiement fibre (FTTH)",
    "viabilisation_verdict": "LABUSE — faisceau viabilisation (faits réseaux)",
    "distance_arret_m": "Réseaux de transport (Citalis / Car Jaune…)",
    "dispositifs_parcelle": "GPU — servitudes et dispositifs (SUP)",
    "rtaa_exigences": "RTAA DOM (arrêté)",
    "prix_terrain_secteur_eur_m2": "DVF — terrains du secteur",
    "dvf_parcelle_liste": "DVF — ventes du secteur",
    "prix_achat_historique_eur": "DVF — dernière mutation",
    "potentiel_verdict": "LABUSE — potentiel (moteur de la fiche)",
    "capacite_logements": "Étude de faisabilité",
    "iris_quartier": "INSEE — IRIS (quartier)",
    "equipements_proximite_liste": "BPE INSEE / IGN — équipements de proximité",
    "dpe_connu": "ADEME — DPE",
}


def _source_champ(cid: str) -> str:
    return _SOURCE_CHAMP.get(cid, "fiche LABUSE")


# NU-E-046 — la COPROPRIÉTÉ est un fait qualitatif lu DIRECTEMENT de la fiche servie (drapeau
# `score_v2.copro` + répertoire RNIC `coproprietes`), hors registre robinet. Réponse OUI/NON
# DÉTERMINISTE (aucun LLM), source RNIC. Détecteur : un mot de copropriété + une tournure de STATUT
# (pas une NOTION « c'est quoi une copropriété » → voie explication).
_COPRO_KW = ("copropriete", "copro", "en copro", "syndic", "coproprietaire", "lots de copropriete")


def est_question_copro(message: str) -> bool:
    m = _fold_py(message.lower())
    if not any(k in m for k in _COPRO_KW):
        return False
    if any(k in m for k in ("c'est quoi", "c est quoi", "qu'est-ce", "qu est-ce", "explique",
                            "definition", "a quoi sert")):
        return False
    return True


def reponse_copro(db: Session, idu: str) -> dict | None:
    """OUI/NON déterministe sur la copropriété d'une parcelle (score_v2.copro + RNIC). Source RNIC.
    Inconnu (ni drapeau ni RNIC servis au run) → on le DIT (« je n'ai pas cette donnée »), JAMAIS un
    « non » par défaut (Règle à graver). None si la parcelle est absente du run servi."""
    fiche = _fiche(db, idu)
    if fiche is None:
        return None
    sv2 = fiche.get("score_v2") or {}
    copros = fiche.get("coproprietes") or []
    src = "RNIC — répertoire des copropriétés"
    if "copro" not in sv2 and not copros:
        return {"texte": f"Je n'ai pas l'information de copropriété pour la parcelle {idu} au run servi.",
                "champ_id": "copro", "valeur": None, "source": src}
    copro = bool(sv2.get("copro")) or bool(copros)
    if copro:
        n = sum(int(c.get("nb_lots_total") or 0) for c in copros if isinstance(c, dict))
        detail = f" ({n} lots recensés au répertoire des copropriétés)" if n else ""
        texte = f"Oui, la parcelle {idu} est en copropriété{detail}."
    else:
        texte = (f"Non, la parcelle {idu} n'est pas répertoriée en copropriété "
                 "(d'après le répertoire des copropriétés servi).")
    return {"texte": texte, "champ_id": "copro", "valeur": copro, "source": src}


def _mot_present(m: str, k: str) -> bool:
    """COPILOTE-5 — un mot-clé COURT acronymique (≤ 3 car. : « plu », « dpu », « ppr », « dpe ») est
    cherché avec BORNES DE MOT (sinon « plu » est happé par « plus proche ») ; un mot-clé plus long
    reste en sous-chaîne (pour attraper les pluriels/accords : « servitude » → « servitudes »,
    « viabilis » → « viabilisée »)."""
    if len(k.replace(" ", "")) <= 3:
        return re.search(r"\b" + re.escape(k) + r"\b", m) is not None
    return k in m


def _quel_champ(message: str) -> tuple[str, str] | None:
    # L'ordre du tableau reste la priorité (le plus spécifique d'abord).
    m = _fold_py(message.lower())
    for kws, cible in _CHAMPS:
        if any(_mot_present(m, k) for k in kws):
            return cible
    return None


def champ_precis(db: Session, idu: str, message: str) -> dict | None:
    """Une question sur UN champ de la fiche → la ligne DÉCLARÉE et son id (jamais un champ jeté).
    Rend {texte, champ_id, valeur, source} ou None si la demande ne vise pas un champ connu."""
    # NU-E-046 — la copropriété d'abord : fait qualitatif lu direct de la fiche (hors registre robinet).
    if est_question_copro(message):
        return reponse_copro(db, idu)
    cible = _quel_champ(message)
    if cible is None:
        return None
    cid, libelle = cible
    fiche = _fiche(db, idu)
    if fiche is None:
        return None
    valeurs = _valeurs(db, idu, fiche)
    v = valeurs.get(cid)
    if v is None or v.valeur in (None, "", [], {}):
        return {"texte": f"{libelle} : non renseigné pour la parcelle {idu} (donnée absente au run servi).",
                "champ_id": cid, "valeur": None, "source": _source_champ(cid)}
    texte = _rendre_champ(cid, libelle, v.valeur, valeurs)
    # FIX-PRIX-ET-OPPORTUNITES (lot 3) — une capacité constructible est un MAXIMUM réglementaire ; on
    # ajoute la mention mesurée (volet D : ~½ utilisé en médiane par les permis réels).
    if cid == "sdp_residuelle_m2":
        from ..capacite_max import MENTION_COURTE as _CAP
        texte = f"{texte} C'est un {_CAP}."
    # CHASSE-APP-FIX-2 (point 4 U) — la source LISIBLE ne porte plus le cid (nom de colonne) : il
    # restait affiché dans l'accueil Copilote (sources.join). Le cid vit dans `champ_id` (structuré).
    # NU-E-048 — et la source est celle du FAIT (zone → PLU, aléas → DEAL, propriétaire → DGFiP),
    # jamais un « cadastre »/« fiche » générique sur un verdict réglementaire.
    return {"texte": texte, "champ_id": cid, "valeur": v.valeur, "source": _source_champ(cid)}


def _rendre_champ(cid: str, libelle: str, valeur: Any, valeurs: dict) -> str:
    """Rendu en clair d'un champ précis — lisible, jamais le JSON brut.

    CHASSE-APP-FIX-2 (point 4 U) — on NE cite PLUS l'id technique du registre (cid) entre
    parenthèses dans la réponse : « (surface_parcelle_m2) », « (zone_plu_famille) » fuitaient des
    noms de colonnes au client. La traçabilité reste côté serveur via le champ `champ_id` renvoyé
    par champ_precis() (structuré, non affiché), plus dans le texte ni dans la source lisible."""
    from ..exports.registre_fmt import fmt_m2, fmt_pct
    if cid == "type_proprietaire":
        return f"Propriétaire : {str(valeur).split(' (SIREN')[0]}."
    if cid == "zone_plu_famille":
        from ..exports.verdicts import zone_libelle
        lib = zone_libelle(valeurs) or f"famille {valeur}"
        return f"Zone PLU : {lib}."
    if cid == "aleas_parcelle_liste" and isinstance(valeur, list):
        red = [a for a in valeur if isinstance(a, dict) and a.get("redhibitoire")]
        if red:
            return f"Risques : {red[0].get('libelle')} — rédhibitoire."
        libs = [a.get("libelle") for a in valeur if isinstance(a, dict) and a.get("libelle")]
        return f"Risques : {' ; '.join(libs[:3]) if libs else 'aucun aléa rédhibitoire relevé'}."
    if cid == "taxe_amenagement_estimee_eur" and isinstance(valeur, dict):
        taux = valeur.get("taux_communal_pct")
        mill = valeur.get("taux_communal_millesime") or ""
        # (mill) = le millésime (année) du taux, pas un nom de colonne — on le garde.
        return (f"Taxe d'aménagement — taux communal {fmt_pct(taux)}" + (f" ({mill})" if mill else "") + ".")
    if cid in ("surface_parcelle_m2", "sdp_residuelle_m2"):
        return f"{libelle} : {fmt_m2(valeur)}."
    if cid in ("tfpb_taux_pct",):
        # RETOUCHES-1 point 2 — la MÊME ligne canonique que la fiche et le Dossier (producteur unique).
        from ..fiscalite_libelle import lignes_taxe_fonciere
        _lignes = lignes_taxe_fonciere(valeur if isinstance(valeur, dict) else {})
        if _lignes:
            return f"{_lignes[0]['ligne']}."
        return f"{libelle} : non renseigné."
    if cid == "pente_deg":
        return f"Pente : {str(valeur).replace('.', ',')}°."
    # ═══ COPILOTE-5 — rendu des sections ajoutées (lu du MÊME robinet que la fiche) ═══
    if cid == "adresse_ban":
        return f"Adresse : {valeur}."
    if cid == "statut_plu" and isinstance(valeur, dict):
        return (valeur.get("libelle") or "Statut du PLU : non précisé").rstrip(".") + "."
    if cid == "surface_libre_sol_m2":
        return f"Surface libre au sol : {fmt_m2(valeur)}."
    if cid == "emprise_batie_m2":
        return f"Emprise bâtie : {fmt_m2(valeur)} au sol."
    if cid == "hauteur_bati_m":
        return f"Hauteur du bâti : {str(valeur).replace('.', ',')} m (faîtage)."
    if cid == "n_batiments":
        n = int(valeur) if isinstance(valeur, (int, float)) else 0
        return (f"{n} bâtiment{'s' if n > 1 else ''} sur la parcelle." if n
                else "Parcelle non bâtie (aucun bâtiment cartographié).")
    if cid == "nature_toit":
        return f"Toiture : {valeur}."
    if cid == "piscine_m2":
        return f"Piscine détectée — environ {fmt_m2(valeur)}."
    if cid == "fibre_parcelle" and isinstance(valeur, dict):
        if valeur.get("ftth"):
            ops = ", ".join(valeur.get("operateurs") or [])
            return "Fibre optique (FTTH) disponible" + (f" — opérateurs : {ops}." if ops else ".")
        return f"Fibre : {valeur.get('etat') or 'non desservie'}."
    if cid == "viabilisation_verdict" and isinstance(valeur, dict):
        return (valeur.get("libelle") or "Viabilisation : à confirmer").rstrip(".") + "."
    if cid == "distance_arret_m" and isinstance(valeur, dict):
        a = valeur.get("arret") or {}
        if a.get("nom"):
            res = f" ({a['reseau']})" if a.get("reseau") else ""
            return f"Arrêt le plus proche : {a['nom']}{res} à {a.get('distance_m')} m."
        return "Transport en commun : aucun arrêt relevé à proximité."
    if cid == "dispositifs_parcelle" and isinstance(valeur, list):
        bouts = [f"{d.get('categorie')} sur {str(d.get('part_pct')).replace('.0', '')} %"
                 for d in valeur[:3] if isinstance(d, dict) and d.get("categorie")]
        return ("Dispositifs / servitudes : " + " ; ".join(bouts) + "."
                if bouts else "Aucun dispositif ni servitude relevé sur la parcelle.")
    if cid == "prix_terrain_secteur_eur_m2" and isinstance(valeur, dict):
        p = valeur.get("prix_m2")
        return (f"Prix du terrain au secteur : {p} €/m² (médiane de {valeur.get('n')} ventes, "
                f"{valeur.get('perimetre')}, {valeur.get('fenetre')}).")
    if cid == "dvf_parcelle_liste" and isinstance(valeur, list) and valeur:
        d = valeur[0]
        return (f"Marché du secteur : médiane {d.get('mediane_prix_m2')} €/m² — {d.get('type_bien')} "
                f"({d.get('n_ventes')} ventes, {d.get('fenetre')}).")
    if cid == "prix_achat_historique_eur":
        v = _scalaire(valeur)
        return (f"Dernier prix d'achat connu : {f'{int(v):,}'.replace(',', ' ')} €."
                if isinstance(v, (int, float)) else f"{libelle} : {valeur}.")
    if cid == "potentiel_verdict" and isinstance(valeur, dict):
        calc = valeur.get("calcul") or {}
        sdp = calc.get("sdp_max_m2")
        return (f"Potentiel constructible : jusqu'à {fmt_m2(sdp)} de surface de plancher (indicatif) — "
                "voir l'Étude de faisabilité pour le détail." if sdp is not None
                else "Potentiel constructible : voir l'Étude de faisabilité.")
    if cid == "capacite_logements" and isinstance(valeur, dict):
        return "Capacité en logements : " + (valeur.get("texte") or "voir l'Étude de faisabilité") + "."
    if cid == "iris_quartier" and isinstance(valeur, dict):
        return (f"Quartier (IRIS) : {valeur.get('nom')} — {valeur.get('logements')} logements "
                f"({valeur.get('millesime')}).")
    if cid == "equipements_proximite_liste" and isinstance(valeur, list):
        bouts = [f"{e.get('nom')} ({e.get('distance_m')} m)"
                 for e in valeur[:3] if isinstance(e, dict) and e.get("nom")]
        return "À proximité : " + " ; ".join(bouts) + "." if bouts else "Aucun équipement relevé à proximité."
    if cid == "dpe_connu":
        return f"DPE : {valeur}." if isinstance(valeur, (str, int, float)) else f"{libelle} : connu."
    # SÉCURITÉ COPILOTE-5 — jamais un dict/list brut au client : on renvoie à la fiche plutôt que du JSON.
    if isinstance(valeur, (dict, list)):
        return f"{libelle} : voir la fiche parcelle pour le détail."
    return f"{libelle} : {valeur}."
