"""COURRIER-2 Lot 3 — COMPOSITION du courrier (recto + verso), source unique front ↔ back.

Textes EXACTS fournis par Vic (21/09) — NE PAS reformuler. Le corps est composé
déterministiquement à partir des seules données réelles de la parcelle et du compte émetteur ;
aucune affirmation de potentiel/valorisation/valeur/logements/SDP. L'ouverture (A→E) est choisie,
première applicable, selon les faits ; une donnée manquante fait retomber sur une ouverture neutre.

Le PDF (api/courrier.py) ET l'aperçu front lisent CE module — jamais deux textes.
"""
from __future__ import annotations

import re

from sqlalchemy import text

from . import courrier_adressage as ca

X_ANNEES_DVF = 3          # fenêtre DVF « secteur actif » (aligne marche_service : 500 m / 3 ans)
RAYON_DVF_M = 500
SEUIL_SECTEUR_ACTIF = 8   # N ≥ 8 mutations → ouverture C (même seuil que marche_service)
_RISK_LAYERS = ("risques", "ravine", "trait_de_cote")   # aléas « certains » = HARD_EXCLUDE

# ─────────────────────────── TEXTES FIXES (Vic — ne pas reformuler) ───────────────────────────
_INTRO = ("LABUSE est une plateforme d'intelligence foncière spécialisée sur La Réunion. Elle croise "
          "des dizaines de sources cadastrales, réglementaires, immobilières et territoriales afin de mieux "
          "comprendre les caractéristiques et les règles qui concernent chaque parcelle.")
_PHRASE_OCCUPANT = ("Ce courrier est destiné au propriétaire de la parcelle {reference}. Si vous n'en êtes "
                    "pas le propriétaire, nous vous remercions de bien vouloir le lui transmettre.")
_PARA_VERSO = ("Vous trouverez au dos une synthèse des principales informations dont nous disposons sur cette "
               "parcelle : ses caractéristiques cadastrales, son contexte réglementaire et quelques repères "
               "sur son environnement immobilier.")
_PARA_OFFRE = ("Si vous souhaitez aller plus loin, nous pouvons vous adresser gratuitement une analyse plus "
               "complète de votre terrain : règles d'urbanisme identifiées, contraintes connues, "
               "caractéristiques de la parcelle et données immobilières disponibles autour de celle-ci. "
               "Il suffit de la demander à contact@labuse.immo.")
_PARA_MAJ = ("Les données foncières et réglementaires évoluent dans le temps. Vous pourrez donc demander une "
             "nouvelle analyse ultérieurement afin de disposer d'informations actualisées.")
_PIED = ("Analyse réalisée avec LABUSE, plateforme d'intelligence foncière spécialisée sur La Réunion, pour "
         "le compte de {societe}. Les informations présentées sont issues des données disponibles au moment "
         "de l'analyse et ne constituent ni une autorisation d'urbanisme, ni une offre d'achat, ni un mandat, "
         "ni un conseil juridique.")
_PIED_STOP = ("Vous ne souhaitez plus recevoir de courrier de notre part : écrivez à stop@labuse.immo en "
              "indiquant la référence cadastrale {reference}.")

# ── OUVERTURES A→E (Vic — ne pas reformuler ; [adresse] manquante → « La parcelle [référence] ») ──
_A = ("La parcelle {situee}, d'une surface cadastrale de {surface} m², est actuellement identifiée comme non "
      "bâtie dans les données disponibles. Elle se situe en zone {zone} du document d'urbanisme actuellement "
      "intégré par LABUSE.")
_B = ("La parcelle {situee} est déjà bâtie. Les données réglementaires actuellement intégrées par LABUSE "
      "indiquent qu'elle mérite néanmoins une analyse complémentaire de ses possibilités d'évolution.")
_C = ("Plusieurs mutations immobilières ont été publiées récemment autour de la parcelle {situee}. Elles "
      "permettent de disposer de repères récents sur l'activité immobilière du secteur : {n} mutations "
      "publiées dans le périmètre analysé sur les {x} dernières années.")
_D = ("La parcelle {situee}, à {commune}, fait partie des biens analysés par LABUSE dans votre secteur. Elle "
      "se situe en zone {zone} du document d'urbanisme actuellement intégré.")
_E = ("La parcelle {situee}, à {commune}, fait partie des biens analysés par LABUSE dans votre secteur. Nous "
      "avons regroupé plusieurs informations cadastrales, réglementaires et immobilières disponibles à son sujet.")


