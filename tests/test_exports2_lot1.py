"""EXPORTS-2 lot 1 — le builder et le catalogue de blocs (mécanique, sans base).

Verrous :
  · nature (1.3) dérivée du registre : projet/sourcé/estimé selon portée + calcul + moteur ;
  · numéro de rapport (1.6) unique et bien formé ;
  · verdict de section (1.4) déterministe, sans IA ;
  · pied de section (1.5) tiré des réservoirs des ids lus ;
  · archive JSON (1.6) reproductible (aller-retour) ;
  · un bloc rendu (identité) : « non chiffré » quand la donnée manque, pastille quand elle est là,
    aucun mot interdit ;
  · le builder assemble un document (page de garde + section 1) sans base (db factice).
"""
from __future__ import annotations

from datetime import date

import pytest

from labuse.exports import archive, nature, numeros, pieds, verdicts
from labuse.exports.blocs import identite
from labuse.registre.valeur import Valeur


def _V(cid, valeur, **kw):
    return Valeur(valeur=valeur, chiffre_id=cid, version_def="x", run=kw.pop("run", None), **kw)


# ── 1.3 nature ────────────────────────────────────────────────────────────────────────────

def test_nature_projet_source_estime():
    # portée projet → projet (ambre)
    assert nature.nature_de(_V("prix_demande_saisi_eur", 1)) == "projet"
    # passe-plat depuis une source → sourcé
    assert nature.nature_de(_V("surface_parcelle_m2", 742)) == "source"
    # moteur qui SERT un fait de source (zonage) → sourcé
    assert nature.nature_de(_V("zone_plu_famille", "U")) == "source"
    # moteur de CALCUL (potentiel) → estimé
    assert nature.nature_de(_V("capacite_logements", 8)) == "estime"


def test_chip_html_et_derive():
    assert 'class="chip s"' in nature.chip(_V("surface_parcelle_m2", 1)) and "sourcé" in nature.chip(_V("surface_parcelle_m2", 1))
    assert 'class="chip p"' in nature.chip(_V("prix_demande_saisi_eur", 1))
    d = nature.chip(_V("surface_parcelle_m2", 1), derive=True)
    assert 'class="chip d"' in d and "dérivé" in d


def test_chip_projet_sort_en_ambre():
    """DA v3 — la couleur ne porte du sens QUE pour `projet` : ambre = saisi par le client.
    Un id de portée projet sort en pastille `p` (ambre), jamais `e`/`s`, et theme.css lie
    `.chip.p` à --amber."""
    from pathlib import Path
    c = nature.chip(_V("prix_demande_saisi_eur", 650000))
    assert 'class="chip p"' in c and "projet" in c
    assert 'class="chip e"' not in c and 'class="chip s"' not in c
    css = (Path(__file__).resolve().parents[1] / "src/labuse/exports/theme.css").read_text()
    import re as _re
    bloc = _re.search(r"\.chip\.p\s*\{[^}]*\}", css)
    assert bloc and "--amber" in bloc.group(0), "theme.css : .chip.p doit être en --amber"


# ── 1.6 numéro de rapport ───────────────────────────────────────────────────────────────────

def test_numero_rapport_forme_courte():
    # format court des anciens documents : 4 derniers chiffres de l'IDU (l'IDU entier est au cartouche)
    n = numeros.numero_rapport("dossier", "97415000BO0852", date(2026, 9, 5))
    assert n == "DP-20260905-0852"
    assert numeros.numero_rapport("financier", "97401000AD0554", date(2026, 9, 5)) == "FI-20260905-0554"
    assert numeros.numero_rapport("resume", "X", date(2026, 9, 5)).startswith("RE-")
    with pytest.raises(ValueError):
        numeros.numero_rapport("inconnu", "X")


# ── 1.4 verdict déterministe ─────────────────────────────────────────────────────────────────

def test_verdict_zonage_deterministe():
    u = verdicts.verdict_zonage({"zone_plu_famille": _V("zone_plu_famille", "U")})
    assert u and u[1] == "" and "constructible" in u[0]
    n = verdicts.verdict_zonage({"zone_plu_famille": _V("zone_plu_famille", "N")})
    assert n and n[1] == "warn" and "non constructible" in n[0]
    assert verdicts.verdict_zonage({}) is None          # rien à conclure → pas de verdict
    # déterministe : deux appels, même sortie
    assert u == verdicts.verdict_zonage({"zone_plu_famille": _V("zone_plu_famille", "U")})


