"""CIRCUIT-3 lot 2 — FABRIQUES DE CONTRÔLES PROPRES.

Des générateurs de `Controle` réutilisables par les filtres par source. Chacun mesure sur la
TABLE du filtre (respectant son `where`), pour que le même contrôle serve plusieurs sources.
Les seuils sont passés par l'appelant, écrits AVEC la mesure qui les a fixés (fait, pas opinion).
"""
from __future__ import annotations

from sqlalchemy import text

from .cadre import Controle, Filtre, Resultat, _et, ko, ok, skip


def compte_mauvais(cid: str, nature: str, severite: str, libelle: str, seuil: str,
                   mauvais_expr: str, params: dict | None = None,
                   extra_where: str | None = None) -> Controle:
    """KO si AU MOINS une ligne satisfait `mauvais_expr` (la condition d'anomalie). La valeur
    rapportée est le nombre de lignes fautives."""
    def m(db, f: Filtre, version: str) -> Resultat:
        if not f.table:
            return skip("pas de table")
        w = _et(f.where, extra_where, mauvais_expr)
        n = int(db.execute(text(f"SELECT count(*) FROM {f.table} WHERE {w}"),
                           params or {}).scalar() or 0)
        d = {"fautives": n}
        return ok(0, d) if n == 0 else ko(n, d)
    return Controle(cid, nature, severite, libelle, seuil, m)


def domaine(cid: str, col: str, valeurs: tuple[str, ...], severite: str, libelle: str,
            seuil: str, nature: str = "distribution") -> Controle:
    """KO si une valeur non nulle de `col` sort du domaine attendu (liste des valeurs hors domaine)."""
    def m(db, f: Filtre, version: str) -> Resultat:
        if not f.table:
            return skip("pas de table")
        w = _et(f.where, f"{col} IS NOT NULL")
        rows = db.execute(text(
            f"SELECT DISTINCT {col} FROM {f.table}" + (f" WHERE {w}" if w else ""))).scalars().all()
        hors = sorted({str(r) for r in rows} - set(valeurs))
        d = {"domaine": list(valeurs), "hors_domaine": hors}
        return ok("∅", d) if not hors else ko(",".join(hors)[:200], d)
    return Controle(cid, nature, severite, libelle, seuil, m)


def couverture(cid: str, nature: str, severite: str, libelle: str, seuil: str,
               bon_expr: str, plancher_pct: float,
               extra_where: str | None = None) -> Controle:
    """Mesure la PART (%) de lignes où `bon_expr` est vrai. KO si sous le plancher (mesuré,
    resserrable). La valeur rapportée est le pourcentage observé."""
    def m(db, f: Filtre, version: str) -> Resultat:
        if not f.table:
            return skip("pas de table")
        base_w = _et(f.where, extra_where)
        total = int(db.execute(text(
            f"SELECT count(*) FROM {f.table}" + (f" WHERE {base_w}" if base_w else ""))).scalar() or 0)
        if total == 0:
            return skip("aucune ligne à couvrir")
        bons = int(db.execute(text(
            f"SELECT count(*) FROM {f.table} WHERE {_et(base_w, bon_expr)}")).scalar() or 0)
        pct = round(100.0 * bons / total, 1)
        d = {"couverts": bons, "total": total, "pct": pct, "plancher_pct": plancher_pct}
        return ok(f"{pct}%", d) if pct >= plancher_pct else ko(f"{pct}%", d)
    return Controle(cid, nature, severite, libelle, seuil, m)


def _luhn_ok(s: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(s)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def siren_luhn(cid: str, col: str, severite: str, libelle: str, seuil: str,
               extra_where: str | None = None) -> Controle:
    """KO si un SIREN à 9 chiffres échoue la clé de Luhn (SIREN INSEE = Luhn). Les SIREN non
    conformes au format 9 chiffres sont hors de ce contrôle (un contrôle de format séparé les
    couvre) — ici on ne juge QUE la validité arithmétique des SIREN bien formés."""
    def m(db, f: Filtre, version: str) -> Resultat:
        if not f.table:
            return skip("pas de table")
        w = _et(f.where, extra_where, f"{col} ~ '^[0-9]{{9}}$'")
        sirens = db.execute(text(
            f"SELECT DISTINCT {col} FROM {f.table} WHERE {w}")).scalars().all()
        bad = [s for s in sirens if not _luhn_ok(str(s))]
        d = {"distincts_9c": len(sirens), "luhn_invalides": len(bad), "exemples": bad[:5]}
        return ok(0, d) if not bad else ko(len(bad), d)
    return Controle(cid, nature="referentiel", severite=severite, libelle=libelle,
                    seuil=seuil, mesure=m)


def part_max(cid: str, nature: str, severite: str, libelle: str, seuil: str,
             cible_expr: str, plafond_pct: float, extra_where: str | None = None) -> Controle:
    """Mesure la PART (%) de lignes où `cible_expr` est vrai. KO si AU-DESSUS du plafond."""
    def m(db, f: Filtre, version: str) -> Resultat:
        if not f.table:
            return skip("pas de table")
        base_w = _et(f.where, extra_where)
        total = int(db.execute(text(
            f"SELECT count(*) FROM {f.table}" + (f" WHERE {base_w}" if base_w else ""))).scalar() or 0)
        if total == 0:
            return skip("aucune ligne")
        cibles = int(db.execute(text(
            f"SELECT count(*) FROM {f.table} WHERE {_et(base_w, cible_expr)}")).scalar() or 0)
        pct = round(100.0 * cibles / total, 1)
        d = {"cibles": cibles, "total": total, "pct": pct, "plafond_pct": plafond_pct}
        return ok(f"{pct}%", d) if pct <= plafond_pct else ko(f"{pct}%", d)
    return Controle(cid, nature, severite, libelle, seuil, m)
