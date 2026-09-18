"""FICHE-COUCHES-3 — audit par la preuve : pour chaque couche thématique, une parcelle témoin,
puis on regarde si l'info atteint le back (JSON fiche), la fiche (DOM — fait par le script
navigateur), et le PDF Dossier expert. Ce script fait le SQL témoin + rebatch + back + PDF.
Sortie : /tmp/fc3_audit.json (fusionné ensuite avec la visibilité DOM du navigateur)."""
import json
import subprocess
import urllib.request

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from labuse.cascade import evaluate_parcels
from labuse.config import get_settings

RUN = "q_v11_m137"
BACK = "http://127.0.0.1:8055"

# (kind, spatial_kind, subtype, mode, seuil_m, needle) — needle = phrase DISTINCTIVE cherchée
# dans le JSON fiche (back), le DOM (navigateur) et le PDF. mode: I=intersect, P=proximity.
CFG = [
    # dispositifs (fiscal, intersect périmètre)
    ("zfang", "zfang", None, "I", 0, "ZFANG"),
    ("frr", "frr", None, "I", 0, "revitalisation rurale"),
    ("tva_primo", "tva_primo", None, "I", 0, "TVA"),
    ("qpv", "qpv", None, "I", 0, "quartier prioritaire"),
    ("anru", "anru", None, "I", 0, "ANRU"),
    # environnement
    ("parc_national", "parc_national", None, "I", 0, "Parc national"),
    ("bassin_versant", "bassin_versant", None, "I", 0, "Bassin versant"),
    ("znieff", "znieff", None, "I", 0, "ZNIEFF"),
    ("enp", "ens", None, "I", 0, "naturel"),
    ("zone_humide", "zone_humide", None, "I", 0, "zone humide"),
    ("foret_publique", "foret_publique", None, "I", 0, "orêt"),
    # equipements (proximité)
    ("amenite_bpe", "amenite_bpe", None, "P", 1500, "proximité"),
    ("amenite", "amenite", None, "P", 800, "ommerces et services"),
    # foncier
    ("sar", "sar", None, "I", 0, "SAR"),
    ("safer", "safer", None, "I", 0, "agricole"),
    ("zone_activite", "zone_activite", None, "I", 0, "zone d'activit"),
    ("friche", "friche", None, "I", 0, "friche"),
    ("piscine_cosia", "piscine_cosia", None, "I", 0, "piscine"),
    # marché
    ("vefa_neuf", "vefa_neuf", None, "I", 0, "logement neuf"),
    # patrimoine
    ("cimetiere", "cimetiere", None, "I", 0, "cimeti"),
    ("abf", "abf", None, "I", 0, "Bâtiments de France"),
    # réseaux (proximité)
    ("ligne_mt", "ligne_mt", None, "P", 50, "moyenne tension"),
    ("ligne_ht", "ligne_ht", None, "P", 500, "haute tension"),
    # risques
    ("tri_zone", "tri_zone", None, "I", 0, "TRI"),
    ("alea_inondation", "georisque_alea", "inondation", "I", 0, "Inondation"),
    ("alea_mvt", "georisque_alea", "mouvement_terrain", "I", 0, "Mouvement de terrain"),
    ("construction_surfacique", "construction_surfacique", None, "I", 0, "barrage"),
    ("casias", "sol_pollue", "casias", "P", 100, "CASIAS"),
    ("bruit_carte", "bruit_carte", None, "I", 0, "Dépassement de bruit"),
    ("bruit_route", "bruit_route", None, "I", 0, "bruit routier"),
    ("peb", "peb", None, "I", 0, "exposition au bruit"),
    ("endiguement", "endiguement", "zone_protegee", "I", 0, "endiguement"),
    ("construction_lineaire", "construction_lineaire", None, "I", 0, "soutènement"),
    ("trait_de_cote", "trait_de_cote", None, "I", 0, "trait de côte"),
    ("dpf", "dpf", None, "I", 0, "marchepied"),
    ("ppr", "ppr", None, "I", 0, "PPR"),
    ("icpe", "icpe", None, "P", 300, "nstallation classée"),
    ("sis", "sol_pollue", "sis", "I", 0, "secteur d'information sur les sols"),
    ("cavite", "cavite", None, "P", 300, "cavité"),
    # transport (proximité)
    ("tcsp", "tcsp_station", None, "P", 1500, "TCSP"),
    ("axe_structurant", "axe_structurant", None, "P", 1000, "Axe structurant"),
    ("transport_ligne", "transport_ligne", None, "P", 400, "Ligne de transport"),
    ("telepherique", "telepherique", "station", "P", 2000, "éléphérique"),
    ("pole_echange", "pole_echange", None, "P", 3000, "ôle d'échange"),
    ("transport_arret", "transport_arret", None, "P", 1500, "Arrêt"),
    # urbanisme
    ("zonage_parcelle", "plu_gpu_zone", None, "I", 0, "Zonage PLU"),
    ("plu_gpu_zone", "plu_gpu_zone", None, "I", 0, "zonage PLU"),
    ("cinquante_pas", "cinquante_pas", None, "I", 0, "50 pas"),
    ("artificialisation", "ocs_ge", None, "I", 0, "artificialis"),
    ("dpu", "dpu", None, "I", 0, "préemption"),
    ("sup", "sup", None, "I", 0, "utilité publique"),
    ("er", "plu_gpu_prescription", "05", "I", 0, "emplacement réservé"),
    ("ebc", "plu_gpu_prescription", "01", "I", 0, "spaces boisés"),
]

