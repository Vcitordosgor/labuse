# M30 — TRAIN 4 : FILTRES / RECHERCHE / CLARTÉ

Régime [A] · branche `m30-train4-filtres` · base `22b9f03` (main post-merge M29, vérifié)
Périmètre : UI/API **lecture uniquement** — aucun changement scoring/tiers/règles (item 8).
Golden de fin de geste : **117/117 PASS, 0 incohérence base↔API** (vérifié, section 8).

---

## 1 · Inventaire exhaustif des filtres (RAPPORT avant tout geste)

### Filtres effectifs (14) — tous appliqués en SQL dans `_q_v2_where()` (app.py:771+)

| Filtre (libellé UI) | Param API | SQL (app.py) | Exposé UI |
|---|---|---|---|
| Verdict · Scoring (5 tiers v2, multi) | `tiers` (CSV) | :793-803 (`s2.tier = ANY` + étage 0 prime) | Header.tsx popover |
| Potentiel ≥ /100 | `score_min` | :811-813 | oui |
| Surf. constr. ≥ m² | `sdp_min` | :820-823 | oui |
| Surface ≥ / ≤ | `surface_min`/`surface_max` | :814-819 | oui |
| Avec événement (BODACC) | `evenement` | :824-826 | oui |
| Veille succession | `veille` | :806-807 (EXISTS) | oui |
| Masquer les copropriétés | `hors_copro` | :804-805 | oui |
| Flags actifs (5 : pollution/ABF/ICPE/risques/prescription PLU) | `flags` | :827-831 | oui |
| Contraintes rédhibitoires (copilote-projet) | `flags_exclus` | :832-836 | copilote |
| Signaux propriétaire (5 groupes §5.3) | `v_signal` | :842-847 (jsonb) | oui |
| Communes (secteur cadreur R2) | `communes` | :791-792 | copilote |
| Personne morale | `personne_morale` | :854-855 | API seule (M11 B2) |
| Zonage PLU (familles U/AU/A/N) | `zonage` | :857-860 | API seule (M11 B2) |
| Défisc / PC caduc / marge | `defisc_active`/`pc_caduc`/`marge_min` | :863-872 | modules |

Deux voies d'accès confirmées : filtres manuels (popover « + Filtre », chips, URL `#f=…`
partageable) et copilote IA (`/ia/search`, sous-ensemble tiers/communes/surface/score_min/
flags_exclus). Sélecteurs hors filtre : commune (Header), tri (`sort` rang/mult/surface/commune).

### Théâtre identifié (liste AVANT suppression — item 2)

| Élément | Preuve | Verdict M30 |
|---|---|---|
| `v_bands` (bandes Score V) | param accepté, jamais envoyé par le front ; le Score V est retiré du produit depuis M11 Phase 0 (RR@1158 = 0,51) — **un filtre qui ment** | **SUPPRIMÉ** |
| `/discover` | endpoint orphelin (plus aucun appelant depuis M5.1, remplacé par /parcels + /stats) | **SUPPRIMÉ** |
| option « dirigeant » (signaux propriétaire) | filters.ts — masquée depuis l'audit A5, codes absents de la base | **SUPPRIMÉE** (code mort) |
| `statuts` (matrice legacy) | accepté, servi par `legacy=1` deprecated | **CONSERVÉ** documenté |
| `brulantes` (bool v1.3) | accepté, remplacé par `tiers` multi | **CONSERVÉ** documenté |

Décision consignée : `statuts`/`brulantes` restent en compat legacy **documentée** — les retirer
casserait le contrat API deprecated encore servi (`legacy=1`), ce qui excède « lecture uniquement ».
À trancher par Vic si une dépréciation dure est voulue (train ultérieur).

