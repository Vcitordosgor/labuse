"""CHASSE-3 angle 3 — prix du neuf (VEFA-1) et prix de sortie (PRIX-SORTIE-1),
face à face de TOUS les lecteurs sur les 24 communes.

Deux notions distinctes depuis la scission (arbitrage Vic RETOURS-11F M1) :
  « VEFA à l'acte »  = neuf_vefa_commune (DVF VEFA, fenêtre d'ancrage, lots habitation)
  « neuf observé »   = resolve_prix_neuf_marche (ventes ≤ 3 ans post-achèvement,
                       préséance secteur > commune > île) — c'est LE prix de sortie servi.

Lecteurs confrontés (même notion ⇒ même valeur, même n) :
  VEFA acte  : contexte commune (neuf_eur_m2) · comparateur (prix_neuf) ·
               baromètre (neuf_reference) · couche carte vefa_neuf (SQL attrs) ·
               Dossier PDF (« Prix du neuf — VEFA »)
  observé    : contexte commune (prix_neuf_observe) · bloc Marché (ligne prix_sortie_neuf)
  prix de sortie, MÊME PARCELLE témoin : faisabilité (prix_sortie.prix) ·
               questionnaire Financier (prefill prix_sortie_saisi_eur_m2) ·
               Dossier PDF (« Prix de vente prévu »)
Négatifs : « ancien », « VEFA », « revente » jamais présentés comme prix de sortie
           (PDF : la valeur du prix de l'ancien ne doit pas suivre un libellé de sortie).

Sorties : docs/audit-2026-10/CHASSE-3/PRIX.csv (une ligne par commune et par notion,
valeurs de chaque lecteur) + anomalies imprimées et préfixées ANOMALIE;.
Rejouable : LABUSE_CHASSE3_API=http://127.0.0.1:6015 python -m scripts.chasse.prix3
"""
from __future__ import annotations

import csv
import json
import os
import re
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import psycopg

BASE = os.environ.get("LABUSE_CHASSE3_API", "http://127.0.0.1:6015")
DSN = os.environ.get("LABUSE_DSN", "dbname=labuse")
OUT = Path(__file__).resolve().parents[2] / "docs" / "audit-2026-10" / "CHASSE-3"
OUT.mkdir(parents=True, exist_ok=True)


def _api(path: str):
    url = BASE + urllib.parse.quote(path, safe="/?&=")
    with urllib.request.urlopen(url, timeout=300) as r:
        return json.loads(r.read())


def _pdf_texte(path: str) -> str:
    url = BASE + urllib.parse.quote(path, safe="/?&=")
    try:
        with urllib.request.urlopen(url, timeout=300) as r:
            pdf = r.read()
    except urllib.error.HTTPError as e:
        return f"[HTTP {e.code}] {e.read().decode('utf-8', 'replace')[:200]}"
    with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
        f.write(pdf)
        f.flush()
        return subprocess.run(["pdftotext", "-layout", f.name, "-"],
                              capture_output=True, text=True).stdout


def _entier_apres(texte: str, motif: str) -> int | None:
    """Premier entier (espaces fines tolérées) qui suit `motif` dans le texte PDF."""
    m = re.search(motif + r"[^\d]{0,80}?(\d[\d   ]{2,})", texte, re.S)
    if not m:
        return None
    return int(re.sub(r"\D", "", m.group(1)))


