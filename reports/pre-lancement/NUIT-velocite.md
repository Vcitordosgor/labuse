# NUIT — Vélocité admin (point 39) · `feat/nuit-velocite`

**NON mergée.** Back + front. Zéro touche scoring. Données réelles m10_permit_delais.

## Lot 0
M05 montrait le délai médian d'instruction par commune (tri par volume/médiane), sans classement
explicite ni tendance.

## Fait
- **Backend** (`/modules/velocite`) : ajoute **`rang_delai`** (1 = commune la plus rapide, par délai
  médian croissant) et **`tendance`** (médiane cohortes anciennes vs récentes, coupe au milieu de la
  période ; `accelere`/`ralentit`/`stable`, None si < 8 dossiers par moitié). Logique de maturité et
  censure Sitadel inchangées.
- **Frontend** (M05) : **badge de rang `#n`** + **délai coloré** (rapides ≤5 en mint, lentes ≥20 en
  rouge) + **flèche de tendance** (↓ accélère / ↑ ralentit / → stable).

## Preuve
`nuit-velocite-classement.png`. Testé PC : #1 Saint-Pierre 8 m (stable), #2 Sainte-Suzanne (ralentit)…

## Garanties
`tsc`/build verts, endpoint testé. Tendance/rang = agrégats SQL réels, aucune invention. `git diff` =
`modules.py` (velocite) + `ModulePanel.tsx` (M05) + QA.

## Merge
`git -C /Users/openclaw/Desktop/labuse checkout main && git merge --no-ff feat/nuit-velocite`
**État : ✅ prêt à merger.**
