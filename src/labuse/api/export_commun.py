"""Éléments COMMUNS des exports client (M6 Phase 2a) — une seule vérité pour :

- le disclaimer réglementaire EXACT (« Ces informations ne remplacent pas un certificat
  d'urbanisme. ») exigé au mot près dans chaque document remis au client ;
- l'attribution des sources principales (textes exacts de l'audit licences §1.11) ;
- le pied de page partagé des PDF fpdf2 (fiche premium, projet) ;
- l'adresse postale BAN d'une parcelle (même règle de rattachement que le pré-dossier PC :
  adresse « principal » d'abord, id_ban stable ensuite ; résilience si la table manque).
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

#: Disclaimer réglementaire — AU MOT PRÈS (mandat M6 2a) : repris dans les PDF et les CGU.
DISCLAIMER_CU = "Ces informations ne remplacent pas un certificat d'urbanisme."

#: Non-garantie historique des exports (inchangée) — complétée par DISCLAIMER_CU.
NON_GARANTIE = ("Estimations indicatives issues de données publiques — ne valent ni conseil "
                "juridique/notarial ni garantie de constructibilité.")

#: Attributions des sources principales — textes exacts consignés à l'audit §1.11 (licences).
SOURCES_ATTRIBUTION = (
    "Sources : DGFiP/Etalab — Plan Cadastral Informatisé · DGFiP — Demandes de valeurs "
    "foncières (DVF) · © IGN — BD TOPO, BD ORTHO, RGE ALTI (Licence Ouverte 2.0) · "
    "ADEME, base DPE · SDES, Sitadel · Géorisques (BRGM/MTE) · Insee · INPI — RNE · "
    "Base Adresse Nationale (DINUM/IGN) · © les contributeurs d'OpenStreetMap — ODbL "
    "(openstreetmap.org/copyright) · Commission européenne, JRC — PVGIS (CC BY 4.0)")


def pied_de_page_pdf(pdf, doc_label: str) -> None:
    """Pied de page commun des PDF fpdf2 : non-garantie + disclaimer CU (au mot près),
    attributions sources, date de génération et pagination. Suppose la fonte « inter »
    déjà enregistrée (render_*_pdf le fait avant add_page)."""
    pdf.set_y(-24)
    pdf.set_font("inter", size=6)
    pdf.set_text_color(140, 152, 145)
    pdf.multi_cell(0, 2.9, f"{NON_GARANTIE} {DISCLAIMER_CU} À vérifier au règlement et "
                           "auprès des services.", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("inter", size=5.4)
    pdf.multi_cell(0, 2.6, SOURCES_ATTRIBUTION, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("inter", size=6)
    pdf.cell(0, 3.2, f"LA BUSE · radar foncier La Réunion · {doc_label} · "
                     f"généré le {date.today().isoformat()} · page {pdf.page_no()}/{{nb}}",
             align="C")


def adresses_ban(db: Session, idus: list[str]) -> dict[str, dict]:
    """Adresse postale BAN par parcelle : {idu: {adresse, code_postal, ville}}.
    Une seule requête (page d'export) ; adresse « principal » prioritaire ; dict vide si
    la table n'existe pas (résilience habituelle) ou si aucune adresse n'est rattachée."""
    if not idus:
        return {}
    if not db.execute(text("SELECT to_regclass('adresse_parcelles') IS NOT NULL")).scalar():
        return {}
    rows = db.execute(text(
        """SELECT DISTINCT ON (ap.idu) ap.idu,
                  NULLIF(concat_ws(' ', a.numero, a.rep, a.voie), '') AS adresse,
                  a.code_postal, a.commune AS ville
           FROM adresse_parcelles ap JOIN adresses a ON a.id_ban = ap.id_ban
           WHERE ap.idu = ANY(:idus)
           ORDER BY ap.idu, (ap.source = 'principal') DESC, a.id_ban"""),
        {"idus": list(idus)}).mappings().all()
    return {r["idu"]: {"adresse": r["adresse"], "code_postal": r["code_postal"],
                       "ville": r["ville"]}
            for r in rows if r["adresse"]}


def format_adresse(a: dict | None) -> str | None:
    """Une entrée d'adresses_ban → une ligne (« 27 Impasse des Pétrels, 97426 Les
    Trois-Bassins ») — None si aucune adresse."""
    if not a:
        return None
    ville = " ".join(x for x in (a["code_postal"], a["ville"]) if x)
    return f"{a['adresse']}, {ville}" if ville else a["adresse"]


def adresse_ban_texte(db: Session, idu: str) -> str | None:
    """Adresse BAN d'UNE parcelle en une ligne — None si aucune adresse rattachée."""
    return format_adresse(adresses_ban(db, [idu]).get(idu))