def _situee(d: dict) -> str:
    """« située [adresse] » si l'adresse existe, sinon « [référence] » (Vic : « La parcelle [référence] »)."""
    return f"située {d['adresse']}" if d.get("adresse") else d["reference"]


def _synthese(db, idu: str) -> dict:
    """Faits réels de la parcelle pour l'ouverture + le verso. Défensif : une source absente dégrade
    (zone None, n_mutations 0, risques []) — jamais une exception, jamais une valeur inventée."""
    row = db.execute(text("""
        SELECT p.id, p.idu, p.section, p.numero, p.commune, round(p.surface_m2)::int AS surface,
               (fb.idu IS NOT NULL) AS batie, (pm.idu IS NOT NULL) AS pm
        FROM parcels p
        LEFT JOIN parcel_filtre_bati fb ON fb.idu = p.idu
        LEFT JOIN parcelle_personne_morale pm ON pm.idu = p.idu
        WHERE p.idu = :i"""), {"i": idu}).mappings().first()
    reference = idu
    d = {"idu": idu, "reference": idu, "commune": None, "surface": None, "batie": False,
         "pm": False, "adresse": None, "zone": None, "zone_document": None, "zone_calibree": False,
         "n_mutations": 0, "x_annees": X_ANNEES_DVF, "risques": []}
    if row:
        reference = " ".join(x for x in (row["section"], row["numero"]) if x) or idu
        d.update(reference=reference, commune=row["commune"], surface=row["surface"],
                 batie=bool(row["batie"]), pm=bool(row["pm"]))
    d["adresse"] = ca.courrier.adresse_ban_parcelle(db, idu)
    # zone PLU + calibration
    try:
        z = db.execute(text("SELECT zone_lib, zone_libelle FROM parcel_zone_plu WHERE idu = :i"),
                       {"i": idu}).mappings().first()
        if z and z["zone_lib"]:
            d["zone"] = z["zone_lib"]
            d["zone_document"] = z["zone_libelle"]
            from .plu_reglement import resolve_reglement
            rg = resolve_reglement(d["commune"], z["zone_lib"])
            d["zone_calibree"] = bool(rg and rg.get("calibree"))
    except Exception:  # noqa: BLE001 — zone optionnelle
        pass
    # DVF : mutations dans le périmètre sur X ans (secteur actif)
    if row:
        try:
            d["n_mutations"] = int(db.execute(text(f"""
                SELECT count(*) FROM dvf_mutations_parcelle m
                JOIN parcels pp ON pp.idu = m.id_parcelle
                WHERE ST_DWithin(pp.geom_2975, (SELECT geom_2975 FROM parcels WHERE idu = :i), :r)
                  AND m.date_mutation >= current_date - make_interval(years => :x)"""),
                {"i": idu, "r": RAYON_DVF_M, "x": X_ANNEES_DVF}).scalar() or 0)
        except Exception:  # noqa: BLE001 — DVF optionnel
            d["n_mutations"] = 0
        # risques CERTAINS (HARD_EXCLUDE des couches d'aléas)
        try:
            rows = db.execute(text(
                "SELECT DISTINCT layer_name, detail FROM cascade_results "
                "WHERE parcel_id = :pid AND result = 'HARD_EXCLUDE' AND layer_name = ANY(:ls)"),
                {"pid": row["id"], "ls": list(_RISK_LAYERS)}).mappings().all()
            d["risques"] = [re.sub(r"^(Exclue?|Exclu)\s*:\s*", "", (r["detail"] or r["layer_name"]).strip())
                            for r in rows if (r["detail"] or r["layer_name"])]
        except Exception:  # noqa: BLE001 — risques optionnels
            d["risques"] = []
    return d


def choisir_ouverture(d: dict) -> tuple[str, str]:
    """Une seule ouverture, première applicable dans l'ordre A→E (règles Vic)."""
    situee, commune, zone = _situee(d), d.get("commune") or "votre commune", d.get("zone")
    if d.get("pm") and not d.get("batie") and zone:                       # A — terrain non bâti (PM)
        return "A", _A.format(situee=situee, surface=d.get("surface") or "—", zone=zone)
    if d.get("batie") and d.get("zone_calibree"):                          # B — bâtie, zone calibrée
        return "B", _B.format(situee=situee)
    if (d.get("n_mutations") or 0) >= SEUIL_SECTEUR_ACTIF:                  # C — secteur actif
        return "C", _C.format(situee=situee, n=d["n_mutations"], x=d.get("x_annees", X_ANNEES_DVF))
    if zone:                                                               # D — neutre avec zone
        return "D", _D.format(situee=situee, commune=commune, zone=zone)
    return "E", _E.format(situee=situee, commune=commune)                  # E — neutre sans zone


