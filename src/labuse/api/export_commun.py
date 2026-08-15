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

#: Attributions des sources — textes exacts consignés à l'audit §1.11 (licences).
#: M73 C9 : une source n'est citée que si elle a PRODUIT un constat dans le document (interdit du
#: mandat). ADEME/DPE (squelette M66-B) et INPI/RNE (dirigeant) sont donc CONDITIONNELS — jamais
#: cités par défaut dans un document qui n'affiche ni DPE ni dirigeant.
def sources_attribution(*, dpe: bool = False, inpi: bool = False) -> str:
    parts = ["DGFiP/Etalab — Plan Cadastral Informatisé",
             "DGFiP — Demandes de valeurs foncières (DVF)",
             "© IGN — BD TOPO, BD ORTHO, RGE ALTI (Licence Ouverte 2.0)"]
    if dpe:
        parts.append("ADEME, base DPE")
    parts += ["SDES, Sitadel", "Géorisques (BRGM/MTE)", "Insee"]
    if inpi:
        parts.append("INPI — RNE")
    parts += ["Base Adresse Nationale (DINUM/IGN)",
              "© les contributeurs d'OpenStreetMap — ODbL (openstreetmap.org/copyright)"]
    return "Sources : " + " · ".join(parts)


#: rétro-compat (rares appelants sans drapeau) — base sans DPE ni INPI (les deux faux positifs).
SOURCES_ATTRIBUTION = sources_attribution()


def pied_de_page_pdf(pdf, doc_label: str, *, dpe: bool = False, inpi: bool = False) -> None:
    """Pied de page commun des PDF fpdf2 : non-garantie + disclaimer CU (au mot près),
    attributions sources, date de génération et pagination. Utilise « inter » si enregistrée
    (render_*_pdf le fait avant add_page), sinon repli sur une police cœur."""
    # M-C (F6) : GARDE — si « inter » n'a pas été enregistrée en amont (appelant tiers, régression),
    # ne pas lever une FPDFException ; retomber sur helvetica (police cœur, latin-1 suffit ici).
    fam = "inter" if "inter" in getattr(pdf, "fonts", {}) else "helvetica"
    pdf.set_y(-24)
    pdf.set_font(fam, size=6)
    pdf.set_text_color(140, 152, 145)
    pdf.multi_cell(0, 2.9, f"{NON_GARANTIE} {DISCLAIMER_CU} À vérifier au règlement et "
                           "auprès des services.", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(fam, size=5.4)
    pdf.multi_cell(0, 2.6, sources_attribution(dpe=dpe, inpi=inpi), align="C",
                   new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(fam, size=6)
    pdf.cell(0, 3.2, f"LABUSE · radar foncier La Réunion · {doc_label} · "
                     f"généré le {date.today().isoformat()} · page {pdf.page_no()}/{{nb}}",
             align="C")


#: Titre unique de la section « limites » — au mot près dans les 4 documents (M73 §5).
LIMITES_TITRE = "Ce que ce document ne peut pas dire"

#: Limites COMMUNES à tous les documents : (ABSENCE, OÙ CHERCHER). Matérialise le 3e terme de la
#: doctrine (ce qui est absent + où le destinataire peut le chercher) — devant un financeur, c'est
#: ce qui rend le reste crédible.
_LIMITES_COMMUN: list[tuple[str, str]] = [
    ("Constructibilité définitive", "certificat d'urbanisme (mairie / service instructeur)"),
    ("Valeur vénale exacte", "avis de valeur notarial / expert"),
    ("État réel du bâti et servitudes privées", "visite + acte notarié"),
    ("Prix de marché fin", "DVF détaillé + agent local"),
]

#: Ajouts SPÉCIFIQUES par document (concaténés au commun).
_LIMITES_SPECIFIQUE: dict[str, list[tuple[str, str]]] = {
    "premium": [("Comparables de vente détaillés", "dossier parcelle / banquier")],
    "banquier": [("Plan de financement et LTV", "établissement prêteur"),
                 ("Coût de démolition / dépollution", "devis entreprise")],
    "dossier": [("Réseaux et raccordements chiffrés", "concessionnaires (eau / électricité)")],
}


def limites_document(doc: str) -> list[tuple[str, str]]:
    """M73 §5 — source de contenu PARTAGÉE (doctrine « un seul endroit ») de la section
    « Ce que ce document ne peut pas dire ». Renvoie une liste de (ABSENCE, OÙ CHERCHER).
    `doc` ∈ {"premium", "banquier", "dossier"} (M93 — one-pager retiré)."""
    return _LIMITES_COMMUN + _LIMITES_SPECIFIQUE.get(doc, [])


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
