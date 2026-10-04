#!/usr/bin/env python3
"""PROPRETE-1 — Étape 0 : inventaire du dépôt (lecture seule, rejouable).

Compte lignes par langage sur les fichiers SUIVIS par git (hors node_modules),
liste les 20 plus gros fichiers du working tree et les 20 plus gros blobs de
l'historique packé. Sortie texte sur stdout (tee vers raw/inventory.txt).
"""
from __future__ import annotations
import subprocess
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXCLUDE = ("node_modules/",)
# extensions textuelles qu'on compte en lignes
CODE_EXT = {
    "py": "Python", "tsx": "TypeScript/React", "ts": "TypeScript",
    "mjs": "JS (config)", "js": "JS", "sql": "SQL", "sh": "Shell",
    "yaml": "YAML", "yml": "YAML", "json": "JSON", "md": "Markdown",
    "html": "HTML", "css": "CSS", "txt": "Texte",
}


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True)


def tracked() -> list[str]:
    files = git("ls-files").splitlines()
    return [f for f in files if not any(e in f for e in EXCLUDE)]


def main() -> None:
    files = tracked()
    print(f"# Inventaire PROPRETE-1  —  {len(files)} fichiers suivis (hors node_modules)\n")

    lines_by_lang: dict[str, int] = defaultdict(int)
    files_by_lang: dict[str, int] = defaultdict(int)
    for f in files:
        ext = f.rsplit(".", 1)[-1].lower() if "." in f else ""
        lang = CODE_EXT.get(ext)
        if not lang:
            continue
        p = ROOT / f
        try:
            n = sum(1 for _ in p.open("rb"))
        except OSError:
            continue
        lines_by_lang[lang] += n
        files_by_lang[lang] += 1

    print("## Lignes par langage (fichiers texte suivis)")
    print(f"{'langage':24} {'fichiers':>9} {'lignes':>12}")
    for lang, n in sorted(lines_by_lang.items(), key=lambda kv: -kv[1]):
        print(f"{lang:24} {files_by_lang[lang]:>9} {n:>12}")
    print(f"{'TOTAL':24} {sum(files_by_lang.values()):>9} {sum(lines_by_lang.values()):>12}\n")

    print("## 20 plus gros fichiers du working tree (octets)")
    sized = []
    for f in files:
        p = ROOT / f
        try:
            sized.append((p.stat().st_size, f))
        except OSError:
            pass
    for sz, f in sorted(sized, reverse=True)[:20]:
        print(f"{sz:>12}  {f}")


if __name__ == "__main__":
    main()
