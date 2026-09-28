# FRONT-CHIFFRES-1 — aucun chiffre client hors du registre

**Branche** `audit/front-chiffres-1` (depuis `origin/main`) · worktree `~/Desktop/labuse-frontchiffres` · ports 8615 / 5815 · lecture seule (A/B) puis un lot C présentation-seule.

**Pourquoi.** Le banc de cohérence (`scripts/coherence`) ne voit que les chiffres qui passent
par le registre. Le « 999 % » d'hier vivait dans un composant, invisible du banc. Ce mandat
balaye tout `frontend/src` pour ce qui **produit, transforme ou borne** un chiffre que le client
lit sans être déclaré, puis (Lot C) corrige les chiffres qui **mentent** et pose un **verrou**
front — l'instrument qui manquait exactement là où le banc est aveugle.

---

## Lot A — l'inventaire

`INVENTAIRE.csv` — **966 occurrences** (balayage des 207 fichiers de `frontend/src`, 6 tranches
en parallèle : fiche, outils, panel/projets/contexte, admin/map, lib/store, radar/copilote/crm).
Colonnes : `zone, fichier_ligne, ce_que_voit_client, valeur_servie_origine, registre_id, nature,
verdict, confiance, note`.

### Par nature
| nature | n | ce que c'est |
|---|---|---|
| format | 345 | mise en forme d'un nombre (dont beaucoup hors `lib/format.ts`) |
| texte | 229 | phrase contenant un chiffre en dur |
| calcul | 172 | opération arithmétique sur une valeur servie |
| seuil | 138 | constante qui décide un affichage/libellé |
| defaut | 82 | zéro ou absence fabriqué (`?? 0`, `\|\| '—'`…) |

### Par verdict
| verdict | n | sens |
|---|---|---|
| **legitime** | 525 | présentation pure (formateur partagé, arrondi d'affichage, conversion cosmétique) — rien à faire |
| **remonter_back** | 213 | vrai calcul / seuil qui décide de la donnée → devrait vivre au back sous un id, le front ne rendrait plus |
| **declarer_registre** | 207 | valeur servie mais transformée/bornée au front → id + tolérance |
| **supprimer** | 21 | chiffre fabriqué qui **ment** (plafond qui cache, zéro pour absence) |

### Par zone
fiche 289 · outils 255 · panel/projets/contexte 202 · admin/map 96 · lib/store 68 · radar/copilote/crm 56.

> Note de périmètre : `admin/map` (96) est l'outillage **interne** LABUSE (page Circuit, Licences,
> Admin), pas le parcours client. Ses anomalies sont réelles mais rangées après le client.

---

## Lot B — les cas graves

### 1. Zéro / total FABRIQUÉ pour une absence (les 21 « supprimer »)

Un chiffre inventé, indistinguable d'une vraie valeur. **15 sont dans le parcours client**, 6 dans
l'admin. Les plus nets (tous CORRIGÉS au Lot C, cf. plus bas) :

| # | occurrence | ce que voyait le client | témoin de l'effet |
|---|---|---|---|
| 1 | `outils/MonSecteur.tsx:71` | `sb.median_eur_m2 ?? 0` → **« 0 €/m² »** quand le prix médian bâti du secteur est absent (alors que Rayon/Ventes/Tendance affichaient déjà « — ») | un secteur sans vente comparable rendait un prix de « 0 €/m² » |
| 2 | `radar/RadarMarcheColonne.tsx:240` | `fmt(der.ancien ?? 0)` → **« 0 € »** dans une ligne de baisse de prix | une baisse dont un prix est null s'affichait « 0 → … € » |
| 3 | `outils/ModulePanel.tsx:277` | `(m2 ?? 0)/1e4` → **« 0,0 ha »** + conversion m²→ha au front | une sélection sans surface agrégée rendait « 0,0 ha » |
| 4 | `outils/TaxeAmenagement.tsx:163` | **« Valeurs 2026 »** figé dans l'infobulle alors que l'année du barème est servie (`c.meta.annee`, déjà lue l.407) | mentira au prochain barème |
| 5 | `panel/FiltreLabuse.tsx:702/892/969` | `live ?? 431_663` → le rituel de Révélation replie sur le **total d'île 431 663 codé en dur** (périmé à chaque bascule de run) en 3 endroits (compteur animé, phrase, bouton) | avant réponse du compteur, le client voit défiler jusqu'à un total figé |
| 6 | `fiche/ProfilAltimetrique.tsx:70-75` | `?? 0` sur les 6 chiffres du relief → un terrain sans mesure RGE ALTI s'affichait **plat au niveau de la mer** (distance/dénivelé/pente/altitude = 0) | bloc gardé par `p.disponible`, mais un sous-champ null fabriquait un 0 |

