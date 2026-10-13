"""SOLIDITE-1 (Lot 4) — une routine de mise à jour toujours pareille.

Sans toucher le VPS : la commande `labuse parite` existe et cible les tables de RÉFÉRENCE (pas les
tables client vivantes) ; `deploy_donnees.sh` enchaîne les gardes dans le BON ordre (bascule en dernier) ;
`deploy_app.sh` porte la garde manifeste (avant + après) ; EXPLOITATION.md documente la routine + les
leçons de q_v18.
"""
import subprocess
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]


def _lire(rel: str) -> str:
    return (RACINE / rel).read_text(encoding="utf-8")


def test_parite_commande_existe_et_cible_les_references():
    from labuse import cli
    assert hasattr(cli, "parite_cmd")
    src = _lire("src/labuse/cli.py")
    # une SEULE définition de parite_cmd (fusion de la version sens/foi de main et de la comparaison live)
    assert src.count("def parite_cmd(") == 1
    deb = src.index("def parite_cmd(")
    corps = src[deb:deb + 3500]
    # pilotée PAR SENS (flux_sens : FOND Mac-fait-foi vs QUOTIDIEN prod-fait-foi)
    assert "flux_sens" in corps and "SOURCES_FOND_MAC" in corps
    # comparaison live par commune + listes pour scripts
    assert "--communes" in corps and "tables_quotidien" in corps
    # on NE compare PAS les tables client vivantes
    assert '"comptes"' not in corps and '"veilles"' not in corps


def test_deploy_donnees_gardes_dans_le_bon_ordre():
    t = _lire("deploy/scripts/deploy_donnees.sh")
    for garde in ("GARDE 1/8", "GARDE 2/8", "GARDE 3/8", "GARDE 4/8",
                  "GARDE 5/8", "GARDE 6/8", "GARDE 7/8", "GARDE 8/8"):
        assert garde in t, f"{garde} absente"
    # l'ordre : intersections (4) et comptages (sync-run, 3) AVANT la bascule (5)
    assert t.index("GARDE 4/8") < t.index("GARDE 5/8") < t.index("GARDE 6/8")
    assert "BASCULE EN DERNIER" in t
    assert "--no-bascule" in t and "sync-run.sh" in t


def test_deploy_donnees_syntaxe():
    r = subprocess.run(["bash", "-n", str(RACINE / "deploy/scripts/deploy_donnees.sh")],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_deploy_app_garde_manifeste_avant_et_apres():
    t = _lire("deploy/scripts/deploy_app.sh")
    assert "REFUS" in t and "score_labuse WHERE run_label" in t        # refus si run local absent de prod
    assert "contrôle du manifeste prod" in t                            # contrôle après envoi
    # le manifeste servi reste EXCLU du rsync (ne jamais l'expédier)
    assert "--exclude /config/served_manifest.json" in t


def test_exploitation_doc_routine_et_lecons_q18():
    t = _lire("docs/EXPLOITATION.md")
    assert "chemin unique" in t.lower() or "chemin UNIQUE" in t
    assert "deploy_donnees.sh" in t
    for lecon in ("Manifeste jamais expédié", "no-owner", "Adresses depuis le Mac",
                  "anti-rebuild des intersections", "Chemin complet des crons"):
        assert lecon in t, f"leçon q_v18 manquante : {lecon}"
