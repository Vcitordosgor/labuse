# FIX LOT 2 — deep-links carte

**Branche** : `feat/fix-lot2` (NON mergée — Vic valide + merge). **Date** : 2026-07-15.
**4 commits séparés**, **front only** (git : aucun fichier `.py` touché, zéro scoring). Base : `main` (fix-lot1 mergé).
Diagnostic source : `reports/pre-lancement/DIAGNOSTIC-OUTILS.md` (groupe 4).

**Objectif** : Maps / Cadastre / 1950 / radar tombaient sur **la zone** ; désormais chacun **centre sur la parcelle et la met en évidence** (dans la limite de ce que chaque cible permet).

| # | Commit | Cible | Fichier |
|---|---|---|---|
| A | `586bcc3` | Maps (renommage + épingle) | `Fiche.tsx` |
| B | `580eccb` | Cadastre (centrer + sélectionner) | `Fiche.tsx` |
| C | `1bb40b0` | 1950 (flyTo parcelle) | `Fiche.tsx` |
| D | `a22d89a` | Radar permis (localiser + non géocodé) | `ModulePanel.tsx` |

La fiche expose déjà `coords = [lon, lat]` (centroïde) et `idu` → matière suffisante. `select(idu)` **recentre + surligne** déjà la parcelle (halo `parcels-sel`, MapView « ping systématique ») ; `setFlyTo({center,zoom})` recentre la carte.

---

## FIX A — Maps (renommage + épingle)
**Avant** : bouton « **G** », `href=https://www.google.com/maps/@{lat},{lng},19z/data=!3m1!1e3` → centrage caméra **sans marqueur** (on ne savait pas quel toit/terrain était la parcelle).
**Après** : renommé « **Maps** », `href=https://www.google.com/maps/search/?api=1&query={lat},{lng}` → Google Maps ouvre **centré avec une épingle** sur la parcelle.
**Preuve** : capture `fixA-maps-bouton.png` (bouton « Maps ») ; href vérifié = `…/search/?api=1&query=-21.096826,55.288783`.

## FIX B — Cadastre (centrer + SÉLECTIONNER)
**Contrainte constatée** : **aucun viewer cadastre externe gratuit n'expose de sélection de parcelle par IDU via URL** — le Géoportail (qui **ferme fin septembre 2026**) n'a pas de tel paramètre, et l'explorateur Etalab est une SPA sans param documenté. Un lien externe ne pouvait donc que **centrer** sur la zone (le défaut d'origine), jamais « sélectionner » (l'exigence).
**Décision (à valider)** : puisque la « mise en évidence » est l'exigence ferme, le bouton « Cadastre » bascule sur le **fond officiel IGN Plan (parcellaire) DANS l'app** + `select(idu)` → la parcelle est **surlignée (halo) et recentrée** sur le cadastre officiel. La géométrie affichée vient de la même source Etalab que le cadastre. C'est un **commit isolé** : si tu préfères re-pointer vers un lien externe (au prix du simple centrage), il se reverte seul.
**Preuve** : capture `fixB-cadastre-selection.png` (fond IGN Plan cadastral + parcelle avec halo violet).

## FIX C — 1950 (flyTo parcelle)
**Avant** : « 1950 » ouvrait le comparateur historique interne (`setModule('temps')`) **sans recentrer** → la carte restait sur l'île.
**Après** : `setFlyTo({center: coords, zoom: 18})` + `setModule('temps')` → la vue historique s'ouvre **centrée sur la parcelle** (ping de sélection visible).
**Preuve** : capture `fixC-1950-centre.png` (ortho 1950-1965 centrée sur la parcelle, ping vert).

## FIX D — Radar permis (localiser + non géocodé)
**Avant** : le drawer d'un permis n'avait **aucun deep-link**, alors que l'API renvoie `geom` (centroïde de la parcelle rattachée) et `parcelles` (IDU).
**Après** :
- **Permis géocodé** : bouton « **◎ Voir la parcelle sur la carte** » → `setFlyTo(geom)` + `select(parcelle)` (halo) + ferme le drawer.
- **Permis non géocodé** (`geom` NULL — **10 749 / 50 043 = 21,5 %**) : message clair *« Permis non géocodé — son adresse n'a pas pu être rattachée à une parcelle du cadastre, il ne peut pas être localisé »*, **jamais un clic mort**.
- **« Non géocodé » expliqué** : tooltip sur le badge de la liste (« permis dont l'adresse n'a pas pu être rattachée à une parcelle du cadastre — non localisable »).
**Preuves** : `fixD-permis-geocode.png` (bouton localiser) ; `fixD-permis-nongeocode.png` (message clair) ; `fixD-permis-localise-carte.png` (après clic → carte).

---

## Tests & non-régression
- 4 fixes prouvés par capture (A href + bouton, B halo, C centrage, D localiser + message).
- `tsc --noEmit` vert. **Front only** — aucun fichier `.py`, zéro scoring/cascade/étage 0/run (`git diff --name-only main..HEAD` = 2 fichiers front).
- Carte, fiches, autres outils : intacts (seuls les handlers des 4 boutons/1 drawer changent).
- **Hors périmètre respecté** : point 24 (swipe/rideau des fonds de plan) NON touché.

## Point à trancher par Vic
**Fix B** est le seul choix de conception : faute d'URL externe sélectionnant une parcelle par IDU, j'ai livré la mise en évidence **dans l'app** (fond IGN officiel + halo) plutôt qu'un lien externe qui ne ferait que centrer. Commit isolé, revertable si tu veux revenir à l'externe (centrage seul).

*4 commits séparés sur `feat/fix-lot2`. Pas de merge. Pas de point 24, pas de LOT 3.*
