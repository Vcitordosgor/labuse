"""PLU-CALIBRAGE-2 lot 0bis — CORRECTION des misattributions base ↔ secteur (Ud, Up, Uv).

Le contrôle d'attribution (qa/plu_calibrage2_sondage.py) a révélé que des valeurs de SECTEUR
avaient été gravées sur la zone de BASE. On corrige, règlement en main (re-lecture par
coordonnées de p.33-34 / 43-44 / 84, citations verbatim) :

  · la BASE porte le prospect / la plage (feuille `plage: true`, sans valeur unique → le calcul
    reste ESTIMÉ dessus, il ne branche pas une hauteur fausse) ;
  · chaque SECTEUR (Udop, Udp, Upi, Upr, Uva, Uvac, Uvl) porte SES valeurs (feuilles validées).

Écriture par la chirurgie de lignes testée (extraction._ecrire_regles) : le reste du fichier
(sous_destinations, silence, meta, autres rubriques) reste intact.

Usage : PYTHONPATH=src .venv/bin/python qa/plu_calibrage2_corriger.py
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from labuse.plu import destinations as D          # noqa: E402
from labuse.plu import extraction as X            # noqa: E402

INSEE = "97411"


def _v(**kw):
    return {**kw, "statut": "valide"}


# ── plages de base (prospect) : pas de valeur unique → l'étape reste ESTIMÉ ──────────────────
UD_HAUTEUR_PLAGE = {
    "faitage": _v(
        plage=True, regle_base="prospect L ≥ H",
        plage_m={"min": 12, "max": 27},          # R+3 (12 m) … R+8 (27 m), selon secteur
        secteurs_m={"Udop": 18, "Udp": 18},
        article="Ud.10", page_pdf=44,
        citation=("En secteur Ud : les constructions devront respecter un prospect L ≥ H "
                  "(alignement opposé, ou ligne à 10 m si l'emprise de la voie < 10 m). "
                  "Aucune hauteur absolue en base — les valeurs (R+5 = 18 m généralisé, "
                  "R+8 = 27 m, R+3 = 12 m) sont fixées par secteur (Udop, Udp)."))
}
UP_HAUTEUR_PLAGE = {
    "faitage": _v(
        plage=True, regle_base="prospect L ≥ H (Disp. Gén. XV)",
        plage_m={"min": 11, "max": 16}, secteurs_m={"Upi": 11, "Upr": 16},
        article="Up.10", page_pdf=34,
        citation=("Il sera fait application des prescriptions des « Dispositions Générales – "
                  "paragraphe XV. Prospects ». Les hauteurs maximales H sont fixées par secteur "
                  "(tableau Up.10) : Upr = 16 m, Upi = 11 m."))
}
UP_EMPRISE_PLAGE = {
    "ces": _v(
        plage=True, plage_pct={"min": 70, "max": 80}, secteurs_pct={"Upi": 80, "Upr": 70},
        article="Up.9", page_pdf=33,
        citation=("En secteur Upi : L'emprise au sol des constructions ne devra pas excéder 80 % de "
                  "la superficie de l'unité foncière. Elle pourra être portée à 100 %, uniquement en "
                  "rez-de-chaussée. En secteur Upr : L'emprise au sol des constructions ne devra pas "
                  "excéder 70 % de la superficie de l'unité foncière. Elle pourra être de 80 % pour "
                  "les parcelles dont la superficie est inférieure à 200 m2."))
}

# ── valeurs par SECTEUR (feuilles validées, citations verbatim, article + page) ──────────────
SECTEURS = {
    "Udop": {
        "hauteur": {
            "faitage": _v(m=18, article="Ud.10", page_pdf=44,
                          citation=("En secteur Udop : Hauteur maximale R+5, soit 18m, au faîtage ou à "
                                    "l'acrotère, généralisé sauf sur les rues suivantes : R+8 Bld Lancastel "
                                    "et rue L. Rambaud, soit 27 m ; R+3, soit 12 m, ruelle Sanisal, rue "
                                    "Mérancienne.")),
            "niveaux": _v(r_plus=5, article="Ud.10", page_pdf=44,
                          citation=("En secteur Udop : Hauteur maximale R+5, soit 18m, au faîtage ou à "
                                    "l'acrotère, généralisé (R+8 sur Bld Lancastel/rue L. Rambaud, R+3 sur "
                                    "ruelle Sanisal/rue Mérancienne).")),
        },
        "emprise_sol": {"ces": _v(pct=70, article="Ud.9", page_pdf=44,
                                  citation=("En secteur Udop, Udp : L'emprise au sol des constructions est "
                                            "limitée à 70 % de la superficie de l'unité foncière, 30% minimum "
                                            "de la parcelle doit être en pleine terre."))},
    },
    "Udp": {
        "hauteur": {
            "faitage": _v(m=18, article="Ud.10", page_pdf=44,
                          citation=("En secteur Udp : Hauteur maximale R+5, soit 18 m, au faîtage ou à "
                                    "l'acrotère, généralisé sauf sur les rues suivantes : R+8 Blvd Jean "
                                    "Jaurès, Bld Lancastel et rue L. Rambaud, soit 27 m ; R+3, soit 12 m, "
                                    "ruelles Tadar, Beauvillain, Magnan, Turpin, Nicaise, rues Marcadet et "
                                    "Magnan et allée de la cité Ah Soune.")),
            "niveaux": _v(r_plus=5, article="Ud.10", page_pdf=44,
                          citation=("En secteur Udp : Hauteur maximale R+5, soit 18 m, au faîtage ou à "
                                    "l'acrotère, généralisé.")),
        },
        "emprise_sol": {"ces": _v(pct=70, article="Ud.9", page_pdf=44,
                                  citation=("En secteur Udop, Udp : L'emprise au sol des constructions est "
                                            "limitée à 70 % de la superficie de l'unité foncière, 30% minimum "
                                            "de la parcelle doit être en pleine terre."))},
    },
    "Upi": {
        "hauteur": {
            "faitage": _v(m=11, article="Up.10", page_pdf=34,
                          citation=("La hauteur maximale H des constructions ne doit pas excéder dans le "
                                    "secteur : Upi = 11 m (tableau Up.10).")),
            "egout": _v(m=6.5, article="Up.10", page_pdf=34,
                        citation=("En secteur Upi (hauteur à l'égout he) : RDC+1 étage +Comble sans "
                                  "dépasser 6m50.")),
        },
        "emprise_sol": {"ces": _v(pct=80, article="Up.9", page_pdf=33,
                                  citation=("En secteur Upi : L'emprise au sol des constructions ne devra "
                                            "pas excéder 80 % de la superficie de l'unité foncière. Elle "
                                            "pourra être portée à 100 %, uniquement en rez-de-chaussée."))},
    },
    "Upr": {
        "hauteur": {
            "faitage": _v(m=16, article="Up.10", page_pdf=34,
                          citation=("La hauteur maximale H des constructions ne doit pas excéder dans le "
                                    "secteur : Upr = 16 m (tableau Up.10).")),
            "egout": _v(m=12, article="Up.10", page_pdf=34,
                        citation=("En secteur Upr (hauteur à l'égout he) : RDC+3 étages +Comble ou attique "
                                  "sans dépasser 12m.")),
            "niveaux": _v(r_plus=3, article="Up.10", page_pdf=34,
                          citation="En secteur Upr : RDC+3 étages +Comble ou attique sans dépasser 12m."),
        },
        "emprise_sol": {"ces": _v(pct=70, article="Up.9", page_pdf=33,
                                  citation=("En secteur Upr : L'emprise au sol des constructions ne devra "
                                            "pas excéder 70 % de la superficie de l'unité foncière. Elle "
                                            "pourra être de 80 % pour les parcelles dont la superficie est "
                                            "inférieure à 200 m2."))},
    },
    "Uva": {"hauteur": {"faitage": _v(m=4, article="Uv.10", page_pdf=84,
                                      citation=("En secteur Uva : La hauteur maximale H des constructions ne "
                                                "doit pas excéder 4 m."))}},
    "Uvac": {"hauteur": {"faitage": _v(m=10, article="Uv.10", page_pdf=84,
                                       citation="En secteur Uvac : … ne doit pas excéder 10m")}},
    "Uvl": {"hauteur": {"faitage": _v(m=10, article="Uv.10", page_pdf=84,
                                      citation="En secteur Uvl : … ne doit pas excéder 10m.")}},
}


def main() -> int:
    path = D._fichier_commune(INSEE)
    regles_par_zone: dict[str, dict] = {}

    # BASES : on retire les feuilles misattribuées, on pose la plage/prospect, on GARDE le reste.
    ud = copy.deepcopy(D.regles_zone(INSEE, "Ud"))
    ud["hauteur"] = UD_HAUTEUR_PLAGE                       # base = prospect (retire faitage/niveaux secteur)
    regles_par_zone["Ud"] = ud

    up = copy.deepcopy(D.regles_zone(INSEE, "Up"))
    up["hauteur"] = UP_HAUTEUR_PLAGE
    up["emprise_sol"] = UP_EMPRISE_PLAGE                   # base Up : plage 70–80 % selon secteur
    regles_par_zone["Up"] = up

    uv = copy.deepcopy(D.regles_zone(INSEE, "Uv"))
    uv.pop("hauteur", None)                                # base Uv : non servie (secteurs Uva/Uvac/Uvl) ;
    regles_par_zone["Uv"] = uv                             # le 4 m était Uva, retiré de la base

    # SECTEURS : leurs propres valeurs
    for code, reg in SECTEURS.items():
        regles_par_zone[code] = reg

    X._ecrire_regles(path, regles_par_zone)
    D._load_yaml.cache_clear()

    # rapport
    print("Correction appliquée. Feuilles validées par zone (après) :")
    for z in ["Ud", "Up", "Uv", "Udop", "Udp", "Upi", "Upr", "Uva", "Uvac", "Uvl"]:
        rows = [r for r in D.regles_commune(INSEE) if r["zone"] == z]
        print(f"  {z:6} : " + ", ".join(f"{r['chemin']}={'plage' if r.get('plage') else (r.get('m') or r.get('pct') or r.get('r_plus') or 'x')}"
                                        for r in rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
