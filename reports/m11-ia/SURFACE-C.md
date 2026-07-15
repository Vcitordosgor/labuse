# M11 · SURFACE C — Onglet Faisabilité : afficher le calcul tracé + l'expliquer par l'IA

**Branche** : `feat/m11-surface-c` (NON mergée — Vic valide + merge). **Date** : 2026-07-15.
**Prérequis mergés** : socle §0, Surface A, B1, B2 (main `29697ab`). **Parcelle-exemple** : **97415000EL0387**
(Saint-Paul / La Saline, chaude, 2 937 m², zone U5c).

**Zéro touche** scoring / cascade / étage 0 / run servi `q_v6_m8` / moteur `engine.py` (git : seuls
API/front/tests). **Solaire NON retiré** (spin-off séparé) — l'onglet Faisabilité prendra sa place lors
de ce futur spin-off (noté dans TABS).

**Distinction cardinale respectée** : le calcul affiché est **déterministe et exact** (steps du moteur,
rendus tels quels) ; l'IA **explique, ne recalcule jamais** (chaque chiffre ancré sur un step, validé socle).

---

## Lot 0 — Constat (vérifié avant code)
- `parcel_faisabilite(db,id)` → `f.steps` = **11 steps** `{label, formule, valeur, source, prov}`. ⚠ Les steps
  capacité ont `prov=''` (seul le bilan porte sourcee/estimee/derive) → provenance d'affichage **dérivée du
  `source`** (Art./Zone/géométrie → Sourcé ; hypothèse → Estimé ; dérivé → Dérivé), **sans toucher au calcul**.
- L'endpoint `GET /modules/faisabilite/{idu}` (`faisabilite_sens1`) renvoyait `capacite` **sans les steps** (droppés).
- Calculette : `Calculette({idu})` (autonome) → `POST /modules/faisabilite/{idu}/charge`.
- Onglets : `TABS` (Fiche.tsx) synthese/…/solaire/bilan ; PDF utilise `calculette` si `tab==='bilan'`.

## Lot 1 — Exposer les steps (backend, additif)
`faisabilite_sens1` : `capacite` gagne `steps` (label/valeur/source + `prov` d'affichage dérivé par
`_faisa_step_prov`) + `avertissements` + `modulation`. Aucun calcul modifié. Preuve (EL0387) : 11 steps,
ex. « Niveaux constructibles = R+1 [Zone U5c, Art. 10.2] · Sourcé », « Emprise bâtie = ~1000 m² · Estimé ».

## Lot 2 — Onglet Faisabilité (front)
Nouvel onglet **« Faisabilité »** (`Fiche.tsx`, `FaisabiliteTab`), inséré avant Solaire (non retiré) :
1. **Résultat** en tête : gabarit R+1 (6 m), SDP 2 001 m², logements 17–18, SHAB vendable ~1 278 m².
2. **« Le calcul, étape par étape (11) »** : liste verticale, chaque ligne = label + **valeur** + badge
   **Sourcé** (vert) / **Estimé** (ambre) / **Dérivé** (gris) + source. Déterministe, repliable, visible par défaut.
3. **« Expliquer ce calcul en clair »** (bouton violet premium, **sur clic uniquement**).
4. **Calculette de charge foncière RAPATRIÉE** ici (retirée de BilanTab, qui porte un renvoi). Entrées client
   (coût/marge) éditables, verdict d'achat — **jamais touchées par l'IA**.
Captures : `c-onglet-faisabilite.png` (résultat + 11 steps sourcés + calculette), `c-explication-ia.png`.

## Lot 3 — L'explication IA (cœur)
`GET /modules/faisabilite/{idu}/explain` : construit un contexte autorisé où **chaque step est un Fact
étiqueté** (`etape_1..11` capacité, `bilan_1..N`, `charge_fonciere`, `prix_dvf_fiabilite`), provenance
mappée (sourcee→SOURCE, estimee/derive→ESTIME). `core.complete(validate=True, require_sources=True)` →
prose qui **narre la dérivation**, chaque chiffre ancré `⟨src:etape_N⟩`. Le **bilan utilise les hypothèses
PAR DÉFAUT de la calculette** (coût 2 500 €/m², marge+frais 21 %) → l'explication porte sur les chiffres
RÉELLEMENT vus. **Cache** `(idu, run, "explication_faisabilite")`. Rendu **`renderRich`** (réutilisé de Surface A).

Extrait réel (EL0387) :
> « …l'emprise disponible est de **~2 223 m²** ; … une surface de plancher brute estimée à **~2 001 m²** … le
> nombre de logements ressort à **17 à 18 unités** … Le bilan à rebours part d'une surface vendable estimée à
> **~1 278 m²** et de prix DVF secteur … (médiane **3 165 €/m²**) — **attention : la fiabilité de ces prix DVF est
> jugée fragile** … la charge foncière acceptable ressort à une **médiane négative d'environ -479 k€** … »

## Lot 4 — Tests & preuves (`tests/test_surface_c.py`, +socle)
- **Ancrage (le test qui compte)** : un chiffre absent des étapes est **REJETÉ** — « ~9 999 m² » → rejet
  « chiffre non sourcé « 9 999 » » ; « 9 000 000 € » → rejet. Le vrai (2 001) et l'arrondi (2 000) passent.
- **Faille d'échelle fermée** (bug socle trouvé et corrigé) : la tolérance k€/M€ ne s'applique plus que
  contre une valeur **≥ 1000**. Sans ça, « 9999/1000 ≈ 10,2 » (le 10,2 d'un « Art. 10.2 ») laissait passer
  n'importe quel grand nombre inventé. « 1,5 M€ » reste ancrable sur 1 500 000.
- **Honnêteté DVF** : l'explication signale la fragilité (« fiabilité … fragile ») et n'affiche jamais la
  charge foncière comme un chiffre dur (elle va jusqu'à énoncer une médiane **négative**). Preuve capture + live.
- **Marqueur malformé** : un `⟨src:a / b⟩` non capté par le regex strict est désormais **strippé** (ne fuit plus).
- **Calculette** : entrées client jamais touchées par l'IA (calcul serveur déterministe inchangé).
- **Non-régression** (live) : Surface A (ask), B1/B2 (search + agrégat), Bilan (getFaisabilite intact),
  **Solaire intact**. 48/48 tests (C + socle + agrégat + sémantique).

## Socle & versions
- `core.complete` inchangé dans son contrat ; **fix de robustesse** : (a) tolérance d'échelle bornée aux
  valeurs ≥ 1000 (ferme la faille d'ancrage) ; (b) strip large de tout `⟨…⟩` résiduel (anti-fuite de marqueur).
  Bénéficient à tous les appelants, aucune régression (24 tests socle/agrégat verts).
- **`CONTEXT_VERSION` bumpé 2 → 3** : le contexte IA de fiche gagne l'explication par steps (nouveau format).
  Effet : le cache antérieur de la barre de fiche est orphelin → régénéré au format courant (jamais d'ancien
  format resservi — le piège réglé sur Surface A).

## Note — retrait futur de Solaire
L'onglet **Faisabilité prendra la place de « Solaire »** lors du spin-off « aménités extérieures » (décidé,
brief séparé de Vic). Ici : Faisabilité ajouté **en plus** ; Solaire intact.

*Commit sur `feat/m11-surface-c`. Pas de merge.*
