"""Recalcul indépendant — chaîne hauteur / surélévation / densité (identités servies).

Le moteur `residuel`/`potentiel` sert plusieurs chiffres liés par des identités simples que
l'on refait à la main, à partir des AUTRES chiffres servis de la même fiche (aucun code de
production importé) :

  · marge de surélévation  = round(hauteur_regle − hauteur_bati, 1)   (potentiel.surelevation)
  · écart faîtage/BD TOPO  = round(faîtage − hauteur_bdtopo, 1)       (hauteur_lidar)
  · marge par contrainte   = round(regle_m − mesure_m, 1)            (surelevation_mesuree)
  · densité                : pct_consomme + pct_residuel = 100        (identité de partition)
  · niveaux existants      = max(1, round(égout/3))                   (ETAGE_REF_M=3, recalc)

Un écart révèle un arrondi mal ordonné, une constante d'étage différente, ou une soustraction
faite sur d'autres entrées que celles affichées.
"""
from __future__ import annotations

from . import socle

ETAGE_REF_M = 3.0


def _r1(x):
    return round(x, 1) if x is not None else None


def verifier(rec: socle.Recalc, conn, echantillon):
    for row in echantillon:
        idu = row["idu"]
        f = socle.fiche(idu)
        pot = socle.chemin(f, "potentiel_transformation")
        bien = socle.chemin(f, "le_bien")

        # 1) marge de surélévation = hauteur_regle − hauteur_bati.
        #    ⚠ Deux chemins clampent DIFFÉREMMENT (constat CALCULS-1) :
        #    · chemin « sourcé » (LiDAR HD, surelevation_mesuree) : marge BRUTE, peut être < 0 ;
        #    · chemin « estimé » (BD TOPO, surelevation)          : marge = max(0, regle−bati).
        #    Le recalcul applique la même règle selon la nature servie.
        if isinstance(pot, dict):
            regle = pot.get("hauteur_regle_m")
            bati = pot.get("hauteur_bati_m")
            marge = pot.get("hauteur_marge_m")
            nature = pot.get("hauteur_nature")
            if regle is not None and bati is not None and marge is not None:
                brut = _r1(regle - bati)
                attendu = brut if nature == "sourcé" else max(0.0, brut)
                rec.compare("potentiel.surelevation", f"hauteur_marge_m[{nature}]", idu,
                            servi=marge, recalc=attendu, tol="0", cause="formule")

            # 2) densité : pct_residuel = max(0, 100 − pct_consomme)  (app.py:5838)
            pc, pr = pot.get("pct_consomme"), pot.get("pct_residuel")
            if isinstance(pc, (int, float)) and isinstance(pr, (int, float)):
                rec.compare("potentiel.densite", "pct_residuel=max(0,100−pct_consomme)", idu,
                            servi=pr, recalc=max(0, 100 - pc), tol="0", cause="formule")

            # 3) marge par contrainte (surélévation mesurée) = regle_m − mesure_m
            for i, c in enumerate(pot.get("hauteur_contraintes") or []):
                if not isinstance(c, dict):
                    continue
                r, m, mg = c.get("regle_m"), c.get("mesure_m"), c.get("marge_m")
                if r is not None and m is not None and mg is not None:
                    rec.compare("potentiel.surelevation_mesuree", f"marge_m[{c.get('base')}]",
                                f"{idu}#{i}", servi=mg, recalc=_r1(r - m), tol="0", cause="formule")

        # 4) écart faîtage / BD TOPO = faîtage − hauteur_bdtopo
        if isinstance(bien, dict):
            fait = bien.get("hauteur_faitage_m")
            bdt = bien.get("hauteur_bdtopo_m")
            ecart = bien.get("ecart_faitage_bdtopo_m")
            if fait is not None and bdt is not None and ecart is not None:
                rec.compare("hauteur_lidar.discordance", "ecart_faitage_bdtopo_m", idu,
                            servi=ecart, recalc=_r1(fait - bdt), tol="0", cause="formule")

            # 5) niveaux existants recalculés depuis l'égout LiDAR (max(1, round(égout/3)))
            egout = bien.get("hauteur_egout_m")
            if isinstance(egout, (int, float)) and egout > 0:
                with conn.cursor() as cur:
                    cur.execute("SELECT egout_m FROM batiment_hauteur_lidar WHERE idu=%s "
                                "ORDER BY faitage_m DESC NULLS LAST LIMIT 1", (idu,))
                    r = cur.fetchone()
                if r and r[0]:
                    niveaux = max(1, round(r[0] / ETAGE_REF_M))
                    # pas de niveaux servi direct : on vérifie au moins que la règle est stable
                    # (déterminisme du calcul sur la donnée brute) — instructif, tol 0.
                    rec.compare("residuel._niveaux_existants", "niveaux(egout)", idu,
                                servi=niveaux, recalc=max(1, round(egout / ETAGE_REF_M)),
                                tol="0", cause="formule")