# ── 1.5 pied de section depuis les réservoirs lus ────────────────────────────────────────────

def test_pied_section_depuis_reservoirs():
    v = _V("surface_parcelle_m2", 742, reservoirs={"cadastre_api_carto": "PCI 2026-08"})
    pied = pieds.pied_section([v])
    assert "Sources" in pied and "Cadastre" in pied and "PCI 2026-08" in pied
    assert pieds.pied_section([_V("surface_parcelle_m2", 1)]) == ""  # aucun réservoir → pas de pied


# ── 1.6 archive reproductible ────────────────────────────────────────────────────────────────

def test_archive_aller_retour(tmp_path):
    vals = {"surface_parcelle_m2": _V("surface_parcelle_m2", 742,
                                      reservoirs={"cadastre_api_carto": "PCI 2026-08"})}
    payload = archive.payload_archive("dossier", "IDU1", "DP-20260905-IDU1", vals, genere_le="2026-09-05")
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.7 fake")
    jpath = archive.ecrire_archive(pdf, payload)
    assert jpath.name == "doc.json"
    relu = archive.lire_archive(jpath)
    assert relu == payload
    assert relu["valeurs"]["surface_parcelle_m2"]["valeur"] == 742
    assert relu["numero_rapport"] == "DP-20260905-IDU1"


# ── bloc identité : « non chiffré » vs pastille, aucun mot interdit ──────────────────────────

def test_bloc_identite_omet_les_lignes_absentes():
    # Décision Vic lot 2 : donnée absente → ligne OMISE (aucun ◌, pas de « non chiffré » ici).
    vals = {"surface_parcelle_m2": _V("surface_parcelle_m2", 742)}  # adresse et proprio absents
    html = identite.rendu(vals)
    assert "742 m²".replace(" ", " ") in html or "742" in html
    assert "non chiffré" not in html      # ligne absente OMISE, pas « non chiffré »
    assert "Adresse" not in html and "Propriétaire" not in html
    assert "◌" not in html
    assert 'class="chip s"' in html       # la surface porte sa pastille
    assert "1. Identité et situation" in html


def test_bloc_identite_sans_mots_interdits():
    import yaml
    from pathlib import Path
    vals = {"surface_parcelle_m2": _V("surface_parcelle_m2", 742),
            "adresse_ban": _V("adresse_ban", "103 Chaussée Royale, Saint-Paul"),
            "type_proprietaire": _V("type_proprietaire", "Personne morale")}
    html = identite.rendu(vals)
    mots = yaml.safe_load((Path(__file__).resolve().parents[1] / "config" / "mots_interdits.yaml").read_text())["mots"]
    trouves = [m for m in mots if m in html]
    assert trouves == [], trouves


# ── builder : un document assemblé sans base (db factice) ────────────────────────────────────

class _FakeDB:
    """db.execute lève → _millesimes le rattrape (millésime None), aucune vraie requête en test."""
    def execute(self, *a, **k):
        raise RuntimeError("pas de base en test unitaire")


def test_builder_construit_dossier_partiel():
    from labuse.exports import builder
    fiche = {"surface_m2": 742, "adresse": "103 Chaussée Royale, Saint-Paul",
             "commune": "Saint-Paul", "proprietaire_moral": True}
    res = builder.construire(_FakeDB(), "97415000BO0852", "dossier", fiche=fiche, jour=date(2026, 9, 5))
    assert res.numero == "DP-20260905-0852"
    assert "Dossier parcelle" in res.html and "1. Identité et situation" in res.html
    assert "surface_parcelle_m2" in res.valeurs
    assert "<html" in res.html and "theme.css" in res.html
    # cartouche @page : n° court, mais l'IDU ENTIER y vit (doc_ref) et sur la page de garde
    assert res.cartouche.doc_ref.endswith(res.numero)
    assert "97415000BO0852" in res.cartouche.doc_ref
    assert "97415000BO0852" in res.html
