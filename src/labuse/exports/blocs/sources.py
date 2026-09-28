"""Bloc « 10. Sources, limites et mentions ». Ce que le document ne peut pas dire (renvois vers
les tiers compétents) + les sources RÉELLEMENT servies (data_sources de la fiche) — NOMS seuls,
aucun millésime ni date côté client (EXPORTS-REBRANCHEMENT-1 lot 2, doctrine PAGE-SOURCES-1 18/09)."""
from __future__ import annotations

from ..lignes import val
from ..rendu import esc, ligne_kv, note, section, table_kv

IDS = ("run_label_servi", "potentiel_verdict")

#: EXPORTS-FIX-1 D3 — alias de source → nom canonique unique (le client ne voit qu'une entrée).
_SOURCE_ALIAS = {
    "Potentiel foncier Région (Région ODS)": "Potentiel foncier — Région Réunion (Opendatasoft)",
    "data.regionreunion.com — Potentiel foncier": "Potentiel foncier — Région Réunion (Opendatasoft)",
}

_LIMITES = [
    ("Constructibilité définitive", "Certificat d'urbanisme — mairie, service instructeur"),
    ("Valeur vénale", "Avis de valeur — notaire, expert"),
    ("État du bâti, servitudes privées", "Visite et acte notarié"),
    ("Coût de démolition, de dépollution", "Devis d'entreprise"),
    ("Réseaux et raccordements chiffrés", "Gestionnaires, DT-DICT"),
    ("Position du propriétaire, prix demandé", "Contact direct ou apporteur d'affaires"),
]


def corps_sources(valeurs) -> str:
    """EXPORTS-REBRANCHEMENT-2 lot 1 — le CORPS de la clôture (limites + noms des sources), sans
    l'en-tête de section : le miroir le rend en §12 (numérotation unique dans miroir.rendu_sections)."""
    corps = "<h3>Ce que ce document ne peut pas dire</h3>"
    corps += table_kv([ligne_kv(k, esc(v), "") for k, v in _LIMITES])
    ds = val(valeurs, "run_label_servi") or []
    # EXPORTS-FIX-1 D2 — une source CITÉE sans aucune ligne servie sort de la liste : on ne garde que
    # les sources RÉELLEMENT lues (celles qui ont alimenté une section, via les réservoirs des Valeur).
    # Ainsi RPG (non ingéré ici), ONF, INPN, Parc national, Cartofriches, 50 pas, classement sonore,
    # érosion côtière, BODACC/INPI (silencieuses sur ces parcelles) ne se citent plus « pour rien ».
    from ..pieds import sources_lues
    _servies = {nom for nom, _m in sources_lues([v for v in valeurs.values()])}
    lignes = []
    _vus: set[str] = set()
    for s in ds:
        if not isinstance(s, dict) or not s.get("nom"):
            continue
        # EXPORTS-FIX-1 D3 — un ALIAS ne se cite pas à côté de sa source canonique (« Potentiel
        # foncier Région (ODS) » ET « data.regionreunion.com — Potentiel foncier » = une seule source).
        nom = _SOURCE_ALIAS.get(s["nom"], s["nom"])
        if nom in _vus:
            continue
        # D2 — non servie sur cette parcelle → hors liste (ni ligne, ni citation orpheline).
        if s["nom"] not in _servies and nom not in _servies:
            continue
        _vus.add(nom)
        # lot 2 — le NOM de la source et son producteur, jamais le millésime (ni « s['millesime'] »
        # ni date) : la fraîcheur est une lecture admin (Circuit), pas une ligne cliente.
        lignes.append(ligne_kv(nom, esc(s.get("fournisseur") or ""), ""))
    # RECETTE-11 A3 — quand une hauteur a été MESURÉE au LiDAR HD, la source doit être citée ici
    # (elle n'y était pas). On l'ajoute avec son survol si elle n'apparaît pas déjà.
    pv = val(valeurs, "potentiel_verdict") or {}
    if isinstance(pv, dict) and pv.get("hauteur_nature") == "sourcé" \
            and not any("lidar" in (l or "").lower() for l in lignes):
        lignes.append(ligne_kv("LiDAR HD (MNS) — hauteurs mesurées", "IGN / Géoplateforme", ""))
    if lignes:
        corps += "<h3>Sources</h3>" + table_kv(lignes)
    corps += note("Document d'information établi à partir de données publiques. Il ne constitue "
                  "ni un document d'urbanisme opposable, ni une étude de faisabilité réglementaire, "
                  "ni un conseil juridique, et ne remplace pas un certificat d'urbanisme. "
                  "Fonds cartographiques : © IGN, © contributeurs OpenStreetMap (ODbL).")
    # RECETTE-12 D4 — la ligne « Sources : BD TOPO… CoSIA… » (pied) imprimée APRÈS les mentions
    # légales, à la fin du §10, est RETIRÉE : le §10 porte déjà sa propre liste « Sources et
    # millésimes » ci-dessus ; ce pied faisait doublon (et fuyait les libellés techniques, D5).
    return corps


def rendu(valeurs) -> str:
    # EXPORTS-REBRANCHEMENT-1 lot 1 — la clôture suit les 11 sections du miroir : plus de numéro.
    return section("Sources, limites et mentions", corps_sources(valeurs))
