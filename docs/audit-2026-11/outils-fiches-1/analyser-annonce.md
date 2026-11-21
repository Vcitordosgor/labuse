# Estimer un bien

<!-- CCM -->
> **Comment ça marche**
> 1. On donne une adresse (→ parcelle) ou un lien d'annonce.
> 2. L'outil retrouve les ventes comparables du secteur et les traits du bien.
> 3. Il en déduit un prix au m², une fourchette et une fiabilité ; pour un lien, l'écart au marché.
> 4. Il rend une estimation indicative et les ventes qui la fondent.
> 5. Le « prix estimé » est en fait la médiane du secteur ; prudence sur les grands terrains.

**Captures — l'outil en action**

![Estimer un bien — Estimer un bien sur DH0076 (Saint-Paul, U2b) — prix estimé 6 275 €/m² (5 508–7 168), fiabilité Élevée sur 79 ventes comparables ; lecture foncière 21 425 000 €.](img/analyser-annonce.png)
*Estimer un bien sur DH0076 (Saint-Paul, U2b) — prix estimé 6 275 €/m² (5 508–7 168), fiabilité Élevée sur 79 ventes comparables ; lecture foncière 21 425 000 €.*

<!-- CCM -->

Clé interne : `analyser-annonce` (num N1) · composant : `frontend/src/components/outils/AnalyserAnnonce.tsx` · endpoint principal : **`POST /radar/annonce/estimation3/{idu}`** (point unique ESTIMER-3) · PDF parcelle `/analyse-annonce/{idu}.pdf` (même point) · chemin lien (Radar seulement) : `POST /radar/annonce/analyser`, PDF `/analyse-annonce.pdf?url=…`.

> Note de nommage : **`src/labuse/pige/estimer3.py` EXISTE** et c'est désormais le **cœur** du calcul (refonte ESTIMER-3 + ESTIMER-ECRAN-1, mergée le 11/11/2026). L'ancienne fiche disait « inexistant » : périmé. L'orchestration servie (écran == PDF == document) vit dans `estimer3.rapport3` ; l'endpoint `radar_annonce_estimation3` (`api.py` l. 2098) l'appelle ; l'adaptateur PDF `_est_bloc_depuis_estimer3` (`api.py` l. 2427) re-façonne le MÊME rapport sans recalculer. `marche_service.comparateur_bien/terrain` reste utilisé **en repli** (secteur) et pour le terrain nu ; `estimation_prix.py` ne fait toujours que la mise en forme.

L'outil n'a plus deux chemins d'entrée. Il a **UN SEUL écran, parcelle uniquement** (`AnalyserAnnonce.tsx` l. 648-665) : boîte `EntreeParcelle` (option A) puis tout se construit dessous. Le **chemin lien Leboncoin** n'est plus une entrée de l'écran : il reste atteignable **depuis le Radar** (« Estimer ce bien → », `annonceLienPrefill`, l. 594-609) et rend un rapport COMMUNE inchangé (SSRF toujours fermé — le serveur ne fetch jamais le lien).

---

## 1. À quoi il sert, et pour qui

Pour un prospecteur/agent qui veut jauger le prix d'un bien à partir d'une **parcelle** (adresse ou clic carte). ESTIMER-3 part désormais des ventes de biens qui **RESSEMBLENT** au bien (même type, surface/terrain proches, distance, ancienneté — pondération par ressemblance), et non de toutes les ventes du secteur. L'estimation **se resserre** à chaque réponse ; **chaque question a dû prouver son gain** au banc no-leak (sinon elle n'est pas posée) ; **la précision servie est mesurée** par commune × type × niveau. Ce n'est **pas** une expertise : c'est un repère de marché honnête sur des comparables, assorti d'une fiabilité mesurée.

## 2. Le parcours

