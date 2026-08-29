"""RADAR-HTML (Lot 1) — INGESTION d'une page de résultats HTML déposée par Vic.

Chemin d'entrée UNIQUE du Radar (remplace capture d'écran + agent vision). Enchaîne :
  parseur __NEXT_DATA__ (html_next, échec bruyant) → cohérence (Lot 2) → rattachement (Lot 3) →
  upsert IDEMPOTENT par list_id (MAJ + historisation des baisses de prix) → archivage du fichier.

Doctrine §2 : aucun réseau. `first_publication_date` fait foi (nouveauté / « repéré le ») ; `index_date`
ne sert QU'À constater une republication (Lot 5) — elle ne crée jamais d'annonce.
"""
from __future__ import annotations

import hashlib
import json

from sqlalchemy import text
from sqlalchemy.orm import Session

from . import coherence, html_next, portails, rattachement_html
from .intake import resoudre_commune
from .tables import (EV_A_QUALIFIER, EV_BAISSE_PRIX, EV_DEPOT_HTML, EV_NOUVELLE, depots_dir,
                     depots_dir_writable, enregistrer_fraicheur, journaliser)


class DepotStockageError(RuntimeError):
    """RADAR-RECETTE-1 D4 — l'archivage du dépôt a échoué à l'ÉCRITURE DISQUE. Le message NOMME le
    chemin fautif (jamais « réseau ou serveur ») : un échec d'écriture se cherche sur le disque."""

# colonnes de pige_faits alimentées depuis un enregistrement aplati (clé faits ← clé rec).
_FAITS_MAP = {
    "prix": "prix", "type_bien": "type", "pieces": "pieces", "surface_hab": "surface_hab",
    "surface_terrain": "surface_terrain", "dpe_classe": "dpe_classe", "ges_classe": "dpe_ges",
    "particulier_pro": "owner_type", "annee_construction": "annee_construction",
    "etat_bien": "etat_bien", "taxe_fonciere": "taxe_fonciere", "prix_m2": "prix_m2",
    "chauffage": "chauffage", "owner_siren": "owner_siren",
}


def _archiver(html: str, nom_fichier: str | None) -> tuple[str, str]:
    """Écrit le HTML DÉPOSÉ dans le répertoire privé d'archivage (content-addressed par hash — un même
    fichier n'est pas dupliqué sur disque). Retourne (chemin, hash). Ne sert jamais le web."""
    h = hashlib.sha256(html.encode("utf-8")).hexdigest()
    d = depots_dir()
    d.mkdir(parents=True, exist_ok=True)
    chemin = d / f"{h}.html"
    if not chemin.exists():
        chemin.write_text(html, encoding="utf-8")
    return str(chemin), h


def _maj_prix(db: Session, bien_id: int, ancien, nouveau) -> None:
    """Historise un CHANGEMENT de prix (pige_prix_historique) ; une baisse journalise EV_BAISSE_PRIX
    (signal le plus actionnable — Lot 5)."""
    if ancien is None or nouveau is None or nouveau == ancien:
        return
    db.execute(text("INSERT INTO pige_prix_historique (bien_id, ancien_prix, nouveau_prix) "
                    "VALUES (:b, :a, :n)"), {"b": bien_id, "a": ancien, "n": nouveau})
    if nouveau < ancien:
        journaliser(db, EV_BAISSE_PRIX, f"Baisse de prix — bien #{bien_id}",
                    detail=f"{ancien} € → {nouveau} €", dedup=f"pige:baisse:{bien_id}:{nouveau}")


def _ecrire_faits(db: Session, bien_id: int, rec: dict, *, insert: bool) -> None:
    # RADAR-RECETTE-1 D1a/D1b — `a_verifier` (champs IA « à vérifier », concept du chemin VISION) reste
    # NULL pour le chemin HTML : la donnée est structurée, aucun champ n'est incertain, et un champ
    # ABSENT n'est pas « à vérifier » (il se dit via `etiquettes`, il ne disqualifie pas). L'INCOHÉRENCE
    # (elle) part dans `a_qualifier` / `a_qualifier_motifs` (écrit par `_ecrire_bien`). Ne plus remplir
    # a_verifier pour tout le monde : c'était l'« initialisation qui remplit la colonne » (69/69 faux).
    cols = {c: rec.get(src) for c, src in _FAITS_MAP.items()}
    etiquettes = {c: ("source" if cols[c] not in (None, "") else "absent") for c in _FAITS_MAP}
    params = {**cols, "b": bien_id, "et": json.dumps(etiquettes),
              "brut": json.dumps(rec.get("brut") or {})}
    champs = list(_FAITS_MAP)
    if insert:
        colnames = ", ".join(champs)
        placeholders = ", ".join(f":{c}" for c in champs)
        db.execute(text(
            f"INSERT INTO pige_faits (bien_id, {colnames}, fraicheur_source, etiquettes, source_brute, "
            f" a_verifier, valide_at) VALUES (:b, {placeholders}, 'publication', CAST(:et AS jsonb), "
            f" CAST(:brut AS jsonb), NULL, now())"), params)   # a_verifier NULL (structuré, cf. D1)
    else:
        sets = ", ".join(f"{c} = :{c}" for c in champs)
        db.execute(text(
            f"UPDATE pige_faits SET {sets}, etiquettes = CAST(:et AS jsonb), "
            f" source_brute = CAST(:brut AS jsonb), a_verifier = NULL, "
            f" updated_at = now() WHERE bien_id = :b"), params)


