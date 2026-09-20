"""Bloc « 10. Sources, limites et mentions ». Ce que le document ne peut pas dire (renvois vers
les tiers compétents) + les sources et millésimes RÉELLEMENT servis (data_sources de la fiche)."""
from __future__ import annotations

from ..lignes import val
from ..rendu import esc, ligne_kv, note, section, table_kv

IDS = ("run_label_servi", "potentiel_verdict")

_LIMITES = [
    ("Constructibilité définitive", "Certificat d'urbanisme — mairie, service instructeur"),
    ("Valeur vénale", "Avis de valeur — notaire, expert"),
    ("État du bâti, servitudes privées", "Visite et acte notarié"),
    ("Coût de démolition, de dépollution", "Devis d'entreprise"),
    ("Réseaux et raccordements chiffrés", "Gestionnaires, DT-DICT"),
    ("Position du propriétaire, prix demandé", "Contact direct ou apporteur d'affaires"),
]


def rendu(valeurs) -> str:
    corps = "<h3>Ce que ce document ne peut pas dire</h3>"
    corps += table_kv([ligne_kv(k, esc(v), "") for k, v in _LIMITES])
    ds = val(valeurs, "run_label_servi") or []
    lignes = []
    for s in ds:
        if not isinstance(s, dict) or not s.get("nom"):
            continue
        four = f" — {s['fournisseur']}" if s.get("fournisseur") else ""
        mill = f" ({s['millesime']})" if s.get("millesime") else ""
        lignes.append(ligne_kv(s["nom"], esc(f"{s.get('fournisseur', '')}{mill}".strip(" —")) or esc(four), ""))
    # RECETTE-11 A3 — quand une hauteur a été MESURÉE au LiDAR HD, la source doit être citée ici
    # (elle n'y était pas). On l'ajoute avec son survol si elle n'apparaît pas déjà.
    pv = val(valeurs, "potentiel_verdict") or {}
    if isinstance(pv, dict) and pv.get("hauteur_nature") == "sourcé" \
            and not any("lidar" in (l or "").lower() for l in lignes):
        survol = pv.get("hauteur_survol")
        mill = f" (survol de {survol})" if survol else ""
        lignes.append(ligne_kv("LiDAR HD (MNS) — hauteurs mesurées",
                               esc(f"IGN / Géoplateforme{mill}"), ""))
    if lignes:
        corps += "<h3>Sources et millésimes</h3>" + table_kv(lignes)
    corps += note("Document d'information établi à partir de données publiques. Il ne constitue "
                  "ni un document d'urbanisme opposable, ni une étude de faisabilité réglementaire, "
                  "ni un conseil juridique, et ne remplace pas un certificat d'urbanisme. "
                  "Fonds cartographiques : © IGN, © contributeurs OpenStreetMap (ODbL).")
    # RECETTE-12 D4 — la ligne « Sources : BD TOPO… CoSIA… » (pied) imprimée APRÈS les mentions
    # légales, à la fin du §10, est RETIRÉE : le §10 porte déjà sa propre liste « Sources et
    # millésimes » ci-dessus ; ce pied faisait doublon (et fuyait les libellés techniques, D5).
    # EXPORTS-REBRANCHEMENT-1 lot 1 — la clôture suit les 11 sections du miroir : plus de numéro.
    return section("Sources, limites et mentions", corps)
