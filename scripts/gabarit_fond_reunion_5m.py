"""Installe le fond hors ligne du pilote à partir de la livraison RGE ALTI IGN D974.

Usage : python scripts/gabarit_fond_reunion_5m.py /chemin/vers/la-livraison.7z
Source : https://data.geopf.fr/telechargement/resource/RGEALTI/RGEALTI_2-0_5M_ASC_RGR92UTM40S-REUN89_D974_2023-09-05
Archive officielle contrôlée avant extraction. Nécessite bsdtar et GDAL en ligne de commande.
"""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory

LIVRAISON = "RGEALTI_2-0_5M_ASC_RGR92UTM40S-REUN89_D974_2023-09-05"
SORTIE = Path(__file__).resolve().parents[1] / "data" / "mnt5m" / "reunion.tif"


def installer(archive, sortie):
    with archive.open("rb") as fichier:
        if hashlib.file_digest(fichier, "md5").hexdigest() != "278ccf19def0d55e28c3027eb0380f5e":
            raise ValueError("Empreinte différente de celle publiée par l’IGN pour cette livraison.")
    sortie.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=sortie.parent) as tmp:
        dossier = Path(tmp)
        subprocess.run([shutil.which("bsdtar") or "tar", "-xf", str(archive.resolve()),
                        "-C", tmp, "--include", "*.asc"], check=True)
        dalles = sorted(dossier.rglob("*.asc"))
        if len(dalles) != 128:
            raise ValueError("La livraison attendue contient 128 dalles.")
        vrt = dossier / "reunion.vrt"
        subprocess.run(["gdalbuildvrt", "-q", "-a_srs", "EPSG:2975", str(vrt), *map(str, dalles)], check=True)
        tif = dossier / "reunion.tif"
        subprocess.run(["gdal_translate", "-q", "-of", "GTiff", "-ot", "Float32",
                        "-co", "TILED=YES", "-co", "COMPRESS=DEFLATE", "-co", "PREDICTOR=3",
                        "-mo", f"LIVRAISON={LIVRAISON}", "-mo", "SOURCE=IGN RGE ALTI",
                        "-mo", "VERTICAL_DATUM=REUN89", str(vrt), str(tif)], check=True)
        os.replace(tif, sortie)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--sortie", type=Path, default=SORTIE)
    args = parser.parse_args()
    installer(args.archive, args.sortie)