def _ecrire_bien(db: Session, bien_id: int, rec: dict, ratt: dict, motifs: list[str]) -> None:
    """Met à jour la face BIEN (position + précision, état de rattachement, à-qualifier)."""
    db.execute(text(
        """UPDATE pige_biens SET
             type_bien = :t, est_copro = :copro, idu = :idu,
             rattachement_niveau = :niv, rattachement_confiance = :conf,
             rattachement_etat = :etat, rattachement_pistes = CAST(:pistes AS jsonb),
             source_position = :srcpos, lat = :lat, lng = :lng, zipcode = :zip, district = :district,
             a_qualifier = :aq, a_qualifier_motifs = CAST(:motifs AS jsonb)
           WHERE bien_id = :b"""),
        {"b": bien_id, "t": rec.get("type"), "copro": rec.get("type") == "appartement",
         "idu": ratt.get("idu"), "niv": ratt.get("niveau"), "conf": ratt.get("confiance"),
         "etat": ratt.get("etat"), "pistes": json.dumps(ratt.get("pistes") or []),
         "srcpos": rec.get("source_position"), "lat": rec.get("lat"), "lng": rec.get("lng"),
         "zip": rec.get("zipcode"), "district": (rec.get("district") or None),
         "aq": bool(motifs), "motifs": json.dumps(motifs)})


def _ingester_annonce(db: Session, rec: dict) -> str:
    """Upsert d'UNE annonce par list_id. Retourne 'nouvelle' | 'maj' | 'hors_perimetre'."""
    resolu = resoudre_commune(rec.get("commune"))
    if not resolu:
        return "hors_perimetre"                     # hors des 24 communes → rien en base
    commune, _insee = resolu
    rec = {**rec, "commune": commune}               # nom officiel pour matcher parcels.commune

    motifs = coherence.evaluer(rec, db)
    # RADAR-RECETTE-1 D1c — un bien INCOHÉRENT ne peut pas être rattaché : le rattachement repose sur la
    # surface de terrain, qui est justement la valeur suspecte (cas 5086 : « terrain » 377 m² = surface
    # habitable, rattaché par cette surface). On suspend le rattachement plutôt que de pinner un faux.
    if motifs:
        ratt = {"etat": "non_rattachee", "niveau": "absent", "idu": None, "confiance": None,
                "pistes": [], "motif": "bien à qualifier — rattachement suspendu (surface suspecte)"}
    else:
        ratt = rattachement_html.rattacher(db, rec)
    list_id = rec.get("list_id")

    existing = db.execute(text(
        "SELECT bien_id FROM pige_annonces WHERE list_id = :l LIMIT 1"), {"l": list_id}).scalar()

    if existing is None:
        bien_id = db.execute(text(
            "INSERT INTO pige_biens (commune, statut, date_publication) VALUES (:c, 'active', "
            " CAST(:fpd AS timestamptz)::date) RETURNING bien_id"),
            {"c": commune, "fpd": rec.get("first_publication_date")}).scalar()
        db.execute(text(
            "INSERT INTO pige_annonces (bien_id, portail, url_sortante, list_id, "
            " first_publication_date, index_date, expiration_date, statut_portail) "
            "VALUES (:b, :p, :u, :l, CAST(:fpd AS timestamptz), CAST(:idx AS timestamptz), "
            " CAST(:exp AS timestamptz), :sp)"),
            {"b": bien_id, "p": portails.slug_pour_url(rec.get("url") or ""),
             "u": rec.get("url"), "l": list_id, "fpd": rec.get("first_publication_date"),
             "idx": rec.get("index_date"), "exp": rec.get("expiration_date"),
             "sp": rec.get("statut_portail")})
        _ecrire_faits(db, bien_id, rec, insert=True)
        _ecrire_bien(db, bien_id, rec, ratt, motifs)
        if not motifs:
            journaliser(db, EV_NOUVELLE, f"Nouveau bien Radar — {commune}",
                        detail=f"bien #{bien_id} ({rec.get('type') or '?'})",
                        idu=ratt.get("idu"), lien=rec.get("url"), dedup=f"pige:nouvelle:{bien_id}")
        else:
            journaliser(db, EV_A_QUALIFIER, f"Annonce à qualifier — {commune}",
                        detail="; ".join(motifs)[:400], lien=rec.get("url"),
                        dedup=f"pige:aq:{list_id}")
        return "nouvelle"

    # ── MISE À JOUR (Lot 5 : une republication est une CONFIRMATION) ──
    bien_id = existing
    ancien = db.execute(text("SELECT prix FROM pige_faits WHERE bien_id = :b"), {"b": bien_id}).scalar()
    _maj_prix(db, bien_id, ancien, rec.get("prix"))
    db.execute(text(
        "UPDATE pige_annonces SET index_date = CAST(:idx AS timestamptz), "
        " expiration_date = CAST(:exp AS timestamptz), statut_portail = :sp, "
        " date_saisie = now() WHERE list_id = :l"),
        {"idx": rec.get("index_date"), "exp": rec.get("expiration_date"),
         "sp": rec.get("statut_portail"), "l": list_id})
    _ecrire_faits(db, bien_id, rec, insert=False)
    _ecrire_bien(db, bien_id, rec, ratt, motifs)
    # republication = confirmation « toujours en vente » : repousse a_reverifier, statut redevient active
    # (jamais retiree/vendue — celles-ci ne se déduisent pas d'une republication).
    db.execute(text(
        "UPDATE pige_biens SET date_derniere_confirmation = now(), "
        " statut = CASE WHEN statut IN ('a_reverifier','en_vente_longue') THEN 'active' ELSE statut END "
        "WHERE bien_id = :b AND statut NOT IN ('retiree','vendue','retiree_sans_vente')"), {"b": bien_id})
    return "maj"


