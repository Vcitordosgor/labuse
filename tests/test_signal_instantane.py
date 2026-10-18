"""FIX-PRIX-ET-OPPORTUNITES lot 4 — instantané mensuel du Signal servi (protocole forward volet E).

Tests SANS base : le registre (job déclaré, mensuel, exploitation, pas de mail), le schéma (sa table),
l'écriture CONFINÉE à sa table, et l'estimateur de Wilson. Le figer/rejouer réels touchent la base →
gestes prod (non joués ici), couverts par la garde « n'écrit que sa table » au niveau du source.
"""
from __future__ import annotations

from pathlib import Path

from labuse import signal_instantane as si

RACINE = Path(__file__).resolve().parents[1]


def test_job_signal_instantane_dans_le_registre():
    from labuse.jobs import JOBS
    assert "signal-instantane" in JOBS
    j = JOBS["signal-instantane"]
    assert j.touche == "exploitation"
    assert j.cadence.startswith("mensuel")
    assert j.cron_utc == "0 2 1 * *"          # 06:00 Réunion, le 1er
    assert j.besoin_db is True
    assert j.envoie_mail is False             # « pas de mail »
    assert j.planifie is True                 # au crontab généré


def test_impl_du_job_existe():
    # le runner résout jobs_impl.signal_instantane (nom avec tirets → underscores)
    from labuse import jobs_impl
    assert hasattr(jobs_impl, "signal_instantane")


def test_schema_sa_table():
    assert "CREATE TABLE IF NOT EXISTS signal_instantanes" in si.DDL
    for col in ("snapshot_le", "run_label", "parcel_id", "signal_p", "signal_niveau", "bande"):
        assert col in si.DDL, col
    assert "PRIMARY KEY (snapshot_le, parcel_id)" in si.DDL     # idempotence par date×parcelle


def test_figer_n_ecrit_que_sa_table():
    # garde anti-débordement : aucune écriture hors de signal_instantanes dans le module.
    src = (RACINE / "src/labuse/signal_instantane.py").read_text()
    import re
    ecritures = re.findall(r"\b(INSERT INTO|UPDATE|DELETE FROM)\s+(\w+)", src)
    cibles = {t for _, t in ecritures}
    assert cibles == {"signal_instantanes"}, f"écrit hors de sa table : {cibles}"
    # idempotence explicite
    assert "ON CONFLICT (snapshot_le, parcel_id) DO NOTHING" in src
    # aucun ENVOI de mail (la docstring peut dire « aucun mail » ; ici on interdit un vrai expéditeur)
    bas = src.lower()
    for sender in ("smtp", "send_mail", "envoyer_mail", "brevo", "sendmail"):
        assert sender not in bas, f"expéditeur de mail interdit : {sender}"


def test_wilson_estimateur():
    p, bas, haut = si.wilson(39, 100)
    assert abs(p - 0.39) < 1e-9
    assert bas < p < haut and 0 <= bas and haut <= 1
    # n=0 → nan, jamais une division par zéro
    assert si.wilson(0, 0)[0] != si.wilson(0, 0)[0]            # nan


def test_rejouer_est_lecture_seule():
    # le juge forward ne doit JAMAIS écrire : son code ne contient aucune écriture SQL ni commit.
    src = (RACINE / "src/labuse/signal_instantane.py").read_text()
    corps_rejouer = src.split("def rejouer(")[1].split("\ndef ")[0]
    for mot in ("INSERT", "UPDATE", "DELETE", "commit("):
        assert mot not in corps_rejouer, f"rejouer() ne doit pas écrire ({mot})"
