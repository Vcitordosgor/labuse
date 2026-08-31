"""RADAR-HTML (Lot 1) — INGESTION d'une page HTML déposée par Vic.

Chemin d'entrée UNIQUE du Radar (remplace capture d'écran + agent vision). Enchaîne :
  parseur `html_next.analyser` (échec bruyant) → cohérence (Lot 2) → rattachement (Lot 3) →
  upsert IDEMPOTENT par list_id (MAJ + historisation des baisses de prix) → archivage du fichier.

Doctrine §2 : aucun réseau. `first_publication_date` fait foi (nouveauté / « repéré le ») ; `index_date`
ne sert QU'À constater une republication (Lot 5) — elle ne crée jamais d'annonce.

RADAR-DEPOT-2 — trois structures (cf. html_next) convergent ici, chaque enregistrement porte sa
PROVENANCE (`json_riche` / `dom_degrade`). RÈGLE DE FUSION (mandat D1) : le RICHE l'emporte toujours ;
le DÉGRADÉ ne fait que COMBLER les trous d'un bien riche déjà acquis — un passage en variante B n'efface
JAMAIS une donnée riche. La page d'annonce (D2) enrichit en plus des FAITS DÉCLARÉS (zone PLU, drapeaux).
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


def _ecrire_faits(db: Session, bien_id: int, rec: dict, *, insert: bool, combler: bool = False) -> None:
    # RADAR-RECETTE-1 D1a/D1b — `a_verifier` (champs IA « à vérifier », concept du chemin VISION) reste
    # NULL pour le chemin HTML : la donnée est structurée, aucun champ n'est incertain, et un champ
    # ABSENT n'est pas « à vérifier » (il se dit via `etiquettes`, il ne disqualifie pas). L'INCOHÉRENCE
    # (elle) part dans `a_qualifier` / `a_qualifier_motifs` (écrit par `_ecrire_bien`). Ne plus remplir
    # a_verifier pour tout le monde : c'était l'« initialisation qui remplit la colonne » (69/69 faux).
    incoming = {c: rec.get(src) for c, src in _FAITS_MAP.items()}
    champs = list(_FAITS_MAP)
    # RADAR-DEPOT-2 D1 — mode COMBLER (dégradé sur un bien déjà RICHE) : on ne remplit QUE les trous, on
    # ne descend jamais une valeur riche. La provenance reste `json_riche` (non touchée), le déclaratif
    # aussi. Hors combler, on écrase (riche fait foi ; dégradé neuf est écrit tel quel).
    if combler:
        existing = db.execute(text(
            f"SELECT {', '.join(champs)}, source_brute FROM pige_faits WHERE bien_id = :b"),
            {"b": bien_id}).mappings().first() or {}
        cols = {c: (existing[c] if existing.get(c) is not None else incoming[c]) for c in champs}
    else:
        cols = incoming
    etiquettes = {c: ("source" if cols[c] not in (None, "") else "absent") for c in champs}
    # provenance : posée par le riche et le dégradé-neuf ; JAMAIS abaissée en combler (on garde le riche).
    prov = None if combler else rec.get("provenance")
    # déclaratif (D2, page d'annonce seule) : posé quand présent, jamais effacé par un dépôt sans lui.
    decl = rec.get("declaratif")
    params = {**cols, "b": bien_id, "et": json.dumps(etiquettes),
              "brut": json.dumps(rec.get("brut") or {}), "prov": prov,
              "decl": json.dumps(decl) if decl is not None else None}
    if insert:
        colnames = ", ".join(champs)
        placeholders = ", ".join(f":{c}" for c in champs)
        db.execute(text(
            f"INSERT INTO pige_faits (bien_id, {colnames}, fraicheur_source, etiquettes, source_brute, "
            f" a_verifier, provenance, declaratif, valide_at) VALUES (:b, {placeholders}, 'publication', "
            f" CAST(:et AS jsonb), CAST(:brut AS jsonb), NULL, :prov, CAST(:decl AS jsonb), now())"), params)
    else:
        sets = ", ".join(f"{c} = :{c}" for c in champs)
        # source_brute & provenance en COALESCE quand combler (jamais écrasés par le dégradé) ; sinon posés.
        brut_sql = "COALESCE(source_brute, CAST(:brut AS jsonb))" if combler else "CAST(:brut AS jsonb)"
        prov_sql = "provenance" if combler else ":prov"
        db.execute(text(
            f"UPDATE pige_faits SET {sets}, etiquettes = CAST(:et AS jsonb), "
            f" source_brute = {brut_sql}, provenance = {prov_sql}, a_verifier = NULL, "
            f" declaratif = COALESCE(CAST(:decl AS jsonb), declaratif), "
            f" updated_at = now() WHERE bien_id = :b"), params)


def _ecrire_bien(db: Session, bien_id: int, rec: dict, ratt: dict, motifs: list[str]) -> None:
    """Met à jour la face BIEN. Position + à-qualifier : toujours. RATTACHEMENT : seulement si le
    client ne l'a PAS déjà tranché à la main (rattachement_humain) — son choix fait foi (Lot 2), une
    republication ne l'écrase jamais."""
    db.execute(text(
        """UPDATE pige_biens SET type_bien = :t, est_copro = :copro,
             source_position = :srcpos, lat = :lat, lng = :lng, zipcode = :zip, district = :district,
             a_qualifier = :aq, a_qualifier_motifs = CAST(:motifs AS jsonb)
           WHERE bien_id = :b"""),
        {"b": bien_id, "t": rec.get("type"), "copro": rec.get("type") == "appartement",
         "srcpos": rec.get("source_position"), "lat": rec.get("lat"), "lng": rec.get("lng"),
         "zip": rec.get("zipcode"), "district": (rec.get("district") or None),
         "aq": bool(motifs), "motifs": json.dumps(motifs)})
    db.execute(text(
        """UPDATE pige_biens SET idu = :idu, rattachement_niveau = :niv, rattachement_confiance = :conf,
             rattachement_etat = :etat, rattachement_pistes = CAST(:pistes AS jsonb),
             rattachement_criteres = CAST(:crit AS jsonb)
           WHERE bien_id = :b AND rattachement_humain = false"""),
        {"b": bien_id, "idu": ratt.get("idu"), "niv": ratt.get("niveau"), "conf": ratt.get("confiance"),
         "etat": ratt.get("etat"), "pistes": json.dumps(ratt.get("pistes") or []),
         "crit": json.dumps(ratt.get("criteres") or [])})