def ingester(db: Session, html: str, nom_fichier: str | None = None, *, archiver: bool = True) -> dict:
    """Ingestion complète d'un dépôt HTML. Lève html_next.NextDataError si le bloc __NEXT_DATA__ est
    absent/altéré (échec bruyant — jamais un « 0 annonce » silencieux). Retourne un compte-rendu."""
    annonces = html_next.extraire_annonces(html)      # ← échoue BRUYAMMENT si structure absente/changée
    # RADAR-RECETTE-1 D4 — vérifier l'accès EN ÉCRITURE du répertoire d'archivage AVANT toute écriture
    # base (comme le chemin captures stocke avant la base) : un échec disque se dit AVEC le chemin, et
    # rien n'entre en base. `depots_dir_writable()` ne lève jamais et NOMME le chemin.
    if archiver:
        ok, detail = depots_dir_writable()
        if not ok:
            raise DepotStockageError(detail)
    chemin, h = _archiver(html, nom_fichier) if archiver else ("(non archivé)", "")

    compte = {"nouvelle": 0, "maj": 0, "hors_perimetre": 0}
    etats: dict[str, int] = {}
    nb_aq = 0
    for ad in annonces:
        rec = html_next.aplatir(ad)
        # l'état de rattachement pour le compte-rendu (recalculé côté _ingester_annonce ; ici pour la synthèse)
        res = _ingester_annonce(db, rec)
        compte[res] = compte.get(res, 0) + 1

    # relecture des états réels en base pour le compte-rendu (source de vérité = ce qui est écrit).
    list_ids = [ad.get("list_id") for ad in annonces]
    rows = db.execute(text(
        "SELECT b.rattachement_etat, count(*) n, sum(CASE WHEN b.a_qualifier THEN 1 ELSE 0 END) aq "
        "FROM pige_biens b JOIN pige_annonces a ON a.bien_id = b.bien_id "
        "WHERE a.list_id = ANY(:ids) GROUP BY b.rattachement_etat"),
        {"ids": list_ids}).mappings().all()
    for r in rows:
        etats[r["rattachement_etat"] or "non_rattachee"] = r["n"]
        nb_aq += int(r["aq"] or 0)

    depot_id = db.execute(text(
        "INSERT INTO pige_depots (nom_fichier, hash, chemin_archive, nb_annonces, nb_nouvelles, "
        " nb_maj, nb_a_qualifier) VALUES (:nf, :h, :c, :na, :nn, :nm, :aq) RETURNING id"),
        {"nf": nom_fichier, "h": h, "c": chemin, "na": len(annonces),
         "nn": compte["nouvelle"], "nm": compte["maj"], "aq": nb_aq}).scalar()
    enregistrer_fraicheur(db)
    journaliser(db, EV_DEPOT_HTML, f"Dépôt Radar HTML — {len(annonces)} annonces",
                detail=f"{compte['nouvelle']} nouvelles, {compte['maj']} MAJ, {nb_aq} à qualifier"
                       + (f", {compte['hors_perimetre']} hors périmètre" if compte["hors_perimetre"] else ""),
                dedup=f"pige:depot:{h[:16]}")
    db.commit()
    return {"depot_id": depot_id, "nb_annonces": len(annonces),
            "nb_nouvelles": compte["nouvelle"], "nb_maj": compte["maj"],
            "nb_hors_perimetre": compte["hors_perimetre"], "nb_a_qualifier": nb_aq,
            "etats": etats, "archive": chemin}
