# EXIGU-GRANDES — pourquoi de grandes parcelles U/AU tombent en `terrain_exigu`, et le correctif

Branche `fix/exigu-grandes` (base `origin/main` `44cf22f0`). Fix = commit `81f21e53`.
Résiduel servi = **run 10** (patché sur les parcelles concernées), score servi = `q_v11_m137`
(inchangé, **aucune bascule**). q_v15 = run candidat, recalculé.

---

## 1. Combien, et où

**218 parcelles > 5 000 m² en zone U/AU sont `terrain_exigu` au run 10** (111 AU, 107 U).
Par forme de zone : 94 en zone AU **numérotée** (65 × 1AU, 26 × 2AU, 3 × 3AU), 17 en AU
(lettre), 107 en U.

## 2. La cause — il y en a plusieurs, une seule est un bug

En traçant les 218 à travers `parcel_faisabilite` (assiette clippée), l'`emprise` finale
tombe < 5 m² (seuil `terrain_exigu`) pour **cinq raisons distinctes** :

| mécanisme | n (~) | verdict |
|---|--:|---|
| **Zone AU numérotée non reconnue par le clip U/AU** | **~59** | **BUG → corrigé** |
| PPR rouge / aléas couvrant toute l'assiette (gabarit) | ~50 | légitime (danger réel) |
| ER / EBC couvrant toute la parcelle (legacy) | ~40 | légitime (terrain entièrement réservé/boisé) |
| PPR / PEB / ravine / 50 pas couvrant l'assiette (legacy) | ~22 | légitime |
| Zone d'implantation du gabarit vidée par les reculs (géom.) | ~18 | à instruire (à part) |

**Le bug (mécanisme 1).** Les zones **à urbaniser numérotées** (`1AUb`, `2AUc`, `3AU5st`…)
portent dans `spatial_layers` un `name` qui **commence par un chiffre** et un `subtype`
normalisé GPU (`1AUb` → subtype `AUc`). Or l'assiette constructible était clippée à la portion
U/AU par `z.name ILIKE 'U%'/'AU%'` — que **0 des 422 zones numérotées** ne matche. Résultat :
la portion U/AU calculée = ∅ (ou un liseré parasite) → `base ≈ 0` → **`terrain_exigu` à tort**,
même sur une parcelle de plusieurs hectares entièrement à urbaniser.

Le classement de **famille** (`zone_servie._FAM`, qui alimente `zone_fam`, `_sous_zone`,
`_pct_constructible`) reconnaît pourtant déjà ces zones — parce qu'il matche sur **`subtype`**.
Le clip d'assiette (`_EMPRISE`, `_GREVE_CERTAINE`) était le seul à matcher sur `name` : **une
incohérence de clé**, pas un problème de recul, de multipolygone ni de seuil de largeur.

> Réponse aux hypothèses posées : ce n'est **pas** un « recul par défaut énorme » (le défaut
> est 3 m, prudent), **pas** un seuil de largeur, **pas** un artefact multipolygone. C'est
> `name` vs `subtype` sur les zones AU numérotées.

## 3. Le correctif (`81f21e53`) — borné

Dans `_EMPRISE` et `_GREVE_CERTAINE`, le clip U/AU rattrape les zones numérotées **via
`subtype`, uniquement quand `name` commence par un chiffre** :

```sql
AND (z.name ILIKE ANY(:uau_pats)
     OR (z.name ~ '^[0-9]' AND z.subtype ILIKE ANY(:uau_pats)))
```

Pourquoi borné : en creusant, `name` est **parfois un code** (`Ub`), **parfois un libellé
littéral** (`"Secteur de centralité"`) dans **8 communes** (Saint-Pierre, Petite-Île,
Bras-Panon, Sainte-Marie, Saint-André, Salazie, Sainte-Rose, Entre-Deux). Là, `name` ne matche
jamais U/AU → l'assiette n'y est **pas clippée du tout** (`base = full`), ce qui **surestime**
la capacité (~94 000 parcelles concernées). **C'est un bug distinct et bien plus large**, à
blast-radius quart-d'île : il exige son propre run et sa propre validation — **hors de ce
correctif**. Le correctif ci-dessus ne touche donc que les zones numérotées (`name` numérique),
et laisse ces 8 communes strictement inchangées.

## 4. Preuve

**Non-régression (contrôle).** 300 parcelles tirées HORS périmètre (ne touchant aucune zone AU
numérotée), recalculées sans-fix vs avec-fix : **0 différence**. Au niveau SQL : 0 zone matche
`name` U/AU sans que `subtype` matche (le fix n'enlève jamais rien). `subtype` jamais NULL (0/5841).

**Tests.** `pytest` périmètre faisabilité/gabarit/résiduel/zonage : **259 passed**, 1 échec
**pré-existant** vérifié à l'identique sur `origin/main` (`test_vocabulaire_client_gravé`, dérive
de vocabulaire de bande, sans rapport avec la géométrie).

**Les 10 « douteuses » du rapport bandes — avant → après fix** (honnêtement, une seule était le bug) :