Observation d'inventaire (aucun geste) : `MIN_DISPLAY_SURFACE_M2 = 2 m²` est **asymétrique** —
appliqué carte/découverte, PAS liste/compteurs. Noté pour arbitrage, pas touché (changer la liste
servie n'est pas un geste de clarté).

---

## 2 · Théâtre supprimé (item 2)

- `app.py` : branche SQL `v_bands` retirée de `_q_v2_where` (remplacée par un commentaire M30
  motivé), paramètre retiré des signatures + sites d'appel de `/parcels`, `/parcels/export.csv`,
  `/stats` ; route `/discover` supprimée (bloc commenté de renvoi vers /parcels + /stats).
- `frontend/src/lib/filters.ts` : option `dirigeant` retirée (commentaire A5 en place).
- Vérification : `grep v_bands` → 1 occurrence restante = le commentaire de motif ; `py_compile` OK.

**Capture** : `captures/popover_filtres_avant.png` / `_apres.png`.

---

## 3 · « Tout montrer » — declasse_* atteignables (item 3)

Avant : les 6 tiers de déclassement étaient **visibles en fiche mais inatteignables au filtre**
(absents du popover, strippés des liens `#tv=`, verdict replié sur le statut matrice muet).

Geste (lecture seule — l'API `tiers` acceptait déjà toute valeur, `s2.tier = ANY`) :
- `status.ts` : type `TierDeclasse` + `TIER_DECLASSE_META` (libellés **motivés** « Déclassée — bâti
  saturé », …, couleur terre éteinte hors palette thermique) — type DISTINCT de `TierV2` : les
  compteurs/entonnoir n'agrègent que les 5 tiers servables, la vue par défaut ne change pas ;
  `verdictMeta`/`TierBadge` servent désormais le label motivé au lieu du repli muet.
- `Header.tsx` : groupe « Déclassées · motif (multi) » dans le popover, rien coché par défaut.
- `filters.ts` : `matchAll` via `filterableTier` (déclassements sélectionnables, vide inchangé),
  chips + liens `#tv=declasse_*` valides.
- Palette carte : **inchangée** (expressions MapLibre codées en dur, non touchées).

Volumétrie servie (run q_v8_calibre) : bâti saturé 29 872 · non constructible 6 168 · bâti révélé
4 010 · zone fermée 2 804 · AU statut inconnu 560 · AU fermée 58.

Vérifié bout en bout : `GET /parcels?source=q_v8_calibre&tiers=declasse_bati_sature` → rows ;
lien `#v=1&f=1&tv=declasse_bati_sature` → liste 29 871 + chip (avant : lien silencieusement strippé).

**Captures** : `captures/liste_declasse_bati_sature_avant.png` / `_apres.png`.

---

## 4 · Adresse absente (item 4)

`strings.ts` : `adresseAbsente = 'adresse non rattachée (Absent)'` — jamais un champ vide ni un
« non disponible » sans étiquette boussole. Témoin : 97416000ET2164 (brûlante rang 25, aucune
adresse BAN).

**Captures** : `captures/fiche_adresse_absente_avant.png` / `_apres.png`.

---

## 5 · Délaissé — filtre surface minimale du bilan (item 5, anomalie AI1886)

Anomalie : 97407000AI1886 (Le Port, **9 m²**) servait un bilan complet « 0–1 logts / R+6 ».
Cause : aucun court-circuit surface dans le chemin bilan.

Geste (API lecture, `modules.py /modules/faisabilite/{idu}`) : sous `DELAISSE_MAX_M2` (**50 m²**,
seuil UNIQUE — celui des délaissés de voisinage d'`au_ouverture.py:127`, pas de nouvelle constante),
le bilan n'est **pas servi** ; un bloc `delaisse` factuel est servi à la place :
`« délaissé (9 m²) — bilan non servi sous 50 m² »`. La capacité reste servie (steps tracés, rien
de masqué) ; le moteur de faisabilité et le scoring ne bougent pas.
Fiche : tiroir « Faisabilité et bilan » affiche `délaissé (9 m²)` + bandeau explicatif ; BilanTab
non rendu. Témoin >50 m² vérifié inchangé (AB1908, 313 m² : bilan servi, `delaisse: null`).

**Captures** : `captures/fiche_delaisse_ai1886_avant.png` / `_apres.png`.

---

## 6 · Étiquette DVF sur la tuile Marché (item 6)

La tuile Marché disait « N ventes secteur » sans source ni fraîcheur. Ajout : ` · DVF — ventes
jusqu'à déc. 2025` (le libellé vient de `marche.dvf_couverture` servi par l'API — période RÉELLE
couverte en SQL, fraîcheur amont, jamais la date d'ingestion).

**Captures** : `captures/fiche_ar2714_avant.png` / `_apres.png` (tuile Marché).

---

## 7 · Clarté des libellés (item 7)

### Corrigés (les 2 mineurs M29 arbitrés)
- **« entrée en tête »** → `« entrée dans la sélection à la bascule du [date] — signal inchangé /
  en progression »` (app.py `_m28_badges`) : une chaude rang 1737 n'est pas « en tête » — visible
  sur AR2714 avant/après.
- **« V Viabilisation … »** : le nom du tiroir s'écrasait en « V » (flex). Fix : `minWidth` sur le
  nom + ellipse propre sur la valeur (Fiche.tsx RefDrawer) et dédoublonnage du préfixe
  « Viabilisation » dans la valeur (`viabValue`).

### Relevés, NON corrigés — vocabulaire produit, arbitrage Vic requis (régime [A], prudence)

| Libellé | Où | Ambiguïté | Piste |
|---|---|---|---|
| « Réserve foncière » | status.ts | évoque l'emplacement réservé PLU ; c'est un tier | « Réserve (scoring) » ? |
| « À creuser » | status.ts | générique | garder si assumé |
| « AU — à urbaniser » | status.ts | une AU peut être FERMÉE/conditionnelle | suffixe statut |
| « Zone fermée » | constructibilite.py | fermée ≠ clôture ; = règlement | « fermée à l'urbanisation » |
| « Viabilisation confirmée par les faits » | viabilisation.py | « confirmée » = faisceau ≥70 pts, pas certitude | tooltip existant suffit ? |
| « Parcelle non constructible » | constructibilite.py | géométrique ≠ réglementaire | « inconstructible (géométrie) » |
| « Brûlante » | status.ts | métaphore assumée produit | ne pas toucher sans Vic |
| « Potentiel ≥ /100 » | Header.tsx | potentiel de QUOI (= Score Q) | tip déjà présent (E1 M12) |

---

## 8 · Non-régression (item 8)

- **Aucun changement scoring/tiers/règles** : diff limité à `app.py` (WHERE/routes lecture),
  `modules.py` (endpoint faisabilité lecture), frontend (affichage/filtres). Aucun fichier de
  `src/labuse/scoring/` ni `src/labuse/faisabilite/` (hors import d'une constante existante) touché.
- **Golden** : `qa/golden_check.py` (API `LABUSE_SERVED_RUN=q_v8_calibre`, `LABUSE_M28_BADGES=1`) →
  **117/117 PASS, 0 FAIL, 0 incohérence base↔API**.
- Témoins servis inchangés : AR2714 (chaude rang 1737, ×4,5), ET2164 (brûlante rang 25, ×13,1),
  AI1886 (écartée ×1,1) — mêmes verdicts avant/après sur les captures.
- Suite pytest : 907 PASS ; **9 FAIL + 23 erreurs PRÉ-EXISTANTS** (vérifié à l'identique sur
  l'arbre SANS le geste M30 — `NameError: marque` dans `argumentaire.py:207` et apparentés,
  base main post-M29). **Hors périmètre M30 → noté, pas corrigé** (règle : fix hors périmètre =
  noter et s'arrêter).

---

## 9 · Captures (avant/après, chaque écran touché)

| Écran | Items couverts | Fichiers |
|---|---|---|
| Popover « + Filtre » | 2, 3 | `popover_filtres_{avant,apres}.png` |
| Liste filtrée declasse_bati_sature | 3 | `liste_declasse_bati_sature_{avant,apres}.png` |
| Fiche ET2164 (sans adresse BAN) | 4 | `fiche_adresse_absente_{avant,apres}.png` |
| Fiche AR2714 | 6, 7a, 7b | `fiche_ar2714_{avant,apres}.png` |
| Fiche AI1886 (9 m²) | 4, 5, 6 | `fiche_delaisse_ai1886_{avant,apres}.png` |

Méthode : mêmes URL/gestes, code « avant » = stash du geste M30 (API relancée sur le code avant),
« après » = geste appliqué. Scripts : `frontend/scripts/shot_m30*.mjs`.

---

# ANNEXE — REVUE VIC (M30-revue, 05/08/2026)

## A1 · « ×13,1 » sur les cartes saturées : chiffre parcelle RÉEL (coïncidence prouvée)

Le multiplicateur affiché est `s2.mult_base` de LA parcelle (aucune constante de tier).
Preuve en base (requête servie sur le run q_v8_calibre) :

```sql
SELECT parcelle_id, p_raw, mult_base, percentile, rang FROM parcel_p_score_v2
WHERE run_id='q_v8_calibre' AND parcelle_id IN
('97409000AR1260','97411000EL0201','97415000CX1395','97415000CX0939','97408000AB0275')
ORDER BY rang;
--  97409000AR1260 | 0.20438 | 13.14 | 100.0  |  20
--  97411000EL0201 | 0.20438 | 13.14 |  99.99 |  54
--  97415000CX1395 | 0.20438 | 13.14 |  99.99 |  58
--  97415000CX0939 | 0.20438 | 13.14 |  99.98 |  79
--  97408000AB0275 | 0.20438 | 13.14 |  99.98 |  84
```

Les 5 partagent `p_raw = 0,20438` : le modèle (m36-l2f-2026) sature sur le même plateau de
probabilité pour ces profils — mult = p/taux_base (pipeline.py:390, arrondi 2 déc.) donne
donc 13,14 pour chacune. Contexte : 99 parcelles du run partagent exactement ce plateau ;
6 saturées sont à 13,14 ; 80 valeurs distinctes de mult parmi les saturées ; max global
64,31 (13,14 n'est PAS un plafond). Aucun changement de code — le chiffre servi est bien
celui de la parcelle (boussole respectée).

## A2 · AI1886 : le guard couvre la tuile ENTIÈRE

La sous-ligne servait encore « R+6 · SDP 18 m² · calcul tracé ». Fix (Fiche.tsx) : quand
`delaisse` est servi, la micro-ligne devient « surface 9 m² · seuil délaissé 50 m² · bilan
non servi ». Témoin > 50 m² inchangé (AR2714 : « R+2 · SDP 822 m² · calcul tracé »).

## A3 · Titre de tuile tronqué : wrap propre

L'ellipse remplaçait un écrasement — le titre restait coupé. Fix (RefDrawer) : le NOM passe
à la ligne (lineHeight 1.25, plus d'ellipse/nowrap sur le titre), la VALEUR garde son
ellipse. « Viabilisation et réseaux » se lit en entier sur les 2 fiches témoins.

## Libellés arbitrés Vic (3 corrigés dans ce geste — frontend uniquement)

1. « Déclassée — zone fermée » → **« Déclassée — fermée à l'urbanisation »** (status.ts).
2. « Déclassée — non constructible » → **« Déclassée — inconstructible (géométrie) »**.
3. « AU — à urbaniser » (légende famille) → **« AU — à urbaniser (statut : ouverte /
   fermée / inconnue) »**. Note d'interprétation : c'est un libellé de FAMILLE (légende
   carte) — le statut PAR PARCELLE vit déjà dans les motifs (« AU fermée » / « AU à statut
   inconnu ») ; un suffixe par parcelle dans la fiche exigerait un changement du
   `zonage_detail` servi (golden) — hors périmètre, à mandater si voulu.

Les 5 autres libellés : consignés au BACKLOG (TRAIN 4, « Vocabulaire produit »), dont
« Réserve foncière » marqué PRIORITAIRE (collision emplacement réservé PLU). Aucun geste.

## Non-régression

Golden **117/117 PASS, 0 incohérence** après le geste. tsc 0 erreur. Diff = Fiche.tsx,
status.ts, BACKLOG.md, scripts de capture — aucun fichier scoring/API.

## Captures (qa/m30/captures_revue/)

| Point | Fichiers |
|---|---|
| A2 + A3 (fiche AI1886) | `fiche_ai1886_{avant,apres}.png` |
| A3 (fiche AR2714) | `fiche_ar2714_{avant,apres}.png` |
| Libellés 1-2 (popover) | `popover_libelles_{avant,apres}.png` |
| Libellé 3 (légende zonage) | `legende_zonage_au_{avant,apres}.png` |
