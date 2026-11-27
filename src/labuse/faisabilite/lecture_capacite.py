"""Lecture des surfaces de plancher d'un projet et des conditions d'ouverture de ses zones AU."""
from sqlalchemy import text

from .au_ouverture import classify
from .au_statut import CLASSE_AU_FERMEE, classify_au_statut
from .constructibilite import AU_SOUS_PLANCHER, DECLASSE_AU_STATUT_INCONNU
from .zonage import resolve_zone


def marques_ouverture(db, idus):
    """Marques du suivi AU, y compris quand le détail géométrique est indisponible."""
    if not db.scalar(text("SELECT to_regclass('parcel_au_statut')")):
        return {}
    rows = db.execute(text("""
        SELECT idu, zone_lib, classe, motif FROM parcel_au_statut
        WHERE idu = ANY(:idus)
    """), {"idus": idus}).mappings()
    return {r["idu"]: r for r in rows}


def statuts_ouverture(idu, commune, parts, marque=None, *, union=False):
    """Conditions applicables aux portions AU, y compris les zones secondaires."""
    reserves = {}
    fermees = set()
    for part in parts:
        code = part.get("zone")
        if part.get("fam") != "AU" or not code or code in reserves:
            continue
        regime = classify(idu[:5], code, part.get("surface_m2"))
        classe_reglement, motif_reglement = classify_au_statut(code, commune)
        classe, motif = regime or (classe_reglement, motif_reglement)
        # Le phasage dépendant d'un tiers reste à vérifier. Une condition communale
        # générique ne rouvre pas une zone où le règlement exclut la construction neuve.
        if classe == CLASSE_AU_FERMEE or (classe_reglement == CLASSE_AU_FERMEE and classe != DECLASSE_AU_STATUT_INCONNU):
            fermees.add(code)
            continue
        if classe:
            reserves[code] = motif
        elif resolve_zone(code, commune) is None:
            reserves[code] = "Règlement indisponible. Vérifier l'ouverture auprès du service urbanisme."
    if marque and marque["motif"]:
        code = marque["zone_lib"] or "Zone AU"
        if marque["classe"] == CLASSE_AU_FERMEE:
            fermees.add(code)
        elif marque["classe"] == AU_SOUS_PLANCHER:
            if not union:
                reserves[code] = marque["motif"]
        else:
            reserves.setdefault(code, marque["motif"])
    return {code: motif for code, motif in reserves.items() if code not in fermees}, fermees


def m2(valeur):
    return f"{float(valeur):,.0f}".replace(",", " ") + " m²"


def lecture_parcelle(surface, motif, portion, reserves):
    """Distingue la surface calculée pour un scénario du chiffre que l'on peut retenir."""
    valeur = (surface or {}).get("valeur_m2")
    source = (surface or {}).get("source")
    if reserves:
        message = "Capacité à vérifier — aucune surface de plancher retenue avant vérification."
        if valeur is not None and not motif:
            message += f" Hypothèse de reconstruction : {m2(valeur)} ({source})."
        message += " " + " ".join(f"{code} — {texte}" for code, texte in reserves.items())
        message += " Confirmer ces conditions auprès du service urbanisme avant de retenir le montant du bilan."
    elif motif or valeur is None:
        message = motif if (motif or "").startswith("Capacité non calculée") else "Capacité non calculée."
        if not motif:
            message += " Vérifier les données de zonage et de faisabilité avant de chiffrer le terrain."
    else:
        message = f"Capacité estimée — {m2(valeur)} de plancher retenus en reconstruction ({source})."
    if motif and motif not in message:
        message += " " + motif
    if portion:
        message += " " + portion
    return message


def lecture_union(zones, reserves, reconstruction, fermees=()):
    """Sur l'union, les SDP par zone proviennent du calcul après fusion des géométries."""
    if reconstruction is None:
        texte = "Capacité non calculée pour l'assemblage. Vérifier le zonage et l'emprise disponible après les reculs."
        if fermees:
            texte = "Capacité non calculée pour l'assemblage après exclusion des zones fermées."
        if reserves:
            texte = "Capacité à vérifier — aucune surface de plancher retenue pour l'assemblage."
        parties = []
    else:
        parties = [z for z in zones if z.get("sdp_m2", 0) > 0]
        certaines = [z for z in parties if z["zone"] not in reserves]
        conditionnelles = [z for z in parties if z["zone"] in reserves]
        if conditionnelles:
            texte = ("Capacité à vérifier — " + (f"{m2(sum(z['sdp_m2'] for z in certaines))} de plancher "
                     "estimés en reconstruction hors portions à vérifier." if certaines else
                     "aucune surface de plancher retenue avant vérification."))
        else:
            texte = f"Capacité estimée pour l'assemblage — {m2(reconstruction)} de plancher en reconstruction."
    for zone in parties:
        code = zone["zone"]
        texte += f" {code} : {m2(zone['sdp_m2'])}" + (" à vérifier." if code in reserves else " estimés.")
    for code in sorted(fermees):
        texte += f" {code} — zone à urbaniser fermée, exclue de la capacité de construction neuve."
    for code, raison in reserves.items():
        inclus = any(z["zone"] == code for z in parties)
        texte += f" {code} — " + ("" if inclus else "portion exclue de la capacité annoncée. ") + raison
    return texte, any(z["zone"] in reserves for z in parties)
