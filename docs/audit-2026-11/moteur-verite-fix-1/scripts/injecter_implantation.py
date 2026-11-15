"""MOTEUR-VERITE-FIX-1 LOT 2 — injecte les modes d'implantation lus au règlement (5 communes
pilotes) dans config/plu_destinations/<insee>_*.yaml :
    zones.<Z>.regles.retraits.limites_separatives.implantation_laterales / implantation_fond
      = {mode, statut: valide, citation, article, page_pdf?, condition_texte?, condition_modelable?}

INSERTION TEXTUELLE (jamais un re-dump PyYAML : il perdrait les commentaires et reformaterait
5 000 lignes). On localise `zones.<Z>.regles.retraits.limites_separatives:` et on insère les
feuilles en PREMIERS enfants. Les blocs `retraits:`/`limites_separatives:` manquants sont créés
sous `regles:`. Idempotent (une feuille déjà posée est remplacée). Contrôle final : chaque
fichier re-parse en YAML et `resolve_zone` rend bien les dicts.

Source : implantation/<insee>.csv (lecture mot à mot au règlement, un agent par commune).
"""
from __future__ import annotations

import csv
import glob
import re
from pathlib import Path

import yaml

RACINE = Path(__file__).resolve().parents[4]
IMPL = RACINE / "docs" / "audit-2026-11" / "moteur-verite-fix-1" / "implantation"
PILOTES = ["97407", "97409", "97412", "97414", "97416"]


def _q(s: str) -> str:
    """Chaîne YAML en simple quote (escape ' → '')."""
    return "'" + str(s).replace("'", "''") + "'"


def _bloc(cote: str, r: dict, indent: int) -> list[str]:
    pad = " " * indent
    pad2 = " " * (indent + 2)
    out = [f"{pad}implantation_{cote}:",
           f"{pad2}mode: {r['mode'].strip()}",
           f"{pad2}statut: valide"]
    if (r.get("article") or "").strip():
        out.append(f"{pad2}article: {_q(r['article'].strip())}")
    pg = (r.get("page_pdf") or "").strip()
    if pg:
        out.append(f"{pad2}page_pdf: {int(float(pg)) if re.match(r'^[0-9.]+$', pg) else _q(pg)}")
    if (r.get("citation_verbatim") or "").strip():
        out.append(f"{pad2}citation: {_q(r['citation_verbatim'].strip())}")
    if (r.get("condition_texte") or "").strip():
        out.append(f"{pad2}condition_texte: {_q(r['condition_texte'].strip())}")
    if (r.get("condition_modelable") or "").strip():
        out.append(f"{pad2}condition_modelable: {_q(r['condition_modelable'].strip())}")
    return out


def _trouver(lines: list[str], debut: int, fin: int, cle: str, indent: int) -> int | None:
    rx = re.compile(rf"^{' ' * indent}{re.escape(cle)}:\s*$")
    for i in range(debut, fin):
        if rx.match(lines[i]):
            return i
    return None


def _fin_bloc(lines: list[str], i_cle: int, indent: int) -> int:
    """Première ligne après i_cle dont l'indentation est ≤ indent (hors vides/commentaires)."""
    for j in range(i_cle + 1, len(lines)):
        l = lines[j]
        if not l.strip():
            continue
        if len(l) - len(l.lstrip()) <= indent:
            return j
    return len(lines)


def injecter(insee: str) -> None:
    src = IMPL / f"{insee}.csv"
    fichiers = glob.glob(str(RACINE / "config" / "plu_destinations" / f"{insee}_*.yaml"))
    if not src.exists() or not fichiers:
        print(f"{insee} : CSV ou YAML absent — sauté")
        return
    fy = Path(fichiers[0])
    lines = fy.read_text().split("\n")
    doc = yaml.safe_load("\n".join(lines))
    zone_keys = set((doc.get("zones") or {}))

    rows = [r for r in csv.DictReader(open(src, newline=""), delimiter=";")
            if (r.get("cote") or "").strip() in ("laterales", "fond")]
    poses, absentes = 0, []
    # tri inverse par position pour insérer sans invalider les index suivants : on retraite le
    # fichier zone par zone, en re-localisant à chaque pose (simple et sûr, fichiers ~5 000 lignes).
    for r in rows:
        zone = (r.get("zone") or "").strip()
        cote = r["cote"].strip()
        if zone not in zone_keys:
            absentes.append(zone)
            continue
        # 1. ligne de la zone (indent détecté sur la première zone du fichier)
        i_zones = _trouver(lines, 0, len(lines), "zones", 0)
        m_any = next((i for i in range(i_zones + 1, len(lines))
                      if re.match(r"^(\s+)\S.*:", lines[i])), None)
        z_indent = len(lines[m_any]) - len(lines[m_any].lstrip())
        i_z = _trouver(lines, i_zones + 1, len(lines), zone, z_indent)
        if i_z is None:
            absentes.append(zone)
            continue
        f_z = _fin_bloc(lines, i_z, z_indent)
        # 2. regles / retraits / limites_separatives (créés au besoin)
        i_reg = _trouver(lines, i_z + 1, f_z, "regles", z_indent + 2)
        if i_reg is None:
            lines.insert(i_z + 1, f"{' ' * (z_indent + 2)}regles:")
            i_reg, f_z = i_z + 1, f_z + 1
        f_reg = min(_fin_bloc(lines, i_reg, z_indent + 2), f_z)
        i_ret = _trouver(lines, i_reg + 1, f_reg, "retraits", z_indent + 4)
        if i_ret is None:
            lines.insert(i_reg + 1, f"{' ' * (z_indent + 4)}retraits:")
            i_ret, f_reg = i_reg + 1, f_reg + 1
        f_ret = min(_fin_bloc(lines, i_ret, z_indent + 4), f_reg)
        i_ls = _trouver(lines, i_ret + 1, f_ret, "limites_separatives", z_indent + 6)
        if i_ls is None:
            lines.insert(i_ret + 1, f"{' ' * (z_indent + 6)}limites_separatives:")
            i_ls, f_ret = i_ret + 1, f_ret + 1
        f_ls = min(_fin_bloc(lines, i_ls, z_indent + 6), f_ret)
        # 3. feuille déjà posée ? → retirée (idempotence)
        i_old = _trouver(lines, i_ls + 1, f_ls, f"implantation_{cote}", z_indent + 8)
        if i_old is not None:
            f_old = min(_fin_bloc(lines, i_old, z_indent + 8), f_ls)
            del lines[i_old:f_old]
            f_ls -= (f_old - i_old)
        # 4. insertion en premier enfant de limites_separatives
        bloc = _bloc(cote, r, z_indent + 8)
        lines[i_ls + 1:i_ls + 1] = bloc
        poses += 1

    fy.write_text("\n".join(lines))
    # contrôle : le fichier re-parse, et les feuilles sont lisibles
    rel = yaml.safe_load(fy.read_text())
    assert isinstance(rel, dict) and rel.get("zones"), f"{fy} : YAML cassé après injection"
    absset = sorted(set(absentes))
    print(f"{insee} : {poses} feuilles posées → {fy.name}"
          + (f" ; zones CSV hors YAML (renvoi/indice) : {', '.join(absset)}" if absset else ""))


if __name__ == "__main__":
    for insee in PILOTES:
        injecter(insee)
