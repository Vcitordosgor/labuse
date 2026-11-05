# NU4-D — Les 100 premières parcelles sont-elles de bonnes affaires ?

**Mandat** audit lecture seule, branche `audit/nu4-d`, worktree `~/Desktop/labuse-nu4d`,
ports 9660/6860. Base Mac `labuse` (434 582 parcelles, **run servi `q_v20`**, cascade étage 0
`q_v19_sources`). **Aucune écriture, aucun merge. Prod NON consultée** — tout le travail porte
sur la copie locale. Lectures d'abord : `docs/audit-2026-11/scoring-copro-1/COMPTE-RENDU.md`
et `docs/SCORING_SPEC.md` (doctrine du scoring).

> **En une ligne.** Le bas de classement est **sain** (0/100 parcelle écartée à tort) ; le haut
> de classement est **pertinent aux deux tiers** (66/100 affaires réelles) — le tiers restant
> est le symptôme d'un choix de doctrine : **le palier classe la PROBABILITÉ DE MUTATION, pas la
> constructibilité**, et 13 « fausses bonnes affaires » sont servies « À suivre » sans le moindre
> avertissement. Les paliers ne bougent **jamais sans raison** entre deux runs.

---

## 1. Méthode (comme un promoteur, par parcelle)

Pour chaque parcelle j'ai instruit le dossier avec les **mêmes faits que le produit sert** (pas
de recalcul maison — même piège évité que NU-4-C), en joignant au score servi `parcel_p_score_v2`
(run `q_v20`) les caches moteur par parcelle :

| Critère promoteur | Source LABUSE lue |
|---|---|
| Zone PLU (constructible ?) | `parcel_zone_plu` (zone_fam / zone_filtre) |
| PPR, servitudes, domaine public, pente, forme, eau | cascade `dryrun_cascade_results` (HARD_EXCLUDE + SOFT_FLAG, run `q_v19_sources`) |
| SDP cohérente bâti/PLU | `parcel_residuel.sdp_residuelle_m2`, `parcel_p_score_v2.potentiel_sdp_m2` |
| Bâti saturé / révélé / inconstructible / AU fermée | `parcel_filtre_bati`, `parcel_bati_revele`, `parcel_constructibilite`, `parcel_au_statut` |
| Propriétaire atteignable | `acces_pm_siren` (SIREN PM), `acces_courrier` (adresse BAN) |
| Marché crédible | `prix_commune_eur_m2`, `valeur_creee_eur` (SDP × médiane communale) |
| Copropriété | `parcel_p_score_v2.copro` |
| **Verdict RÉELLEMENT servi au client** | `labuse.verdict_servi.verdict_servi_batch()` (le point de traduction unique) |

**Rappel de doctrine (confirmé dans le code).** Depuis PALIERS-1, le palier servi est une fonction
**pure de la probabilité `p`** (`statuts.py` : Priorité ≥ 0,20 / À suivre ≥ 0,10 / Sans signal
sinon ; Écartée = étage 0 de la cascade). La constructibilité, le bâti saturé, la zone fermée, l'AU
non ouverte **ne font plus baisser le palier** — ils deviennent des *motifs* secondaires. Seule la
copropriété est masquée hors des paliers actionnables. **Aujourd'hui `PRIORITE_SERVIE = False`** :
le tier `priorite` est affiché « À suivre » — le client ne voit donc que deux libellés en tête,
« À suivre » et « Écartée ».

**Les deux échantillons** (déterministes, rejouables — `preuves/extract.sql`) :
- **TOP-100** = les 100 meilleurs `rang` du run `q_v20` (rang = ordre de `p`, hors copro) ;
- **BAS-100** = 100 parcelles tirées dans le palier le plus bas `ecartee` (153 283 parcelles),
  ordre `md5(idu)` (tirage reproductible).

---

## 2. TOP-100 — taux de pertinence **66 %**

