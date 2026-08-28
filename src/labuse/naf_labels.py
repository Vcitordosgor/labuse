"""ÉTUDE DE ZONE · Z4 — correspondance NAF (activité) ↔ libellé français, pour l'outil « Étude de zone ».

L'utilisateur cherche « boulangerie » → on propose le code 1071C. Table CURÉE et EXTENSIBLE (commerces
et services de proximité utiles au démarcheur foncier) — ce n'est pas la nomenclature complète (~732
sous-classes), mais les activités qu'on étudie en chalandise. Les codes sont NORMALISÉS sans point
(comme `sirene_etablissements.naf` : 10.71C → 1071C), pour se comparer directement.

Ajouter une activité = une ligne ici. Aucune dépendance externe.
"""
from __future__ import annotations

import unicodedata

# code NAF normalisé → libellé français court (celui qu'on montre et qu'on cherche).
NAF_LABELS: dict[str, str] = {
    "1071C": "Boulangerie et boulangerie-pâtisserie",
    "1071D": "Pâtisserie",
    "4711B": "Alimentation générale (épicerie)",
    "4711C": "Supérette",
    "4711D": "Supermarché",
    "4711F": "Hypermarché",
    "4721Z": "Primeur (fruits et légumes)",
    "4722Z": "Boucherie-charcuterie",
    "4723Z": "Poissonnerie",
    "4724Z": "Commerce de pain et pâtisserie (revente)",
    "4725Z": "Cave (vins et boissons)",
    "4726Z": "Tabac",
    "4730Z": "Station-service (carburants)",
    "4776Z": "Fleuriste / jardinerie",
    "4777Z": "Bijouterie",
    "4778C": "Commerce de détail spécialisé",
    "4791B": "Vente à distance / e-commerce",
    "5610A": "Restaurant (restauration traditionnelle)",
    "5610C": "Restauration rapide",
    "5630Z": "Bar / débit de boissons",
    "9602A": "Coiffure",
    "9602B": "Soins de beauté (esthétique)",
    "4773Z": "Pharmacie",
    "8621Z": "Médecin généraliste",
    "8622A": "Médecin spécialiste",
    "8623Z": "Chirurgien-dentiste",
    "8690D": "Cabinet d'infirmiers / paramédical",
    "5510Z": "Hôtel",
    "5520Z": "Hébergement touristique (meublé, gîte)",
    "8891A": "Crèche / garde d'enfants",
    "9313Z": "Salle de sport",
    "6419Z": "Banque (activité bancaire)",
    "6820A": "Location de logements",
    "6831Z": "Agence immobilière",
}


def _norme(s: str) -> str:
    """Minuscule, sans accents — pour une recherche tolérante (« pâtisserie » ≡ « patisserie »)."""
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.lower().strip()


def chercher(q: str, *, maxi: int = 20) -> list[dict]:
    """Cherche une activité par libellé français OU par code. Retourne [{"code","label"}] triés
    (préfixe d'abord, puis sous-chaîne)."""
    ql = _norme(q)
    if not ql:
        return []
    prefixes, contient = [], []
    for code, label in NAF_LABELS.items():
        nl = _norme(label)
        if ql == _norme(code) or _norme(code).startswith(ql):
            prefixes.append({"code": code, "label": label})
        elif nl.startswith(ql):
            prefixes.append({"code": code, "label": label})
        elif ql in nl:
            contient.append({"code": code, "label": label})
    return (prefixes + contient)[:maxi]


def label(code: str) -> str | None:
    """Libellé d'un code NAF normalisé (None si hors table curée)."""
    return NAF_LABELS.get((code or "").replace(".", "").upper())