def _rattacher(db: Session, rec: dict, motifs: list[str]) -> dict:
    """Calcule le rattachement d'un enregistrement. RADAR-DEPOT-2 D1 — un enregistrement DÉGRADÉ (variante
    B, sans position) n'est JAMAIS rattaché et ne tente RIEN. Un bien INCOHÉRENT non plus (la surface, base
    du rattachement, est la valeur suspecte — cas 5086)."""
    if rec.get("provenance") == html_next.PROV_DEGRADE:
        return {"etat": "non_rattachee", "niveau": "absent", "idu": None, "confiance": None,
                "pistes": [], "criteres": [], "motif": "annonce dégradée (variante B) — position au quartier, pas de rattachement"}
    if motifs:
        return {"etat": "non_rattachee", "niveau": "absent", "idu": None, "confiance": None,
                "pistes": [], "criteres": [], "motif": "bien à qualifier — rattachement suspendu (surface suspecte)"}
    return rattachement_html.rattacher(db, rec)


def _ingester_annonce(db: Session, rec: dict) -> str:
    """Upsert d'UNE annonce par list_id. Retourne 'nouvelle' | 'maj' | 'hors_perimetre'."""
    resolu = resoudre_commune(rec.get("commune"))
    if not resolu:
        return "hors_perimetre"                     # hors des 24 communes → rien en base
    commune, _insee = resolu
    rec = {**rec, "commune": commune}               # nom officiel pour matcher parcels.commune
    degrade = rec.get("provenance") == html_next.PROV_DEGRADE
    list_id = rec.get("list_id")

    existing = db.execute(text(
        "SELECT a.bien_id, f.provenance FROM pige_annonces a JOIN pige_faits f ON f.bien_id = a.bien_id "
        "WHERE a.list_id = :l LIMIT 1"), {"l": list_id}).mappings().first()

    if existing is None:
        motifs = coherence.evaluer(rec, db)
        ratt = _rattacher(db, rec, motifs)
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
                        detail=f"bien #{bien_id} ({rec.get('type') or '?'}"
                               + (", dégradé" if degrade else "") + ")",
                        idu=ratt.get("idu"), lien=rec.get("url"), dedup=f"pige:nouvelle:{bien_id}")
        else:
            journaliser(db, EV_A_QUALIFIER, f"Annonce à qualifier — {commune}",
                        detail="; ".join(motifs)[:400], lien=rec.get("url"),
                        dedup=f"pige:aq:{list_id}")
        return "nouvelle"

    # ── MISE À JOUR ──
    bien_id = existing["bien_id"]
    # RADAR-DEPOT-2 D1 — COMBLER : un dépôt DÉGRADÉ sur un bien déjà RICHE ne remplit que les trous et
    # n'efface RIEN (ni faits riches, ni position, ni rattachement, ni prix). Un passage en B est une
    # simple re-vue : on repousse la date de dernière vue, on ne rejoue ni le prix ni la cascade.
    combler = degrade and existing["provenance"] == html_next.PROV_RICHE
    if combler:
        _ecrire_faits(db, bien_id, rec, insert=False, combler=True)
        db.execute(text("UPDATE pige_annonces SET date_saisie = now() WHERE list_id = :l"), {"l": list_id})
        db.execute(text(
            "UPDATE pige_biens SET date_derniere_confirmation = now(), "
            " statut = CASE WHEN statut IN ('a_reverifier','en_vente_longue') THEN 'active' ELSE statut END "
            "WHERE bien_id = :b AND statut NOT IN ('retiree','vendue','retiree_sans_vente')"), {"b": bien_id})
        return "maj"

    # riche-sur-tout, ou dégradé-sur-dégradé : mise à jour pleine (Lot 5 : republication = CONFIRMATION).
    # ENRICHISSEMENT B→A : un dépôt RICHE sur un bien dégradé remplit tout et le fait passer riche
    # (`_ecrire_faits` pose provenance=json_riche), et rejoue la cascade (il a désormais une position).
    motifs = coherence.evaluer(rec, db)
    ratt = _rattacher(db, rec, motifs)
    ancien = db.execute(text("SELECT prix FROM pige_faits WHERE bien_id = :b"), {"b": bien_id}).scalar()
    _maj_prix(db, bien_id, ancien, rec.get("prix"))
    # dates portail en COALESCE : un dépôt DÉGRADÉ (valeurs NULL) ne nulle jamais des dates riches acquises.
    db.execute(text(
        "UPDATE pige_annonces SET index_date = COALESCE(CAST(:idx AS timestamptz), index_date), "
        " expiration_date = COALESCE(CAST(:exp AS timestamptz), expiration_date), "
        " statut_portail = COALESCE(:sp, statut_portail), date_saisie = now() WHERE list_id = :l"),
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
    """Ingestion complète d'un dépôt HTML. Reconnaît variante A (searchData), variante B (vignettes DOM,
    dégradé) et page d'annonce (D2, enrichissement). Lève html_next.NextDataError si aucune structure
    n'est reconnue (échec bruyant NOMMANT les trois chemins — jamais un « 0 annonce » silencieux).
    Retourne un compte-rendu (dont la PROVENANCE et le mode de dépôt)."""
    resultat = html_next.analyser(html)               # ← échoue BRUYAMMENT si structure absente/changée
    records = resultat["records"]
    provenance = resultat["provenance"]
    mode = resultat["mode"]
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
    for rec in records:
        res = _ingester_annonce(db, rec)
        compte[res] = compte.get(res, 0) + 1

    # relecture des états réels en base pour le compte-rendu (source de vérité = ce qui est écrit).
    list_ids = [r.get("list_id") for r in records]
    rows = db.execute(text(
        "SELECT b.rattachement_etat, count(*) n, sum(CASE WHEN b.a_qualifier THEN 1 ELSE 0 END) aq "
        "FROM pige_biens b JOIN pige_annonces a ON a.bien_id = b.bien_id "
        "WHERE a.list_id = ANY(:ids) GROUP BY b.rattachement_etat"),
        {"ids": list_ids}).mappings().all()
    for r in rows:
        etats[r["rattachement_etat"] or "non_rattachee"] = r["n"]
        nb_aq += int(r["aq"] or 0)
    degrade_lbl = "dégradée (variante B)" if provenance == html_next.PROV_DEGRADE else \
        ("page d'annonce" if mode == "annonce" else "riche (variante A)")

    depot_id = db.execute(text(
        "INSERT INTO pige_depots (nom_fichier, hash, chemin_archive, nb_annonces, nb_nouvelles, "
        " nb_maj, nb_a_qualifier) VALUES (:nf, :h, :c, :na, :nn, :nm, :aq) RETURNING id"),
        {"nf": nom_fichier, "h": h, "c": chemin, "na": len(records),
         "nn": compte["nouvelle"], "nm": compte["maj"], "aq": nb_aq}).scalar()
    enregistrer_fraicheur(db)
    journaliser(db, EV_DEPOT_HTML, f"Dépôt Radar HTML — {len(records)} annonces [{degrade_lbl}]",
                detail=f"{compte['nouvelle']} nouvelles, {compte['maj']} MAJ, {nb_aq} à qualifier"
                       + (f", {compte['hors_perimetre']} hors périmètre" if compte["hors_perimetre"] else ""),
                dedup=f"pige:depot:{h[:16]}")
    db.commit()
    return {"depot_id": depot_id, "nb_annonces": len(records),
            "nb_nouvelles": compte["nouvelle"], "nb_maj": compte["maj"],
            "nb_hors_perimetre": compte["hors_perimetre"], "nb_a_qualifier": nb_aq,
            "etats": etats, "archive": chemin, "provenance": provenance, "mode": mode}