Libellé **réellement servi** au client : **92 « À suivre », 8 « Écartée »** (ces 8 ont un top-rang
mais sont écartées — cf. §2.3).

| Verdict promoteur | n | Détail |
|---|---:|---|
| ✅ **Affaire plausible** | **66** | SDP résiduelle > 0, zone U/AU, non déclassée, valeur de marché réelle |
| ❌ SDP résiduelle **nulle** (rien à bâtir) | 20 | bâti saturé « construit au maximum » ou terrain exigu |
| ❌ Déclassée **non-constructible / zone fermée**, palier maintenu | 6 | moteur constructibilité dit non, le palier reste « À suivre » |
| ❌ **Écartée** mais logée dans le top-rang | 8 | zone A, forêt publique, DPF, PPR, surface, prescription |
| | | **Fausses bonnes affaires : 34 / 100** |

> **Taux de pertinence = 66 %** (66 affaires réelles sur 100 mieux classées).
> Si l'on ne compte que les 92 **présentées** comme actionnables (« À suivre »), **72 %** (66/92).

### 2.1 La cause racine : le palier mesure la mutation, pas la constructibilité
Le modèle P prédit la **probabilité de vente sous 12 mois**. Les petits lots bâtis urbains vendent
souvent → `p` élevé → haut de classement, **même sans rien à construire**. Les 26 fausses affaires
servies « À suivre » (34 − 8 écartées) se répartissent ainsi :

- **SDP résiduelle = 0** (`valeur_creee = 0`) : le propre moteur de capacité de LABUSE dit « plus
  rien à bâtir », et pourtant la parcelle est en tête. Ex. `97416000EM0764` (Saint-Pierre, UP,
  bâti saturé, rang 48) ; `97405000AO0557` / `97405000AK1006` (Petite-Île, UC saturés).
- **Zone fermée / non-constructible, palier maintenu.** Cas le plus net — `97422000AX1253`
  (Le Tampon, **2AUe = AU fermée**, rang 79) : la constructibilité le marque *zone fermée*, et
  pourtant `parcel_residuel` lui calcule **25 426 m² de SDP** et **57 M€ de valeur créée**, servis
  tels quels, **« À suivre » sans aucun avertissement**. C'est à la fois une fausse affaire ET une
  **incohérence interne** (le résiduel ignore la fermeture de zone que la constructibilité signale).

### 2.2 Sous-finding majeur — 13 pièges **silencieux**
Des 26 fausses affaires servies « À suivre », **seules 13 portent un avertissement** (`declasse` +
motif, uniquement les bâties saturées). Les **13 autres sont servies en « À suivre » sans aucune
mention** : `verdict_servi` ne lit ni `parcel_constructibilite` ni `parcel_au_statut`, donc une
parcelle *inconstructible* ou en *AU fermée* arrive propre à l'écran. Liste (rang · idu · zone · cause réelle) :

```
21 97415000CW1056 AU3A   terrain exigu           79 97422000AX1253 2AUe  zone fermée (25 426 m² servis)
22 97422000BS1761 UB     terrain exigu (47 m²)   80 97408000BO0374 UAV   terrain exigu (46 m²)
23 97418000AT2289 1AUep  habitat interdit        81 97420000AB1530 UB    terrain exigu
29 97422000AX1477 2AUe   zone non constructible  84 97415000HL0033 U2C   inconstructible
57 97422000AX1478 2AUe   zone non constructible  86 97418000AC0150 UEp   habitat interdit
58 97422000AX1479 2AUe   zone non constructible  90 97403000AR1424 UB    inconstructible
                                                 91 97413000DD1355 UCA   inconstructible
```

