"""NU4-B — prouve la CONSÉQUENCE du piège #6 : un essai expiré qui PAIE est ré-suspendu au 1er accès.

On prend le compte de test « essai-expire-paye » (statut actif après paiement, mais essai_expire_at
resté au passé), on ouvre une VRAIE session, et on appelle session_utilisateur (le point de contrôle
d'accès de chaque requête). Lecture du résultat + du statut APRÈS.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "src"))

import sqlalchemy as sa
from labuse.db import session_scope
from labuse.comptes import creer_session, session_utilisateur

ENV = {}
for line in (ROOT / ".env").read_text().splitlines():
    k, _, v = line.partition("=")
    if k.startswith("LABUSE_"):
        ENV[k.strip()] = v.strip()
ENGINE = sa.create_engine(ENV["LABUSE_DATABASE_URL"])

out = {}
with ENGINE.begin() as c:
    row = c.execute(sa.text(
        "SELECT k.id AS cid, u.id AS uid, k.statut, k.essai_expire_at"
        " FROM comptes k JOIN utilisateurs u ON u.compte_id=k.id"
        " WHERE k.nom LIKE '%essai-expire-paye%' ORDER BY k.id DESC LIMIT 1")).mappings().first()
out["compte_choisi"] = {"compte_id": row["cid"], "statut_avant": row["statut"],
                        "essai_expire_at": row["essai_expire_at"].isoformat()}

with session_scope() as db:
    tok = creer_session(db, row["uid"])
with session_scope() as db:
    res = session_utilisateur(db, tok)     # le contrôle d'accès de CHAQUE requête
out["session_utilisateur_retour"] = res    # None attendu = accès refusé

with ENGINE.begin() as c:
    statut_apres = c.execute(sa.text("SELECT statut FROM comptes WHERE id=:c"),
                             {"c": row["cid"]}).scalar()
out["statut_apres_1er_acces"] = statut_apres

out["verdict"] = ("BUG CONFIRMÉ : compte PAYÉ (actif) → session_utilisateur renvoie "
                  f"{res!r} et le statut retombe à {statut_apres!r} dès le 1er accès."
                  if res is None and statut_apres == "suspendu"
                  else "comportement inattendu — revoir")
print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
