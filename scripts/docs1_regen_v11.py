"""DOCS-DA-1 (gabarit-documents-A, arbitrage Vic) — RÉGÉNÉRATION V11 : tous les documents servis,
habillés du GABARIT UNIQUE, dans ~/Desktop/LABUSE-EXPORTS-2026-11-07-V11/ + un SOMMAIRE.md.

Ce que la V11 apporte par rapport à la V7 :
  * UN seul gabarit (src/labuse/exports/theme.css) pour les 11 documents : papier blanc partout, le
    seul noir est le bandeau de couverture ; deux familles (Inter 400/500/600/700 + JetBrains Mono),
    polices EMBARQUÉES ; une échelle unique 34/20/13,5/12,5/11/10,5 px, rien sous 10,5 px ;
  * la couverture du Dossier refaite d'après la maquette (bandeau LABUSE, référence mono, adresse
    34 px, sous-titre, plan de situation, six tuiles, sommaire paginé, cartouche « données à jour
    au ») ;
  * l'ORDRE des sections (fiche ET Dossier, miroirs) : 1 Identité · 2 Urbanisme · 3 Potentiel ·
    4 Risques · 5 Terrain · 6 Bâti · 7 Réseaux · 8 Marché · 9 Fiscalité · 10 Quartier · 11 Limites ;
  * les RETRAITS de l'inventaire (RNB, BAN PLUS, APER, GéoMCE, FRR, « hors TCSP », parts à 0 %,
    piscine absente, historique de détention nul, VEFA insuffisant) + sources rassemblées au §11 ;
  * la correction du PRODUCTIBLE SOLAIRE (le Dossier disait « non calculé » à tort ; désormais la
    valeur de la fiche, même lecteur).

En process (TestClient, base locale `labuse`), rendu PDF in-process (venv weasyprint). AUCUNE écriture
prod, AUCUN mail.

    PROJ_DATA=$HOME/miniforge3/envs/labusedb/share/proj PYTHONPATH=$PWD/src \
      ~/Desktop/labuse/.venv/bin/python scripts/docs1_regen_v8.py
"""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse")
os.environ.setdefault("LABUSE_PDF_PROCESS_ISOLE", "0")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

OUT = Path.home() / "Desktop" / "LABUSE-EXPORTS-2026-11-07-V11"

CIBLE = "97411000BZ1065"                 # Saint-Denis (La Montagne) — bâtie, Uh, PPR bleue (référence)
VOISINES = ["97411000BZ1066", "97411000BZ1288"]
NUE_U = "97409000AK0804"                 # Saint-André — nue, UB
PPR_U = "97415000DH0076"                 # zone U partiellement en zone ROUGE de PPR — l'Étude PRODUIT un scénario
ZONE_N = "97421000AB0133"                # Salazie — zone N : le Gabarit rend un refus propre


def _compte_actif(db) -> int:
    from sqlalchemy import text
    r = (db.execute(text("SELECT id FROM comptes WHERE statut='actif' ORDER BY id LIMIT 1")).scalar()
         or db.execute(text("SELECT id FROM comptes ORDER BY id LIMIT 1")).scalar())
    return int(r) if r else 1


#: saisies ILLUSTRATIVES du Bilan (programme saisi, postes vides → « non calculable — saisissez vos coûts »).
_BILAN_ILLUSTRATIF = {
    "programme": {"terrain": None, "surface_taxable": 65, "sdp": 35},
    "produits": [{"libelle": "Logement", "lots": 1, "suv": 65, "prix_ttc_m2_suv": 4500, "tva": 0.021}],
    "postes": {}, "mode": "marge", "marge_cible": 9, "calendrier": {},
}


