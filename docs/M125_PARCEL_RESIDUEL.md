# M125 — BOUCHER LE TROU parcel_residuel (Phase 1 : diagnostic, STOP)

*Branche `feat/m125-parcel-residuel`. Donnée seulement : modèle, features servies, run intouchés.
Mesures : 431 663 parcelles · `parcel_residuel` 253 351 · **manquant 178 312 (41,3 %)**.*

---

## 1. LA CHAÎNE DE CALCUL (qui produit, sur quoi, quand)

**Producteur unique** : `faisabilite/residuel.py` — `compute_residuel()` (`:53`) croise la **capacité
max** du moteur de pré-faisabilité (`faisabilite/db.py:parcel_faisabilite` : zone PLU résolue par
`resolve_zone`, enveloppe = ST_Buffer du contour par le recul séparatif, clippée U/AU et amputée des
ER) avec le **bâti existant** (BD TOPO `bati.stats_batch` + CoSIA `parcel_bati_revele` ; niveaux =
étages/hauteur BD TOPO sinon hypothèse). `sdp_residuelle = max(0, sdp_max − emprise_bâtie × niveaux)`.

**Écriture** : `compute_residuel_batch()` (`:118`) — lancé par `labuse compute-residuel --commune X`
(`cli.py:1188`, one-shot par commune, PAS de cron) et `audit.py:64`. **Le trou est un choix d'écriture,
pas un échec de calcul** : quand `disponible=False`, le batch **DELETE la ligne et n'écrit RIEN**
(`residuel.py:127-129`) — le manquant est **muet par construction**. S'y ajoute une exception avalée
en silence (`:125-126`, `except Exception: continue`).

## 2. LE TABLEAU — CAUSES × VOLUMES × COÛT (classification EXACTE par règle de zone)

Chaque manquant classé par `resolve_zone(zone_lib, commune)` (la règle réelle du moteur) ; le palier
géométrique ventilé par rejeu de `compute_residuel` sur échantillon stratifié (200 U + 40 AU/A/N).

