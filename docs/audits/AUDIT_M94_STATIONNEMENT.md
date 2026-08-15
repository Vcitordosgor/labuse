# AUDIT M94 — stationnement réglementaire : la variabilité des barèmes

**Mandat M94 · Phase 1 (mesure, lecture des YAML seuls) · branche `feat/m94-stationnement` · NON mergé**

Doctrine : *mesurer avant d'affirmer* · *source réglementaire > géométrique* · *un critère
= un seul endroit* · *Sourcé / Estimé / Absent* · *aucune valeur inventée*.

## 0. Correction de la prémisse (mesuré)

La prémisse du mandat — « la norme vit en texte libre (`regles_transverses.stationnement`),
le moteur lit un `place_m2` global » — est **partiellement inexacte**. Mesure :

- La norme EST déjà extraite **par zone** dans le champ `stat_logement` de chaque zone
  (ex. `stat_logement: "1,5 place / logement"`, avec `stat_src` = citation d'origine et
  `stat_note` pour les cas « Sans objet »). **20 communes sur 21** l'ont renseigné (14–35
  zones chacune).
- Le moteur lit cette norme via `ZoneRules.places_par_logement()` (plu_rules.py:51) qui
  REGEX-extrait un nombre de `stat_logement`, PAS le `place_m2` global.
- `place_m2` (= 25.0) est la **conversion places→m²**, pas la norme. Il est distinct.
- `regles_transverses.stationnement` est le **barème complet / citation** (texte libre) ;
  `stat_logement` par zone en est la **valeur extraite** (déjà simplifiée).

Donc la « structure exploitable par commune » que le mandat imagine construire est
**largement déjà en place** (per-zone, single-value). Le vrai sujet est ailleurs : la
FLATTENING des barèmes conditionnels et des TROUS de parsing/statut. Détail ci-dessous.

## 1. La forme de chaque norme (21 communes ; 3 sans YAML)

3 communes sans YAML (donc génériques, non calibrées) : **Saint-André, Saint-Leu,
Saint-Philippe**.

Valeur résidentielle dominante extraite (`ppl` servi), par commune :

| Commune | ppl dominant (place/logt) | Dimensions CONDITIONNELLES présentes dans le texte libre (non captées par ppl) |
|---|---|---|
| Cilaos | 1,5 | commerces ≥ 50 % SHON (unité %SHON) ; **« 1 place = 25 m² »** (seule conversion réglementaire explicite) |
| Entre-Deux | 2,0 | +1 visiteur/5 logts ; LLS 1 max +1 visiteur/10 |
| La Plaine-des-Palmistes | 1,5 (>30 m²) / 1 (<30) | **seuil de surface SDP** ; arrondi entier inférieur |
| La Possession | 2,0 | seuil ≤50/>50 m² ; +1 visiteur/5 ; LLS 0,5 à <500 m TCSP |
| Le Port | 0,3 | +1 visiteur/100 m² SDP (unité m²) ; LLS 0,2 +8/1000 m² ; part en ouvrage |
| Le Tampon | 1,0 (individuel) | **collectif 0,5 par CHAMBRE/studio** (unité chambre) ; LLS 1 max |
| Les Avirons | 1,5 | collectif « 1,25/logt OU 1/35 m² SDP, la + productive » ; LLS 1 max ; +0,5 voie lotissement |
| Les Trois-Bassins | 1,5 | collectif « OU 1/35 m² », **plafond 2/logt** ; LLS 1 max ; lotissement +0,5 |
| Bras-Panon | 1,0 | **seuil ≤100/≥100 m²** (→ 1 / 1,5) ; LLS 1 max ; hôtel 1/3 chambres |
| Petite-Île | 1,0 | LLS 1 sauf **LLTS 0 place** ; 20 % perméable ; activités % SDP |
| Saint-Denis | 1,5 (« 1 à 1,5 ») | seuil <100/≥100 m² ; logement aidé 1 |
| Saint-Joseph | 2,0 (et 1,0 selon zone) | RPA 0,5 +2 visiteurs/10 (clé `stationnement_rpa`) |
| Saint-Louis | 2,0 (UZ 1,5) | sociaux 1 ; >10 logts +0,5 place PUBLIQUE |
| Saint-Paul | 2,0 / 1,5 / 1,0 selon zone | LLS 1 (clé `stationnement_aide`) ; 10 zones a_verifier ; 1 zone exempt |
| Saint-Pierre | 1,5 / 1,0 selon zone | **norme par zone (Art. Z6)** ; réductions -30 % TCSP, mutualisation, petites parcelles exemptées ; **4 zones « 1/75 m² SDP » → None** |
| Sainte-Marie | 1,5 | seuil <100/≥100 ; <500 m gare 1 (aidés 0,5) |
| Sainte-Rose | 2,0 | (règle simple) |
| Sainte-Suzanne | 2,0 | seuil <50/≥50 ; >10 logts +0,5 publique ; LLS 1 (0,5 TCSP) |
| Salazie | 2,0 | seuil ≤50/>50 ; LLS/RPA/résid. univ. 1 |
| L'Étang-Salé | **a_verifier** (8 zones) | « tableau non extractible (2.7.3), à compléter en lecture visuelle » |
| Saint-Benoît | **aucun `stat_logement`** | norme en texte libre SEULEMENT (1/logt ; >5 logts +visiteur ; aidés 1/2) — non extraite |