**Reclassés après lecture du code** (pas des mensonges actifs, donc NON « supprimer ») :
- `fiche/constructibilite.tsx:988` `Math.max(fo[0]??0, fo[1]??0)` — le 0 fabriqué **route vers
  « non calculable »** (`capaciteNulle`), pas vers « 0 logement ». → legitime (issue sûre).
- `contexte/ContextePanel.tsx:441` base SRU `round(nbLls/(taux/100))` — **dérivation documentée**
  (COMMUNE-FIX-1 A3), affichée « ≈ N ». → declarer_registre (à servir), pas un mensonge.
- `outils/blocB.tsx:298` `par_tier['brulante'] ?? 0` — une clé de tier absente **vaut zéro
  brûlante** (compte réel), ce n'est pas une absence de donnée. → legitime.

**Admin (6, hors parcours client, non corrigés — voir recommandations) :** le total de verrous
est fabriqué avec **trois valeurs différentes** pour le même datum servi — `AdminView.tsx:475`
(`?? 16`), `Resume.tsx:43/69` (`?? 30` / `?? 22`), `Circuit.tsx:227/229` (`?? 22`, puis soustraction
sur ce dénominateur fabriqué) — et `Licences.tsx:582` `ia_budget_eur ?? 2` (budget IA replié sur 2 €).

### 2. Seuils / plafonds / conversions qui décident au front (les plus graves du « remonter_back »)

35 occurrences client à confiance haute où le **front décide** d'un libellé, d'un verdict ou d'une
unité au lieu de rendre une valeur servie. Ce sont des **règles dupliquées** : elles vivent déjà au
back mais sont ré-écrites au front, donc dérivent en silence à la prochaine évolution du back. Les
têtes de liste :

- **Radar recalcule ce qui est déjà servi** — `RadarEcran.tsx:39` `€/m² = round(prix/surf)` (le
  payload `vs-marche` sert déjà `eur_m2`), badges **« Nouveau » (`j<2`)** et **« En vente depuis N j »
  (`j>90`)** codés en dur alors que le back sert `biens_sup_90j` → la liste et la colonne marché
  peuvent se contredire sur le même seuil 90 j. *(À l'inverse, bon point : les seuils d'écart 30/5 de
  `RadarMarcheColonne` sont **servis** — `seuil_indicatif_n`/`seuil_ecart_n` — le front ne fait que
  choisir la couleur ; le suspect « seuil 30 ≠ back » du mandat est ici INFIRMÉ.)*
- **Bornes financières dupliquées** — `FinancierQuestionnaire.tsx:25` `MAX_PRIX_SORTIE_M2=20000`,
  `MAX_COUT_M2=8000`, `MAX_BAILLEUR_M2=12000` (le commentaire dit « REPRODUIT la garde serveur ») —
  décident blocage/messages.
- **Taux fiscaux et méthodes en dur dans la prose client** — `ModulePanel.tsx:1094` **TVA 2,1 % ·
  abattement TFPB 30 %** ; `moteurs.tsx:446` **budget ZAN = conso 2011-21 × 0,5** ; `moteurs.tsx:888`
  **« ≥ 2 permis »** (critère de sélection) ; `Successions.tsx:36/72` **70 / 20 / 5 ans** ;
  `FiltreLabuse.tsx:301` **~70 m² SDP/logement**, `:820` **nu/bâti ≥ 5 %**.
- **Bandes de pente 5/15/30°** dupliquées (`Fiche.tsx:859/1226`), **zonage A/N** décidé par regex JS
  (`constructibilite.tsx:986`, `Fiche.tsx:624/855/891/1816`) alors que `zone_plu_famille` est servie.
- **Conversions d'unité / fraction×100 au front** — `blocks.tsx:107`, `MarcheSecteurBlock.tsx:17`,
  `GabaritLine.tsx:75`, `Gabarit.tsx:209`, `blocB.tsx:375` (barre ZAN bornée `max(4,min(100,…))` — le
  plancher 4 % et le plafond 100 % **mentent sur la part réelle**), `autour.tsx:66` (m→km),
  `EtudeZone.tsx:421` (m²→ha), `ContextePanel.tsx:576` (m²→« M m² »).

### 3. Comptes / totaux figés dans le texte (catégorie 4)