| Cause | Volume | % | La vérité de la SDP | Coût de complétion |
|---|--:|--:|---|---|
| **C1 · Zone NON CONSTRUCTIBLE au règlement** — A 64 702 · N 32 369 · U-éco (habitat interdit) 1 961 · AU fermée/transition 1 653 | **100 685** | 56,5 % | **0 m² — vraie valeur** (aucun droit neuf) | **AUCUNE formule nouvelle** : le moteur répond déjà « non constructible » ; il suffit d'ÉCRIRE la ligne (cause + valeur) au lieu de la supprimer |
| **C2 · A/N Saint-Paul « non résolues »** (11 libellés : A 8 231, N 2 243, Acu 608, Nerl 538…) | **12 510** | 7,0 % | **0 m²** aussi — le YAML calibré de Saint-Paul ne couvre que U/AU, mais A/N y sont sans droits neufs comme partout | Idem C1 — classer « non constructible (A/N hors YAML) », rien à calibrer POUR la SDP |
| **D1 · Zone constructible, refus GÉOMÉTRIQUE** — terrain exigu (~79 % du palier : l'enveloppe après reculs est vide), rédhibitoire ER/PPR (~7 %), transition (~4 %), habitat fin (~9 %) | **~60 260** | 33,8 % | **≈ 0 m² — vraie valeur en l'état** (reculs/servitudes mangent tout) | AUCUNE formule : le moteur calcule déjà l'enveloppe vide ; écrire (cause + valeur) |
| **D2 · STALE recalculable** (constructible=True aujourd'hui, ligne jamais (ré)écrite — 2/200 au sondage) | **~600** | 0,3 % | calculable telle quelle | **Relancer le batch** (chemin existant, zéro code) |
| **A · Hors PLU outillé** — Saint-Philippe RNU 4 162 (le 23/24) + 82 trous GPU | **4 244** | 2,4 % | **réellement inconnaissable** (pas de règle d'urbanisme dématérialisée) | Non calculable POUR UNE RAISON DITE — écrire la cause, jamais un NULL muet |

**Lecture d'ensemble** : ~97 % du « trou » n'est **pas de la donnée manquante** — c'est une **valeur
vraie (0) jamais écrite** parce que le batch ne stocke que les constructibles (son contrat d'origine :
« alimenter le filtre sous-densité », pas nourrir un modèle). Pour le modèle M127, un bin « manquant »
à 38,9 % cache en réalité « pas de droits résiduels » — un signal fort, aujourd'hui dilué.

## 3. LES OPTIONS D'ARBITRAGE (Phase 2)

L'extension proposée (UN chemin, le même : `compute_residuel_batch` étendu, jamais une 2e formule) :
ajouter à `parcel_residuel` une colonne **`cause`** et écrire TOUTES les parcelles :

- **Option 1 (recommandée)** — C1/C2/D1 : `sdp_residuelle_m2 = 0` + cause précise (`zone_non_constructible`,
  `terrain_exigu`, `redhibitoire`…) ; A : `sdp_residuelle_m2 = NULL` + cause `hors_plu` ; D2 : recalcul.
  → le M127 lira un VRAI zéro (bin réel) au lieu de « manquant » sur 174 k parcelles ; manquant résiduel
  ~1 % (hors PLU), avec sa cause.
- **Option 2 (conservatrice)** — tout manquant reste `NULL` mais porte sa cause ; le choix 0-vs-manquant
  se fait à la construction du dataset M127.
  → la table dit la vérité, le modèle décide plus tard ; le bin « manquant » reste à 41 % en attendant.

*Les deux respectent « le doute ne classe pas » : le 0 de C1/D1 n'est pas un doute, c'est la réponse
du moteur. Ta décision fixe aussi ce que `sous_densite`/`pct_potentiel` portent sur ces lignes
(proposé : NULL — seules la cause et la SDP ont un sens hors constructible).*

**STOP — arbitrage attendu : Option 1 ou 2 (ou variante), et le sort des exceptions avalées
(`residuel.py:125` — proposé : compter et logger, jamais avaler).**

---

# PHASES 2-3 — EXÉCUTION (arbitrage Vic : Option 1 + causes lisibles + invariance des filtres)

## Ce qui a été fait

- **Colonne `cause`** (`models.ensure_residuel_cache`) : NULL = ligne CALCULÉE ; sinon le code
  structuré. **Distinction C1/C2/D1 lisible** (exigence #1) : `zone_non_constructible:<zone>` (remap
  du `zone_transition` moteur — nom trompeur émis à l'unique branche constructible_neuf=False),
  `habitat_interdit:<zone>`, `terrain_exigu`, `redhibitoire`, `zone_non_resolue:<lib>`, `hors_plu`,
  `capacite_nulle`, `hauteur_indispo`. Attribution par les MÊMES résolveurs — jamais une 2e formule.
- **Le batch écrit TOUT** (`compute_residuel_batch`) : valeurs pleines si disponible ; sinon cause +
  sdp **0** (vraie valeur) ou **NULL** (hors_plu seul) ; taux/pct/sous_densite NULL hors constructible.
  **Exceptions comptées et loggées, jamais avalées** (`:125` corrigé).
- **Gardes lecteurs vivants** (exigence #2) : app.py `sdp_min`/`sdp_max`/`capacite_min`/`ca_min`
  (seuil 0 possible → flip sinon) + 3 LEFT JOIN d'affichage + `flash/data.py` + `score_e.py` ne
  lisent que `cause IS NULL`. NULL-safe sans garde (prouvé) : nu_pm, etat_sol (COALESCE), sous_densite
  (bool), mode_b/moteurs (`> 0` strict). `cascade/context.residuel_sdp` volontairement NON gardé :
  hors_plu→NULL→UNKNOWN inchangé ; les 0 seront lus au run M128 (voulu).
- **Run île : 178 312 manquants traités en 37,7 min · 0 erreur · 413 stales (D2) recalculées.**

## Le taux AVANT → APRÈS

| | Avant | Après |
|---|--:|--:|
| Parcelles sans ligne | **178 312 (41,3 %)** | **0 (0,00 %)** — dans les 24 communes |
| Lignes calculées (cause NULL) | 253 351 | **253 764** (+413 D2) |
| Lignes à cause (vérité dite) | 0 | **177 899** |
| « Manquant » réel pour le modèle | 41,3 % muet | **hors_plu 4 397 (1,0 %), avec sa cause** |

Familles de cause (mesuré) : `zone_non_constructible` **100 953** (tous sdp=0) · `terrain_exigu`
**50 192** · `zone_non_resolue` **12 566** · `habitat_interdit` **5 645** · `hors_plu` **4 397**
(seuls NULL) · `redhibitoire` **4 145** · `hauteur_indispo` 1.

## Les preuves

1. **Invariance des filtres (exigence #2) — PROUVÉE au chiffre près** : snapshot AVANT de 10 compteurs
   (sous_densite 63 917, sdp_min 0/1/100/300, sdp_max, capacite, etat_sol nu/bâti, nu_pm) ; APRÈS,
   les seuls écarts (+9 à +413) sont **à 100 % les 413 D2 arbitrées** — compteurs recalculés hors-D2 :
   **tous IDENTIQUES à l'avant**. Les 177 899 lignes à cause ne fuient dans AUCUN filtre.
2. **Golden : 0 FAIL** (86 PASS · 33 INDÉTERMINÉ quota env). Rien de servi ne bouge.
3. **Plausibilité** : SDP > surface×4 = **0 ligne** ; suite 1 618 passed (seul failed = flake fuseau
   pré-existant `partners.py:458`, hors mandat, consigné M124).

**Le modèle M127 lira un VRAI zéro (avec sa nuance) sur 173 502 parcelles, et un « manquant » honnête
sur 4 397.** Le bin « manquant » passe de 38,9 % à ~1 %.
