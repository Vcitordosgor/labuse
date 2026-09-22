# RAPPORT M55-L — Fiche parcelle (14 points)

Branche `feat/m55-l` (base `5eac45fa` = M55-K mergé sur main). **NON mergée** — Vic
valide et merge lui-même. Points 1-12 = modifications (un commit atomique par point) ;
points 13-14 = **audits en constat seul** (aucune correction autonome sauf le fix
trivial du traducteur, explicitement autorisé).

- Précondition vérifiée : `feat/m55-k` mergé sur main (`5eac45fa`).
- `tsc -b` 0 · `vitest` 32/32 · `npm run build` vert · console : 0 erreur **nouvelle**.
- Captures : `reports/m55-l/captures/`. Parcelle de référence riche : `97415000CT1389`
  (Saint-Paul, potentiel épuisé, zone U3c).

## ⚠ Fichiers PARTAGÉS avec M55-M (ordre des merges)

M55-M (panneau) et M55-L (fiche) sont globalement disjoints, **sauf deux fichiers** —
Vic re-résoudra au 2ᵉ merge :

| Fichier | M55-M | M55-L |
|---|---|---|
| `store/useApp.ts` | `panneauSection: …\|'listing'`, `analyseRecap` | `verdictRevele` (pt5), `ficheTiroir` (pt10) — zones distinctes de l'objet |
| `lib/strings.ts` | `revelation.changerFiltres` | `fiche.adresseAbsenteInfo` (pt2), `fiche.demanderAnalyse` (pt5), `fiche.crm*` + `fiche.suivre` (pt9) |

---

## Points 1-12 — modifications

### Point 1 — Accueil : section fixe, sans barre de défilement — `b4b851ec`
**Constat/Modif.** `overflow-y-auto` → `overflow-hidden` (clip propre, aucune barre),
padding vertical généreux `py-6`. Acquis M55-I préservé (`my-auto` garde logo + CTA
visibles en tête). **Fichier** : `panel/LeftPanel.tsx` (AccueilPreuves).

**MESURE taille par taille (contrepartie du choix fixe — scroll NON réintroduit).**
L'accueil PARTAGE le panneau avec la section Couches ouverte (invariant accordéon
M55-I : une section toujours ouverte hors listing) → il n'a jamais la pleine hauteur.
Hauteur dispo / rendu :

| Taille | dispo | rendu | clip |
|---|---|---|---|
| 1440×900 | 333 | 338 | 5px (dernier filet) |
| 1200×800 | 271 | 338 | 67px |
| 1024×700 | 209 | 396 | 187px |
| 900×700 | 209 | 396 | 187px |
| 768×800 | 271 | 396 | 125px |

**Cause = STRUCTURELLE** (Couches ouverte), pas le padding : contenu 347px (panneau
240px) > 209px dispo même à py-0. **Recommandation Vic** : donner au panneau l'accueil
en pleine hauteur dans l'état accueil (accordéon plié) — hors périmètre du point 1,
non fait unilatéralement.

### Point 2 — « Adresse non rattachée » + « i » — `2320879a`
Quand l'adresse manque, un « i » (Tip) explique POURQUOI : aucune adresse BAN rattachée ;
le rattachement couvre ~la moitié des parcelles (227 545 / 431 663 — mesure M55-G) ; les
parcelles naturelles/sans bâti n'ont souvent pas d'adresse — absence réelle, pas un défaut.
Contenu depuis `CLIENT.fiche.adresseAbsenteInfo` (source unique, chiffres avec provenance).
**Fichiers** : `lib/strings.ts`, `fiche/Fiche.tsx`.

### Point 3 — Header : retrait de l'icône « partager » — `b0684548`
Icône de partage retirée (restent cloche, loupe, croix). Cloche NON touchée (chantier
notifications reporté). `ShareButton` + import/export `createShare` 0-caller → supprimés ;
endpoint back /partners/share intact. **Fichiers** : `fiche/Fiche.tsx`, `lib/api.ts`.

### Point 4 — Fiche élargie de 10 % — `01f8844f`
`w-[400px]` → `w-[440px]` (valeur unique), `max-w-full` conservé (aucun débordement).
**Fichier** : `fiche/Fiche.tsx`.