| idu | zone | avant | après | |
|---|---|---|---|---|
| 97407000BM0011 | 1AUmut | terrain_exigu (0) | **(constructible) 56 490 m²** | ✅ bug corrigé |
| 97409000AB0523 | 1AUt | redhibitoire (0) | redhibitoire (0) | inchangée (assiette recalculée, 0 pour autre motif) |
| 97409000AB0550 | 1AUt | redhibitoire (0) | redhibitoire (0) | inchangée |
| 97411000EH0136 | AUa | terrain_exigu (0) | terrain_exigu (0) | légitime — PPR rouge sur 100 % (121 618 m²) |
| 97411000DP0425 | Uva | redhibitoire (0) | redhibitoire (0) | légitime (limites non qualifiées) |
| 97412000BM1142 | U3 | redhibitoire (0) | redhibitoire (0) | légitime |
| 97422000BZ0133 | Uav | (constructible) 0 | (constructible) 0 | légitime |
| 97415000AD0044 | U1pso | redhibitoire (0) | redhibitoire (0) | légitime |
| 97411000CD1083 | Uh | (constructible) 0 | (constructible) 0 | légitime |
| 97411000HL0033 | Uu | (constructible) 0 | (constructible) 0 | légitime |

Les « douteuses » que j'avais listées étaient donc majoritairement des **zéros légitimes** ou
d'autres mécanismes — le fix les laisse à 0 à raison, et ne débloque que le vrai bug.

**Dix parcelles où le bug est réellement corrigé** (zone AU numérotée, `terrain_exigu` → capacité) :

| idu | zone | surface | SDP avant → après |
|---|---|--:|---|
| 97422000DH0603 | 1AUb | 72 306 | 0 → **92 717 m²** |
| 97407000BA0271 | 1AUm | 45 625 | 0 → 61 453 m² |
| 97407000BM0011 | 1AUmut | 72 704 | 0 → 56 490 m² |
| 97422000AX0437 | 2AUe | 60 075 | 0 → 54 724 m² |
| 97414000DE1868 | 1AUb | — | 0 → 33 014 m² |
| 97407000BA0325 | 1AU | — | 0 → 26 449 m² |
| 97414000EN1148 | 1AU | — | 0 → 22 515 m² |
| 97414000DE1858 | 1AU | — | 0 → 17 186 m² |
| 97422000EM0260 | 1AU | — | 0 → 15 747 m² |
| 97422000BW3184 | 1AU | — | 0 → 13 591 m² |

**Sur les 218 > 5 000 m² :** après fix, **48 → constructible** (SDP débloquée 641 908 m²),
19 → `redhibitoire` (toujours 0, mais assiette enfin calculée, verdict par un vrai motif),
**151 restent `terrain_exigu`** — légitimes (PPR/aléas/ER/EBC couvrent l'assiette, ou zone
d'implantation gabarit vidée, mécanismes 2-5).

## 5. Recalcul ciblé (pas l'île)

Le fix ne peut changer QUE les parcelles touchant une zone AU numérotée (le clip n'ajoute que
ces zones). Ensemble complet = **10 414 parcelles** (`--parcelles-fichier`, `--into-run 10`,
`--assiette-clippee`, run 10 dé-servi le temps du patch puis re-servi ; retour `residuel-serve 8`).

Effet sur ces 10 414 dans run 10 :
- parcelles à SDP > 0 : **4 001 → 4 141** (+140) ;
- SDP cumulée : **3,41 → 5,36 Mm²** (+1,95 Mm²) ;
- `terrain_exigu` : 2 355 → 2 214 (−141).

**Île entière (run 10)** : SDP totale **79,05 → 81,00 Mm² (+1,95 Mm², +2,5 %)**,
parcelles à SDP > 0 147 838 → 147 978. Concentré sur 7 communes à zonage codé (Cilaos,
Saint-Louis, Le Tampon, Saint-Joseph, Les Trois-Bassins, Le Port, Sainte-Suzanne).

## 6. Distribution des bandes q_v15 après correctif

Bandes rebâties (`score-labuse --run q_v15 --signal-run q_v15`) sur le run 10 patché :

| bande | avant fix | **après fix** | Δ |
|---|--:|--:|--:|
| **0** | 269 087 | **268 947** | **−140** |
| A | 5 258 | **5 321** | +63 |
| B | 27 439 | **27 495** | +56 |
| C | 39 647 | **39 679** | +32 |
| D | 75 494 | **75 483** | −11 |
| NC | 14 738 | **14 738** | 0 |
| total | 431 663 | 431 663 | 0 |

Le fix sort **140 parcelles** de la bande 0 (vers A +63 / B +56 / C +32 ; D −11 net) — peu
nombreuses mais à forte capacité (les grandes AU numérotées). Aucune bascule : `q_v11_m137`
reste servi.

## 7. Ce qui reste (hors de ce correctif)

1. **Communes à `name` littéral (8, ~94 000 parcelles)** : l'assiette n'y est pas clippée à la
   portion U/AU (`base = full`) → capacité **surestimée**. Bug distinct, blast-radius quart
   d'île → mandat séparé (run île + validation dédiée). Le bon correctif y est probablement de
   matcher `subtype` partout, mais il faut le mesurer commune par commune avant de le servir.
2. **Mécanisme gabarit `zoneImpl ≈ 0` (~18)** : la zone d'implantation du gabarit se vide sous
   les reculs par côté sur certaines grandes parcelles — à instruire géométriquement (étroitesse
   réelle vs artefact).
3. Les 151 `terrain_exigu` restants > 5 000 m² sont, à l'inspection, des zéros **légitimes**
   (PPR rouge, aléas, emplacement réservé ou EBC couvrant toute l'assiette).

**Rien n'est mergé. Aucune bascule.**
