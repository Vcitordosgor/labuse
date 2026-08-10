# RAPPORT M55-D stage 6 — PHASE 2 : Communes en tête, Signaux de vie, panneau final

Branche `feat/m55-d-stage6` (phase 1 `fb076e9f` + phase 2 `ccfb9222`), non mergée. Arbitrages Vic
appliqués : **8 signaux** (friche incluse) · #1 **toute procédure** (658, « i » précise « en cours
ou récente ») · #6 **PM privées** (3 082) · #8 **cession 24 mois** (2 434) · #9 **assemblage privé
≥ 3** (22 813) · **dormance écartée**. tsc 0, vitest 32/32, pytest signaux 2/2, build vert.

## A. Le panneau final (livré, capture `s6_panneau_ouvert`)
```
FILTRES                                 [N actifs]
1 · COMMUNES        24 chips CODE POSTAL (BAN) + « i » nom commune + tout/rien
2 · LE TERRAIN      surface · zonage · état du sol · contraintes EN DERNIER
3 · SIGNAUX DE VIE  8 chips + « i » sourcés/datés
────────────────────────────────────────
    [ Analyser les parcelles ]          (Révélation stage 5, rituel intact)
```

## B. Communes — rang 1, maître unique
- 24 chips **code postal** (CP dominant mesuré dans la BAN — ex. 97460 Saint-Paul, 97410
  Saint-Pierre, 97470 Saint-Benoît) ; « i » au survol nomme la commune ; **tout/rien en un clic**.
- **Un seul état** : `filters.communes` (multi) est le MAÎTRE ; `commune` (la carte) est **dérivée**
  — 1 sélection → mode commune (fit/zoom existants), 0 ou ≥2 → mode île, le filtre borne les
  résultats. `setCommune` et `focusCommune` (clic-commune M55-C : fiche+zoom+périmètre) écrivent
  dans CE filtre.
- **Header = REFLET** : affiche « Toute l'île » / « Saint-Paul » / « 3 communes » et **ouvre la
  section Filtres** au clic (desktop + tiroir mobile, via le store). Le dropdown a disparu (la
  fiche commune reste accessible par ⓘ Contexte et les marqueurs carte).
- URL : `cs=` multi persisté (prouvé : `#f=1&cs=Saint-Paul,Saint-Pierre,Saint-Denis`) ; vieux
  liens `c=` mono compatibles (redirigés vers le maître).

## C. Signaux de vie
- **Backend** : param `/filtre?signaux=` (CSV whitelisted, 8 clés) — **OU dans le groupe, ET avec
  le reste**. Les 3 lourds lisent la table **pré-calculée `parcel_signaux_vie`**
  (`labuse build-signaux-vie`, idempotent DELETE+INSERT, **test d'idempotence 2/2**) ; les 5
  légers en EXISTS indexés directs. Vérifié à l'endpoint (conforme phase 1) :
  procédure 658 · permis_actif 7 002* · caduc 2 161 · défisc 797 · nu_pm 3 082 · friche 1 801 ·
  cession 2 393 · assemblage 21 897 ; OU (défisc, friche) = 2 595 ; **requête reine** tiers hauts ×
  défisc = 3. *(7 002 < 8 003 phase 1 : jointure `parcels` en plus — seuls les idus réellement
  rattachés comptent.)*
- **Front** : chips multi + « i » (libellés validés au STOP, dans `strings.ts`), badge N global
  inclus, **filtrables SANS analyse** (`TERRAIN_FIELDS` — un signal n'allume pas l'interrupteur).
- **Legacy** : `ev=1` en URL mappe vers le signal « procédure collective » (testé — le flag binaire
  « Avec événement (BODACC) » n'existe plus dans l'UI).
- **Révélation enrichie** : parc de l'intro = le PÉRIMÈTRE (communes seules) ; la phrase
  récapitule — mesuré : « *LABUSE a analysé les 131 692 parcelles de 3 communes. Selon vos
  critères (3 communes, > 1 000 m², Sortie de défisc) : 4 retenues — …* ». Rituel **3,00/3,01 s**.

## D. Ménage acté
« Vous cherchez ? », pré-réglages et « Mes vues » **retirés de l'UI** (0-caller vérifié) ; le
backend `saved_searches`/veilles reste intact (la cloche de notifications les sert toujours).
Contraintes de secteur déjà en dernier de l'étage terrain.

## E. Non-régression (vert)
- **5 combinaisons identiques** : 9822 · 188 · 1710 · 3770 · 51129.
- **Vieux liens** : `c=` périmètre unique ✓ · `tv=chaude&smin=2000` → 17 ✓ · `al=1` direct ✓ ·
  `ev=1` → signal procédure ✓.
- Rituel 3 s intact, phrase récap conforme, mobile vérifié.
- Captures : `s6_panneau_ferme/ouvert`, `s6_communes`, `s6_signaux`, `s6_revelation_recap`,
  `s6_mobile`.

## À rejouer sur le VPS
`labuse build-signaux-vie` (comme les autres pré-calculs). Scoring/tiers non touchés.
CC ne merge jamais.
