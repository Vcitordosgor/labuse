# Vérification — `origin/feat/plu-nuit-verif` vs calibrage PLU servi par main

Lecture seule. Rien modifié, rien mergé. HEAD branche `60733dca`, HEAD main `a263239f`
(branche **non mergée**).

## Verdict en une ligne

**Main porte déjà TOUTES les valeurs de la branche, à l'identique. La branche est un
TÉMOIN (contre-extraction de nuit) qui confirme le servi — rien à faire.** Les arbitrages
Vic du 28/07 ont été gravés dans le calibrage servi par les mandats intermédiaires
(M-PLU-REF 14/08, M-PLU-REF-B + M94 15/08, M131 22/08) ; la branche les re-dérive en aveugle
et tombe dessus.

## Fait structurel décisif

- **Le calibrage SERVI = `config/plu_<commune>.yaml`**, chargé par `resolve_zone`
  (`src/labuse/faisabilite/plu_rules.py:90` — `_CONFIG_DIR / f"plu_{slug}.yaml"`).
- **La branche ne touche QUE `config/verif/plu_*_contre.yaml`** (3 fichiers : saint_louis,
  les_avirons, petite_ile). Ces contre-fichiers sont **absents de main** ET **jamais chargés
  par aucun code** (grep : zéro référence à `verif/`/`_contre` dans `src/labuse`). Ce sont des
  artefacts de vérification purs — ils ne servent rien, ni sur la branche ni ailleurs.
- Donc la branche **ne peut pas** contredire le servi : elle ne le touche pas. La seule
  question réelle — les VALEURS sont-elles dans le servi de main ? — se vérifie fichier par
  fichier ci-dessous.

## Les 4 familles, valeur par valeur (verdict : IDENTIQUE partout)

| # | Famille | Zone · champ | Valeur branche (contre) | Valeur **main servi** | `main fichier:ligne` | Verdict |
|---|---------|--------------|-------------------------|-----------------------|----------------------|---------|
| 1 | Recul voirie AUs (tiroir géo., 3 tranches verbatim) | petite_ile `AUs.recul_voirie_m` | **4** (majorité gravée, RD/RN écartées) | **4** — même citation 3-tranches + « TIROIR GÉOGRAPHIQUE… arbitrage Vic 28/07 » | `plu_petite_ile.yaml:215` | **IDENTIQUE** |
| 2 | Ub4 plafond absolu (convention B) | les_avirons `Ub4.he_m / hf_m` | **8 / 8** (plafond unique ⇒ he=hf) | **8 / 8** | `plu_les_avirons.yaml:154` | **IDENTIQUE** |
| 3 | H/2 doctrine b — UC1 | saint_louis `UC1.recul_limites_sep_m` | **4,5** (H/2 à 9 m) | **4,5** | `plu_saint_louis.yaml:143` | **IDENTIQUE** |
| 3 | H/2 doctrine b — UE | saint_louis `UE.recul_voirie / limites` | **6 / 6** (H/2 à 12 m) | **6 / 6** | `plu_saint_louis.yaml:176,178` | **IDENTIQUE** |
| 3 | H/2 doctrine b — US | saint_louis `US.recul_voirie / limites` | **6 / 6** | **6 / 6** | `plu_saint_louis.yaml:186,188` | **IDENTIQUE** |
| 3 | H/2 — renvois 1AU (mêmes zones via renvoi) | saint_louis UC1/UE renvoi ×5 | idem | idem (4,5 ×1 · 6 ×4) | `plu_saint_louis.yaml:261,291,292,300,301` | **IDENTIQUE** |
| 4 | 39 rétro-annotations de libellé (doctrine-a pleine terre) | `pleine_terre_src` (annotation) | « … sans sous-minimum de pleine terre (doctrine a) » | doctrine-a **présente** dans le servi (ex. 20 occ. « sous-minimum de pleine terre » dans saint_louis servi ; les_avirons Ub4 : « SANS sous-minimum de pleine terre ») ; les `pleine_terre_pct` (valeurs) sont **inchangées** | `plu_les_avirons.yaml:160`, `plu_saint_louis.yaml` (×20) | **PRÉSENT** (libellé ; zéro impact valeur) |

**Décompte Famille 3** : la branche modifie **10** reculs en H/2 (2× limites 3→4,5 ; 4× limites
4→6 ; 4× voirie 5→6). Main servi porte exactement **8 reculs à 6 m + 2 reculs à 4,5 m = 10**,
zone pour zone (base + renvois). Concordance stricte.

## Gravité par famille (comme demandé)

- **Familles 1–3 (valeurs : reculs, plafond de hauteur, H/2)** — les seules à gravité réelle :
  toutes **présentes et identiques** dans le servi. Aucun écart. Le PLU calibré servi **ne
  contredit pas** les arbitrages du 28/07 ; il les porte.
- **Famille 4 (39 relabels de libellé)** — gravité minimale par nature : ce sont des annotations
  de la chaîne `_src` (citation de source), **pas** des valeurs. Les `pleine_terre_pct` sont
  identiques ; le servi porte déjà la substance doctrine-a. Rien à aligner.

## Les « 17 défauts consignés, laissés intacts »

Ce sont des défauts **documentés** (known-issues) dans les contre-fichiers de la branche, laissés
tels quels par décision Vic. Ce ne sont **pas des valeurs à appliquer** au servi — hors périmètre
de cette vérification (aucune valeur servie n'en dépend). Signalés pour mémoire, non traités.

## Conclusion

Cas propre : **main porte déjà les valeurs**. La branche `feat/plu-nuit-verif` est un témoin de
contre-extraction — on la garde telle quelle, **rien à faire**. Aucun écart valeur à re-graver,
aucun arbitrage en attente.

*Lecture seule. Aucun fichier de calibrage modifié, aucun merge. STOP.*