### Point 5 — Verdict à la demande — `2a48b9bd`
À l'ouverture, le bloc verdict est remplacé par un bouton vert « Demander l'analyse
LABUSE » (seul élément vert du niveau) ; au clic, le bloc complet se déploie. Choix
MÉMORISÉ PAR PARCELLE/session (`store.verdictRevele`, jamais persisté ; autre parcelle =
bouton ; reload = bouton). Vérifié E2E (bouton → clic → verdict → mémorisé). Mode factuel
inchangé : le bloc verdict de la FICHE décrit le verdict PROPRE de la parcelle (indépendant
de l'interrupteur d'analyse de la liste) → le bouton apparaît pareillement. PDF : le rail
back (pdfUrl) génère le verdict sans condition — inchangé.
- **À arbitrer (éléments d'opinion — repli ou non ?)** : le badge « Renouvellement — rang
  N/M » est DANS le bloc verdict → se replie avec lui (OK). HORS bloc restent : le rappel
  « qualité commune dégradée » (data-qualite-commune-rappel), le tiroir « Renouvellement —
  pourquoi ce rang », le tiroir « Pourquoi pas ? » — ce sont aussi des analyses. **Reco** :
  les laisser (accessibles à la demande via leurs tiroirs) ; Vic tranche.
**Fichiers** : `store/useApp.ts`, `lib/strings.ts`, `fiche/Fiche.tsx`.

### Point 6 — Retirer « 431 663 parcelles analysées » — `0f3b32d9`
`TheatreCompteur` retiré (fonction 0-caller supprimée). **Constat** : le périmètre reste
mentionné où requis — page Sources (« Échantillon : les 431 663 parcelles ») et PDF.
**Fichier** : `fiche/Fiche.tsx`.

### Point 7 — Retirer le widget feedback, mention légale relogée — `f991210e`
`FeedbackStrip` retiré (fonction + imports front `postFeedback`/`FeedbackVerdict`).
**⚠ Signalé (NON touché)** : endpoint POST /feedback (M54-EXPO A4) + binding api.ts n'ont
plus AUCUN point d'entrée UI — Vic décide (peut revenir en CRM). Mention légale conservée,
relogée en pied de fiche à 9px (couleur discrète) ; **constat** : présente dans les PDF
(`export_commun.py` pied de page « au mot près » + `export.py`). **Fichier** : `fiche/Fiche.tsx`.

### Point 8 — Actions sur deux lignes — `71d4af7b`
Ligne 1 : PDF · Dossier · Finance · Cadastre ; Ligne 2 : 1950 · Maps · Courrier ·
One-pager · Pré-dossier PC. `gridAutoFlow:column + gridAutoColumns:1fr` → colonnes égales
même avec tuiles conditionnelles (Cadastre/1950/Maps sur f.coords, sans trou). Équilibre
vérifié (capture p8_p11). **Fichier** : `fiche/Fiche.tsx`.

### Point 9 — Comparer outil à part + « + CRM » — `f4ac352f`
**Constat** : « Comparer » ne vivait QUE sur la fiche (absent de registry.ts) → ajouté aux
Outils (registry « comparer », groupe Analyser ; le clic OUVRE le comparateur).
**⚠ BLOCAGE MESURÉ (Vic tranche)** : retirer le bouton fiche rendrait le comparateur NON
PEUPLABLE — l'ajout (addToCompare) est l'UNIQUE voie, et ouvrir le tiroir Outils remet
`selectedIdu` à null (toggleOutils) → un outil ne peut pas récupérer « la parcelle
regardée ». Donc : **bouton fiche CONSERVÉ = l'AJOUT** (compareIdus persiste en session),
**outil Outils = l'OUVERTURE**. Design cohérent vérifié E2E (fiche → +1 colonne ; Outils →
Comparer rouvre la sélection). **Reco** : ajouter un sélecteur de parcelle au comparateur
permettrait de retirer le bouton fiche proprement.
Renommage « + Pipeline » → « + CRM » (source unique `CLIENT.fiche.crm*` ; tooltip cloche
« sans pipeline » → « sans passer par le CRM »). Grep : plus aucun « Pipeline » à l'écran
DANS LA FICHE (reste un commentaire de code). La vue CRM (Kanban) garde « pipeline de
prospection » en interne — hors périmètre, signalé. **Fichiers** : `outils/registry.ts`,
`Rail.tsx`, `App.tsx`, `compare/ComparePanel.tsx`, `fiche/Fiche.tsx`, `lib/strings.ts`.

