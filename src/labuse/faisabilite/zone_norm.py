"""Normalisation des codes de zone PLU — POINT DE CALCUL UNIQUE (arbitrage RE-RUN pt2.2, Vic).

Un même code de zone s'écrit de plusieurs façons selon le SIG communal : casse (AUB vs AUb), accents,
espaces/tirets, suffixes. Trois matchers en dépendaient chacun avec leur propre bricolage (resolve_zone,
au_ouverture.zone_regime, cascade classe()). On centralise ici pour qu'ils partagent EXACTEMENT la même
règle — un correctif de casse à un endroit ne doit plus manquer aux deux autres.

DEUX usages DISTINCTS, à ne pas confondre :

* `normalize_key(code)` — clé de MATCHING d'une (sous-)zone contre une clé de calibration. Insensible à
  la casse / aux accents / aux séparateurs, mais le RANG DE PHASAGE est CONSERVÉ : `1aub` ≠ `2aub`.
  1AU, 2AU, 3AU sont trois STATUTS D'OUVERTURE différents (phasage de Saint-Joseph, Bras-Panon) — la
  normalisation ne doit JAMAIS les confondre (exigence Vic).

* `famille_normalisee(code)` — famille U/AU/A/N pour la CASCADE, où le rang de phasage EST retiré
  (« 2AUc » doit se classer AU, pas « autre » — sinon la zone échappe au test U/AU et est servie sans
  contrôle : les 454 fermées-servies mesurées au pt2). `zone_phasage(code)` expose le rang à part.
"""
from __future__ import annotations

import re
import unicodedata


def _deaccent(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")


def normalize_key(code: str | None) -> str:
    """Clé de matching : minuscules, sans accents, sans séparateurs (espaces/tirets/apostrophes/points).
    Le RANG DE PHASAGE et les chiffres du code sont conservés (1aub ≠ 2aub ≠ aub). '' si vide."""
    if not code:
        return ""
    return re.sub(r"[^a-z0-9]", "", _deaccent(code).casefold())


def famille_normalisee(code: str | None) -> str:
    """Radical famille en MAJUSCULES, sans accents, PRÉFIXE DE PHASAGE RETIRÉ (« 2AUc » → « AUC »,
    « 1AUst » → « AUST »). Sert à tester l'appartenance famille (startswith 'AU'/'U'/'A'/'N')."""
    if not code:
        return ""
    return re.sub(r"^\d+", "", _deaccent(code).upper().strip())


def zone_phasage(code: str | None) -> int | None:
    """Rang de phasage (préfixe numérique) : « 2AUc » → 2, « AUc » → None. À conserver À CÔTÉ de la
    famille — jamais fondu dedans (1AU/2AU/3AU = trois statuts d'ouverture distincts)."""
    if not code:
        return None
    m = re.match(r"\s*(\d+)", code)
    return int(m.group(1)) if m else None


def est_famille(code: str | None, prefixes) -> bool:
    """La zone appartient-elle à l'une des familles `prefixes` (phasage ignoré, casse/accents ignorés) ?
    `prefixes` = codes famille tels que 'U','AU','A','N' (config cascade positive/negative)."""
    fam = famille_normalisee(code)
    return any(fam.startswith(_deaccent(p).upper()) for p in prefixes)
