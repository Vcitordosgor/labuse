"""Synchronisation des dispositions et des détails cadastraux d’une publication géo-DVF."""
from datetime import date
import re

from sqlalchemy import text
from sqlalchemy.orm import Session

from . import dvf_detail
from .dvf_etalab import Ressource

COLONNES = ('id_mutation', 'date_mutation', 'nature_mutation', 'valeur_fonciere', 'code_commune',
            'id_parcelle', 'type_local', 'surface_reelle_bati', 'surface_terrain', 'nature_culture',
            'longitude', 'latitude', 'millesime')
NUMERIQUES = ('valeur_fonciere', 'surface_reelle_bati', 'surface_terrain', 'longitude', 'latitude')
DETAILS = ('adresse', 'code_postal', 'nombre_pieces', 'surface_carrez_m2', 'nombre_lots',
           'ancien_id_parcelle', 'source_millesime')


def _dispositions(ressource: Ressource, lignes: list[dict]) -> list[dict]:
    debut, fin = ressource.bornes
    dispositions = []
    for source in lignes:
        jour = date.fromisoformat(source['date_mutation'])
        if not debut <= jour <= fin or source['code_departement'] != '974' or not source['id_mutation']:
            raise ValueError(f'Disposition DVF hors période ou territoire pour {ressource.token}')
        idu = source.get('id_parcelle')
        if not idu:
            continue  # Les actes sans référence cadastrale restent éligibles à l’agrégat des mutations.
        if not re.fullmatch(r'974[0-9A-Z]{11}', idu) or source.get('code_commune') != idu[:5]:
            raise ValueError(f'Référence cadastrale DVF incohérente pour {ressource.token}')
        row = {key: source.get(key) or None for key in COLONNES}
        row.update(date_mutation=jour, millesime=jour.year)
        for key in NUMERIQUES:
            if row[key] is not None:
                row[key] = float(row[key].replace(',', '.'))
        dispositions.append(row)
    if not dispositions:
        raise ValueError(f'{ressource.token} ne contient aucune disposition cadastrale réunionnaise')
    return dispositions


def actualiser(session: Session, ressource: Ressource, lignes: list[dict]) -> dict:
    """Remplace les actes modifiés de la période. Le niveau supérieur possède la transaction."""
    dispositions = _dispositions(ressource, lignes)
    debut, fin = ressource.bornes
    bornes = {'debut': debut, 'fin': fin}
    cols = ', '.join(COLONNES)
    valeurs = ', '.join(':' + col for col in COLONNES)
    session.execute(text(f'''CREATE TEMP TABLE dvf_nouvelles_dispositions ON COMMIT DROP AS
        SELECT {cols} FROM dvf_mutations_parcelle WITH NO DATA'''))
    session.execute(text(f'INSERT INTO pg_temp.dvf_nouvelles_dispositions ({cols}) VALUES ({valeurs})'), dispositions)
    # EXCEPT ALL préserve la multiplicité des subdivisions fiscales et des lignes de lots identiques.
    # Les identifiants locaux restent stables sur les actes dont la publication ne modifie aucune ligne.
    session.execute(text(f'''CREATE TEMP TABLE dvf_actes_modifies ON COMMIT DROP AS
        WITH anciens AS (SELECT {cols} FROM dvf_mutations_parcelle WHERE date_mutation BETWEEN :debut AND :fin),
             nouveaux AS (SELECT {cols} FROM pg_temp.dvf_nouvelles_dispositions)
        SELECT DISTINCT id_mutation FROM (
          (SELECT * FROM anciens EXCEPT ALL SELECT * FROM nouveaux)
          UNION ALL (SELECT * FROM nouveaux EXCEPT ALL SELECT * FROM anciens)
        ) delta'''), bornes)
    collision = session.execute(text('''SELECT EXISTS (SELECT FROM dvf_mutations_parcelle d
        JOIN pg_temp.dvf_nouvelles_dispositions n USING (id_mutation)
        WHERE d.date_mutation NOT BETWEEN :debut AND :fin)'''), bornes).scalar_one()
    if collision:
        raise ValueError(f'Une mutation de {ressource.token} figure aussi hors de sa période')

    dvf_detail.ensure_table(session)
    idus = set(session.execute(text('''SELECT DISTINCT p.idu FROM parcels p
        JOIN pg_temp.dvf_nouvelles_dispositions n ON p.idu=n.id_parcelle''')).scalars())
    agg = {}
    dvf_detail.ajouter_details(agg, lignes, idus, ressource.token.lower())
    session.execute(text('''CREATE TEMP TABLE dvf_nouveaux_details (LIKE dvf_mutation_detail INCLUDING DEFAULTS)
        ON COMMIT DROP'''))
    dvf_detail.ecrire_details(session, agg, temporaire=True)
    session.execute(text('''DELETE FROM dvf_mutation_detail d WHERE
        (EXISTS (SELECT FROM pg_temp.dvf_actes_modifies a WHERE a.id_mutation=d.id_mutation)
         OR EXISTS (SELECT FROM pg_temp.dvf_nouvelles_dispositions n WHERE n.id_mutation=d.id_mutation))
        AND NOT EXISTS (SELECT FROM pg_temp.dvf_nouveaux_details n
                        WHERE (n.id_mutation,n.id_parcelle)=(d.id_mutation,d.id_parcelle))'''))
    detail_cols = ', '.join(DETAILS)
    nouveau = ', '.join('excluded.' + nom for nom in DETAILS)
    ancien = ', '.join('d.' + nom for nom in DETAILS)
    session.execute(text(f'''INSERT INTO dvf_mutation_detail AS d(id_mutation,id_parcelle,{detail_cols})
        SELECT id_mutation,id_parcelle,{detail_cols} FROM pg_temp.dvf_nouveaux_details
        ON CONFLICT(id_mutation,id_parcelle) DO UPDATE SET ({detail_cols})=({nouveau}), ingere_le=now()
        WHERE ({ancien}) IS DISTINCT FROM ({nouveau})'''))
    session.execute(text('''DELETE FROM dvf_mutations_parcelle d USING pg_temp.dvf_actes_modifies a
        WHERE d.id_mutation=a.id_mutation AND d.date_mutation BETWEEN :debut AND :fin'''), bornes)
    session.execute(text(f'''INSERT INTO dvf_mutations_parcelle ({cols}) SELECT {cols}
        FROM pg_temp.dvf_nouvelles_dispositions JOIN pg_temp.dvf_actes_modifies USING(id_mutation)'''))
    session.execute(text('DROP TABLE pg_temp.dvf_nouvelles_dispositions, pg_temp.dvf_nouveaux_details, pg_temp.dvf_actes_modifies'))
    return {'dispositions': len(dispositions), 'couples_detail': len(agg)}
