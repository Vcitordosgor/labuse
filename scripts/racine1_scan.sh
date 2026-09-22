#!/usr/bin/env bash
# RACINE-1 read-only scan. Writes reports/racine-1/*.txt
set -u
R=/Users/openclaw/Desktop/labuse-racine
cd "$R" || exit 1
OUT=reports/racine-1
mkdir -p "$OUT"

# 1) root files (regular files only, incl. dotfiles)
: > "$OUT/_rootfiles.txt"
for e in * .[!.]*; do
  [ -f "$e" ] && echo "$e" >> "$OUT/_rootfiles.txt"
done
sort -u "$OUT/_rootfiles.txt" -o "$OUT/_rootfiles.txt"

# search haystack: everything EXCEPT root-level *.md/*.html themselves and .git
# We grep code + config + tests + scripts + deploy + frontend + qa + ci + docs
: > "$OUT/refs.txt"
while IFS= read -r f; do
  # exact fixed-string search across dirs known to contain executable/config material
  hits=$(grep -rIn -F "$f" \
      src tests config scripts deploy frontend/src qa .github \
      deploy.sh pyproject.toml Dockerfile docker-compose.yml docker-compose.pilot.yml docker-compose.caddy.yml \
      requirements.txt requirements-ml.txt .dockerignore .gitignore .env.example .env.pilot.example \
      2>/dev/null | grep -v 'Binary file')
  if [ -n "$hits" ]; then
    {
      echo "=== $f ==="
      echo "$hits"
      echo ""
    } >> "$OUT/refs.txt"
  fi
done < "$OUT/_rootfiles.txt"

echo "ROOT FILES: $(wc -l < "$OUT/_rootfiles.txt")"
echo "FILES WITH >=1 CODE/CONFIG REF:"
grep -c '^=== ' "$OUT/refs.txt"
echo "--- ref headers ---"
grep '^=== ' "$OUT/refs.txt"