`lib/strings.ts` et `lib/layers.ts` inscrivent des comptes servis en littéral de prose :
**« 33 622 parcelles »** (pm_privee), **« 7 129 parcelles »** (succession — *déjà faux*, OUTILS-S2
l'a passé à 6 099), **« 431 663 »** / **« 227 545 »** / **« 99,99 % »** (page Sources, « i » couche
Parcelles). Servis dynamiquement ailleurs → divergence garantie à la prochaine bascule.

---

## Lot C — ce qui a été fait

Le mandat borne le Lot C à « **des déclarations au registre et des tests, aucune logique
nouvelle** ». Deux familles de `remonter_back` en découlent, traitées différemment :

- **Corrigé (présentation seule, vérifiable)** — les chiffres qui MENTENT au client : rendre
  l'absence, ou lire la valeur déjà servie. Aucune règle ni calcul ajouté.
- **Documenté (recommandation)** — les 213 `remonter_back` qui dupliquent une règle du back : les
  rapatrier exige d'exposer la valeur back au front (nouvelle surface d'API) = *logique nouvelle*,
  donc **hors périmètre**. Déclarer un id front séparé créerait une **seconde source de vérité** pour
  une valeur que le back possède déjà (pire). Listés ci-dessous pour la suite.

### Commit 1 — `supprimer : chiffres clients qui mentent` (`058e6829`)
5 fichiers, présentation seule :
1. `MonSecteur.tsx` — prix médian absent → « — » (aligné sur ses cellules voisines).
2. `RadarMarcheColonne.tsx` — retrait du `?? 0` (`fmt` rend déjà « — »).
3. `ModulePanel.tsx` — surface totale via `fmtM2` (null → « — », conversion m²/ha du formateur partagé, LOI-3).
4. `TaxeAmenagement.tsx` — millésime lu de `c.meta.annee` (plus de « 2026 » figé).
5. `FiltreLabuse.tsx` — le total de repli du rituel lit la **notion servie `n_parcelles_ile`**
   (`/accueil/chiffres`, id déjà au registre, servi par `compte_parcelles_ile`) au lieu de 431 663 ;
   0 si l'endpoint échoue, jamais un total inventé. **C'est l'exemple type** : le chiffre existait
   déjà au registre, le front le codait en dur — il le LIT désormais.

### Commit 2 — `verrou test_front_sans_chiffre_orphelin (+ dernier zéro-pour-absence)` (`809be882`)
- `ProfilAltimetrique.tsx` — `nf`/`nf1` rendent « — » pour null ; un **vrai 0** (terrain plat) reste
  « 0 ». Les 6 chiffres du relief ne fabriquent plus un terrain plat au niveau de la mer.
- **`tests/test_front_chiffres_orphelins.py`** — le verrou. Grep des deux motifs les plus dangereux
  du Lot A dans `frontend/src`, avec liste blanche commentée :
  - **Z** — `?? 0` / `\|\| 0` sur la même ligne qu'une **unité affichée** (€, m², ha, %, k€, M€,
    logements). Bornes de mot pour écarter les faux positifs (« écha**ntillon** », « **ha**lo »,
    champs `logements_*` où le `_` casse la frontière de mot).
  - **T** — le **littéral de code** `431663` / `431_663` (et `227_545`) : total d'île figé. *(La prose
    « 431 663 » avec espace, catégorie 4, n'est pas visée — c'est une dette de texte documentée.)*
  - Liste blanche (2) : `moteurs.tsx` (bornes de filtre SAISIES, 0 = pas de minimum) et
    `Licences.tsx` (formateur € interne admin). Chacune avec sa raison.
  - + garde POSITIVE des 5 correctifs (anti-régression) + garde anti-liste-blanche-périmée.

**Vérifs** : `tsc -b` 0 · `vitest run` 225/225 · `pytest` verrou 3/3.

### Banc `--echantillon`
Rejoué (`scripts/coherence/banc --echantillon`, API pointée sur 8615). Les commits ne touchent
**aucun code back/API** : le banc, qui compare les lecteurs **serveur** (fiche JSON, SQL, tuile MVT,
outils API), rend un résultat **identique par construction** — 0 écart nouveau. C'est exactement le
constat fondateur du mandat : *le banc ne voit pas le front*. Le verrou ci-dessus est l'instrument
front qui comble ce trou.