### Point 10 — Tiroirs de la fiche : accordéon exclusif — `57429ae5`
Tous les tiroirs en accordéon EXCLUSIF (un seul ouvert, zéro ouvert légal, initial tout
fermé). Champ unique `store.ficheTiroir[idu]` exposé par contexte React → RefDrawer
contrôlé (plus d'état local, `defaultOpen` retiré, `servable` 0-caller supprimé). Le
défilement suit (`goDrawer` ouvre + scrolle). Vérifié E2E (vide → exclusif → zéro).
**Fichiers** : `store/useApp.ts`, `fiche/Fiche.tsx`.

### Point 11 — Boutons IA en tête (mauve) — `63b3fb33`
« Une question ? » + « Synthèse » remontés en tête de fiche (sous le bouton verdict),
encadrés dans un bloc violet léger (couleur IA LABUSE), visibles sans défilement (mesuré :
offset 258px). Même palette qu'avant — aucun nouveau composant. **Fichier** : `fiche/Fiche.tsx`.
Avant : bas de la pile des tiroirs. Après : capture p8_p11_actions_ia.

### Point 12 — Courrier SPF : renvoyer vers l'outil dédié — `33c49562`
**Constat** : le lien ouvrait `/parcels/{idu}/spf-letter` — une lettre TEXTE brute (200
text/plain), pas un outil. **Fix** : ouvre désormais l'outil courrier M09 (`setModule
('courriers')`), pré-rempli sur la parcelle (M09 lit selectedIdu, préservé). Contexte
parcelle VÉRIFIÉ E2E. `spfLetterUrl` 0-caller retiré de l'import fiche ; export api.ts +
endpoint back préservés.
- **Nuances (Vic tranche)** : (1) M09 n'a pas de motif « SPF » dédié (motifs standard/
  indivision/succession) — reco : ajouter un motif SPF branché sur `proprietaire_type.
  spf_letter` pour générer la vraie lettre de demande SPF ; (2) les 404 /courrier/statut &
  /courrier/envois sont PRÉEXISTANTS (dev, endpoints prestataire non déployés), déclenchés
  par toute entrée du module — **désormais résolus par le fix proxy du point 13**.
**Fichier** : `fiche/Fiche.tsx`.

---

## Point 13 — AUDIT (constat seul) : véracité, placement, boussole des tiroirs

Parcelle de référence riche `97415000CT1389` (+ vérifs DB). Audit **représentatif**
(pas exhaustif champ-par-champ sur les 11 tiroirs × 2 parcelles — recommandé en passe
dédiée si Vic veut la couverture totale) ; findings à plus forte valeur ci-dessous.

### 13.a — Véracité (spot-checks display vs source DB) — sains
| Info affichée | Valeur affichée | Source (table/colonne) | Valeur source | Verdict |
|---|---|---|---|---|
| Surface (header) | 328,31 m² | `parcels.geom` (ST_Area geog) | 328,3 m² | ✅ conforme |
| Zone PLU (Règles/Traducteur) | U3c | `parcel_zone_plu.zone_lib` | U3c (fam U) | ✅ conforme |
| Adresse (header) | 4 Impasse Cordonnier… | `parcel_adresse` (BAN) | idem | ✅ conforme |
| « Les données » | 28 sources | cascade run servi (cf. 13.c) | 28 distinctes | ✅ conforme (per-parcelle) |

Le câblage des champs vérifiés est **fidèle** (aucune divergence sur l'échantillon).

### 13.b — Boussole (étiquette Sourcé/Estimé/date)
Le traducteur étiquette chaque règle (Sourcé/Estimé) + source au survol ✅. Le score/×N
porte son « ⓘ » ✅. **Point d'attention** (cf. 13.c) : dans « Les données », la colonne
millésime affiche « — » pour la grande majorité des sources (dette M54-AB, mesurée).

### 13.c — Tiroir « Les données » : définition de la liste
**Règle de sélection trouvée** (`app.py:_data_sources_fiche`, M52 L3) : la liste = les
sources DISTINCT jointes aux **résultats de cascade de CETTE parcelle** dans le run servi
(`dryrun_cascade_results ⋈ data_sources WHERE run_label ∧ parcel_id`). C'est donc « les
sources RÉELLEMENT utilisées sur cette fiche » (per-parcelle, varie d'une parcelle à
l'autre). **Règle SAINE, pas un bug de filtre.**
- « 28 sources » pour la parcelle de référence (le mandat citait « 21 » — c'est simplement
  une AUTRE parcelle : le compte est par-parcelle).
- **Univers = 62 sources branchées** (`SELECT count(*) FROM data_sources`), **pas 52**.
- **Absentes** pour cette parcelle = 62 − 28 = 34 : sources sans résultat de cascade pour
  elle (non applicables : pas de permis/DPE/friche/ICPE… sur cette parcelle). Raison saine.
- **Libellé honnête proposé** : « N sources utilisées sur cette fiche » (au lieu de « N
  sources » sec) — le code le dit déjà en commentaire, le libellé client peut le refléter.
- **DETTE MILLÉSIME (M54-AB) — plus large que noté** : mesuré, **54 des 62 sources** n'ont
  NI `source_millesime` NI `source_horizon_at` → afficheraient « — » (4 sont sauvées par
  l'horizon, seules ~8 portent un vrai millésime). Le mandat ne citait que Cadastre / RGE
  ALTI ; c'est en réalité quasi-général. **Reco** : peupler `source_millesime` (ou l'horizon)
  en masse, ou assumer « — = millésime non renseigné » explicitement.

### 13.d — Traducteur de zone : les DEUX anomalies (diagnostic)
- **(a) chaîne « L'IA ne juge pas le sentiment d'une communauté… »** = le composant PARTAGÉ
  `<AvisIA/>` (source unique `CLIENT.avisIa`), délibérément posé sur TOUTE surface IA. **Ce
  n'est PAS une chaîne mal câblée** (hypothèse du mandat infirmée) — mais elle est
  thématiquement HORS-SUJET pour une traduction de règles PLU (factuelle). Comme ce n'est
  pas un mis-câblage, **pas de fix auto** (ambigu) → **reco Vic** : retirer `<AvisIA/>` du
  traducteur (rien à « juger » : c'est de la lecture de règles) ou le remplacer par une note
  spécifique.
- **(b) « Traduction indisponible — réessayer »** = **CAUSE RACINE trouvée et CORRIGÉE**
  (fix trivial autorisé, `046f47e4`) : le fetch relatif `POST /traducteur-plu/{idu}` n'était
  PAS proxifié en dev (absent de `vite.config apiPaths`) → 404 sur vite. L'endpoint répond
  **200** à :8000 (prod OK, même origine FastAPI). Même famille que /moi, /events, /adresses
  déjà comblés. Ajout `/traducteur-plu` (+ `/courrier`, `/dossier-banquier`). Vérifié : le
  traducteur affiche désormais zone U3c + 6 règles en dev. **Dev-only, aucun impact prod.**

### 13.e — Placement (candidats au déménagement)
Sur l'échantillon, le placement est cohérent. Un seul candidat notable relève du **doublon**
(cf. point 14) : la SDP résiduelle apparaît en tête de DEUX tiroirs. Pas d'autre info
manifestement « dans le mauvais tiroir » relevée sur la parcelle de référence.

---

## Point 14 — AUDIT (constat seul) : doublons d'information

Note de méthode : depuis le point 10 (accordéon exclusif), un seul CORPS de tiroir est
visible à la fois → la duplication simultanée est fortement réduite. Les doublons se lisent
donc surtout entre les **en-têtes de tiroirs (toujours visibles)** et le bloc verdict.

| Information | Emplacements | Avis |
|---|---|---|
| **SDP résiduelle (~101 m²)** | en-tête tiroir **Règles** (« 101 m² SDP ») **ET** en-tête tiroir **Faisabilité** (« ~101 m² SDP ») | **À retirer d'un des deux** — même valeur, deux en-têtes voisins. Garder en Faisabilité (le bilan) ; Règles peut porter la hauteur/CES à la place. *Vic tranche.* |
| Zone PLU (U3c) | chip verdict « constructible U3c » (si verdict déployé) · en-tête/corps Règles · Traducteur | Légitime en partie (résumé verdict vs détail règles vs traduction) ; le code de zone se répète 2-3×. Acceptable, à surveiller. |
| Rang | « rang N » (verdict, brûlante/chaude) · « Renouvellement — rang N/M » (badge) | **NON doublon** : rangs distincts (classement global vs rang de segment). Légitime. |

Reste (surface, commune, verdict) : une seule occurrence visible à la fois grâce à
l'accordéon exclusif — pas de doublon manifeste sur l'échantillon.

---

## Validation

| Contrôle | Résultat |
|---|---|
| `tsc -b` | 0 |
| `vitest run` | 32/32 |
| `npm run build` | vert |
| Console | 0 erreur **nouvelle** (les 404 dev /courrier /traducteur-plu sont désormais corrigés ; aucun autre) |
| Point 5 (parcours mémorisé) | vérifié E2E |
| Point 10 (accordéon) | vérifié E2E (vide → exclusif → zéro) |
| Point 9 (comparateur) | vérifié E2E (ajout fiche → ouverture Outils) |
| Point 13 (traducteur) | vérifié E2E (zone U3c, 6 règles) |
| Non-régression | persistance filtres, invariants panneau, mode factuel, logo M55-I |

**Ne pas merger.** Attention aux fichiers partagés `store/useApp.ts` et `lib/strings.ts`
(tableau en tête). Décisions en attente de Vic : pt5 (repli des opinions hors bloc), pt7
(sort backend feedback), pt9 (bouton Comparer fiche / sélecteur au comparateur), pt12
(motif SPF dans M09), pt13.c (dette millésime), pt13.d.a (AvisIA du traducteur), pt14 (SDP
en double).
