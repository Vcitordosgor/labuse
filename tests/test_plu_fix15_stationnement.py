from labuse.plu_reglement import resolve_reglement


def conditions(commune, zone):
    rows = resolve_reglement(commune, zone)["regles_valeurs"]
    stat = next(r for r in rows if r["cle"] == "stationnement")
    return " ".join(c["texte"] for c in stat["conditions"])


def test_tampon_plafond_ud():
    assert "une place au maximum" in conditions("Le Tampon", "Ud")


def test_saint_louis_place_publique_ua():
    texte = conditions("Saint-Louis", "UA").lower()
    assert "stationnement public par logement" in texte and "hors parcelle" not in texte
