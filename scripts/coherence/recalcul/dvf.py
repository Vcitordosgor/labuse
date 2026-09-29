"""Recalcul indépendant — médiane €/m² du secteur (bâti maison/appartement).

Le back sert `dvf_parcelle.secteur[].mediane_prix_m2` depuis la table pré-calculée
`dvf_secteur_medianes`, bâtie par `ingestion/dvf_marche.compute_medianes_secteur` avec un
`percentile_cont(0.5)` SQL sur le grain MUTATION.

On refait le calcul À LA MAIN, en Python, à partir des lignes brutes de
`dvf_mutations_parcelle`, SANS importer le code de production :
  · agrégation par mutation (valeur=max, bati_m2=Σ des lignes Vente/VTB) ;
  · type = maison si une ligne 'Maison', sinon appartement si 'Appartement' ;
  · prix_m2 = valeur / bati_m2 (garde bati_m2>0), écarte VTB portant du bâti, valeur>1000 ;
  · médiane = interpolation des deux centraux (socle.mediane), filtre 50–20000 €/m².

Comparé à (a) la valeur STOCKÉE et (b) la valeur SERVIE dans la fiche : trois sources qui
doivent coïncider. Un écart révèle un percentile_cont mal aligné, un grain différent, ou un
filtre divergent.
"""
from __future__ import annotations

from . import socle

#: mêmes bornes que le back (dvf_marche.py : FILTER prix_m2 BETWEEN 50 AND 20000).
BORNE_M2 = (50, 20000)
VALEUR_MIN = 1000


def _mutations_du_secteur(conn, secteur: str) -> dict[str, dict]:
    """Toutes les mutations touchant le secteur (préfixe IDU 10 car.), agrégées au grain
    mutation À PARTIR DE TOUTES leurs lignes Vente/VTB (le bâti d'une mutation est global)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT l.id_mutation, l.valeur_fonciere, l.type_local,
                   COALESCE(l.surface_reelle_bati,0) AS bati, l.nature_mutation
            FROM dvf_mutations_parcelle l
            WHERE l.id_mutation IN (
              SELECT DISTINCT id_mutation FROM dvf_mutations_parcelle
              WHERE substring(id_parcelle FROM 1 FOR 10) = %(sect)s)
              AND l.nature_mutation IN ('Vente', 'Vente terrain à bâtir')
            """, {"sect": secteur})
        rows = cur.fetchall()
    muts: dict[str, dict] = {}
    for id_mut, valeur, type_local, bati, nature in rows:
        m = muts.setdefault(id_mut, {"valeur": 0.0, "bati": 0.0,
                                     "a_maison": False, "a_appart": False, "vtb": False})
        m["valeur"] = max(m["valeur"], float(valeur or 0))
        m["bati"] += float(bati or 0)
        if type_local == "Maison":
            m["a_maison"] = True
        if type_local == "Appartement":
            m["a_appart"] = True
        if nature == "Vente terrain à bâtir":
            m["vtb"] = True
    return muts


def mediane_bati_secteur(conn, secteur: str, type_bien: str):
    """→ (mediane_prix_m2:int|None, n:int). type_bien ∈ {'maison','appartement'}."""
    muts = _mutations_du_secteur(conn, secteur)
    prix = []
    for m in muts.values():
        if m["valeur"] is None or m["valeur"] <= VALEUR_MIN:
            continue
        # écarte la VTB qui porte du bâti (M101 B2)
        if m["vtb"] and m["bati"] > 0:
            continue
        est_maison = m["a_maison"]
        est_appart = m["a_appart"] and not m["a_maison"]
        if type_bien == "maison" and not est_maison:
            continue
        if type_bien == "appartement" and not est_appart:
            continue
        if m["bati"] <= 0:
            continue
        p = m["valeur"] / m["bati"]
        if BORNE_M2[0] <= p <= BORNE_M2[1]:
            prix.append(p)
    med = socle.mediane(prix)
    return (round(med) if med is not None else None), len(prix)


def verifier(rec: socle.Recalc, conn, echantillon):
    """Pour chaque parcelle de l'échantillon, recalcule la médiane maison ET appartement de
    son secteur, compare au STOCKÉ (dvf_secteur_medianes) et au SERVI (fiche)."""
    secteurs_vus = set()
    for row in echantillon:
        idu = row["idu"]
        secteur = idu[:10]
        for type_bien in ("maison", "appartement"):
            cle = (secteur, type_bien)
            if cle in secteurs_vus:
                continue
            secteurs_vus.add(cle)
            med_recalc, n_recalc = mediane_bati_secteur(conn, secteur, type_bien)
            # (a) valeur stockée
            with conn.cursor() as cur:
                cur.execute("SELECT mediane_prix_m2, n_ventes FROM dvf_secteur_medianes "
                            "WHERE secteur=%s AND type_bien=%s", (secteur, type_bien))
                r = cur.fetchone()
            med_stocke = r[0] if r else None
            # seuil d'honnêteté du back : la fiche masque n<seuil, mais la table stocke tout ;
            # on compare la table (calcul brut) au recalcul brut. Tolérance 1 % (arrondi entier
            # + percentile_cont vs médiane-interpolée peuvent différer de 1 € sur n pair).
            rec.compare(
                "dvf_marche.compute_medianes_secteur",
                f"mediane_prix_m2[{type_bien}]", f"{secteur}",
                servi=med_stocke, recalc=med_recalc, tol="1 %", cause="formule")
        # (b) valeur servie dans la fiche (maison) vs recalcul
        f = socle.fiche(idu)
        secteur_fiche = socle.chemin(f, "dvf_parcelle.secteur")
        if isinstance(secteur_fiche, list):
            for s in secteur_fiche:
                if s.get("type_bien") in ("maison", "appartement") and s.get("mediane_prix_m2"):
                    med_recalc, n_recalc = mediane_bati_secteur(conn, secteur, s["type_bien"])
                    rec.compare(
                        "dvf_parcelle.secteur (servi)",
                        f"mediane_prix_m2[{s['type_bien']}]", f"{idu}",
                        servi=s["mediane_prix_m2"], recalc=med_recalc, tol="1 %", cause="formule")
