# OUTILS-LOT-4 bis — trois dernières retouches (vues sur les captures du lot 4)

Même branche `fix/outils-lot-4`. `git merge origin/main` d'abord (le helper `adresseInsecable` du lot 2 y
est — mais il ne vise que la commune APRÈS un code postal à 5 chiffres, cf. ci-dessous). Pas de merge
produit→prod. Hook vert.

| # | Point | État | Captures |
|---|-------|------|----------|
| 1 | Accueil : exemple Copilote coupé « Saint- / Paul » → trait d'union insécable | **Fait** | `lot4bis-01-accueil-copilote-{AVANT,APRES}` |
| 2 | Pièges 100 % rouge : « parcelle entièrement INCONSTRUCTIBLE » + étiquette « Inconstructible » (sans « (partie rouge) ») | **Fait** | `lot4bis-02-03-pieges-rouge100-{AVANT,APRES}` |
| 3 | Pièges : « L562-1 » coupé « L562- / 1 » → insécable | **Fait** | idem |

---

### 1 — Accueil : « Saint‑Paul » insécable
L'exemple du Copilote « *« terrain 1 000 m² à Saint-Paul »* » se coupait en fin de ligne entre « Saint- »
et « Paul » (visible sur `lot4-08-accueil-APRES`). `adresseInsecable` (lot 2) ne s'applique qu'à la commune
qui SUIT un code postal à 5 chiffres — l'exemple n'en a pas. On met donc le **trait d'union insécable
U+2011** directement dans « Saint‑Paul » (`LeftPanel.tsx`, commenté). AVANT = « à Saint- / Paul » ; APRÈS =
« à / Saint‑Paul » (le nom reste d'un seul tenant).

### 2 — Pièges, parcelle 100 % rouge : « entièrement » + étiquette nette
`servitudes.py _ppr_ligne` : quand `pct ≥ 100`, le texte dit « **parcelle entièrement INCONSTRUCTIBLE** »
au lieu de « partie INCONSTRUCTIBLE » (il n'y a pas de partie constructible). En dessous de 100 %,
inchangé (« partie INCONSTRUCTIBLE » + « Partie hors zone rouge (N %) »). L'**étiquette** (`blocB.tsx`)
passe de « Inconstructible (partie rouge) » à « **Inconstructible** » quand l'effet porte « entièrement
INCONSTRUCTIBLE » (signal servi par le back) ; sous 100 %, elle garde « (partie rouge) ». Témoin
97401000AC0003 (100 % rouge). Verrous : `_ppr_ligne(…, 100)` (back) + deux tests de badge 100 %/40 % (front).

### 3 — Pièges : « L562‑1 » insécable
`servitudes.py _ppr_ligne` : le numéro d'article « C. env. L562-1 » se coupait « L562- / 1 ». **Trait
d'union insécable U+2011** → « L562‑1 » ne se coupe plus. Verrou : `assert "L562‑1" in … and "L562-1" not
in …`.

---

## Tests (au premier plan)
`npx tsc -b` 0 · `npx vitest run` **340** · `pytest -m "not db and not local and not reel and not network"`
**3317 passed, 49 skipped** · `scripts/ci/coherence_run.sh` **7 passed** · `scan_secrets.sh` rien trouvé.

Fichiers : `servitudes.py` (2, 3), `blocB.tsx` (2), `LeftPanel.tsx` (1) ; tests : `test_servitudes.py`,
`blocB.O5.test.tsx`. Captures avant/après via `git stash` des 3 sources (HMR + `--reload`).