### 2.3 Incohérence rang ↔ palier — 8 écartées au sommet du classement
Le `rang` est calculé sur **toutes** les parcelles non-copro, **y compris celles de l'étage 0**.
Résultat : 8 parcelles écartées occupent des rangs d'élite. La plus frappante, `97416000CV0474`
(Saint-Pierre) : **rang 5**, `p = 0,60`, mais **zone A agricole** → écartée. Les listes clientes
filtrent sur les tiers servables (l'écartée n'y figure pas), **mais la fiche affiche « rang 5 /
428 239 » à côté de « Écartée »** — un signal contradictoire. Le rang devrait exclure l'étage 0.
*(Note : `97415000AB0840`, rang 42, est écartée par `prescription_plu` alors qu'elle porte 2 542 m²
de SDP et un bâti révélé — à revoir si la prescription justifie bien l'exclusion dure.)*

### 2.4 Les 66 plausibles — réserves honnêtes
Elles sont réelles (SDP > 0 en zone constructible, valeur de marché cohérente ; ex. `97415000HP0029`
Saint-Paul U5B 17 334 m²/51 M€ « divisible », ou le beau grappe AUBM de La Possession). Deux réserves :
- **11** sont en **zone AU sous condition d'opération** — affaires de moyen terme (ZAC), pas
  mobilisables seules ;
- **24** n'ont **aucun accès propriétaire** (ni SIREN ni adresse BAN) — le contact passera par les
  fichiers fonciers / notaire (friction, pas un disqualifiant).

---

## 3. BAS-100 — **0 vraie affaire écartée à tort**

Libellé servi : **100 / 100 « Écartée »**. **Toutes** portent un motif de cascade explicite
(HARD_EXCLUDE) — aucune exclusion « sans raison ».

Profil zone : **54 A, 21 N** (agricole/naturel — inconstructibles par le zonage, exclusion
légitime), 23 U, 1 AU, 1 sans zone. Familles d'exclusion de l'échantillon :

| Famille (couche cascade) | n | Lecture promoteur |
|---|---:|---|
| `zonage_plu_gpu` (A/N) | 73 | zone non constructible — correct |
| `risques` (PPR rouge) | 36 | inconstructible — correct |
| `emprise_lineaire` / `emprise_routiere` | 13 | parcelle = voirie/linéaire — correct |
| `surface` | 8 | lot trop petit (aucun ≥ 100 m²) — correct |
| `foret_publique` / `parc_national` / `safer` / `ens` | 18 | foncier non acquérable — correct |
| `dpf` (servitude marchepied) | 6 | domaine public fluvial — correct |
| `prescription_plu`, `peb`, `eau`, `osm_faux_positif` | … | contraintes dures — correct |

**Seules 3 parcelles** cumulent *zone U/AU* **et** *SDP résiduelle > 0* — les seules candidates
possibles à une « vraie affaire perdue ». Les trois ont été instruites une à une :

1. `97411000CH0196` (Saint-Denis, UH, 31 m²) — **PPR zone rouge sur 64 %** + « 31 m², rien à
   construire ». Exclusion **correcte**.
2. `97411000IB0044` (Saint-Denis, UM, 62 m²) — **emprise routière** 132 m d'axes (densité 0,78) +
   2 emplacements réservés d'alignement. Exclusion **correcte** (c'est de la voirie).
3. `97416000ER0385` (Saint-Pierre, UD, 1 710 m²) — **foncier public hospitalier** (Groupe
   Hospitalier Sud Réunion), parking de l'hôpital sur 81 %. Non mobilisable. Exclusion **correcte**
   sur le fond ; **réserve de libellé** : le motif de tête servi est `osm_faux_positif` (« parking,
   faux positif géométrique ») alors que le motif honnête serait `foncier_public` / zone d'activité.

