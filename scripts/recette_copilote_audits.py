"""Recette HTTPS explicite des dix derniers correctifs et des six requêtes historiques en 504.

Depuis la racine : python -m scripts.recette_copilote_audits https://hote-de-recette
Utilise le compte LABUSE_RECETTE_* et supprime uniquement les fils ouverts par ce passage.
"""
import argparse
import json
from time import monotonic
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from uuid import uuid4

from scripts.verite_permanente import _cookie_recette

A, B = "97411000BZ1281", "97415000BY0083"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base")
    args = parser.parse_args()
    base = args.base.rstrip("/")
    if urlparse(base).scheme != "https":
        parser.error("Une origine HTTPS est requise.")
    cookie, erreur = _cookie_recette(base)
    if not cookie:
        raise RuntimeError(erreur)

    def api(path, method="GET", body=None):
        req = Request(base + path, method=method, headers={"Cookie": cookie, "Content-Type": "application/json"},
                      data=json.dumps(body).encode() if body is not None else None)
        with urlopen(req, timeout=65) as res:
            return json.load(res)

    def verifier(cas, tours):
        fil = None
        try:
            for question, attendu in tours:
                debut = monotonic()
                rep = api("/api/copilote-v2/ask", "POST", {"message": question, "conversation_id": fil,
                                                          "request_id": str(uuid4())})
                fil = rep.get("conversation_id") or fil
                texte = rep.get("text", "")
                compact = "".join(texte.lower().split())
                if not fil or rep.get("erreur") or "".join(attendu.lower().split()) not in compact:
                    raise AssertionError(f"{cas} · {question} · attendu {attendu} · reçu {texte[:250]}")
                print(f"{cas} OK ({monotonic()-debut:.2f} s) {texte[:240]}", flush=True)
        finally:
            if fil and not api(f"/api/copilote-v2/missions/{fil}", "DELETE").get("ok"):
                raise RuntimeError(f"Nettoyage du fil {fil} non confirmé")

    fiche = api("/parcels/" + B)
    solaire = api("/modules/prospection-solaire/parcelle/" + B)
    from math import radians, tan
    pente = f"{100*tan(radians(fiche['terrain']['pente_moy_deg'])):.1f}".replace(".", ",")
    parcelle_u = sum(z["part"] for z in fiche["reglement_plu"]["zones"]
                     if z["zone"].upper().startswith("U"))
    cas = [
        ("2.08", f"Quelle est la surface totale de {A} et {B} ?", "3057"),
        ("2.08", f"Quelle est la surface totale de {B} et {A} ?", "3057"),
        ("2.08", f"Quelle est la pente du toit sur {A} ?", "toit"),
        ("2.08", f"Quelle est la capacité en logements de {B} ?", "logements"),
        ("2.08", f"Quelle est la surface et la zone PLU de {A} ?", "Uh"),
        ("2.08", "Quelle est la surface au 1 chemin de la Citerne 97417 Saint-Denis ?", "663"),
        ("5.01", "Calcule 3 % de 1,2 million d’euros.", "36000 €"),
        ("5.01", "Combien font 5 % de 300 milliers d’euros ?", "15000 €"),
        ("5.02", "Calcule −10 % de 600 €.", "= -60 €"),
        ("5.03", "Quel prix après une réduction de 10 % sur 600 € ?", "540 €"),
        ("5.03", "Quel prix après une hausse de 5 % sur 900 € ?", "945 €"),
        ("5.03", "Quel prix total, TVA de 20 % sur 500 € HT comprise ?", "600 €"),
        ("5.04", "Calcule 10 % de 2 ha en m².", "2000 m²"),
        ("5.04", "Calcule 25 % de 400 m² en hectares.", "0,01 ha"),
        ("5.05", f"Calcule 10 % de la surface de {B}.", "245,8 m²"),
        ("5.06", f"Quelle est la pente en pourcentage de {B} ?", pente + "%"),
        ("5.07", f"Combien de panneaux photovoltaïques de 400 Wc correspondent à la puissance installable sur {B} ?",
         str(round(solaire["kwc"] * 1000 / 400, 2)).replace(".", ",") + " panneaux"),
        ("5.08", f"Quelle est la production photovoltaïque mensuelle moyenne en kWh sur {B} ?",
         str(round(solaire["prod_annuel"]/12, 1)).replace(".", ",") + " kWh/mois"),
        ("5.09", f"Quelle est la surface en mètres carrés de la partie zonée U de {B} ?",
         f"{round(fiche['contenance_m2']*parcelle_u)} m²"),
    ]
    for numero, question, attendu in cas:
        verifier(numero, [(question, attendu)])
    verifier("5.05", [(f"Quelle est la surface de {A} ?", "599 m²"), ("Calcule 10 % de ce chiffre.", "59,9 m²")])
    if not api("/readyz")["ready"]:
        raise RuntimeError("L’API ne se déclare pas prête")


if __name__ == "__main__":
    main()