### L'écran unique (parcelle)
`AnalyserAnnonce.tsx` l. 648. Boîte **`EntreeParcelle`** (option A : adresse en gras + « IDU · zone · surface » + ✕ pour changer). Dès qu'une parcelle est choisie, `<Estimer3>` (l. 357) lit `POST /radar/annonce/estimation3/{idu}` et affiche, dans l'ordre :
- **« Dernière vente de ce bien »** (`DerniereVente`, l. 97) — juste sous la boîte, **jamais** dans le calcul : « mois/année · surface · prix ». Absente si la parcelle n'a aucune vente DVF.
- **« Ce que LABUSE a mesuré »** (`Mesures`, l. 110) — en puces, UNIQUEMENT ce qui est connu : type, terrain, bâti au sol, niveaux, piscine, pente (la zone vit dans la boîte).
- **La question UNIQUE — surface habitable** (`Question`, l. 296) : pré-remplie par l'estimation LABUSE (badge **estimée**, formule LiDAR écrite dessous), saisie au clavier (`inputMode=numeric`, commise au blur/Entrée, badge **saisie** dès qu'on la change). Une **vente DVF** du bien la rend « connue » sans rien taper. Pour un **appartement** s'ajoute le **nombre de pièces** (chips 2·3·4·5·6+). Pour un **terrain nu**, aucune question.
- **La valeur estimée** (`ValeurEstimee`, l. 149) : montant en gros + badge **Fiabilité** (Élevée/Moyenne/Limitée) + **jauge à deux bandes** servies telles quelles par l'API : « 1 fois sur 2 » (écart médian) et « 3 fois sur 4 » (Q3), chacune avec ses deux bornes en euros (`Jauge`, l. 132). Dessous : la **méthode servie** (« Biens semblables » / « Prix du secteur », suivant `methode_prix`) + « mesuré sur les ventes réelles de [type] à [commune] ».
- **Les ventes retenues** (`VentesRetenues`, l. 221) : date, surface·terrain, prix, distance ; chaque ligne se **décoche** → l'API **recalcule** (`ecartees`).
- **« En vente en ce moment · Radar »** (`RadarEnVente`, l. 270) : les 5 biens similaires les plus proches (commune + distance), s'il y en a ; sinon le bloc n'apparaît pas.
- La ligne « LABUSE ne connaît ni l'état du bien ni sa vue : ce prix est un repère de marché, pas une expertise. » et l'**export PDF** (l. 44, même point que Docs).

### Chemin lien (rapport COMMUNE) — depuis le Radar seulement
`RapportAnnonce` (l. 440) : « Ce que dit l'annonce » (champs présents seulement), « Prix face au marché » (écart % au repère du type + lecture foncière terrain × terrain nu, fiabilité « Limitée » gravée en dur l. 510), bloc « La commune ». Un bien absent du Radar → phrase d'erreur FR (`messageErreur`, l. 573), aucun fetch Leboncoin.

## 3. Les données lues