def regen() -> list[str]:
    from fastapi.testclient import TestClient

    from labuse.api import bilan as _bilan, tenant
    from labuse.api.app import app
    from labuse.db import session_factory, session_scope
    from labuse.flash.report import generate_flash_report

    cid = _compte_actif(session_factory()())
    tenant.current_compte = lambda request=None: cid     # type: ignore[assignment]
    _bilan.current_compte = lambda request=None: cid      # type: ignore[assignment]
    client = TestClient(app)
    OUT.mkdir(parents=True, exist_ok=True)
    produits: list[str] = []

    def _ecrire(nom: str, octets: bytes):
        (OUT / nom).write_bytes(octets)
        produits.append(f"{nom} ({len(octets)} o)")

    def _doc_get(num, label, idu, route, ext="pdf"):
        r = client.get(route)
        if r.status_code == 200 and (r.content[:4] == b"%PDF" or ext != "pdf"):
            _ecrire(f"{num} — {label} — {idu}.{ext}", r.content)
        else:
            produits.append(f"{num} — {label} — {idu} : NON RENDU ({r.status_code})")

    tags = {CIBLE: "", NUE_U: " [nue zone U]", PPR_U: " [zone U, PPR rouge partielle — scénario]",
            ZONE_N: " [zone N — Gabarit refus]"}
    for idu in (CIBLE, NUE_U, PPR_U, ZONE_N):
        tag = tags[idu]
        _doc_get("01", f"Dossier{tag}", idu, f"/dossier/{idu}.pdf")
        try:
            with session_scope() as db:
                fp = generate_flash_report(idu, order_ref="V11", force=True, db=db, with_map=True)
            _ecrire(f"02 — Flash{tag} — {idu}.pdf", fp.read_bytes())
        except Exception as exc:  # noqa: BLE001
            produits.append(f"02 — Flash — {idu} : NON RENDU ({exc})")
        g = client.post(f"/bilan/{idu}/generer", json=_BILAN_ILLUSTRATIF)
        if g.status_code == 200 and g.json().get("doc_id"):
            did = g.json()["doc_id"]
            _doc_get("03", f"Bilan{tag}", idu, f"/bilan/{idu}.pdf?doc_id={did}")
            _doc_get("04", f"Bilan (Excel){tag}", idu, f"/bilan/{idu}.xlsx?doc_id={did}", ext="xlsx")
        else:
            produits.append(f"03 — Bilan — {idu} : NON RENDU (generer {g.status_code})")
        _doc_get("05", f"Apporteur{tag}", idu, f"/apporteur/{idu}.pdf")
        _doc_get("06", f"Pre-dossier PC{tag}", idu, f"/pre-dossier/{idu}.zip", ext="zip")
        _doc_get("07", f"Gabarit{tag}", idu, f"/gabarit/{idu}.pdf")
        _doc_get("09", f"Etude de zone{tag}", idu, f"/etude-zone.pdf?idu={idu}&rayon_km=1")
        e = client.post("/modules/etude/pdf", json={"idus": [idu]})
        if e.status_code == 200 and e.content[:4] == b"%PDF":
            _ecrire(f"10 — Etude de faisabilite{tag} — {idu}.pdf", e.content)
        else:
            produits.append(f"10 — Etude de faisabilite — {idu} : NON RENDU ({e.status_code})")
        _doc_get("12", f"Estimer un bien{tag}", idu, f"/analyse-annonce/{idu}.pdf")
        cpdf = client.post("/courrier/pdf", json={"idu": idu})
        if cpdf.status_code == 200 and cpdf.content[:4] == b"%PDF":
            _ecrire(f"13 — Courrier{tag} — {idu}.pdf", cpdf.content)
        else:
            produits.append(f"13 — Courrier — {idu} : NON RENDU ({cpdf.status_code})")

    _doc_get("08", "Comparatif", CIBLE, f"/comparatif.pdf?idus={CIBLE},{VOISINES[0]},{VOISINES[1]}")
    return produits


