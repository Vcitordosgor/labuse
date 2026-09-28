# COHERENCE-1 — le banc de cohérence et de vérité

**Branche** `audit/coherence-1` · worktree `labuse-coherence` · 28/09/2026 · lecture seule
(le banc n'écrit que sous `scripts/coherence/` et ce dossier). Run servi `q_v11_m137`,
run résiduel servi seq 10, base 431 663 parcelles, 24 communes.

**Le banc est le produit.** `scripts/coherence/` rejoue tout sans navigateur :

```
python -m scripts.coherence.banc --echantillon   # 120 parcelles + 24 communes, ~4,5 min
python -m scripts.coherence.banc --ile           # + recalculs géo des 24 communes, ~6,5 min
python -m scripts.coherence.ile                  # comparaisons SQL 431 663 parcelles, ~8 s
python -m scripts.coherence.distributions        # plausibilité/unités/absences île
python -m scripts.coherence.verite               # oracles externes (réseau), ~25 min
python -m scripts.coherence.aggregats            # compteurs=liste=stats=SQL, prédicat=fiche
python -m scripts.coherence.recompose            # dérivés recomposés indépendamment
python -m scripts.coherence.documents [--copilote]  # PDF pdftotext + digest dry-run + Copilote
python -m scripts.coherence.referentiel          # régénère NOTIONS/LECTEURS/ABSENCES
python -m scripts.coherence.echantillon          # gèle l'échantillon (déjà gelé — no-op)
```

(L'alias `labuse coherence` demandé appartient à COHERENCE-FIX-1 : ce mandat n'a pas le
droit d'écrire dans `src/` — la commande module ci-dessus est l'équivalent exact.)

## Les chiffres

| Quoi | Combien |
|---|---|
| Notions au référentiel (`NOTIONS.csv`) | **286** (165 nombres, 48 couches, 28 classes…) |
| Notions à ≥ 2 lecteurs (matière à incohérence) | **190** |
| Arêtes notion → lecteur (`LECTEURS.csv`) | **653** (169 robinets + 232 lectures fines + déclarations) |
| Phrases d'absence déclarées (`ABSENCES.csv`) | **178** |
| Comparaisons jouées (banc `--ile`, `ECARTS.csv`) | **3 244** |
| Écarts | **283** : 6 FAUX-CLIENT · 251 INCOHÉRENT · 26 TOLÉRABLE |
| Comparaisons SQL île entière (`ECARTS-ILE.csv`) | 8 notions × 431 663 — **2 divergent** (SDP 98 004 · sous-densité 26 016), 6 à zéro |
| Distributions île (`DISTRIBUTIONS.csv`) | 17 colonnes — 2 alarmes `pct_hors_bornes` (le « 999 ») |
| Oracles externes (`VERITE.csv`) | **183 lignes · 157 VRAI · 19 FAUX** · 7 skips dits |
| Agrégats (`ECARTS-AGGREGATS.csv`) | 13 vérifications — compteurs ✗, prédicat=fiche ✓ 20/20, bande liste=fiche ✓ 15/15 |
| Recompositions (`ECARTS-RECOMPOSE.csv`) | **55, 0 écart** (les dérivés tiennent) |
| Documents + Copilote (`ECARTS-DOCUMENTS.csv`) | **44, 0 écart** (Dossier=miroir ✓, Copilote 10/10 ✓, digest dry-run ✓) |

## FAUX-CLIENT — un client lit une valeur fausse aujourd'hui

**1. Fiche commune, « part en aléa mouvement de terrain » : 23 communes sur 24 servent
0,0–3,4 % quand la vérité est 87,9–100 %.** Le cas fondateur du mandat, mesuré : le banc
recalcule la part depuis `spatial_layers` (même définition que la couche carte) pour les
24 communes — Bras-Panon 0,1→100, Saint-Paul 0,1→90,3, Saint-Benoît 0,1→100…
Saint-Denis (0,4 vs 0,1) est la seule cohérente : la couche y est quasi absente.
**Cause** : `commune_contexte_cache` calculé le 25/09, AVANT le merge SOURCES-FIX-2 qui a
changé la définition (inventaire BDMvt `kind=mvt` → aléa réglementaire
`georisque_alea/mouvement_terrain`) ; le job nocturne n'est pas repassé depuis. La preuve
par contraste : `ppr_pct` (définition inchangée) = **0 écart sur 24**. Une définition qui
change sans régénérer le cache = tous les écrans mentent ensemble.
→ correctif : régénérer le cache après toute bascule/merge qui touche une notion (et le
banc au CRON l'attrapera à J+1).

**2. « % de densité consommée » : la fiche affiche « 999 % ».** `residuel.py:206-207`
plafonne `min(999, 100×bâti/max)` et le front l'affiche tel quel
(`constructibilite.tsx:45`, `moteurs.tsx:441`) : **2 304 parcelles à exactement 999**,
106 514 au-dessus de 100 (`DISTRIBUTIONS.csv`, alarme `pct_hors_bornes`). Un plafond
technique servi comme un pourcentage réel. Pire, la même ligne fait `else 0.0` : quand
l'emprise max est inconnue, le client lit « 0 % consommé » — un zéro à la place d'une
absence.

**3. La carte contredit la fiche sur la SDP restante : 98 004 parcelles (23 % de l'île).**
`mvt_parcels` (tuiles servies : tooltips, couche Densifier) porte un état résiduel
antérieur à la bascule du run seq 10 (25/09) ; fiche = vue `parcel_residuel` = Copilote
sont cohérents entre eux (témoin AB1117 : fiche/vue/copilote 27 m², tuile 0). Idem
`sous_densite` : 26 016 parcelles. Chiffre l'alerte « tuiles figées, rebuild requis »
d'ALGO-AUDIT-1. Les 6 lignes FAUX-CLIENT d'`ECARTS.csv` (« ∅ contre 0 ») sont cette même
famille vue de l'échantillon.

**4. Le panneau Filtres ne compte pas comme la page Stats.** `/filtre.compte` <
`/stats.total` systématiquement : Saint-Paul 51 005 vs 51 129 (SQL indépendant : 51 129) ;
`flags=ravine` : compte 13 970 vs 13 972 idus **dans la même réponse** ; la ventilation
par tiers de `/filtre` somme à 40 405 (les tiers `declasse_*` sont partiellement repliés).
Trois périmètres pour « le nombre de parcelles » du même écran.

**5. Zéros à la place d'absences, côté front** (scan statique, `notes/ABSENCES-FRONT.md`) :
`MonSecteur.tsx:71` (médiane nulle → « 0 €/m² »), `ProfilAltimetrique.tsx:70-75`
(`?? 0` ×5 → « 0 m »), `Licences.tsx:27` (« 0,00 € »), `ResultsSection.tsx:107` (cluster),
et côté back `moteurs.py:600` (part habitat ZAN : source NULL → « 0 % »),
`fiche_couches2.py:28` (`coverage or 0`), `financier_bilan.py:108-124` (`or 0` en série).

**6. « Habitants » de la fiche commune : 10 communes sur 24 à 5–8 % sous la population
légale publiée** (geo.api.gouv, ex. Sainte-Marie 34 344 vs 37 093). La fiche lit Sudocuh
au 31/12/2024 et n'affiche pas le millésime — vrai hier, faux aujourd'hui, sans date pour
le dire.

## INCOHÉRENT — deux écrans, deux valeurs (le chiffre peut être bon quelque part)

- **Cache fiche commune > 48 h sur 24/24 communes** au moment du banc (« rafraîchis chaque
  nuit » du pied de page était faux) — même cause que le n° 1.
- **Emprise bâtie** : fiche ≠ `p_model_bati` sur 68/120 (la fiche clippe le bâti à la
  parcelle et arrondit ; la table porte le brut — DE0231 : 276 vs 296 m²). À trancher par
  une définition unique.
- **Copropriété** : fiche `coproprietes=[]` alors que `p_model_ext_copro.copro_rnic=true`
  (3/120, ex. 97411000DT0159) — la fiche ne lit pas le RNIC là où le modèle du scoring le lit.
- **Vigilances 50 pas / fiche vs run** : la fiche calcule ses flags en live quand
  `parcel_flags` porte l'état du run (5/120) — un rejeu de cascade qui a bougé depuis la
  bascule.
- Oracles : **zone N (LABUSE) vs U (GPU)** sur 97403000AM0515 ; **5 parcelles de
  Saint-André « U » là où le GPU ne rend aucun zonage au point** (partition GPU à
  instruire) ; CatNat Saint-Joseph 20 vs 21 (un arrêté de retard d'ingestion) ;
  2 surfaces où contenance cadastrale et aire géométrique divergent > 5 % (parcelles
  < 100 m²).

## ÉTIQUETTE — bon chiffre, mauvais libellé

- **« Secteur » multi-périmètres, jamais nommé côte à côte** (mesuré 85/120) : fiche
  `dvf_parcelle.secteur` (fenêtre 2021-2025) vs Mon secteur (rayon adaptatif
  500→1500 m, affiché dans l'outil) vs comparateur (commune entière, tooltip qui « avoue »).
  BZ1065 maison : 3 494 vs 3 821 €/m² — deux vrais chiffres, aucun rayon dans le libellé
  de la fiche.
- **Taxe d'aménagement 20 % vs 3 %** (Les Trois-Bassins) : la parcelle est en secteur
  majoré (dit dans son millésime), la fiche commune affiche le taux de droit commun sans
  « hors secteurs majorés ».
- **Azimut du bâti badgé « Estimé »** (Prospection solaire) alors que l'orientation vient
  du bâti mesuré ; **millésimes en dur** : « FLAIR/CoSIA 2025 », « OLL 2024 », « ANCT 2024 »
  (`notes/SEMANTIQUE.md`).
- **Trois idiomes d'absence** : « — » (format.ts), « n.c. » (SIRENE), « non chiffré »
  (PDF financier) ; compteurs nuls « 0 » dans AdminView mais « — » dans Radar.
- Le PDF Dossier écrit la zone « U » où la fiche dit « Uh » (famille vs libellé).

## TOLÉRABLE (arrondi documenté)

26 lignes : surfaces fiche arrondies à l'entier vs float base (≤ 1 %), prix médians ±1 €,
PDF qui arrondit la pente à une décimale.

## La vérité (lot C) — 157 VRAI / 19 FAUX sur 176 valeurs comparées

Oracles joués : GPU (zone au centroïde, 40), cadastre PCI (contenance, 40), population
légale (24), GASPAR CatNat (24), DVF brut Etalab (3 611 lignes 97411/2024 : présence et
valeurs OK), alti IGN (7 témoins, plage du profil ✓), SIRENE (8 dénominations PM ✓),
taux TA (2 délibérations vérifiées en recette ✓), 30 règles PLU calibrées ouvertes au
PDF direct des annexes GPU à la page citée par la fiche : **29/30 les nombres s'y lisent**
(1 lien sans page, dit). Le fichier DHUP SRU a changé de format de colonnes (skip dit). Skips DITS : PPR/aléas (pas de GetFeatureInfo public stable — couvert
par le lot B), CoSIA raster, Sitadel brut, Filosofi, PDF Kelfoncier CK0678 (introuvable
sur le poste). Détail : `VERITE.csv`.

## Ce que le banc n'a PAS trouvé (et qui rassure)

- Île entière : surface, zone (lib et famille), tier, flags — **0 divergence** sur
  431 663 entre tuiles et tables.
- Les recompositions indépendantes (55) passent toutes : parts d'aléa = aire
  d'intersection/aire (par sous-type), pct_residuel = 100−pct_consomme, déficit SRU,
  vacance, marge de surélévation.
- Dossier PDF = miroir de la fiche (19/19), Copilote FICHE cite les chiffres exacts avec
  leur id de registre (10/10), le digest dry-run ne fabrique rien.
- Déterminisme : fiche et contexte commune rendent la même chose à deux appels.

## Doctrine appliquée

1. **Cohérent** — lots B/E (banc multi-lecteurs, compteurs, île entière).
2. **Vrai** — lot C (oracles) : cohérent-mais-faux attrapé (aléa mvt : tous les écrans du
   contexte commune disaient la même erreur ; habitants : tous à jour du même retard).
3. **Plausible** — lot D (999 %, faîtage 53 401 m en base — badgé par DONNEES-FIX-1 mais
   la valeur brute reste servie aux distributions).
4. **Honnête sur l'absence** — ABSENCES.csv (178 phrases déclarées) vs les `?? 0`/`or 0`
   mesurés (lot D + scan front).

## COHERENCE-FIX-1 (matière, dans l'ordre)

1. **Régénérer ce qui est périmé** (une commande, pas du code) : cache fiche commune
   (24 communes) + tuiles `mvt_parcels` (98 004 parcelles) — puis rejouer le banc pour
   constater ~70 % des écarts éteints.
2. **Corriger à la source** : 999/0 de `residuel.py:206-207` (servir « ≥ 100 % » et une
   vraie absence), compte/total/tiers du filtre, zéros-pour-absence listés (front + back),
   millésime des Habitants affiché, copro RNIC dans la fiche.
3. **Verrou V6** : le banc sur 10 témoins dans pytest — les tables de `checks_parcelle`/
   `checks_commune` sont déjà data-driven, il suffit d'un test qui appelle
   `passe_parcelles` sur les témoins et échoue sur tout écart non-TOLÉRABLE.
4. **Job nocturne** `coherence --ile` au registre CRON + onglet « Cohérence » page Données
   + cloche au premier écart nouveau.
5. **Golden par témoin** + règle de mandat (toute nouvelle donnée déclarée au registre
   avec sa tolérance — le référentiel est DÉRIVÉ, il suivra tout seul).

## Fichiers

`NOTIONS.csv` · `LECTEURS.csv` · `ABSENCES.csv` · `ECHANTILLON.csv` (120 gelées) ·
`ECARTS.csv` · `ECARTS-ILE.csv` · `ECARTS-AGGREGATS.csv` · `ECARTS-RECOMPOSE.csv` ·
`ECARTS-DOCUMENTS.csv` · `DISTRIBUTIONS.csv` · `VERITE.csv` ·
`notes/` (LECTEURS-ACCES, ABSENCES-FRONT, BALAYAGE-STATIQUE, SEMANTIQUE).

Notes de banc (pièges rejouables) : l'API limite le débit (429 → retry intégré) ; la
tuile z14 ne porte pas l'attribut `flags` (ABSENT, pas False) ; `parcelle_id` du scoring
est l'idu ; `plu_reglement_extrait.source_url` pointe le PACK zip GPU ; le témoin
AC0198 du mandat (« Sainte-Suzanne ») est `97418000AC0198`, commune=Sainte-Marie en base
(libellé historique des mandats précédents).
