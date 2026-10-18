"""FIX-PRIX-ET-OPPORTUNITES (lot 1) — générateur de captures AVANT/APRÈS.

Rend, SANS base, les surfaces qui affichent une valeur de parcelle estimée, via le harnais de test
(`_FakeDB` + fiche fixture) et les fonctions pures. Lancé une fois sur le code APRÈS, une fois sur le
code AVANT (via `git stash`) → on compare. Écrit dans captures/prix-et-opportunites/<etat>/.

    PYTHONPATH=src python scripts/captures_prix_fourchette.py apres|avant
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))

from labuse.api.blocs_documents import rehab_bloc_html  # noqa: E402
from labuse.exports import builder  # noqa: E402

RACINE = Path(__file__).resolve().parents[1]

# fiche fixture : représentative (clés réelles du payload). On duplique ici la part « terrain nu » du
# bilan pour que la capture soit autoporteuse même quand le harnais de test évolue.
_TERRAIN_NU_AVANT = {"prix_m2": 768, "valeur_eur": 569831, "surface_m2": 742, "valeur_libelle": "569 831 €",
                     "libelle": "terrain nu — secteur"}
# APRÈS : le bilan sert la fourchette ±30 % + la mention mesurée (cf. estimation_prix). On la calcule
# avec le point de calcul unique pour coller exactement au produit.
try:
    from labuse.estimation_prix import MENTION, fourchette
    _fr = fourchette(569831)
    _TERRAIN_NU_APRES = {**_TERRAIN_NU_AVANT,
                         "valeur_bas_eur": _fr["bas"], "valeur_haut_eur": _fr["haut"],
                         "valeur_fourchette_libelle": f"{_fr['bas']:,} € – {_fr['haut']:,} €".replace(",", " "),
                         "incertitude": MENTION}
except Exception:            # AVANT : le module n'existe pas → on reste sur le chiffre sec
    _TERRAIN_NU_APRES = _TERRAIN_NU_AVANT


def _fiche(terrain_nu: dict) -> dict:
    return {
        "surface_m2": 742, "adresse": "103 Chaussée Royale, 97460 Saint-Paul", "commune": "Saint-Paul",
        "reglement_plu": {"zones": [{"zone": "U1a", "idurba": "97415_PLU_20251217", "regles_valeurs": [],
                                     "destinations": {"autorisees": ["Logement"], "interdites": [],
                                                      "sous_conditions": []}}]},
        "mode_b": {"terrain_nu": terrain_nu, "achat_max_libelle": "180 000 €",
                   "surface_parcelle_m2": 742, "disponible": True, "porte_par_terrain": True},
        "prix_ancien": {"median": 3811, "n": 24, "n_exclus": 3, "radius_m": 500, "min": 1569, "max": 10135,
                        "type_prix": "appartement", "periode": [2022, 2025],
                        "prix_points": [1569, 3067, 3811, 4746, 10135]},
        "dvf_parcelle": {"secteur": [{"type_bien": "appartement", "n_ventes": 36, "mediane_prix_m2": 3804,
                                      "fenetre": "2021-2025"}], "derniere_mutation": None},
    }


class _FakeDB:
    def execute(self, *a, **k):
        raise RuntimeError("pas de base — capture sur fonctions pures")


def main() -> None:
    etat = sys.argv[1] if len(sys.argv) > 1 else "apres"
    tn = _TERRAIN_NU_APRES if etat == "apres" else _TERRAIN_NU_AVANT
    out = RACINE / "captures" / "prix-et-opportunites" / etat
    out.mkdir(parents=True, exist_ok=True)

    fiche = _fiche(tn)
    # 1) Dossier (contient « 8. Marché » → valeur terrain au prix du secteur).
    dossier = builder.construire(_FakeDB(), "97415000BO0852", "dossier", fiche=fiche, jour=date(2026, 9, 5)).html
    (out / "dossier.html").write_text(dossier)
    # 2) Financier (bloc « Face au prix demandé » → terrain nu au prix du marché).
    try:
        financier = builder.construire(_FakeDB(), "97415000BO0852", "financier", fiche=fiche, jour=date(2026, 9, 5)).html
        (out / "financier.html").write_text(financier)
    except Exception as e:  # noqa: BLE001
        (out / "financier.html").write_text(f"<p>financier indisponible dans ce harnais : {e}</p>")
    # 2b) Bloc PDF « 5. Marché et prix » rendu DIRECTEMENT (fonction pure) — c'est lui qui porte la
    # ligne « Terrain nu au prix du secteur » et la note d'incertitude. On construit les Valeur du registre.
    try:
        from labuse.exports.blocs import marche as bloc_marche
        from labuse.registre.valeur import Valeur
        def _V(cid, v):
            return Valeur(valeur=v, chiffre_id=cid, version_def="capture", run=None)
        valeurs = {
            "prix_terrain_secteur_eur_m2": _V("prix_terrain_secteur_eur_m2", tn),
            "prix_sortie_bati_eur_m2": _V("prix_sortie_bati_eur_m2", fiche["prix_ancien"]),
            "dvf_parcelle_liste": _V("dvf_parcelle_liste", fiche["dvf_parcelle"]["secteur"]),
        }
        corps = bloc_marche.rendu(valeurs)
        (out / "bloc_marche.html").write_text(
            "<html><head><meta charset='utf-8'><style>body{font-family:sans-serif;padding:24px;"
            "background:#fff;color:#111;max-width:720px}h2,h3{color:#1b5}.num{font-weight:600}"
            "td{padding:4px 10px}.note,p{color:#555;font-size:12px}</style></head><body>" + corps + "</body></html>")
    except Exception as e:  # noqa: BLE001
        (out / "bloc_marche.html").write_text(f"<p>bloc marché indisponible : {e}</p>")

    # 3) Bloc réhabilitation (autoporteur).
    (out / "rehab.html").write_text(
        "<html><head><meta charset='utf-8'><style>body{font-family:sans-serif;padding:24px;"
        "background:#0f1512;color:#cfe}.bloc{border:1px solid #2a3a30;border-radius:8px;padding:16px}"
        ".bloc-note{color:#8FA69A;font-size:12px}</style></head><body>"
        + rehab_bloc_html(fiche["mode_b"]) + "</body></html>")

    # 4) Fiche React — rendu ISOLÉ des deux lignes « valeur estimée » (Marché + Constructibilité). Les
    # nombres sont produits par le MÊME calcul que lib/fourchette.ts (mêmes ±30 %) → fidèle au produit.
    if etat == "apres":
        from labuse.estimation_prix import fourchette as _f
        fr = _f(569831)
        bas = f"{fr['bas']:,}".replace(",", " ")
        haut = f"{fr['haut']:,}".replace(",", " ")
        marche_val = f"≈ {bas} – {haut} <small>€</small>"
        constr_val = f"~{bas} € – {haut} € <span style='font-size:10px'>(768 €/m² × 742 m² · Estimé, fourchette ±30 %)</span>"
    else:
        marche_val = "≈ 569 831 <small>€</small>"
        constr_val = "~569 831 € <span style='font-size:10px'>(768 €/m² × 742 m² · Estimé)</span>"
    (out / "fiche.html").write_text(
        "<html><head><meta charset='utf-8'><style>body{font-family:sans-serif;padding:24px;"
        "background:#0f1512;color:#cfe;max-width:560px}.ligne{display:flex;justify-content:space-between;"
        "border-bottom:1px solid #223;padding:8px 0}.lab{color:#9fb}.val{font-weight:600}"
        "small{opacity:.7}h4{color:#8FA69A}</style></head><body>"
        "<h4>Fiche · Marché (rendu isolé de la Ligne)</h4>"
        f"<div class='ligne'><span class='lab'>Valeur au prix du secteur</span><span class='val'>{marche_val}</span></div>"
        "<h4 style='margin-top:24px'>Fiche · Constructibilité (mode B)</h4>"
        f"<p style='color:#8FA69A;font-size:11px'>terrain nu au prix du secteur : <b style='color:#cfe'>{constr_val}</b></p>"
        "</body></html>")

    # 5) Étiquettes (d) prix de sortie neuf « île » + (c) charge Assemblage + (e) commune officielle.
    if etat == "apres":
        from labuse.communes import nom_officiel
        from labuse.ingestion.dvf_prix_neuf import niveau_prix_label
        from labuse.ingestion.score_e import niveau_label
        label_ile = niveau_prix_label("ile_validee")
        label_score = niveau_label("ile_validee")
        commune = f"Parcelle 97404000AW0099 à <b>{nom_officiel('97404000AW0099')}</b>"
        charge = ("Charge foncière cumulée <b>(estimée)</b> : 450 k€ — Estimée (bilan à rebours) : repose "
                  "sur un prix de sortie estimé (écart médian mesuré ~27 % au backtest DVF) et des "
                  "hypothèses de coût — pas une valeur de marché.")
    else:
        label_ile = "Estimé — estimation à l'échelle de l'île (± 12 %)"
        label_score = "estimation à l'échelle de l'île (± 12 %)"
        commune = "Parcelle 97404000AW0099 à <b>Saint-Denis</b> <i>(parcels.commune erroné)</i>"
        charge = "Charge foncière cumulée : 450 k€ (chiffre sec, pas de mention « estimée »)"
    (out / "labels.html").write_text(
        "<html><head><meta charset='utf-8'><style>body{font-family:sans-serif;padding:24px;"
        "background:#0f1512;color:#cfe;max-width:720px;line-height:1.5}h4{color:#8FA69A;margin:18px 0 4px}"
        "p{margin:0;font-size:12.5px}</style></head><body>"
        f"<h4>(d) Prix de sortie neuf — repli île (dvf_prix_neuf)</h4><p>{label_ile}</p>"
        f"<h4>(d) Prix de sortie neuf — niveau score_e</h4><p>{label_score}</p>"
        f"<h4>(e) Commune nommée par le Copilote (IDU 97404 = L'Étang-Salé)</h4><p>{commune}</p>"
        f"<h4>(c) Charge foncière d'Assemblage</h4><p>{charge}</p>"
        "</body></html>")

    print(f"[{etat}] écrit dans {out}")
    for f in sorted(out.glob("*.html")):
        print("  ", f.name, f.stat().st_size, "o")


if __name__ == "__main__":
    main()
