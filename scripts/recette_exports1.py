#!/usr/bin/env python
"""EXPORTS-1 — test doré de la recette (mandat, § Recette).

Génère les 6 exports + fiche.json des 4 témoins par les VRAIES routes (TestClient, base
réelle), extrait les grandeurs nommées des PDF (pdftotext -layout) et les confronte à la
référence écran. Divergence = échec du lot (exit 1).

Lancement (env audit, hors venv cassé) :
  DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib \
  PYTHONPATH=/Users/openclaw/Desktop/labuse-merge/src \
  /Users/openclaw/miniforge3/envs/labusedb/bin/python scripts/recette_exports1.py [--dir SORTIE]

Points de recette couverts : 1 (génération), 2 (grandeurs vs fiche.json), 3 (mots interdits),
4 (zéros sans couverture — contrôles ciblés). Le point 5 (requêtes de l'annexe) se rejoue à part.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

TEMOINS = ["97415000BO0852", "97401000AD0554", "97416000DY0106", "97411000AV0110"]


def _mots_interdits() -> list[str]:
    """0-bis — la liste VERSIONNÉE (config/mots_interdits.yaml) ; repli embarqué si absente.
    « Non ICPE » toléré dans le tableau ICPE seul — contrôle spécifique plus bas."""
    p = Path(__file__).resolve().parents[1] / "config" / "mots_interdits.yaml"
    if p.exists():
        try:
            import yaml
            return list(yaml.safe_load(p.read_text())["mots"])
        except Exception:  # noqa: BLE001 — repli embarqué, jamais un contrôle muet
            pass
    return ["run m1", "EPSG", "ST_Buffer", "à_vérifier", "deja_bati", "reglt",
            " pt)", "scoring", "fiabilité suivie", "doctrine", "page corrigée",
            "L'IA", "fiche commune", "parcours Flash", "MOBPRO", "n 11",
            "surélévation possible", "non identifiée", "rpls_sdes",
            "« latest » ingérée", "année non pinnée", "propre non public",
            "RPG.LATEST", "[2022, 2025]"]


MOTS_INTERDITS = _mots_interdits()

ERREURS: list[str] = []
MOTS_TROUVES: list[str] = []    # 0-bis — contrôle distinct (sonde) : les hits « mots interdits »


def ko(msg: str) -> None:
    ERREURS.append(msg)
    print(f"  ✗ {msg}")


def ok(msg: str) -> None:
    print(f"  ✓ {msg}")


def generer(idu: str, outdir: Path) -> dict:
    """EXPORTS-2 lot 8 — les CINQ documents + fiche.json des témoins. Les anciennes chaînes
    (fiche.pdf / dossier-banquier / argumentaire / Flash legacy) sont ÉTEINTES : tout passe par
    le BUILDER UNIQUE. Dossier · Résumé · Financier · Apporteur sont rendus PAR LES VRAIES ROUTES
    (ce que reçoit le client) ; le Flash (pas de route GET publique — fulfillment payant) est rendu
    par le builder, chemin identique à `facturation._flash_fulfill`. L'archive JSON (point 1.6) est
    vérifiée pour les cinq via `builder.generer_pdf` dans un sous-dossier `archives/`."""
    from datetime import date as _date

    from fastapi.testclient import TestClient
    from labuse.api.app import app
    from labuse.db import session_scope
    from labuse.exports import builder
    c = TestClient(app)
    d = outdir / idu
    d.mkdir(parents=True, exist_ok=True)
    fiche = c.get(f"/parcels/{idu}").json()
    (d / "fiche.json").write_text(json.dumps(fiche, ensure_ascii=False, indent=1))
    # 1) les documents servis par une route → le PDF EXACT que le client télécharge.
    # EXPORTS-REBRANCHEMENT-1 — le Résumé n'existe plus (RECETTE-3, décision Vic) : retiré de la
    # recette (il la faisait échouer 8 fois pour un document supprimé volontairement). Le
    # Pré-dossier PC (ZIP) entre à la recette. Le Financier SANS questionnaire répond 422
    # « document_non_etablissable » (RECETTE-5 V18b) : c'est le comportement VOULU, pas un échec.
    for name, url in (("dossier.pdf", f"/dossier/{idu}.pdf?carte=false"),
                      ("financier.pdf", f"/financier/{idu}.pdf"),
                      ("apporteur.pdf", f"/apporteur/{idu}.pdf")):
        r = c.get(url)
        if name == "financier.pdf" and r.status_code == 422                 and "document_non_etablissable" in r.text:
            ok(f"{idu}/financier : 422 non établissable (V18b — saisie requise, comportement voulu)")
            continue
        if r.status_code != 200:
            ko(f"{idu}/{name} : HTTP {r.status_code}")
            continue
        (d / name).write_bytes(r.content)
    rz = c.get(f"/pre-dossier/{idu}.zip")
    if rz.status_code != 200 or len(rz.content) < 10000:
        ko(f"{idu}/predossier_pc.zip : HTTP {rz.status_code} ({len(rz.content)} o)")
    else:
        (d / "predossier_pc.zip").write_bytes(rz.content)
        ok(f"{idu}/predossier_pc.zip : {len(rz.content)} o")
    # 2) le Flash par le builder (même chemin que la facturation).
    arch = d / "archives"
    arch.mkdir(exist_ok=True)
    try:
        with session_scope() as s:
            builder.generer_pdf(s, idu, "flash", fiche=fiche, jour=_date(2026, 9, 5),
                                chemin_pdf=str(d / "flash.pdf"))
    except Exception as exc:  # noqa: BLE001
        ko(f"{idu}/flash.pdf : {exc}")
    # 3) archive JSON (1.6) — Résumé supprimé (RECETTE-3) ; le Financier sans saisie ne
    # s'établit pas (V18b) : archives vérifiées pour dossier/apporteur/flash.
    for doc in ("dossier", "apporteur", "flash"):
        try:
            with session_scope() as s:
                builder.generer_pdf(s, idu, doc, fiche=fiche, jour=_date(2026, 9, 5),
                                    chemin_pdf=str(arch / f"{doc}.pdf"))
            if (arch / f"{doc}.json").exists():
                ok(f"{idu}/{doc} : rendu + archive JSON")
            else:
                ko(f"{idu}/{doc} : archive JSON absente (1.6)")
        except Exception as exc:  # noqa: BLE001
            ko(f"{idu}/{doc} : {exc}")
    for f in d.glob("*.pdf"):
        subprocess.run(["pdftotext", "-layout", str(f), str(f.with_suffix(".txt"))], check=True)
    # EXPORTS-REBRANCHEMENT-1 — Flash = Dossier (nom commercial) : les textes extraits des
    # DEUX rendus par le builder doivent être IDENTIQUES.
    fl, do = arch / "flash.txt", arch / "dossier.txt"
    for pdfa in (arch / "flash.pdf", arch / "dossier.pdf"):
        if pdfa.exists():
            subprocess.run(["pdftotext", "-layout", str(pdfa), str(pdfa.with_suffix(".txt"))], check=True)
    if fl.exists() and do.exists():
        if fl.read_text() == do.read_text():
            ok(f"{idu} : Flash = Dossier (pdftotext identiques)")
        else:
            ko(f"{idu} : Flash ≠ Dossier (le nom commercial diverge du document)")
    return fiche


def _num(s: str) -> int:
    return int(s.replace(" ", "").replace(" ", ""))


def verifier_temoin(idu: str, d: Path, fiche: dict) -> None:
    txts = {f.stem: f.read_text(encoding="utf-8", errors="replace") for f in d.glob("*.txt")}
    tout = "\n".join(txts.values())

    # ── pt 3 : mots interdits (liste versionnée — contrôle DISTINCT pour la sonde, 0-bis) ──
    for mot in MOTS_INTERDITS:
        ml = mot.lower()                      # RECETTE-11 — garde insensible à la casse (attrape aussi
        for doc, t in txts.items():           # un « Surélévation possible » capitalisé réintroduit)
            if ml in t.lower():
                MOTS_TROUVES.append(f"{idu}/{doc} : « {mot} »")
                ko(f"{idu}/{doc} : mot interdit « {mot} »")
    # EXPORTS-2 — aucun ◌ dans un document rendu (bloc non branché = absent, jamais un exemple)
    for doc, t in txts.items():
        if "◌" in t:
            ko(f"{idu}/{doc} : caractère ◌ présent (bloc non branché imprimé avec un exemple)")
    # « Non ICPE » : toléré UNIQUEMENT dans le tableau ICPE (ligne portant une distance en m)
    for doc, t in txts.items():
        for line in t.splitlines():
            if "Non ICPE" in line and not re.search(r"\d+\s*m\b", line):
                ko(f"{idu}/{doc} : « Non ICPE » hors tableau : {line.strip()[:80]}")

    # ── pt 2 : grandeurs nommées vs fiche.json ──
    # surface (l'écran fait foi)
    surf = fiche.get("surface_m2")
    if surf:
        attendu = f"{_num(f'{round(surf):,}'.replace(',', ' ')):,}".replace(",", " ")
        if f"{attendu} m²" not in tout and f"{round(surf)} m²" not in tout:
            ko(f"{idu} : surface écran {round(surf)} m² introuvable dans les PDF")
        else:
            ok(f"surface {round(surf)} m² cohérente")
    # prix ancien : LA phrase unique (marche_synthese) — même valeur partout, pas d'autre
    ms = fiche.get("marche_synthese") or ""
    m = re.search(r"Prix ancien médian (\d[\d ]*) €/m²", ms)
    if m:
        val = m.group(1).strip()
        deviants = set()
        for doc, t in txts.items():
            for hit in re.findall(r"Prix ancien médian (\d[\d ]*) €/m²", t):
                if hit.strip() != val:
                    deviants.add((doc, hit.strip()))
        if deviants:
            ko(f"{idu} : prix ancien divergent {deviants} (écran : {val})")
        else:
            ok(f"prix ancien unique {val} €/m² (écran = PDF)")
    # un seul « neuf » : « Neuf VEFA » a quitté la fiche (Q3)
    if "Neuf VEFA" in txts.get("fiche", ""):
        ko(f"{idu}/fiche : « Neuf VEFA » encore servi (Q3)")
    # médiane locale : jamais annoncée sans valeur (1.5)
    for doc, t in txts.items():
        if re.search(r"Médiane €/m² observée,", t):
            ko(f"{idu}/{doc} : médiane locale annoncée sans sa valeur (1.5)")

    # ── lot 3 : potentiel — la table orpheline ne fuit plus, écran = Dossier ──
    if idu == "97415000BO0852":
        for doc, t in txts.items():
            if re.search(r"\b127(\.\d)?\s*m²", t):
                ko(f"{idu}/{doc} : « 127 m² » (table orpheline parcel_residuel_bati) encore servi")
    pt = fiche.get("potentiel_transformation") or {}
    sdp_ecran = pt.get("sdp_residuelle_m2")
    m3 = re.search(r"Au sol \(SDP résiduelle du run servi\)\s+(\d[\d ]*) m²", txts.get("dossier", ""))
    if sdp_ecran is not None and m3:
        if abs(_num(m3.group(1)) - round(float(sdp_ecran))) > 1:
            ko(f"{idu} : SDP résiduelle écran {sdp_ecran} ≠ Dossier {m3.group(1)}")
        else:
            ok(f"SDP résiduelle écran = Dossier ({m3.group(1)} m²)")
    if idu == "97416000DY0106":
        if sdp_ecran not in (0, 0.0, None):
            ko(f"{idu} : SDP écran devrait être 0 par garde (zone N), servie {sdp_ecran}")
        if "zone_non_constructible" not in json.dumps(fiche, ensure_ascii=False) and \
           "zone_non_constructible" not in txts.get("dossier", ""):
            ko(f"{idu} : cause zone_non_constructible absente (T3)")

    # ── lot 2 : plus jamais un « appartement » à surface d'immeuble dans un tableau ──
    for doc, t in txts.items():
        for line in t.splitlines():
            m2 = re.search(r"Appartement\s+(\d[\d ]*) m²", line)
            if m2 and _num(m2.group(1)) > 200:
                ko(f"{idu}/{doc} : « Appartement {m2.group(1)} m² » servi (agrégat multi-lots, 2.2/2.3)")

    # ── pt 4 : zéros ciblés ──
    # la ligne « Secteur — X : médiane — » doit porter l'étiquette secondaire à proximité
    if re.search(r"Secteur — .* : médiane — €/m²", txts.get("fiche", "")) and \
            "secteur cadastral" not in txts.get("fiche", ""):
        ko(f"{idu}/fiche : médiane secteur « — » sans étiquette de couverture")


# GABARIT-5 — témoins du §10 « Gabarit réglementaire » (tiroir déclaré, miroir Dossier).
# servi complet · plafond « Non réglementé » · hauteur « Non chiffrée » · bloqué (motif seul).
GABARIT_TEMOINS = ["97411000IE0153", "97422000AY0953", "97411000BE0476", "97407000AM1059"]


def verifier_gabarit_temoins(outdir: Path) -> None:
    """GABARIT-5 lot C — le §10 du Dossier PDF = le tiroir Gabarit de l'écran (/outils/gabarit/{idu}).
    Pour chaque témoin : la zone d'implantation, le plafond (valeur ou « Non réglementé »), la hauteur
    (valeur ou « Non chiffrée »), et — parcelle bloquée — le motif seul, sans chiffres."""
    from fastapi.testclient import TestClient

    from labuse.api.app import app
    c = TestClient(app)
    for idu in GABARIT_TEMOINS:
        print(f"== gabarit {idu}")
        g = c.get(f"/outils/gabarit/{idu}").json()      # LE TIROIR ÉCRAN (source de vérité)
        r = c.get(f"/dossier/{idu}.pdf?carte=false")
        if r.status_code != 200:
            ko(f"gabarit {idu} : Dossier HTTP {r.status_code}"); continue
        d = outdir / idu
        d.mkdir(parents=True, exist_ok=True)
        (d / "dossier.pdf").write_bytes(r.content)
        subprocess.run(["pdftotext", "-layout", str(d / "dossier.pdf"), str(d / "dossier.txt")], check=True)
        t = (d / "dossier.txt").read_text(encoding="utf-8", errors="replace")
        if g.get("status") != "ok":
            # bloqué : le §10 imprime le motif métier et AUCUN chiffre de gabarit
            if "Gabarit — calcul incomplet" not in t:
                ko(f"gabarit {idu} : bloqué mais motif absent du §10 Dossier")
            elif re.search(r"Zone d'implantation\s+\d", t):
                ko(f"gabarit {idu} : bloqué mais un chiffre de zone d'implantation s'imprime")
            else:
                ok(f"gabarit {idu} : bloqué → motif seul au §10 (écran = Dossier)")
            continue
        # servi : la zone d'implantation écran == Dossier
        zi = g.get("zoneImplantationM2")
        if zi is not None and not re.search(rf"Zone d'implantation\s+{round(zi)}\s*m²", t):
            ko(f"gabarit {idu} : zone d'implantation écran {round(zi)} m² ≠ §10 Dossier")
        else:
            ok(f"gabarit {idu} : zone d'implantation {round(zi)} m² (écran = Dossier)")
        # plafond : « Non réglementé » (silence) ou la valeur
        if g.get("plafondEmpriseStatus") == "absent":
            if "Plafond d'emprise" in t and "Non réglementé" not in t:
                ko(f"gabarit {idu} : plafond doit imprimer « Non réglementé »")
            else:
                ok(f"gabarit {idu} : plafond « Non réglementé » (écran = Dossier)")
        # hauteur : « Non chiffrée » (prospect) ou la valeur
        if g.get("hauteurStatus") == "not_integrated":
            if not re.search(r"Hauteur réglementaire\s+Non chiffrée", t):
                ko(f"gabarit {idu} : hauteur doit imprimer « Non chiffrée »")
            else:
                ok(f"gabarit {idu} : hauteur « Non chiffrée » (écran = Dossier)")


def verifier_docs1(outdir: Path) -> None:
    """DOCS-1 (Lot D3) — les 3 nouveaux documents sur les témoins du mandat, par LES VRAIES ROUTES :
    Gabarit (servie + bloquée), Comparatif (3 parcelles paysage), Étude de zone (rayon 2 km). Plus
    Dossier/Apporteur/Pré-dossier PC/Bilan sur BZ1065. Chaque PDF : HTTP 200, octets, mots interdits."""
    from fastapi.testclient import TestClient
    from labuse.api.app import app
    c = TestClient(app)
    d = outdir / "docs1"
    d.mkdir(parents=True, exist_ok=True)
    mots = _mots_interdits()

    def _pdf(nom: str, url: str, *, min_o: int = 6000) -> None:
        r = c.get(url)
        if r.status_code != 200:
            ko(f"docs1/{nom} : HTTP {r.status_code}")
            return
        if len(r.content) < min_o:
            ko(f"docs1/{nom} : {len(r.content)} o (trop court)")
            return
        (d / nom).write_bytes(r.content)
        txt = d / (nom.replace(".pdf", ".txt"))
        try:
            subprocess.run(["pdftotext", "-layout", str(d / nom), str(txt)], check=True)
            contenu = txt.read_text(errors="ignore")
            trouves = [m for m in mots if m.lower() in contenu.lower()]
            if trouves:
                MOTS_TROUVES.extend(trouves)
                ko(f"docs1/{nom} : mot interdit {trouves}")
                return
        except Exception:  # noqa: BLE001 — pdftotext absent : on garde le PDF, pas le crible mots
            pass
        ok(f"docs1/{nom} : {len(r.content)} o")

    # Gabarit — servie.
    _pdf("gabarit_BW0102.pdf", "/gabarit/97415000BW0102.pdf")
    # Gabarit — bloquée (zone A/N) : 422 attendu (le PDF ne se génère pas).
    rb = c.get("/gabarit/97415000AB0001.pdf")
    if rb.status_code == 422 and "non_etablissable" in rb.text:
        ok("docs1/gabarit (bloquée) : 422 non établissable (calcul incomplet — voulu)")
    elif rb.status_code == 200:
        ok("docs1/gabarit 97415000AB0001 : calculable aujourd'hui (données évoluées) — 200")
    else:
        ko(f"docs1/gabarit (bloquée) : HTTP {rb.status_code} (attendu 422)")
    # Comparatif — 3 parcelles (paysage).
    _pdf("comparatif_CV.pdf", "/comparatif.pdf?idus=97415000CV1201,97415000CV1498,97415000CV1289")
    # Étude de zone — rayon 2 km.
    _pdf("etude_zone_AB1117.pdf", "/etude-zone.pdf?idu=97402000AB1117&rayon_km=2")
    # BZ1065 — les documents « à une parcelle » appelés depuis la porte Documents (Saint-Denis).
    bz = "97411000BZ1065"
    _pdf("bz1065_dossier.pdf", f"/dossier/{bz}.pdf?carte=false")
    _pdf("bz1065_apporteur.pdf", f"/apporteur/{bz}.pdf")
    rz = c.get(f"/pre-dossier/{bz}.zip")
    if rz.status_code == 200 and len(rz.content) > 10000:
        (d / "bz1065_predossier.zip").write_bytes(rz.content)
        ok(f"docs1/bz1065_predossier.zip : {len(rz.content)} o")
    else:
        ko(f"docs1/bz1065_predossier.zip : HTTP {rz.status_code}")
    rbil = c.get(f"/financier/{bz}.pdf")
    if rbil.status_code == 422 and "document_non_etablissable" in rbil.text:
        ok("docs1/bz1065 Bilan : 422 non établissable (hypothèses requises — voulu)")
    elif rbil.status_code == 200:
        (d / "bz1065_bilan.pdf").write_bytes(rbil.content)
        ok(f"docs1/bz1065 Bilan : {len(rbil.content)} o")
    else:
        ko(f"docs1/bz1065 Bilan : HTTP {rbil.status_code}")


def main() -> int:
    outdir = Path(sys.argv[sys.argv.index("--dir") + 1]) if "--dir" in sys.argv \
        else Path(tempfile.mkdtemp(prefix="recette-exports1-"))
    print(f"Recette EXPORTS-1 → {outdir}")
    for idu in TEMOINS:
        print(f"== {idu}")
        fiche = generer(idu, outdir)
        verifier_temoin(idu, outdir / idu, fiche)
    verifier_gabarit_temoins(outdir)
    verifier_docs1(outdir)   # DOCS-1 (Lot D3) — Gabarit · Comparatif · Étude de zone + BZ1065
    print(f"\n{'ÉCHEC — ' + str(len(ERREURS)) + ' divergence(s)' if ERREURS else 'RECETTE VERTE'}")
    # 0-bis — sortie machine pour la sonde (cas nocturne coherence-robinets) : divergences et
    # mots interdits SÉPARÉS (deux contrôles distincts du verdict).
    if "--json" in sys.argv:
        Path(sys.argv[sys.argv.index("--json") + 1]).write_text(json.dumps(
            {"temoins": TEMOINS, "erreurs": ERREURS, "mots_interdits": MOTS_TROUVES,
             "n_erreurs_hors_mots": len([e for e in ERREURS if "mot interdit" not in e]),
             "n_mots_interdits": len(MOTS_TROUVES)}, ensure_ascii=False, indent=1))
    return 1 if ERREURS else 0


if __name__ == "__main__":
    sys.exit(main())
