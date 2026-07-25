# M17 — LOT B : veilles en langage naturel

**Branche** `feat/m17-b-veilles-nl` (base `main`). Prouvé, **non mergé**. Garde-fou : **jamais de veille
non déclenchable** (audit M16-A5).

## B1 — Champ de saisie NL (zone Veilles du panneau Notifications)
Un champ « Décrivez : « les grandes parcelles à Saint-Paul qui deviennent chaudes » ». Il appelle
**`POST /events/veille-nl`**, qui **RÉUTILISE la brique de traduction existante** (`ia_search`,
validée par schéma FILTER_SCHEMA — aucun second moteur). Pas de SQL généré.

## B2 — Traduction en filtres VISIBLES et modifiables
La réponse `ok` ne garde **que les dimensions que le matcher de veille honore réellement** (statut/tier,
commune, événement BODACC, Q, surface, SDP). Le front **`setFilters(...)`** → les filtres deviennent des
**chips actives dans l'en-tête** (« Chaude », « Secteur 1 commune »…) que le client vérifie/ajuste, plus
un résumé lisible « ✓ Alerte quand une parcelle devient chaude, à Saint-Paul. » Jamais une boîte noire.

## B3 — Refus honnête de l'indéclenchable
`veille-nl` refuse, AVANT toute traduction, les intentions non détectables (audit A5) : **changement de
PLU/zonage**, **permis abandonné/annulé** (on ne détecte que l'apparition), mouvement de prix, changement
de DPE — avec un message ciblé + la liste des vrais déclencheurs. Si la traduction ne produit **aucune
dimension déclenchable** → refus générique. **Aucune veille muette n'est enregistrée** (le front n'affiche
pas de résumé, ne pré-remplit rien).

## B4 — Cohérence avec les chips M16
Les chips d'exemples M16 restent. La saisie libre **et** les chips produisent le **même objet veille**
(`saved_searches`, enregistré par le **même** `saveSearch(filtersToHash(...))`) et alimentent le **même**
matcher. Un seul système.

## Correctif de fond (honnêteté du déclenchement)
Le matcher de veille lisait `st` et **ignorait `tv` (tiers du front) et la commune** — les veilles
sur-alertaient silencieusement sur ces deux dimensions. `_parse_hash_filters` honore désormais **`tv`**
(union avec `st`) et **`cs`** (commune, nouvelle clause dans `_veilles_match`). Une veille fait enfin
**exactement ce qu'elle affiche**.

## Preuve (`:8060`, `qa/m17/B/prove.mjs`)
- **B1/B2** : « les parcelles à Saint-Paul qui deviennent chaudes » → résumé « Alerte quand une parcelle
  devient chaude, à Saint-Paul » ; chips **Chaude + commune** visibles ; nom pré-rempli.
- **B4 (save)** : « + Veille » → veille enregistrée (0 → 1). Hash `#f=1&tv=chaude&cs=Saint-Paul` — et
  `_parse_hash_filters` le rend `st=['chaude'], cm=['Saint-Paul']` : **honoré** par le matcher.
- **B3** : « préviens-moi si le PLU change » → **refus honnête**, aucun résumé, **rien enregistré**.
- Chips M16 toujours présentes.
Captures : `b1_nl_traduit.png`, `b2_veille_enregistree.png`, `b3_refus_honnete.png`.

## Golden
**116/116 PASS** (`LABUSE_DEV_MODE=1`, `LABUSE_API_BASE=:8060`). Zéro touche scoring.

## Décision ouverte
- En **stub NL** (dev, sans clé IA), l'extraction reste basique (« grandes » n'a pas produit de
  surfaceMin) ; la brique réelle (clé présente) enrichit sans changer le contrat. Le garde-fou
  déclenchable est **côté serveur**, donc identique dans les deux modes.