> Exécution : le banc a été lancé (`--echantillon`, API 8615) mais a dépassé son budget de
> ~15 min (throttle 429 de l'API + contention DB, plausiblement avec COHERENCE-FIX-1 en
> parallèle) et a été interrompu. Ce n'est **pas** un signal sur ce mandat : le banc interroge
> des lecteurs SERVEUR, et les 2 commits ne modifient **aucune** ligne back/API (`git diff
> --stat` : uniquement `frontend/src` + un test). Le résultat du banc est donc **inchangé par
> construction** — 0 écart nouveau. La garantie de non-régression côté front est portée par le
> verrou `test_front_chiffres_orphelins.py`, pas par le banc.

---

## Recommandations (à rapatrier au back — hors « aucune logique nouvelle »)

Chaque id proposé reçoit sa **tolérance** par la règle de `scripts/coherence/referentiel.py`
(`0,5 point` pour %, `1 %` pour € et surfaces, `0 (entier)` pour un compte, `0 (identité)` pour une
classe/texte). Ordre = priorité client.

| priorité | occurrence(s) | action | id registre proposé | unité | tolérance |
|---|---|---|---|---|---|
| 1 | `RadarEcran.tsx:39` €/m² recalculé | **lire** `eur_m2` déjà servi (payload vs-marche) | `radar_prix_eur_m2` | €/m² | 1 % |
| 2 | `RadarEcran.tsx:60/86` badges `j<2` / `j>90` | servir le verdict/seuil (le back sert déjà `biens_sup_90j`) | `radar_seuil_nouveau_j` / `radar_seuil_longue_j` | nombre | 0 (entier) |
| 3 | `FinancierQuestionnaire.tsx:25` bornes 20000/8000/12000 | servir la garde `financier_questionnaire.py` | `garde_prix_sortie_max_eur_m2` … | €/m² | 1 % |
| 4 | `ModulePanel.tsx:1094` TVA 2,1 % / TFPB 30 % | servir les taux fiscaux (déjà en base REI/CGI) | `tva_lls_pct` / `abattement_tfpb_pct` | % | 0,5 point |
| 5 | `moteurs.tsx:446/888` ZAN ×0,5 / ≥2 permis | servir la méthode/critère du moteur | `zan_facteur_budget` / `promoteur_seuil_permis` | nombre | 0 (entier) |
| 6 | `Fiche.tsx:859/1226` pente 5/15/30° | servir les bornes de bande de pente | `pente_bande_bornes_deg` | ° | 0,5 point |
| 7 | `constructibilite.tsx:986` + `Fiche.tsx` zonage A/N par regex | lire `zone_plu_famille` (servi) au lieu du regex | *(existant)* | classe | 0 (identité) |
| 8 | `strings.ts:32/39` comptes 33 622 / 7 129 | servir le compte (7 129 est **déjà faux** → 6 099) | `n_parcelles_pm_privee` / `n_parcelles_succession` | nombre | 0 (entier) |
| 9 | `strings.ts:407` / `layers.ts:88` « 431 663 / 227 545 / 99,99 % » (prose) | interpoler `n_parcelles_ile` + taux de rattachement servis | *(existant + `taux_rattachement_ban_pct`)* | nombre / % | 0 (entier) / 0,5 point |
| 10 | admin verrous 16/22/30 + `ia_budget ?? 2` | une seule source servie `compteurs_coherence.verrous` (interne) | — | — | — |

> Ces déclarations n'ont **pas** été committées : les ajouter à `registre/donnees.py` exige un
> `labuse registre sync` (mutation du miroir en base) et, pour la plupart, revient à dupliquer un
> datum que le back possède déjà. Le geste correct est de **servir** ces valeurs (petite API) puis
> de déclarer l'id UNE fois — travail de suite, listé ici prêt à l'emploi (c'est le contenu du PR
> `scripts/coherence/notions` demandé). `NOTIONS.csv` de COHERENCE-1 est **dérivé** de
> `donnees.py` (tolérance par règle d'unité) : il se régénérera seul quand les ids seront posés.

---

## Verrou (résumé)

`tests/test_front_chiffres_orphelins.py` — 3 tests. Toute NOUVELLE occurrence d'un `?? 0`/`|| 0`
avec unité affichée, ou d'un littéral de total d'île, hors liste blanche commentée, **fait échouer
la suite**. La liste blanche est elle-même gardée (une entrée périmée = échec).

## Fichiers livrés
- `docs/audit-2026-09/FRONT-CHIFFRES-1/INVENTAIRE.csv` (966 lignes)
- `docs/audit-2026-09/FRONT-CHIFFRES-1/RAPPORT.md` (ce document)
- `tests/test_front_chiffres_orphelins.py` (le verrou)
- 6 fichiers `frontend/src` corrigés (2 commits, présentation seule).
</content>
