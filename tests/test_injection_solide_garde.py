"""INJECTION-SOLIDE-2 — la GARDE : aucune ingestion ne remplace une table SERVIE « à vif ».

Mandat : « un test refuse toute nouvelle ingestion qui écrirait directement dans une table servie ».
Pas besoin de base : on analyse le SOURCE des modules d'ingestion (SQL littéraux de `text(...)`).
"""
from __future__ import annotations

from pathlib import Path

from labuse.ingestion import garde_injection as g

ING = Path(__file__).resolve().parents[1] / "src" / "labuse" / "ingestion"


def test_aucune_ingestion_ne_remplace_une_table_servie_a_vif():
    """LE GARDE. Tout `TRUNCATE`/`DELETE`-sans-`WHERE` sur une table servie doit être CONVERTI
    (passe par injection_sure → disparaît du scan) ou DÉCLARÉ (dette/exclu, avec raison). Un motif
    non déclaré = une ingestion qui écrit directement dans la servie → ÉCHEC."""
    viols = g.violations(ING)
    assert not viols, (
        "Remplacement-en-place d'une table SERVIE non routé par injection_sure et non déclaré :\n  "
        + "\n  ".join(f"{v.module}:{v.ligne} {v.operation} {v.table}" for v in viols)
        + "\n→ route-le par `injection_sure.remplacer_servie`, ou déclare-le dans "
          "garde_injection.DETTE/EXCLUS avec une raison.")


def test_les_modules_convertis_sont_propres():
    """Cliquet : un module converti ne doit JAMAIS ré-introduire un TRUNCATE/DELETE-à-vif sur une
    table qu'il a sécurisée (régression). SOLIDE-3 : tous les modules (8 de SOLIDE-2 + 18 de SOLIDE-3)."""
    sites = g.scanner(ING)
    for module, tables in g.MODULES_CONVERTIS.items():
        for table in tables:
            assert not any(s.module == module and s.table == table for s in sites), (
                f"{module} a ré-introduit un remplacement-en-place de {table} (régression)")


def test_la_dette_est_vide_garde_strict():
    """INJECTION-SOLIDE-3 — le garde est STRICT : plus AUCUNE tolérance (DETTE vide). Les 18
    `DELETE`-sans-`WHERE` de SOLIDE-2 sont convertis ; seule reste EXCLUS (tables NON servies)."""
    assert g.DETTE == {}, (
        "DETTE doit rester VIDE (garde strict) — une ingestion non sûre ne se DÉCLARE plus, elle se "
        "convertit à injection_sure.remplacer_servie ou échoue au garde.")
    assert set(g.EXCLUS) == {("demo_saint_paul.py", "*"),
                             ("division_or.py", "division_or_revue_snapshot")}


def test_source_sur_chemin_sur_et_sources_sures():
    """INJECTION-SOLIDE-3 — injection-nuit ne lance QUE les sources SÛRES. Les sources routées par
    `injection_sure` sont dans `SOURCES_SURES` (donc `source_sur_chemin_sur` = True) ; une source
    inconnue / non vettée est False → injection-nuit la tiendrait comme « décision à prendre »."""
    for nom in ("Trafic RN (Région Réunion — SIR)", "Base Adresse Nationale",
                "SIRENE établissements géolocalisés", "CatNat (arrêtés GASPAR / Géorisques)"):
        assert g.source_sur_chemin_sur(nom), f"{nom} devrait être sûre (routée par injection_sure)"
    assert not g.source_sur_chemin_sur("Une source neuve jamais vettée")
    # toutes les entrées sont des chaînes non vides (noms data_sources.name)
    assert all(isinstance(n, str) and n for n in g.SOURCES_SURES)


def test_un_nouvel_offenseur_est_pris_truncate():
    """Test POSITIF : une ingestion NEUVE qui ferait `TRUNCATE servie` est détectée (sinon le garde
    ne garderait rien)."""
    src = '''
from sqlalchemy import text
def ingest(session):
    session.execute(text("TRUNCATE parcels"))
    session.execute(text("INSERT INTO parcels SELECT * FROM amont"))
'''
    sites = g.scanner_texte("nouvelle_source.py", src)
    assert any(s.operation == "TRUNCATE" and s.table == "parcels" for s in sites)
    # … et il n'est PAS déclaré → ce serait une violation.
    assert all(not g._declare(s) for s in sites if s.table == "parcels")


def test_un_nouvel_offenseur_est_pris_delete_sans_where():
    """Test POSITIF : `DELETE FROM servie` sans WHERE est détecté ; AVEC un WHERE, non (remplacement
    partiel légitime — ex. par millésime/kind)."""
    offenseur = g.scanner_texte(
        "x.py", 'from sqlalchemy import text\ntext("DELETE FROM dvf_mutations_parcelle")')
    assert any(s.operation == "DELETE-sans-WHERE" and s.table == "dvf_mutations_parcelle"
               for s in offenseur)
    partiel = g.scanner_texte(
        "x.py", 'from sqlalchemy import text\ntext("DELETE FROM spatial_layers WHERE kind = :k")')
    assert partiel == [], "un DELETE AVEC WHERE (remplacement partiel) ne doit PAS être signalé"


def test_les_tables_de_travail_ne_sont_pas_des_violations():
    """Les tables de TRAVAIL (staging, tmp, placeholder f-string) sont ignorées."""
    src = ('from sqlalchemy import text\n'
           'text("TRUNCATE tmp_ocsge_x")\n'
           'text(f\'TRUNCATE "{staging}"\')\n'
           'text("DELETE FROM parcels__inj_staging")\n')
    assert g.scanner_texte("x.py", src) == []


def test_le_registre_ne_pourrit_pas():
    """Hygiène : chaque entrée DETTE/EXCLUS (hors joker `*`) correspond à un motif RÉELLEMENT présent
    au scan — sinon elle est obsolète (le site a été converti/supprimé) et doit être retirée."""
    sites = {(s.module, s.table) for s in g.scanner(ING)}
    for (module, table) in list(g.DETTE) + list(g.EXCLUS):
        if table == "*":
            continue
        assert (module, table) in sites, (
            f"entrée de registre obsolète : {module}:{table} n'apparaît plus au scan "
            "(convertie/supprimée ?) — retire-la de DETTE/EXCLUS")