def sommaire(produits: list[str]) -> str:
    return (
        "# LABUSE — Tous les documents (V11, DOCS-DA-1 : un seul gabarit), par parcelle\n\n"
        "**Mandat DOCS-DA-1 (arbitrage Vic)** — UN seul gabarit pour les 11 documents, et un Dossier\n"
        "complet, utile, rangé. Référence visuelle : `docs/design/maquettes/gabarit-documents-A.pdf`.\n\n"
        "## V11 — deux écarts corrigés\n"
        "1. **Pied sur UNE SEULE ligne, IDENTIQUE partout** : à gauche « Document d'information · ne\n"
        "   remplace ni un certificat d'urbanisme, ni une étude réglementaire, ni un conseil juridique »,\n"
        "   à droite la pagination ; **« Généré via LABUSE » retiré**. Source unique `rendu.FOOT_LIGNE`\n"
        "   (exports, Bilan, Étude, Flash). Testé.\n"
        "2. **Étude de faisabilité** : plus de **Verdana** ni d'**Andale Mono** (textes du plan masse SVG)\n"
        "   → Inter / JetBrains Mono. Le test des polices porte sur TOUS les PDF générés, Étude comprise.\n\n"
        "## V10 — six écarts de maquette corrigés\n"
        "1. **Pied de page sur une ligne, SANS date**, tous documents (la date ne vit qu'en couverture,\n"
        "   « Données à jour au »). Testé (`test_pied_de_page_sans_date`).\n"
        "2. **Polices** : « IBM Plex Mono » → **JetBrains Mono** partout (nom embarqué) ; le **Courrier**\n"
        "   passe sous le gabarit (Inter embarquée, forme de lettre conservée). Testé sur les 11 documents.\n"
        "3. **§Potentiel** : schéma 2D et vue 3D dans **deux cadres de même taille côte à côte**, légende\n"
        "   sous chacun.\n"
        "4. **PPR** : une seule date, celle de l'**approbation du PPR de la commune**, dans tout le Dossier\n"
        "   (plus la date d'édition de la couche DEAL) ; le fait `date_ppr` du banc attrape la régression.\n"
        "5. **Productible solaire** : « 1 548 kWh/kWc — **très favorable** » (même lecture que la fiche).\n"
        "6. Plus aucune ligne « **Sources :** » sous une section dans le **Flash**, le **Gabarit** et\n"
        "   l'**Étude de zone** (comme le Dossier).\n\n"
        "## A — Le gabarit (à la source, une fois pour tous)\n"
        "- **Papier blanc partout** ; le seul aplat sombre est le **bandeau de couverture** (un bandeau,\n"
        "  jamais une page entière).\n"
        "- **Deux familles** : Inter (400/500/600/700) pour le texte, JetBrains Mono pour les références\n"
        "  cadastrales — **polices embarquées** dans chaque PDF (plus de Space Grotesk ni de repli Verdana).\n"
        "- **Une échelle unique** : 34 / 20 / 13,5 / 12,5 / 11 / 10,5 px — **rien sous 10,5 px**.\n"
        "- **Couverture** refaite d'après la maquette : bandeau LABUSE + nom du document, référence mono,\n"
        "  adresse 34 px, sous-titre (type de bien, zone), plan de situation, six tuiles-chiffres, sommaire\n"
        "  paginé, cartouche (n° de rapport · généré le · **données à jour au** = date du run servi),\n"
        "  disclaimer sur une ligne. Pas de légende des badges en couverture.\n\n"
        "## B — Le Dossier (rangé)\n"
        "- **Ordre** (fiche à l'écran ET Dossier, miroirs) : 1 Identité · 2 Urbanisme · 3 Potentiel ·\n"
        "  4 Risques et environnement · 5 Terrain · 6 Bâti · 7 Réseaux et desserte · 8 Marché ·\n"
        "  9 Fiscalité et dispositifs · 10 Quartier · 11 Limites et sources.\n"
        "- **Retraits** de l'inventaire : identifiants RNB, adresses BAN PLUS, APER, GéoMCE, FRR,\n"
        "  « hors rayon TCSP », parts à 0 %, piscine absente, historique de détention nul, VEFA quand\n"
        "  l'échantillon est insuffisant. **Les sources ne figurent plus sous chaque section** — elles\n"
        "  sont rassemblées au §11.\n"
        "- **Correction** : le **productible solaire** (le Dossier disait « non calculé » à tort) affiche\n"
        "  désormais la valeur de la fiche (même lecteur : `viabilisation.solaire`).\n"
        "- **15 FAITS AJOUTÉS** (V11), chacun lu au MÊME robinet que la fiche (payload / moteur partagé)\n"
        "  et vérifié par le banc : pente maximale + alerte terrassement · hauteur à l'égout mesurée ·\n"
        "  acquéreurs professionnels à moins de 300 m sur 36 mois, nommés et datés · permis de la\n"
        "  section cadastrale sur 36 mois · fourchette DVF (Q1–Q3) · les 8 comparables les plus proches\n"
        "  (comme Estimer) · loyer de marché OLL · niveau de vie Filosofi 200 m · gestionnaires de\n"
        "  réseaux nommés · ligne de bus au contact · taux départemental de taxe d'aménagement ·\n"
        "  saturation de la densité · niveaux maximum · vue 3D du gabarit À CÔTÉ du schéma 2D ·\n"
        "  arrêtés CatNat (seulement si le compte de la commune est complet). **Tendance DVF : un seul\n"
        "  lecteur** (`prix_ancien`) ou rien. Le front de la fiche n'est pas touché ; le CERFA garde sa\n"
        "  typographie réglementaire.\n\n"
        "## C — Les dix autres documents\n"
        "Flash, Bilan, Apporteur, Pré-dossier PC, Gabarit, Comparatif, Étude de zone, Étude de\n"
        "faisabilité, Estimer, Courrier reçoivent le même gabarit (polices et échelle unifiées) sans\n"
        "changer de contenu ; le Courrier garde sa forme de lettre.\n\n"
        "## Parcelles\n"
        f"- `{CIBLE}` — Saint-Denis (La Montagne), bâtie, Uh, PPR bleue (témoin de référence).\n"
        f"- `{NUE_U}` — Saint-André, **nue en zone U**.\n"
        f"- `{PPR_U}` — **zone U partiellement en zone ROUGE de PPR** (l'Étude rend un scénario).\n"
        f"- `{ZONE_N}` — Salazie, **zone N** (Gabarit et Étude : refus motivé).\n\n"
        "## Documents produits\n" + "\n".join(f"- {p}" for p in produits) + "\n\n"
        "*Généré en process (base locale `labuse`), prod jamais touchée. DOCS-DA-1 — un seul gabarit.*\n"
    )


if __name__ == "__main__":
    prods = regen()
    (OUT / "SOMMAIRE.md").write_text(sommaire(prods), encoding="utf-8")
    print(f"=== V11 → {OUT} ===")
    for p in prods:
        print(" ", p)
    print(f"\nSOMMAIRE.md écrit ({len(prods)} entrées).")