def _telephone(coordonnees: str | None) -> str | None:
    if not coordonnees:
        return None
    m = re.search(r"(0\d[\s.\-]?(?:\d{2}[\s.\-]?){4})", coordonnees)
    return m.group(1).strip() if m else None


def expediteur_du_compte(marque: dict | None, commune: str | None) -> dict:
    """Signataire du courrier depuis la marque blanche du compte (jamais inventé)."""
    marque = marque or {}
    societe = (marque.get("raison_sociale") or "").strip() or "LABUSE"
    return {"signataire": (marque.get("signataire") or "").strip() or None,
            "societe": societe,
            "commune": commune or None,
            "telephone": _telephone(marque.get("coordonnees"))}


def _signature(exp: dict) -> str:
    """« Cette étude vous est offerte par [Prénom Nom], [société], qui intervient à [commune]. Il est
    joignable au [téléphone]… » — clauses absentes retirées proprement (jamais un [champ] vide)."""
    par = f"{exp['signataire']}, {exp['societe']}" if exp.get("signataire") else exp["societe"]
    ou = f" qui intervient à {exp['commune']}" if exp.get("commune") else ""
    s = f"Cette étude vous est offerte par {par}{ou}."
    if exp.get("telephone"):
        s += f" Il est joignable au {exp['telephone']} si vous souhaitez échanger au sujet de votre bien."
    s += " Cette démarche ne vous engage à rien."
    return s


def composer(db, idu: str, *, resolution: dict, marque: dict | None = None) -> dict:
    """Compose le courrier COMPLET (recto + verso) pour une parcelle et un compte émetteur.

    Retourne {recto, verso, ouverture, reference, situee, expediteur, synthese}. Le recto est le
    texte prêt à imprimer (objet + phrase d'entrée éventuelle + corps + signature) ; `verso` est la
    liste de lignes de la synthèse. Aucun placeholder {…} ne subsiste (garde de dépôt Lot 3)."""
    d = _synthese(db, idu)
    exp = expediteur_du_compte(marque, d.get("commune"))
    ref, commune = d["reference"], d.get("commune") or ""
    _code, ouv = choisir_ouverture(d)

    lignes = [f"Objet : Votre parcelle {ref}, à {commune}", ""]
    if resolution.get("type") == "occupant":     # phrase d'entrée UNIQUEMENT pour les plis « à l'occupant »
        lignes += [_PHRASE_OCCUPANT.format(reference=ref), ""]
    lignes += ["Madame, Monsieur,", "", _INTRO, "", ouv, "", _PARA_VERSO, "", _PARA_OFFRE, "",
               _PARA_MAJ, "", _signature(exp), "", "Cordialement,"]
    recto = "\n".join(lignes)

    verso = composer_verso(d)
    return {"recto": recto, "verso": verso, "ouverture": _code, "reference": ref,
            "expediteur": exp, "synthese": d}


def composer_verso(d: dict) -> list[str]:
    """Synthèse verso — faits seulement, JAMAIS une valeur du terrain (Vic)."""
    lignes: list[str] = ["Synthèse de la parcelle"]
    id_lignes = [("Référence cadastrale", d.get("reference")),
                 ("Commune", d.get("commune")),
                 ("Adresse", d.get("adresse")),
                 ("Surface cadastrale", f"{d['surface']} m²" if d.get("surface") is not None else None)]
    lignes += [f"{k} : {v}" for k, v in id_lignes if v]
    if d.get("zone"):
        doc = d.get("zone_document")
        doc_txt = f" — {doc}" if doc and doc.strip() and doc.strip() != d["zone"] else ""
        lignes.append(f"Zone d'urbanisme : {d['zone']}{doc_txt}"
                      + (" (règles calibrées)" if d.get("zone_calibree") else ""))
    if d.get("risques"):
        lignes.append("Contraintes connues : " + " ; ".join(d["risques"][:4]))
    if (d.get("n_mutations") or 0) > 0:
        lignes.append(f"Environnement immobilier : {d['n_mutations']} mutation(s) publiée(s) "
                      f"dans le périmètre analysé sur les {d.get('x_annees', X_ANNEES_DVF)} dernières années.")
    return lignes
