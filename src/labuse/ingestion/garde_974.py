"""SOURCES-3 lot 4 — LE GARDE-FOU 974, commun à toute ingestion à maille adresse / parcelle /
bâtiment.

Le DPE a laissé passer 75 logements de Saint-Leu-la-Forêt (Val-d'Oise) portant un code postal
réunionnais (97436) : le code postal SEUL ne suffit pas (homonymie de commune, géocodage BAN qui
rabat, saisie fautive). Le garde croise TROIS critères indépendants et n'en croit AUCUN seul :

  1. le code postal est réunionnais — **974xx** (géographique) ou **977xx** (CEDEX, ex. la mairie
     de Saint-Denis « 97717 ») ;
  2. **et** le nom de commune est l'une des 24 (comparaison normalisée — accents, casse, tirets et
     abréviations « ST/STE » neutralisés) ;
  3. **et**, quand des coordonnées existent, elles tombent dans l'emprise de l'île.

Un critère ABSENT ne vote pas. Parmi les critères PRÉSENTS, s'ils ne confirment pas TOUS La Réunion
(deux qui se contredisent → au moins un dit « ailleurs »), la ligne est **rejetée** et journalisée
avec ses trois valeurs. Cas d'école : Saint-Leu-la-Forêt = CP 974 ✓ + commune « ST LEU » ✓ +
coordonnées Val-d'Oise ✗ → contradiction → rejet (le CP et la commune ne sauvent pas des coordonnées
métropolitaines). Mieux vaut une absence honnête qu'un bien de métropole épinglé sur l'île.
"""
from __future__ import annotations

from dataclasses import dataclass

from .run_all import REUNION_COMMUNES

# Emprise de l'île (WGS84), PADDÉE au-delà de l'étendue cadastrale réelle (lon 55.217→55.837,
# lat -21.389→-20.872) pour ne jamais rejeter un point littoral / 50 pas légitime.
REUNION_LON_MIN, REUNION_LON_MAX = 55.10, 55.95
REUNION_LAT_MIN, REUNION_LAT_MAX = -21.45, -20.80


def _fold(s: str) -> str:
    """Pliage d'un nom de commune : casse + accents + tirets/apostrophes + abréviations ST/STE.
    « L'Étang-Salé » → « letang sale » ; « ST LEU » → « saint leu » ; « Ste-Marie » → « sainte marie »."""
    if not s:
        return ""
    t = s.strip().lower()
    for a, b in (("à", "a"), ("â", "a"), ("ä", "a"), ("é", "e"), ("è", "e"), ("ê", "e"),
                 ("ë", "e"), ("î", "i"), ("ï", "i"), ("ô", "o"), ("ö", "o"), ("ù", "u"),
                 ("û", "u"), ("ü", "u"), ("ç", "c"), ("'", " "), ("’", " "), ("-", " ")):
        t = t.replace(a, b)
    mots = []
    for m in t.split():
        if m in ("st",):
            m = "saint"
        elif m in ("ste",):
            m = "sainte"
        mots.append(m)
    return " ".join(mots)


#: les 24 noms de communes, pliés — comparaison normalisée (jamais l'égalité brute).
COMMUNES_24_FOLD: frozenset[str] = frozenset(_fold(nom) for _, nom in REUNION_COMMUNES)


@dataclass(frozen=True)
class Verdict974:
    ok: bool
    raison: str
    cp: str | None
    commune: str | None
    lon: float | None
    lat: float | None
    cp_ok: bool | None          # None = critère absent (ne vote pas)
    commune_ok: bool | None
    coords_ok: bool | None


#: préfixes de code postal réunionnais : 974xx (géographique) ET 977xx (CEDEX — ex. « 97717
#: SAINT-DENIS CEDEX 9 », vérifié sur l'annuaire des 24 mairies). « 974 seul » rejetterait à tort
#: les adresses administratives CEDEX de l'île.
REUNION_CP_PREFIXES = ("974", "977")


def _cp_prefixe_974(cp: str | None) -> bool | None:
    if cp is None or str(cp).strip() == "":
        return None
    return str(cp).strip().startswith(REUNION_CP_PREFIXES)


def _commune_dans_24(commune: str | None) -> bool | None:
    if commune is None or str(commune).strip() == "":
        return None
    return _fold(str(commune)) in COMMUNES_24_FOLD


def _coords_dans_emprise(lon: float | None, lat: float | None) -> bool | None:
    if lon is None or lat is None:
        return None
    try:
        lo, la = float(lon), float(lat)
    except (TypeError, ValueError):
        return None
    return (REUNION_LON_MIN <= lo <= REUNION_LON_MAX
            and REUNION_LAT_MIN <= la <= REUNION_LAT_MAX)


def verifier_974(cp: str | None = None, commune: str | None = None,
                 lon: float | None = None, lat: float | None = None) -> Verdict974:
    """Le verdict du garde pour UNE ligne. `ok=True` seulement si au moins un critère est présent
    ET que TOUS les critères présents confirment La Réunion (unanimité). Sinon rejet + raison."""
    cp_ok = _cp_prefixe_974(cp)
    commune_ok = _commune_dans_24(commune)
    coords_ok = _coords_dans_emprise(lon, lat)
    presents = [c for c in (cp_ok, commune_ok, coords_ok) if c is not None]

    def _mk(ok: bool, raison: str) -> Verdict974:
        return Verdict974(ok, raison, (str(cp) if cp is not None else None),
                          (str(commune) if commune is not None else None),
                          (float(lon) if lon is not None else None),
                          (float(lat) if lat is not None else None),
                          cp_ok, commune_ok, coords_ok)

    if not presents:
        # aucun localisateur : on ne peut ni confirmer ni infirmer — passe, mais dit son incertitude
        # (à maille adresse/parcelle/bâtiment ce cas est rare et vaut d'être signalé, pas rejeté à l'aveugle).
        return _mk(True, "aucun critère de localisation (ni CP, ni commune, ni coordonnées) — non jugeable")
    if all(presents):
        return _mk(True, "confirmé La Réunion (tous les critères présents concordent)")
    # au moins un critère présent contredit : rejet, la raison NOMME les trois valeurs
    parts = []
    if cp_ok is False:
        parts.append(f"CP « {cp} » hors 974")
    if commune_ok is False:
        parts.append(f"commune « {commune} » hors des 24")
    if coords_ok is False:
        parts.append(f"coordonnées ({lon}, {lat}) hors emprise île")
    confirmants = []
    if cp_ok is True:
        confirmants.append("CP 974")
    if commune_ok is True:
        confirmants.append(f"commune « {commune} »")
    if coords_ok is True:
        confirmants.append("coordonnées dans l'île")
    raison = "rejet — " + " ; ".join(parts)
    if confirmants:
        raison += f" (contredit : {', '.join(confirmants)})"
    return _mk(False, raison)


def journaliser_rejet(db, source: str, v: Verdict974, *, cle: str | None = None) -> None:
    """Journalise UNE ligne rejetée avec ses trois valeurs (circuit_journal, action 'garde_974').
    Silencieux si la table de journal est absente (base de test) — jamais bloquant pour l'ingestion."""
    from .. import circuit_journal
    details = {"cle": cle, "cp": v.cp, "commune": v.commune, "lon": v.lon, "lat": v.lat,
               "raison": v.raison}
    try:
        circuit_journal.journaliser(db, "garde_974", source, "ingestion", "rejet", details)
    except Exception:  # noqa: BLE001 — un journal absent ne bloque pas l'ingestion
        pass
