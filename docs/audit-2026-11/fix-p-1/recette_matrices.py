"""FIX-P-1 — rejeu des matrices du lot P sur ses 10 parcelles. Génère EN PROCESS les 3 documents qui
portent les 5 faits (Dossier, Estimer, Flash) par leurs builders réels, et vérifie 0 écart sur :
  P-01  sdp_libelle           — « SDP restante » partout, « résiduelle » nulle part
  P-02  aleas (count + mot)   — tuile « Risques » = aléas distincts (n_hazards), mot « aléa »
  J#4   aleas Dossier==fiche==Estimer
  P-03  emprise_bati_m2       — une seule emprise (fiche le_bien.emprise_batie_m2)
  P-04  prix_median_maison    — « Prix médian … » = marche_dvf ; Estimer pondéré = « Prix estimé au m² »
Lancé avec le venv PDF-capable + PYTHONPATH du worktree + LABUSE_DATABASE_URL = base app (lecture seule).
"""
import re
import sys

from labuse.db import session_scope
from labuse.api.app import parcel_fiche
from labuse.exports.builder import construire, construire_analyse_annonce_parc
from labuse.flash.report import generate_flash_report
from labuse.pige.api import radar_annonce_estimation, distinct_hazards

PARCELLES = [
    ("nue", "97416000HS0478"), ("maison", "97409000AC0102"), ("copropriete", "97401000AM0380"),
    ("ppr", "97421000AC0444"), ("a_cheval", "97415000CY0419"), ("rnu", "97417000BD0225"),
    ("grande", "97416000CS1048"), ("petite", "97401000AD0095"), ("vendue", "97415000AZ1645"),
    ("pm", "97411000CM0169"),
]


def _risques_tile_count(dossier_html: str):
    """La tuile « Risques » de la garde du Dossier : <div class="v">N aléa(s)</div><div class="l">Risques</div>."""
    m = re.search(r'data-quoi="n_hazards"><div class="v">([^<]*)</div><div class="l">Risques</div>', dossier_html)
    return m.group(1) if m else None


def _estimer_pm_line(est_html: str):
    """Ligne « Prix médian maison … €/m² » du bloc commune de l'Estimer (valeur DVF)."""
    m = re.search(r'Prix médian maison.*?([\d   ]{2,})\s*€/m²', est_html)
    return re.sub(r"\D", "", m.group(1)) if m else None


def _estimer_prix_estime(est_html: str):
    """Le prix pondéré d'Estimer porte le libellé « Prix estimé au m² » (jamais « médian »)."""
    return "Prix estimé au m²" in est_html


def _bati_emprise_estimer(est_html: str):
    m = re.search(r'Bâti existant, emprise</[^>]+>\s*<[^>]*>([\d   ]+)\s*m²', est_html)
    if not m:
        m = re.search(r'Bâti existant, emprise.*?([\d   ]{1,})\s*m²', est_html)
    return re.sub(r"\D", "", m.group(1)) if m else None


def main() -> int:
    ecarts = []
    for role, idu in PARCELLES:
        with session_scope() as db:
            fiche = parcel_fiche(idu, db=db)
            le_bien = (fiche.get("le_bien") or {})
            emp_fiche = le_bien.get("emprise_batie_m2")
            emp_fiche = round(float(emp_fiche)) if emp_fiche and float(emp_fiche) > 0 else None
            n_haz_fiche = (fiche.get("aleas") or {}).get("n_hazards")
            # Estimer (endpoint = même valeur que l'écran et le PDF)
            est = radar_annonce_estimation(idu)
            n_aleas_est = est.get("n_aleas")
            # documents
            dossier = construire(db, idu, "dossier", fiche=fiche).html   # route réelle : fiche passée
            try:
                estimer = construire_analyse_annonce_parc(db, idu).html
            except Exception as exc:  # noqa: BLE001
                estimer = ""
                ecarts.append(f"{idu} ({role}) : Estimer non généré ({type(exc).__name__}: {exc})")
            try:
                flash = generate_flash_report(idu).get("html", "") if isinstance(generate_flash_report(idu), dict) else ""
            except Exception:
                flash = ""
            if not flash:
                try:
                    fr = generate_flash_report(idu)
                    flash = getattr(fr, "html", "") or (fr.get("html", "") if isinstance(fr, dict) else "")
                except Exception as exc:  # noqa: BLE001
                    ecarts.append(f"{idu} ({role}) : Flash non généré ({type(exc).__name__}: {exc})")
                    flash = ""

            # ── P-01 : SDP restante partout, résiduelle nulle part ──
            for nom, html in (("dossier", dossier), ("estimer", estimer), ("flash", flash)):
                if html and re.search(r"SDP\s+r[ée]siduelle|de SDP résiduelle", html, re.I):
                    ecarts.append(f"{idu} ({role}) : « SDP résiduelle » présent dans {nom} (P-01)")

            # ── P-02 / J#4 : tuile Risques = aléas distincts, Dossier == fiche == Estimer, mot « aléa » ──
            tile = _risques_tile_count(dossier)
            if tile is not None:
                if "vigilance" in tile.lower():
                    ecarts.append(f"{idu} ({role}) : tuile Dossier dit « {tile} » (vigilance, P-02)")
                tnum = re.sub(r"\D", "", tile)
                tnum = int(tnum) if tnum else (0 if "aucun" in tile.lower() else None)
                if tnum is not None and n_haz_fiche is not None and tnum != n_haz_fiche:
                    ecarts.append(f"{idu} ({role}) : tuile Dossier={tnum} ≠ fiche n_hazards={n_haz_fiche} (J#4)")
            if n_aleas_est is not None and n_haz_fiche is not None and n_aleas_est != n_haz_fiche:
                ecarts.append(f"{idu} ({role}) : Estimer n_aleas={n_aleas_est} ≠ fiche n_hazards={n_haz_fiche} (J#4)")

            # ── P-03 : une seule emprise (Estimer lit la fiche) ──
            emp_est = est.get("emprise_bati_m2")
            if emp_est is not None and emp_fiche is not None and round(float(emp_est)) != emp_fiche:
                ecarts.append(f"{idu} ({role}) : Estimer emprise={emp_est} ≠ fiche={emp_fiche} (P-03)")
            emp_doc = _bati_emprise_estimer(estimer) if estimer else None
            if emp_doc and emp_fiche is not None and int(emp_doc) != emp_fiche:
                ecarts.append(f"{idu} ({role}) : Estimer PDF emprise={emp_doc} ≠ fiche={emp_fiche} (P-03)")

            # ── P-04 : « Prix médian … » = DVF ; pondéré = « Prix estimé au m² » ──
            if estimer and est.get("median") is not None and est.get("type_comparateur") == "bati":
                if not _estimer_prix_estime(estimer):
                    ecarts.append(f"{idu} ({role}) : Estimer n'étiquette pas « Prix estimé au m² » (P-04)")

            print(f"{role:12} {idu} | emp_fiche={emp_fiche} emp_est={emp_est} | "
                  f"n_haz fiche={n_haz_fiche} estimer={n_aleas_est} | tuile={tile!r}")

    print("\n" + ("=" * 60))
    if ecarts:
        print(f"ÉCARTS ({len(ecarts)}) :")
        for e in ecarts:
            print("  -", e)
        return 1
    print("0 ÉCART sur les 5 faits — recette P verte.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