> **Vraies affaires écartées à tort : 0 / 100.** L'étage 0 est fiable sur l'échantillon. Les
> 1 710 m² de SDP de la parcelle 3 montrent au passage que le **résiduel se calcule même sur du
> foncier public en service** (même angle mort qu'au §2.1).

---

## 4. Changements de palier entre deux runs — **0 sans raison**

| Transition | Parcelles changeant de palier | Cause |
|---|---:|---|
| `q_v19` → **`q_v20`** (servi) | **3** | 3/3 par **mouvement de `p`** (franchissement de seuil 0,20/0,09). Aucune à `p` constant. |
| `q_v20` → `q_v21` (candidat, non servi) | **746** | **393** copropriétés → Sans signal (règle E-010) + **353** PPR code `i` → Écartée (Saint-Philippe). |

Vérifié en base pour `q_v20→q_v21` : les **746 ont un `p_raw` strictement identique** (aucune dérive
de modèle) ; les **393** sont **toutes `copro = true`** ; les **353** sont **toutes en 97417** et
**toutes exclues par la couche `risques`** de `q_v21_sources`. **Attribution à 100 %**, conforme à
SCORING-COPRO-1. **Aucun changement de palier inexpliqué dans aucune des deux transitions.**

---

## 5. Causes par famille (synthèse)

| Famille | Où | n | Nature |
|---|---|---:|---|
| **F1 — SDP résiduelle nulle en tête** | TOP | 20 | le palier suit `p` (mutation), pas la capacité à bâtir |
| **F2 — Non-constructible / zone fermée, palier maintenu** | TOP | 6 | motif secondaire, pas de rétrogradation |
| **F3 — Écartée logée dans le top-rang** | TOP | 8 | `rang` inclut l'étage 0 → rang d'élite sur une écartée |
| **F1+F2 servies SANS avertissement** | TOP | **13** | `verdict_servi` ignore constructibilité/AU → piège silencieux |
| **G1 — Exclusions de l'étage 0** | BAS | 100 | toutes motivées (zonage A/N, PPR, emprise, foncier public) — **justes** |
| **G2 — Libellé d'exclusion imprécis** | BAS | 1 | hôpital servi comme `osm_faux_positif` au lieu de `foncier_public` |
| **Dérive de run** | runs | 0 | 100 % attribuable (p / copro / PPR-i) |

**Correctif de doctrine suggéré (hors mandat, pour Vic)** : soit (a) servir la SDP résiduelle / un
drapeau « rien à bâtir » dans le palier de tête, soit (b) faire lire `parcel_constructibilite` et
`parcel_au_statut` par `verdict_servi` pour que **toute** parcelle non-constructible porte son motif
— les 13 pièges silencieux disparaissent. Et exclure l'étage 0 du calcul du `rang` (F3).

---

## 6. Limites

- **Sans API tierce par parcelle** je n'ai pas revérifié le réseau (eau/élec/assainissement
  raccordables), la forme fine ni la pente *in situ* : je m'appuie sur les faits déjà calculés par
  LABUSE (cascade pente/emprise, `parcel_terrain`). L'audit vérifie la **cohérence interne** et la
  **pertinence promoteur** des faits servis, pas une contre-expertise terrain.
- `acces_courrier/acces_pm_siren` disent « adresse BAN / SIREN connus », pas « propriétaire
  inconnu » : un privé sans adresse BAN reste joignable via fichiers fonciers.
- Échantillon BAS = 100 tirées (sur 153 283) : « 0 à tort » vaut **sur l'échantillon**, pas une
  preuve d'exhaustivité sur tout le palier.
- Travail sur base Mac `q_v20` ; la prod n'a pas été sondée (fenêtre et consigne lecture seule).

## 7. Reproductibilité (`docs/audit-2026-11/nu-4/D/preuves/`)
- `extract.sql` — extraction des deux dossiers (TOP / BAS) ;
- `top100.csv`, `bas100.csv` — faits bruts par parcelle ;
- `top100_verdict.csv`, `bas100_verdict.csv` — verdict **réellement servi** (`verdict_servi_batch`) ;
- `ANALYSE.txt` — tous les comptages de ce rapport, régénérables.

Rejeu : `psql --csv -v sample=top -f extract.sql` ; verdict via `labuse.verdict_servi` (venv
`~/Desktop/labuse/.venv`, `PYTHONPATH=.../labuse-nu4d/src`, `LABUSE_DATABASE_URL` local).