**Dimensions récurrentes** : type de logement (individuel/collectif/LLS/LLTS/RPA), unité
(par logement / par chambre / par m² SDP / % SHON), seuil de surface SDP, plafonds
(« MAXIMUM »), exemptions/réductions (TCSP, petites parcelles, LLTS 0), visiteurs.

## 2. La convertibilité places → surface (`place_m2`)

- **Valeur** : `place_m2 = 25.0` (Hypotheses dataclass, engine.py:35), **déclarée à 25.0 dans
  les 21 YAML** (uniforme).
- **Nature** : **modélisation** — le moteur écrit « 1 place de stationnement supposée 25 m²
  (au sol restant) » (engine.py:364). Marqué « supposée » (Estimé-like) déjà.
- **Réglementaire ?** UNE seule commune donne un m²/place au règlement : **Cilaos, « 1 place =
  25 m² »**. Les 25 m² coïncident donc avec le réglementaire de Cilaos mais sont de la
  modélisation partout ailleurs (aucune autre commune ne le déclare au règlement lu).
- **Usage** : engine.py:355 `log_max = sol_dispo / (ppl × place_m2)` — le stationnement au sol
  BORNE la capacité (scénario au sol) ; scénario sous-sol/silo = non borné. C'est structurant
  quand ppl est grand (2 places × 25 = 50 m²/logt au sol).

## 3. Ce qui est chiffrable, ce qui ne l'est pas, et les TROUS (mesuré)

Le moteur a déjà 4 régimes (engine.py:349-372) : nombre → **borne** (Sourcé) ; `EXEMPT` →
« non réglementé, capacité non bornée » (dit) ; `A_VERIFIER` → « à vérifier, garde-fou non
appliqué » (dit) ; **None → `non_applique` SILENCIEUX** (rien dit).

- **Chiffrable (Sourcé)** : 18 communes ont des zones à « X place/logement » nette → ppl 0,3–2,0.
- **Non chiffrable, DÉJÀ signalé** : `A_VERIFIER` (L'Étang-Salé 8z, + zones à Possession/
  Saint-Denis/Saint-Paul/Saint-Pierre) ; `EXEMPT` (1 zone Saint-Paul).
- **TROUS à combler** (le cœur du mandat) :
  1. **None SILENCIEUX** : le régime `non_applique` sur `ppl=None` ne DIT rien — devrait dire
     « norme de stationnement non modélisable pour cette commune/zone » (Phase 3.2 du mandat).
  2. **Unité par m² SDP non parsée** : Saint-Pierre « 1 place par tranche de 75 m² SDP » (4
     zones) → le regex `X place/logement` renvoie **None** → stationnement silencieusement non
     appliqué. L'unité par-SDP existe (Le Port visiteur/100 m², Cilaos commerces %SHON) et
     n'est pas modélisée.
  3. **Saint-Benoît sans `stat_logement`** : la norme (texte libre : 1/logt) n'est pas extraite
     par zone → ppl None partout → stationnement non appliqué, sans le dire.
  4. **Barèmes conditionnels flattenés** : le collectif « 0,5/chambre » (Le Tampon), les seuils
     de surface, les plafonds LLS, les « OU 1/35 m² » sont réduits au ppl dominant (individuel).
     La citation d'origine reste dans le texte libre, mais la nuance n'atteint pas le calcul.
  5. **Départage des seuils non documenté** : sur un barème de surface, le regex prend le nombre
     collé à « place/logement » — La Plaine → 1,5 (tranche >30 m²) ; Saint-Denis « 1 à 1,5 » →
     1,5. Choix implicite du MAJORANT, non tracé.

## STOP 1 — Vic tranche la structure cible

La structure « valeur unique par (commune, zone) » **existe déjà** (`stat_logement` +
`places_par_logement`). Le vrai choix n'est donc pas « barème vs valeur unique » à partir de
zéro, mais **jusqu'où structurer les dimensions conditionnelles**, sachant que le calcul servi
modélise un programme résidentiel générique (le ppl résidentiel domine ; LLS/collectif/
visiteurs/seuils sont secondaires pour une estimation de capacité). Trois options :

1. **Consolider l'existant (minimal, honnête)** — garder la valeur unique par zone ; COMBLER
   les trous : parser l'unité par-m² SDP, extraire Saint-Benoît, faire DIRE le None (« non
   modélisable »), tracer le départage de seuil. Aucun barème structuré ajouté.
2. **Barème structuré par dimension** — remplacer `stat_logement` texte par une structure
   {type, seuil_surface, unité, plafond, exemption} exploitée par le moteur. Capture tout, mais
   lourd, et le gain sur la capacité SERVIE reste à démontrer (c'est l'objet de la Phase 2 / STOP 2).
3. **Hybride** — valeur unique là où la règle est simple (le cas dominant), barème structuré
   SEULEMENT pour les formes qui changent un chiffre servi (à identifier en Phase 2).

Recommandation mesurée : **option 1 ou 3**, l'option 2 (barème complet partout) paraît sur-
dimensionnée tant que la Phase 2 n'a pas montré qu'une dimension conditionnelle bouge un chiffre
servi. La Phase 2 (STOP 2) mesurera justement l'impact de la norme réelle sur la capacité/bilan.

**Rien n'est extrait ni branché avant les deux arbitrages** (interdit du mandat).
