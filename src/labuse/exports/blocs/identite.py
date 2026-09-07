"""Bloc « 1. Identité et situation ». Lit des Valeur du registre, pose la nature de chacune,
pied depuis les réservoirs lus. Ligne absente → OMISE (aucun ◌)."""
from __future__ import annotations

from ..lignes import ligne, pied
from ..registre_fmt import fmt_eur, fmt_m2
from ..rendu import section, table_kv

IDS = ("surface_parcelle_m2", "adresse_ban", "type_proprietaire", "pente_deg",
       "prix_achat_historique_eur", "coproprietes_liste")


def _pente(v):
    return f"{str(v).replace('.', ',')}° (pente moyenne)"


def _achat(v):
    # D-a : dict {valeur, date, …} — dernière mutation DVF sur la parcelle
    d = v.get("date") or v.get("date_mutation")
    return fmt_eur(v["valeur"]) + (f" — mutation du {d}" if d else "")


def _copro(v):
    n = len(v) if isinstance(v, list) else v
    return f"Bâti en copropriété ({n} lot(s)) — la vente porte sur des lots, pas sur la parcelle"


def rendu(valeurs) -> str:
    lignes = [x for x in [
        ligne(valeurs, "Contenance cadastrale", "surface_parcelle_m2", fmt_m2),
        ligne(valeurs, "Adresse", "adresse_ban", str),
        ligne(valeurs, "Propriétaire", "type_proprietaire", str),
        ligne(valeurs, "Pente", "pente_deg", _pente),
        ligne(valeurs, "Prix d'achat de la parcelle", "prix_achat_historique_eur", _achat),
        ligne(valeurs, "Copropriété", "coproprietes_liste", _copro),
    ] if x]
    if not lignes:
        return ""      # aucune donnée servie → section omise (aucun ◌)
    return section("1. Identité et situation", table_kv(lignes) + pied(valeurs, IDS))
