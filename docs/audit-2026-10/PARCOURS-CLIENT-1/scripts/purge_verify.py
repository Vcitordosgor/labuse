"""SECTION D / step 13 — PURGE RGPD des comptes [CT-PARCOURS] + PREUVE 0 ligne orpheline.
Liste les comptes de test, note leurs id, appelle effacer_compte_rgpd, puis vérifie que CHAQUE
table portant une colonne compte_id n'a plus aucune ligne pour ces id (ni mail_queue par destinataire)."""
import os, sys
os.environ.setdefault('LABUSE_DATABASE_URL', 'postgresql+psycopg://openclaw@localhost:5432/labuse')
sys.path.insert(0, 'src')
from sqlalchemy import text
from labuse.db import session_scope
from labuse import comptes

with session_scope() as db:
    rows = db.execute(text("select c.id, u.email from comptes c join utilisateurs u on u.compte_id=c.id "
                           "where u.email like 'ct-parcours%' or c.nom like '%[CT-PARCOURS]%'")).mappings().all()
    ids = sorted({r['id'] for r in rows})
    emails = sorted({r['email'] for r in rows})
    print('comptes [CT-PARCOURS] AVANT purge :', ids, emails)

    # purge RGPD par e-mail
    for e in emails:
        print('  effacer_compte_rgpd(%s) ->' % e, comptes.effacer_compte_rgpd(db, e))

with session_scope() as db:
    # toutes les tables avec une colonne compte_id
    tabs = [r[0] for r in db.execute(text(
        "select table_name from information_schema.columns "
        "where column_name='compte_id' and table_schema='public' order by table_name")).all()]
    print('\\n%d tables portent compte_id. Lignes restantes pour %s :' % (len(tabs), ids))
    total = 0
    for t in tabs:
        n = db.execute(text('select count(*) from "%s" where compte_id = any(:ids)' % t), {'ids': ids}).scalar()
        if n:
            total += n; print('  !! %-28s %d' % (t, n))
    # aussi mail_queue par destinataire + utilisateurs/comptes
    nmq = db.execute(text("select count(*) from mail_queue where destinataire like 'ct-parcours%'")).scalar()
    nu = db.execute(text("select count(*) from utilisateurs where email like 'ct-parcours%'")).scalar()
    nc = db.execute(text("select count(*) from comptes where id = any(:ids)"), {'ids': ids}).scalar()
    print('  mail_queue par destinataire ct-parcours%% :', nmq)
    print('  utilisateurs ct-parcours%% :', nu)
    print('  comptes restants :', nc)
    print('\\nRESULTAT :', 'PURGE PROPRE — 0 ligne orpheline' if (total == 0 and nmq == 0 and nu == 0 and nc == 0)
          else 'RESTE DES LIGNES (voir ci-dessus)')
