"""1.A — propriétaires personnes morales DGFiP : classifieur + loader (parse), cœur PUR."""
from __future__ import annotations

from pathlib import Path

from labuse.ingestion import personnes_morales as pm
from labuse.proprietaire_type import classify_dgfip

# ── Classifieur DGFiP (groupe + forme + dénomination → owner_type) ──

def test_groupes_publics():
    assert classify_dgfip(1, "", "ÉTAT")["owner_type"] == "etat"
    assert classify_dgfip(4, "COM", "COMMUNE DE SAINT-PAUL")["owner_type"] == "commune"
    assert classify_dgfip(2, "", "REGION REUNION")["owner_type"] == "collectivite"
    assert classify_dgfip(5, "SA", "SHLMR")["owner_type"] == "bailleur_social"
    assert classify_dgfip(6, "SEM", "SEMADER")["owner_type"] == "sem"
    o9 = classify_dgfip(9, "", "EPF REUNION")
    assert o9["owner_type"] == "epf"            # raffinage dénomination « EPF »
    assert classify_dgfip(9, "", "CHU")["owner_type"] == "etablissement_public"


def test_groupe0_raffine_par_forme():
    assert classify_dgfip(0, "SCI", "SCI TACQUET")["owner_type"] == "sci"
    assert classify_dgfip(0, "SARL", "TACQUET BTP")["owner_type"] == "societe"
    assert classify_dgfip(0, "ASL", "ASL LES HAUTS")["owner_type"] == "copropriete"


def test_owner_name_et_famille():
    o = classify_dgfip(0, "SCI", "SCI JACOB")
    assert o["owner_name"] == "SCI JACOB" and o["famille"] == "prive" and o["identifiable"] is True
    assert classify_dgfip(4, "COM", "COMMUNE")["famille"] == "public"


# ── Loader : construction d'IDU + parsing CSV ──

def test_build_idu():
    assert pm._build_idu("97415", "", "EL", "0394") == "97415000EL0394"
    assert pm._build_idu("97415", "", "A", "12") == "974150000A0012"   # section/numéro padés
    assert pm._build_idu("97415", "", "", "0394") is None              # section manquante


def test_rows_from_csv_filtre_commune(tmp_path: Path):
    # Mini-CSV DGFiP (entête 24 cols + 2 communes) — on ne garde que 415 (Saint-Paul).
    head = ";".join(["Dep", "Dir", "Code Commune", "Nom", "Prefixe", "Section", "Nplan",
                     "voirie", "ind", "vmajic", "rivoli", "natvoie", "nomvoie", "cont", "suf",
                     "natcult", "contsuf", "droit", "majic", "siren", "Groupe", "FJ", "FJabr", "Denom"])
    def row(commune, section, nplan, groupe, fjabr, denom):
        c = [""] * 24
        c[2], c[5], c[6], c[20], c[22], c[23] = commune, section, nplan, groupe, fjabr, denom
        return ";".join(c)
    csv = tmp_path / "974.csv"
    csv.write_text("\n".join([head,
        row("415", "EL", "0394", "0 - Personnes morales non remarquables", "SCI", "SCI JACOB"),
        row("415", "EL", "0394", "0", "SCI", "SCI JACOB"),     # doublon SUF → dédoublonné
        row("401", "AB", "0001", "4 - Commune", "COM", "COMMUNE DES AVIRONS"),  # autre commune
    ]), encoding="utf-8")
    rows = list(pm._rows_from_csv(csv, "415"))
    assert len(rows) == 1                                   # 1 parcelle (doublon écarté, 401 exclu)
    r = rows[0]
    assert r["idu"] == "97415000EL0394" and r["groupe"] == 0
    assert r["forme"] == "SCI" and r["denomination"] == "SCI JACOB"
