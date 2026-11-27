"""Recette isolée d'une publication, d'un retrait et d'une panne fournisseur."""
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from labuse.ingestion import exonerations_delta as sync
from labuse.taxe_amenagement import SurfaceCategorie, calculer, config


class PublicationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "exonerations.json"
        self.day = date(2026, 11, 26)
        self.version = "A"
        row = dict(departement="974", zone_application="Communale", date_effet="2022-01-01",
                   date_fin=None, parcelle=None, section=None, prefixe=None, def_prov="DEFINITIF")
        row.update(dict.fromkeys(sync.CHAMPS))
        self.rows = [dict(row, commune=f"{n:02d}") for n in range(1, 25)]
        self.rows.append(dict(row, commune=None, zone_application="Départementale"))
        self.compte = len(self.rows)
        self.exports = 0

    def source(self, client, suffix="", **params):
        if suffix == "/records":
            return {"total_count": self.compte}
        if suffix == "/exports/json":
            self.exports += 1
            return self.rows
        return {"metas": {"default": {"data_processed": self.version, "modified": "date",
                                      "records_count": self.compte}}}

    def run_sync(self):
        with patch.object(sync, "_json", self.source):
            return sync.synchroniser(None, self.path, self.day, 2026)

    def test_publication_retrait_et_calcul_sans_redemarrage(self):
        self.run_sync()
        self.run_sync()
        self.assertEqual(self.exports, 1)
        self.version = "B"
        self.rows[2]["locaux_habitation"] = 60
        self.rows[-1]["locaux_habitation"] = 20
        self.rows.append(dict(self.rows[2], section="AR", parcelle="1066", locaux_habitation=80))
        self.compte += 1
        self.run_sync()
        with patch.object(sync, "FICHIER", self.path):
            projet = dict(surface_taxable_m2=80, logement_aide=True, taux_communal_pct=5,
                          commune_projet="97403", idu_projet="97403000AR1066")
            self.assertEqual(config(projet["idu_projet"])["exonerations_locales"]["communes"]["97403"]["social"], 80)
            r = calculer(**projet)
            self.assertEqual(r["part_communale_eur"], 356.8)
            self.assertEqual(r["part_departementale_eur"], 713.6)
            self.rows[-1]["locaux_habitation"] = None
            self.version = "C"
            self.run_sync()
            self.assertEqual(calculer(**projet)["part_communale_eur"], 1784)

    def test_six_categories_depuis_une_publication_et_seuils(self):
        from labuse.ingestion.exonerations_delta import CHAMPS

        for champ in CHAMPS:
            self.rows[2][champ] = 40
            self.rows[-1][champ] = 20
        self.run_sync()
        with patch.object(sync, "FICHIER", self.path):
            for categorie, surface, principale, equivalent, eligible in (
                ("industrie", 100, None, 50, True),
                ("boutique", 450, 300, 450, True), ("boutique", 450, 400, 450, False),
                ("jardin", 20, None, 20, True), ("jardin", 20.1, None, 20.1, False),
                ("pigeonnier", 25, None, 25, True), ("sante", 100, None, 100, True),
                ("transformation", 100, None, 50, True),
            ):
                with self.subTest(categorie=categorie, surface=surface, principale=principale):
                    local = SurfaceCategorie(categorie=categorie, surface=surface, surface_principale=principale)
                    r = calculer(surfaces=[local], commune_projet="97403", taux_communal_pct=5)
                    base = equivalent * 892
                    self.assertAlmostEqual(r["part_communale_eur"], round(base * (.6 if eligible else 1) * .05, 2))
                    attendu_dep = 0 if categorie == "transformation" else base * (.8 if eligible else 1) * .025
                    self.assertAlmostEqual(r["part_departementale_eur"], round(attendu_dep, 2))
            r = calculer(terrain_rehabilite=True, commune_projet="97403", taux_communal_pct=5,
                         surfaces=[SurfaceCategorie(categorie="industrie", surface=100)], piscine_m2=10)
            self.assertEqual(r["exonerations_locales"]["base_exoneree_communale"], (44600 + 2510) * .4)
            self.assertEqual(r["exonerations_locales"]["base_exoneree_departementale"], (44600 + 2510) * .2)

    def test_catalogue_complete_sans_nouvelle_publication_delta(self):
        # Une formule homologuée sur un champ déjà publié arrive aux lecteurs
        # via le même relevé atomique, même si la DGFiP n'a pas changé de version.
        from copy import deepcopy
        cfg = deepcopy(sync.load_yaml_config("taxe_amenagement"))
        self.rows[2]["maisons_de_sante"] = 30
        self.run_sync()
        cfg["formules_locales"]["cas_recette"] = {**cfg["formules_locales"]["sante"],
                                                  "label": "Cas de recette isolé"}
        with patch.object(sync, "load_yaml_config", return_value=cfg), patch.object(sync, "FICHIER", self.path):
            self.run_sync()
            self.assertEqual(self.exports, 2)
            r = calculer(surfaces=[SurfaceCategorie(categorie="cas_recette", surface=100)],
                         taux_communal_pct=5, commune_projet="97403")
            self.assertEqual(r["part_communale_eur"], 3122)

    def test_export_incomplet_et_echec_reseau(self):
        self.run_sync()
        avant = self.path.read_bytes()
        self.version = "B"
        self.compte += 1
        with self.assertRaises(ValueError):
            self.run_sync()
        with patch.object(sync, "_json", side_effect=OSError("Source indisponible")), self.assertRaises(OSError):
            sync.synchroniser(None, self.path, self.day, 2026)
        self.assertEqual(self.path.read_bytes(), avant)

    def test_date_effet_sans_republication(self):
        self.rows.append(dict(self.rows[2], date_effet="2026-11-27", immeubles_classes=75))
        self.compte += 1
        self.run_sync()
        self.assertFalse(sync.releve(self.path)["communes"])
        self.day = date(2026, 11, 27)
        self.run_sync()
        self.assertEqual(sync.releve(self.path)["communes"]["97403"]["monument"], 75)


if __name__ == "__main__":
    unittest.main()