def main() -> None:
    conn = psycopg.connect(DSN)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT commune FROM parcels ORDER BY 1")
    communes = [r[0] for r in cur.fetchall()]
    comparateur = {r["commune"]: r for r in _api("/comparateur-communes")["communes"]}
    anomalies: list[str] = []
    lignes_csv: list[list] = []

    for commune in communes:
        ctx = _api(f"/communes/{commune}/contexte")
        marche = ctx.get("marche") or ctx  # tolérance de forme
        s = json.dumps(ctx, ensure_ascii=False)
        vefa_ctx = (re.search(r'"neuf_eur_m2":\s*(\d+)', s) or [None, None])[1]
        obs = ctx.get("prix_neuf_observe") or {}
        if not obs:
            m = re.search(r'"prix_neuf_observe":\s*({[^}]*})', s)
            obs = json.loads(m.group(1)) if m else {}
        comp = comparateur.get(commune, {})
        insee = comp.get("insee")
        baro = _api(f"/moteurs/barometre?insee={insee}") if insee else {}
        neuf_ref = (baro.get("neuf_reference") or {})
        bloc = _api(f"/moteurs/marche/{commune}")
        l3 = next((l for l in bloc.get("lignes", []) if l.get("cle") == "prix_sortie_neuf"), {})
        l3v = l3.get("valeurs") or {}

        # couche carte VEFA (SQL — ce que les tuiles/geojson servent)
        cur.execute("""SELECT attrs FROM spatial_layers
                       WHERE kind='vefa_neuf' AND commune=%s LIMIT 1""", (commune,))
        row = cur.fetchone()
        carte_attrs = row[0] if row else None
        carte_prix = None
        if isinstance(carte_attrs, dict):
            for k in ("prix_m2_neuf", "prix_eur_m2", "median_eur_m2", "prix_m2", "prix"):
                if isinstance(carte_attrs.get(k), (int, float)):
                    carte_prix = round(carte_attrs[k])
                    break

        # parcelle témoin (même règle que le bloc marché : proche du centroïde, géométrie posée)
        cur.execute("""
            SELECT p.idu FROM parcels p
            WHERE p.commune = %s AND p.geom_2975 IS NOT NULL
              AND EXISTS (SELECT 1 FROM parcel_residuel r
                          WHERE r.parcel_id = p.id AND r.sdp_residuelle_m2 > 200)
            ORDER BY p.id LIMIT 1""", (commune,))
        trow = cur.fetchone()
        idu = trow[0] if trow else None
        fais_prix = fin_prefill = pdf_sortie = pdf_vefa = None
        if idu:
            fais = _api(f"/modules/faisabilite/{idu}")
            fais_prix = ((fais.get("prix_sortie") or {}).get("prix"))
            quest = _api(f"/financier/{idu}/questionnaire")
            qs = json.dumps(quest, ensure_ascii=False)
            m = re.search(r'"id": "prix_sortie_saisi_eur_m2".*?"prefill": ({[^}]*}|null)', qs, re.S)
            if m and m.group(1) != "null":
                fin_prefill = json.loads(m.group(1)).get("valeur")
            texte = _pdf_texte(f"/dossier/{idu}.pdf")
            pdf_vefa = _entier_apres(texte, r"Neuf VEFA — commune")
            texte_fin = _pdf_texte(f"/financier/{idu}.pdf")
            pdf_sortie = _entier_apres(texte_fin, r"Prix de vente prévu")
            if re.search(r"prix de sortie[^\n]{0,60}ancien", texte_fin, re.I):
                anomalies.append(f"{commune};{idu};PDF Financier : « prix de sortie » adossé à « ancien »")
            # négatif : « prix de sortie » ne doit jamais introduire la valeur de l'ancien
            if re.search(r"prix de sortie[^\n]{0,60}ancien", texte, re.I):
                anomalies.append(f"{commune};{idu};PDF : « prix de sortie » adossé à « ancien »")

        vefa_vals = {"contexte": int(vefa_ctx) if vefa_ctx else None,
                     "comparateur": comp.get("prix_neuf"),
                     "barometre": neuf_ref.get("prix_m2_neuf"),
                     "carte": carte_prix, "pdf": pdf_vefa}
        obs_vals = {"contexte": obs.get("eur_m2"), "bloc_marche": l3v.get("prix_eur_m2")}
        sortie_vals = {"faisabilite": fais_prix and round(fais_prix),
                       "financier_prefill": fin_prefill and round(fin_prefill),
                       "pdf": pdf_sortie}

        for notion, vals in (("vefa_acte", vefa_vals), ("neuf_observe", obs_vals),
                             ("prix_sortie_parcelle", sortie_vals)):
            posees = {k: v for k, v in vals.items() if v is not None}
            uniques = set(posees.values())
            verdict = "OK" if len(uniques) <= 1 else "DIVERGE"
            if verdict == "DIVERGE":
                anomalies.append(f"{commune};{idu or ''};{notion} diverge : {posees}")
            lignes_csv.append([commune, idu or "", notion, verdict,
                               json.dumps(vals, ensure_ascii=False)])
        print(f"{commune:<22} vefa={vefa_vals} obs={obs_vals} sortie={sortie_vals}")

    with (OUT / "PRIX.csv").open("w", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["commune", "parcelle_temoin", "notion", "verdict", "valeurs_par_lecteur"])
        w.writerows(lignes_csv)
    print(f"\n{len(anomalies)} divergence(s) :")
    for a in anomalies:
        print("ANOMALIE;" + a)
    conn.close()


if __name__ == "__main__":
    main()
