"""CIRCUIT-1 lot 1.5 — LE MIROIR EN BASE : `labuse registre sync` écrit registre_chiffres,
registre_robinets et registre_aretes DEPUIS le code (le code est la vérité ; la base sert la
page Circuit et la sonde). Idempotent : truncate + insert dans une transaction — deux `sync`
successifs laissent la base identique.
"""
from __future__ import annotations

from sqlalchemy import text

from . import CHIFFRES, ROBINETS, aretes

DDL = """
CREATE TABLE IF NOT EXISTS registre_chiffres (
  id varchar(80) PRIMARY KEY,
  libelle text NOT NULL,
  unite varchar(20) NOT NULL,
  niveau varchar(20) NOT NULL,
  definition text NOT NULL,
  moteur varchar(60),
  calcul varchar(20) NOT NULL,
  fonction text NOT NULL,
  reservoirs text[] NOT NULL DEFAULT '{}',
  portee varchar(8) NOT NULL,
  version_def varchar(12) NOT NULL,
  classe_regle varchar(20),
  verdict_regle varchar(24),
  valide_par varchar(12),
  verifie_le varchar(12),
  reference_regle jsonb,
  sync_le timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE registre_chiffres ADD COLUMN IF NOT EXISTS classe_regle varchar(20);
ALTER TABLE registre_chiffres ADD COLUMN IF NOT EXISTS verdict_regle varchar(24);
ALTER TABLE registre_chiffres ADD COLUMN IF NOT EXISTS valide_par varchar(12);
ALTER TABLE registre_chiffres ADD COLUMN IF NOT EXISTS verifie_le varchar(12);
ALTER TABLE registre_chiffres ADD COLUMN IF NOT EXISTS reference_regle jsonb;
CREATE TABLE IF NOT EXISTS registre_robinets (
  id varchar(80) PRIMARY KEY,
  categorie varchar(20) NOT NULL,
  nom text NOT NULL,
  parent varchar(80),
  route text NOT NULL,
  mode_rendu varchar(20) NOT NULL,
  chiffres text[] NOT NULL DEFAULT '{}',
  hors_registre text,
  sync_le timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS registre_aretes (
  type varchar(30) NOT NULL,          -- reservoir_vers_chiffre | chiffre_vers_robinet
  source varchar(80) NOT NULL,
  cible varchar(80) NOT NULL,
  PRIMARY KEY (type, source, cible)
);
"""


def sync(db) -> dict:
    """Écrit le miroir. Rend les compteurs (pour le CLI et les tests)."""
    for stmt in DDL.split(";"):
        if stmt.strip():
            db.execute(text(stmt))
    db.execute(text("TRUNCATE registre_chiffres, registre_robinets, registre_aretes"))
    # CIRCUIT-4 lot 5.1 — le miroir porte la RÈGLE de chaque donnée (classe, verdict, référence,
    # valide_par, verifie_le), lue des fiches (le code est la vérité).
    import json as _json

    from .. import regles as _regles
    for cid, c in CHIFFRES.items():
        rg = _regles.pour_api(cid) or {}
        db.execute(text(
            "INSERT INTO registre_chiffres (id, libelle, unite, niveau, definition, moteur, calcul,"
            " fonction, reservoirs, portee, version_def, classe_regle, verdict_regle, valide_par,"
            " verifie_le, reference_regle) VALUES (:i, :l, :u, :n, :d, :m, :c, :f,"
            " :r, :p, :v, :cr, :vr, :vp, :vl, :rr)"),
            {"i": cid, "l": c.libelle, "u": c.unite, "n": c.niveau, "d": c.definition,
             "m": c.moteur, "c": c.calcul, "f": c.fonction, "r": list(c.reservoirs),
             "p": c.portee, "v": c.version_def,
             "cr": rg.get("classe"), "vr": rg.get("verdict"), "vp": rg.get("valide_par"),
             "vl": rg.get("verifie_le"),
             "rr": _json.dumps(rg.get("reference"), ensure_ascii=False) if rg.get("reference") else None})
    for rid, r in ROBINETS.items():
        db.execute(text(
            "INSERT INTO registre_robinets (id, categorie, nom, parent, route, mode_rendu,"
            " chiffres, hors_registre) VALUES (:i, :c, :n, :p, :r, :m, :ch, :h)"),
            {"i": rid, "c": r.categorie, "n": r.nom, "p": r.parent, "r": r.route,
             "m": r.mode_rendu, "ch": list(r.chiffres), "h": r.hors_registre})
    ar = aretes()
    for typ, paires in ar.items():
        for src, cible in paires:
            db.execute(text(
                "INSERT INTO registre_aretes (type, source, cible) VALUES (:t, :s, :c)"),
                {"t": typ, "s": src, "c": cible})
    return {"chiffres": len(CHIFFRES), "robinets": len(ROBINETS),
            "aretes": sum(len(v) for v in ar.values())}