| Source (catalogue) | Table(s) SQL réellement lues | Millésime servi | Cadence |
|---|---|---|---|
| **DVF / valeurs foncières** | `dvf_mutations_parcelle` (pool de comparables SEMBLABLES mono-parcelle, `estimer3._POOL_SQL` l. 118) ; `dvf_mutation_detail` (nombre de pièces des comparables, pré-remplissage pièces) ; `dvf_mutations` (repli secteur `comparateur_bien`, terrain nu `comparateur_terrain`) ; `dvf_mutations_histo` (ventes 2014-2020, dernière vente) | géo-DVF Etalab — base locale arrêtée au 31/12/2025 | semestriel |
| **`estimer3_precision`** (précision MESURÉE) | `estimer3.charge_precision` l. 274 : écart médian + Q3 + part ±20 % + **méthode gagnante** (secteur / semblable) par (type, commune, niveau d'information) ; repli commune→île→bande prudente | écrite chaque nuit par le job **`estimer-banc-precision`** (`banc_estimer.calcule_niveaux`/`persiste3`) | quotidien (job de nuit) |
| **Radar (pige d'annonces)** | `pige_biens` / `pige_faits` (biens similaires EN VENTE, `estimer3.radar_semblables` l. 525) ; `vendue_ecart_prix` (écart affiché/vendu, servi seulement si ≥ 20 annonces rattachées à une vente) | collecte manuelle | quotidien (statut `manuel`) |
| piscine (couche détectée) | `piscines` (photo aérienne / CoSIA, île entière — `_piscine_mesuree` l. 218) | couche servie | — |
| pente / niveaux / emprise | `parcel_terrain` (pente RGE ALTI), hauteur LiDAR (`_niveaux_lidar_parcelle`), emprise BD TOPO (`_emprise_bati_fiche_m2`) | run servi | selon run |
| PLU / zonage (tuile zone) | `faisabilite.potentiel_batir` (`zone_lib`) | run PLU servi | selon run |

**Important** : rien ne vient de Leboncoin en direct (fermeture SSRF, le serveur n'appelle jamais le lien). La seule donnée d'annonce provient du Radar.

## 4. Les calculs — la mécanique ESTIMER-3

### 4a. Nature du bien (quelle méthode ?)
`estimer3.rapport3` (l. 647) puis `estimation_semblable` (l. 342) décident : **terrain nu** (dernière vente DVF = terrain, ou sans vente parcelle nue) → repère de secteur ESTIMER-2 (§4e) ; **copropriété / appartement** (flag `copro` ou vente typée appartement) → comparateur appartements ; **maison** sinon (ou type dominant du secteur si aucune vente typée).

### 4b. €/m² — comparables SEMBLABLES (pondérée par ressemblance)
`estimer3.eur_m2_semblable` (l. 183) : €/m² **médiane PONDÉRÉE par la ressemblance** des ventes du même type. Chaque comparable pèse selon sa **distance** (gaussien), son écart de **surface habitable** (laplacien — **seulement si la surface est connue** : saisie ou vente DVF), pour la **maison** son écart de **taille de terrain** (laplacien), son **ancienneté** (demi-vie), et son écart de **nombre de pièces** (laplacien — **uniquement pour l'appartement**). Échelles non inventées (`POIDS` l. 45, issues d'ESTIMER-PRECISION-1 ; `H_PIECES=0,8` réglé au banc ESTIMER-3). Rayon **adaptatif** 500→1000→1500 m jusqu'à 8 ventes (`_selection_rayon` l. 168), sinon repli commune.

### 4c. La MEILLEURE des deux méthodes, cellule par cellule
Au-dessus de 8 ventes semblables, l'outil calcule **toujours** la médiane pondérée (semblable = ESTIMER-3) ET la médiane simple du secteur (secteur = ESTIMER-2), et **sert celle que le banc a désignée** comme la plus précise pour cette (commune, type, niveau) — colonne `methode` de `estimer3_precision`, lue dans `charge_precision`, appliquée l. 415 (`med = med_sect if methode=="secteur" else med_sembl`). Le libellé de l'écran **suit la méthode réellement servie** (« Biens semblables » / « Prix du secteur », `AnalyserAnnonce.tsx` l. 152). Mesuré au banc (COMPTE-RENDU §verdict) : **sans saisie, « semblables » ne bat pas le secteur** (maison 30,3 % contre 30,3 %) → on sert le secteur ; **surface connue, « semblables » gagne** (maison 25,3 %→24,5 % ; appartement 16,4 %→15,4 %) → on la sert. ESTIMER-3 **n'est jamais pire** qu'ESTIMER-2.

### 4d. Repli secteur
Quand il reste **moins de 8** ventes semblables (commune/type rare), l'outil **replie sur le prix de secteur d'ESTIMER-2** (`comparateur_bien`) et **le dit** (`repli_secteur: true`, `methode_prix: "repli_secteur"`, `repli_note` servie — `estimer3.py` l. 418-426).

### 4e. Terrain nu
Branche terrain de `rapport3` (l. 669) → `estimation_annonce` (ESTIMER-2, repère de secteur terrain nu `comparateur_terrain`, rayon adaptatif). **Aucune question** (la viabilisation n'est pas mesurable). Les deux bandes sortent du même central ± écart médian / Q3 mesurés.

### 4f. Précision MESURÉE par (type, commune, niveau)
`charge_precision` (l. 274) lit `estimer3_precision` : **deux percentiles** de l'écart |estimé − réel| — l'**écart MÉDIAN** (`precision_pct`, « 1 fois sur 2 », c'est lui qui se resserre) et le **Q3** (`precision_q3_pct`, « 3 fois sur 4 », bande prudente), tous deux servis en euros autour du central (`estimation_semblable` l. 439-450). Repli commune→île→bande prudente (`_BANDE_REPLI` l. 269, **jamais un 500**). Fiabilité (`_fiabilite_mot` l. 299, comme ESTIMER-2) : « Élevée » si écart médian < 15 % & n ≥ 15 ; « Moyenne » si < 25 % & n ≥ 8 ; sinon « Limitée ».

### 4g. DÉFAUT A — surface inconnue + Q3 > 50 % → total masqué
`estimation_semblable` l. 459 : si la surface habitable **n'est pas connue** (ni saisie, ni vente DVF — estimée au LiDAR) **et** que le Q3 dépasse ± `SEUIL_Q3_MASQUE` = 50 %, l'API **ne sert plus de valeur totale** (`total_masque=True`, `valeur_eur=null`). L'écran affiche le **prix au m² du secteur + sa fourchette** (`eur_m2`, `eur_m2_bas`–`eur_m2_haut`) et **invite à saisir la surface** (`AnalyserAnnonce.tsx` l. 164-180). Dès la surface saisie, le masque tombe.

### 4h. DÉFAUT B — plus aucune valeur de terrain sur un bien BÂTI
`estimer3.py` l. 463 (commentaire) + `AnalyserAnnonce.tsx` l. 158 : sur un bien **bâti**, **aucune valeur de terrain n'est affichée** (ni bandeau, ni bloc). Mesuré no-leak sur 2 060 maisons (`mesure_plancher.py`) : retenir la valeur du terrain comme plancher **dégrade** la précision des cas concernés (terrain > bâti, 28,6 % des maisons : écart médian 29,7 %→45,2 %). La fiabilité reste celle du banc (jamais rabaissée à cause du terrain). La valeur de terrain **reste servie pour les terrains nus** (branche terrain, §4e).

## 5. Chaque chiffre affiché (écran parcelle)

| Libellé à l'écran | D'où il vient | Sourcé / Estimé |
|---|---|---|
| Dernière vente du bien | `rapport3.derniere_vente` (DVF, hors calcul) | sourcé (DVF) |
| « Ce que LABUSE a mesuré » (puces) | `mesures{}` : terrain (contenance), bâti au sol (BD TOPO), niveaux (LiDAR), piscine (`piscines`), pente (RGE ALTI), zone (PLU) | sourcé (mesures) |
| Surface habitable (champ) | `surface_hab_detail` : badge **connue** (vente DVF) / **estimée** (emprise×niveaux×ratio LiDAR) / **saisie** | sourcé si DVF/saisie ; estimé si LiDAR |
| Nombre de pièces (appart.) | pré-rempli de la dernière vente DVF (`pieces_prerempli`) | sourcé (DVF) |
| **Valeur estimée (€)** | `estimation.valeur_eur` = surface_utilisée × €/m² (semblable ou secteur, la meilleure mesurée) | **estimé** |
| « 1 fois sur 2 » (bandes €) | `valeur_basse`/`valeur_haute` = central ± `precision_pct` (écart MÉDIAN mesuré) | estimé |
| « 3 fois sur 4 » (bandes €) | `valeur_basse_q3`/`valeur_haute_q3` = central ± `precision_q3_pct` (Q3 mesuré) | estimé |
| Prix au m² (si total masqué) | `eur_m2`, `eur_m2_bas`–`eur_m2_haut` (q1–q3 €/m²) | estimé |
| Méthode servie | `methode_prix` → « Biens semblables » / « Prix du secteur » / repli secteur | — (métadonnée) |
| Fiabilité (badge) | `fiabilite_mot` ← écart médian mesuré + n | estimé (mesuré au banc) |
| Ventes retenues (lignes) | `ventes_retenues[]` — ventes DVF réelles, décochables (recalcul `ecartees`) | sourcé (lignes DVF) |
| Radar « En vente » | `radar.biens[]` (pige, 5 plus proches, commune + distance) | sourcé (annonces relevées) |

## 6. Les limites

- **Ce n'est pas un total à bâtir** : repère de marché du secteur, pas une expertise (écrit à l'écran).
- **Maison : précision plancher élevée**. Sur l'échantillon no-leak 1 500 ventes, l'écart médian maison **sans saisie = 30,3 %** et **surface connue = 24,5 %** ; sur témoin **BZ1065** (Saint-Denis), la précision servie est **± 28 %** médian / **56–60 %** Q3 et la fiabilité ressort « Limitée » (Saint-Denis est la commune la plus dispersée, c'est là que le **secteur** bat les semblables). Honnête, mais un chiffre à ± 28 % reste large.
- **DÉFAUT A — total masqué** : sans surface connue et Q3 > 50 %, **aucune valeur totale** n'est servie (on sert le €/m² + fourchette + invite). Mesuré : BZ1065 sans saisie masque le total (eur_m2 3 684, 2 533–4 722 €/m²) ; avec 140 m² saisis, la valeur revient (529 000 €).
- **DÉFAUT B — terrain non valorisé sur bâti** : voir §4h. Résiduel : voir §10.3.
- **Terrain nu : valeur indicative = contenance ENTIÈRE × €/m² de lot** (limite résiduelle, §10.3) — témoin AK0804 : 27 862 m² × 278 = **7,7 M€** sur 2,8 ha.
- **Chemin lien** : fiabilité TOUJOURS « Limitée », dépend entièrement du Radar (collecte `manuel`), lat/lng = centroïde de quartier.
- **Écart affiché/vendu (Radar)** : **non servi sur la base locale** (0 annonce rattachée à une vente DVF, seuil 20) ; l'outil l'écrit plutôt que d'inventer un chiffre. S'affichera quand `cycle.matcher_dvf` aura peuplé `vendue_ecart_prix` en prod.

## 7. Les tests

- `tests/test_estimer3.py` : **18 verts, 0 ignoré** (pur + canary + réel) — pondération par ressemblance, questions prouvées par type, **meilleure des deux méthodes**, écartement qui recalcule, précision par niveau mesurée, Radar, repli bande, DÉFAUT A (total masqué sur AW1367), DÉFAUT B (terrain dominant). L'**endpoint POST** est exercé pour de vrai (conftest redirige la session vers la base réelle).
- `tests/coherence_ecrans/test_temoins.py::test_estimer3_ecran_egale_document` : sur les 12 témoins, `rapport3(...).estimation.valeur_eur` == la valeur **imprimée** dans le document, à l'euro. **0 écart**.
- `banc_estimer` : canary du banc étendu + job de nuit `estimer-banc-precision` verts.
- `mesure.py` / `mesure_plancher.py` (`docs/audit-2026-11/estimer-3/`) : prototypes no-leak de mesure des gains (surface, pièces, piscine) et du plancher terrain (DÉFAUT B).
- Front : `tsc -b` 0, `vitest` 326 verts.

**Non vérifié par les tests** : la **justesse marchande** absolue du €/m² hors échantillon (c'est le rôle du banc de précision, pas d'un test unitaire) ; le bon sens de la valeur indicative d'un très grand terrain nu (§10.3).

## 8. Les documents liés (PDF, exports)

Le PDF parcelle `/analyse-annonce/{idu}.pdf` lit son estimation du **MÊME point que l'écran** (`estimer3.rapport3` via l'adaptateur `_est_bloc_depuis_estimer3`, `api.py` l. 2427) — « un seul prix partout », 0 écart (banc `test_estimer3_ecran_egale_document`). La surface saisie voyage de l'écran au PDF (`docAnalyseAnnonceUrl`). Le PDF se comporte comme l'écran sur DÉFAUT A (pas de total imprimé si masqué, €/m² + fourchette). PDF lien `/analyse-annonce.pdf?url=…` inchangé.

## 9. Témoins rejoués (sorties RÉELLES de l'endpoint estimation3)

`POST /radar/annonce/estimation3/{idu}` sur `http://127.0.0.1:7280`, le 2026-11-11. Chiffres bruts copiés des réponses JSON.

**97411000BZ1065 (Saint-Denis) — maison.** POST `{}` (sans saisie) :
`type_bien=maison`, `methode_prix=semblable`, `total_masque=true`, `surface_connue=false`, `eur_m2=3684`, `eur_m2_bas=2533`, `eur_m2_haut=4722`, `valeur_eur=null` (masqué), `precision_pct=28`, `precision_q3_pct=60`, `pct_20_mesure=35`, `fiabilite_mot=Limitée`, `precision_perimetre=commune`, `n_comparables=33`, `radius_m=500`, `periode=[2022,2025]`. Mesures : terrain 1 567 m², bâti 193 m² au sol, 1 niveau, pente 25 %, zone Uh, pas de piscine, surface habitable estimée 95 m². Questions : surface_hab (pré-remplie 95). — Illustre **DÉFAUT A** : sans surface, le total est masqué, on sert le prix au m² + invite.
→ **Avec surface 140 m²** (`{"surface_hab":140}`) : `total_masque=false`, `surface_connue=true`, `surface_source=saisie`, `methode_prix=secteur` (Saint-Denis : le secteur bat les semblables à ce niveau), `eur_m2=3778`, `valeur_eur=529000`, bandes médian **381 000–677 000 €** (« 1 fois sur 2 »), bandes Q3 **233 000–825 000 €** (« 3 fois sur 4 »), `precision_pct=28`, `precision_q3_pct=56`, `fiabilite_mot=Limitée`.
→ **Écarter une vente** (`ecartees:["2025-1270532"]`, surface 140) : `n_comparables` passe de 33 à **32**, la vente est servie `ecartee:true` (jamais une disparition muette), valeur recalculée (529 000 €, méthode secteur → stable).

**97409000AK0804 (Saint-André) — terrain nu.** POST `{}` :
`type_bien=terrain`, `methode_prix=secteur`, `eur_m2=278`, `valeur_eur=7746000`, `surface_utilisee_m2=27862`, bandes médian **5 035 000–10 457 000 €** (= bandes Q3, `precision_pct=precision_q3_pct=35`), `fiabilite_mot=Limitée`, `n_comparables=26`, `repli_secteur=false`. `questions=[]` (aucune — viabilisation non mesurable), `note_terrain` servie. Mesures : terrain 27 862 m², pente 6 %, zone UB. — **Limite résiduelle §10.3** : `valeur_eur` = contenance entière 27 862 m² × 278 €/m² = 7,7 M€ sur 2,8 ha, un « ordre de grandeur » non marchand.

**97415000DH0076 (Saint-Pierre) — copropriété / appartement.** POST `{}` :
`type_bien=appartement`, `methode_prix=semblable`, `surface_connue=true` (surface de la vente DVF 2024, 61 m²), `surface_source=vente DVF`, `eur_m2=6438`, `valeur_eur=393000`, bandes médian **349 000–436 000 €**, bandes Q3 **298 000–487 000 €**, `precision_pct=11`, `precision_q3_pct=24`, `pct_20_mesure=69`, `fiabilite_mot=Élevée`, `n_comparables=72`, `radius_m=500`. Questions : surface_hab (pré-remplie 61) **et pièces** (pré-remplies 4, dernière vente DVF).
→ **Avec pièces = 3** (`{"pieces":3}`) : `niveau_info=surface_pieces`, `methode_prix=semblable`, `eur_m2=6275`, `valeur_eur=383000`, `precision_pct=11`, `precision_q3_pct=24`, `fiabilite_mot=Élevée`, `n_comparables=72` — les pièces resserrent légèrement l'estimation de l'appartement (gain mesuré, question posée pour l'appartement seulement).

## 10. Tes doutes

1. **(CORRIGÉ) « Prix estimé au m² » = médiane de secteur qui écrase la pondération.** L'ancien défaut grave est traité : ESTIMER-3 calcule les **deux** médianes (semblable pondérée ET secteur simple) et **sert la meilleure des deux mesurée au banc** par (commune, type, niveau) ; le libellé de l'écran **suit la méthode réellement servie** (« Biens semblables » / « Prix du secteur »). Mesuré sur les témoins : BZ1065 surface connue sert « secteur » (Saint-Denis est dispersé), DH0076 sert « semblable ». Plus de divergence entre le libellé et la mécanique.
2. **(CORRIGÉ) Fiabilité maison presque toujours « Limitée ».** La précision reste mesurée et honnête (BZ1065 ± 28 % Limitée), mais ce n'est plus caché : la jauge **à deux bandes** expose « 1 fois sur 2 » et « 3 fois sur 4 » en euros, la méthode servie est nommée, et **DÉFAUT A** refuse carrément un total quand la surface est inconnue et le Q3 > 50 % (invite à saisir). L'utilisateur voit l'incertitude plutôt qu'un faux chiffre précis.
3. **(RÉSIDUEL — mesuré) Terrain nu : valeur indicative = contenance ENTIÈRE × €/m² de lot.** Sur un bien **bâti**, DÉFAUT B a retiré toute valeur de terrain (mesuré : la retenir dégrade). MAIS pour un **terrain nu**, la valeur indicative multiplie toujours la **contenance entière** par un €/m² de lot à bâtir : `estimation_annonce` fixe `surface_parc` = contenance (`api.py` l. 1961, doctrine CONTENANCE-1) et la passe à `_valeur_indicative(surface_parc, med, ecart)` (`api.py` l. 2008), repris par la branche terrain de `rapport3`. Témoin AK0804 : **27 862 m² × 278 = 7 746 000 €** — un « ordre de grandeur » faux sur 2,8 ha (le €/m² vient de ventes de lots de quelques centaines de m²). Aucun seuil de garde. **Limite résiduelle réelle**, non corrigée par ESTIMER-3 (qui ne touche pas le terrain nu).
4. **(mineur — mesuré) Pool de comparables : ventes au terrain nul gardées à pleine pondération.** La pondération ESTIMER-3 **saute** la pénalité d'écart de terrain quand le comparable a terrain = 0 (`estimer3.py` l. 200, `(terrain_m2 or 0) > 0`). Sur l'île, 9,1 % des ventes maison ont un terrain nul/absent, médiane €/m² −7 % vs celles avec terrain (COMPTE-RENDU recette 2) — gardées à pleine pondération, elles tirent légèrement le €/m² vers le bas. Constat, non modifié.
5. **(mineur) Une même mutation peut apparaître en double dans les ventes retenues** (plusieurs lots d'un même acte — vu sur BZ1065, id `2025-1269356` deux fois avec surfaces 94 et 71 m²). Le front dédoublonne à l'affichage par identifiant (`AnalyserAnnonce.tsx` l. 227-228), mais les deux lignes entrent toutes deux dans la médiane pondérée (poids distincts). Effet marginal, constaté.
6. **(mineur) Écart affiché/vendu Radar non servi en base locale** (0 annonce rattachée à une vente, seuil 20). Honnête (l'outil l'écrit), mais le repère « prix affiché vs vendu » promis n'existe pas tant que `cycle.matcher_dvf` n'a pas peuplé `vendue_ecart_prix` en prod.

---

## Synthèse INDEX (≈12 lignes)

- Fiche réécrite : `docs/audit-2026-11/outils-fiches-1/analyser-annonce.md` — reflète la refonte **ESTIMER-3 + ESTIMER-ECRAN-1** (mergée 11/11/2026).
- `src/labuse/pige/estimer3.py` **existe** et est le cœur du calcul ; endpoint principal **`POST /radar/annonce/estimation3/{idu}`** (`api.py` l. 2098), PDF via adaptateur `_est_bloc_depuis_estimer3` (l. 2427, 0 écart écran==document).
- **Un seul écran, parcelle uniquement** : boîte `EntreeParcelle` (option A) + « Ce que LABUSE a mesuré » (puces) + question surface (badge estimée/connue/saisie) + pièces pour l'appartement + valeur avec **jauge à deux bandes** (« 1 fois sur 2 » médian / « 3 fois sur 4 » Q3) + ventes décochables + Radar + PDF. Le **lien Leboncoin** n'est plus une entrée d'écran (Radar seulement, rapport commune inchangé, SSRF fermé).
- Méthode réelle : comparables **SEMBLABLES** (médiane pondérée par distance/surface/terrain/ancienneté/pièces) ; **meilleure des deux méthodes** (secteur ESTIMER-2 vs semblable) par cellule selon `methode_prix` mesuré au banc ; **repli secteur** si < 8 semblables (dit) ; précision **mesurée** (`estimer3_precision`, job nuit `estimer-banc-precision`).
- **DÉFAUT A** : surface inconnue + Q3 > 50 % → total masqué, €/m² + invite. **DÉFAUT B** : sur un bien bâti, plus aucune valeur de terrain (mesuré : la retenir dégrade) ; valeur terrain servie pour les terrains nus.
- Part sourcé vs estimé : mesures/ventes/Radar = **sourcés** ; tout le bloc prix (€/m², bandes, valeur, fiabilité) = **estimé**.
- 3 témoins rejoués (sorties réelles) : BZ1065 maison sans saisie **total masqué** (3 684 €/m², ± 28 %/60 %, Limitée) → surface 140 m² **529 000 €** (secteur) ; AK0804 terrain **278 €/m² · 7,7 M€** (contenance 27 862 m²) ; DH0076 appart **6 438 €/m² · 393 000 €** (semblable, Élevée, ± 11 %/24 %).
- **Les deux doutes graves de l'ancienne fiche sont CORRIGÉS** : la pondération n'est plus écrasée (meilleure des deux, libellé qui suit la méthode servie) ; la valeur de terrain disparaît sur le bâti.
- **Limite résiduelle réelle** : le **terrain nu** multiplie toujours la **contenance entière** par un €/m² de lot (`api.py` l. 1961 → l. 2008), sans seuil de garde (AK0804 = 7,7 M€ sur 2,8 ha). Non corrigée par ESTIMER-3.