I_SQL = text(
    "SELECT p.idu FROM spatial_layers s JOIN parcels p ON ST_Intersects(p.geom_2975, s.geom_2975) "
    "WHERE s.kind = :k AND (CAST(:st AS text) IS NULL OR s.subtype = :st) LIMIT 1")
P_SQL = text(
    "SELECT p.idu FROM parcels p, (SELECT geom_2975 FROM spatial_layers WHERE kind=:k "
    "AND (CAST(:st AS text) IS NULL OR subtype=:st) AND geom_2975 IS NOT NULL LIMIT 1) s "
    "WHERE ST_DWithin(p.geom_2975, s.geom_2975, :seuil) ORDER BY p.geom_2975 <-> s.geom_2975 LIMIT 1")


def main():
    eng = create_engine(get_settings().database_url)
    rows = []
    with Session(eng) as s:
        # 1) témoins
        for kind, sk, st, mode, seuil, needle in CFG:
            sql = I_SQL if mode == "I" else P_SQL
            params = {"k": sk, "st": st} | ({"seuil": seuil} if mode == "P" else {})
            idu = s.execute(sql, params).scalar()
            rows.append({"kind": kind, "spatial_kind": sk, "subtype": st, "mode": mode,
                         "seuil": seuil, "needle": needle, "idu": idu})
        # 2) rebatch (une passe, tous les témoins trouvés)
        ids = [r_["idu"] for r_ in rows if r_["idu"]]
        pid_of = {r_["idu"]: s.execute(text("SELECT id FROM parcels WHERE idu=:i"), {"i": r_["idu"]}).scalar()
                  for r_ in rows if r_["idu"]}
        pids = sorted({pid_of[i] for i in ids})
        print(f"rebatch {len(pids)} parcelles témoins…", flush=True)
        evaluate_parcels(pids, s, persist=True, dryrun_label=RUN)
        s.commit()
    # 3) back (JSON) + PDF, par témoin
    for r_ in rows:
        idu, needle = r_["idu"], r_["needle"]
        r_["back"] = r_["pdf"] = False
        if not idu:
            continue
        try:
            js = urllib.request.urlopen(f"{BACK}/parcels/{idu}", timeout=60).read().decode("utf-8", "ignore")
            r_["back"] = needle.lower() in js.lower()
        except Exception as e:
            r_["back_err"] = str(e)
        try:
            urllib.request.urlretrieve(f"{BACK}/dossier/{idu}.pdf", f"/tmp/fc3_{r_['kind']}.pdf")
            txt = subprocess.run(["pdftotext", f"/tmp/fc3_{r_['kind']}.pdf", "-"],
                                 capture_output=True, text=True, timeout=60).stdout
            r_["pdf"] = needle.lower() in txt.lower()
        except Exception as e:
            r_["pdf_err"] = str(e)
        print(f"  {r_['kind']:24s} idu={idu} back={r_['back']} pdf={r_['pdf']}", flush=True)
    with open("/tmp/fc3_audit.json", "w") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    print("→ /tmp/fc3_audit.json", len(rows), "couches")


if __name__ == "__main__":
    main()
