# M11 · AUDIT SURFACE C — L'IA explique un chiffrage de faisabilité existant

**Date** : 2026-07-15. Lecture seule (code + base + appels réels sur instance dev). Aucune modif, aucun commit.

**Parcelle-exemple** (fil rouge, réelle) : **97415000EL0387** — Saint-Paul (La Saline), **chaude**, 2 937 m², zone **U5c**. Tous les chiffres ci-dessous sont ceux réellement produits par le moteur pour cette parcelle.

---

## 1. LE MOTEUR DE FAISABILITÉ (`faisabilite/`)

### CE QUI EXISTE
`faisabilite/engine.py` → `estimate_capacity(rules, surface, contraintes, hyp, emprise_geo)` : calcule une **enveloppe constructible + une fourchette de capacité** à partir du règlement PLU (calibré par YAML communal) et de la géométrie réelle. Orchestré par `db.py:fiche_payload(session, parcel_id)` → payload JSON de la carte de faisabilité de la fiche.

**ENTRÉES exactes consommées :**
- **Parcelle** : `surface_m2`, la **géométrie cadastrale réelle** (EPSG:2975) pour l'emprise insetée des reculs, la commune/zone.
- **Règles PLU** (`plu_rules.resolve_zone` depuis `config/plu_<commune>.yaml`) : reculs voirie/limites, `he_m`/`hf_m` (hauteur), `emprise_sol_pct`, `pleine_terre_pct`, places/logement, `constructible_neuf`, `habitat`, sources article/page. Zone non outillée → **estimation générique prudente** (hé 9 m ≈ R+2), flag `calibree=False`.
- **Contraintes réunionnaises** : `pente_pct`, `alea_ppr`, `bande_littorale`, `agricole_sar` (modulation).
- **Hypothèses** (`Hypotheses`, éditables YAML) : hauteur d'étage 3 m, coef occupation 0,45, coef rendement 0,80, 65–80 m²/logt, 25 m²/place, plafond densité 30 logts/ha/niveau.

**SORTIES exactes (`fourchette` + `steps` + `residuel`) :**
| Sortie | Champ | Valeur réelle (EL0387) |
|---|---|---|
| Niveaux (gabarit) | `niveaux` / `niveaux_max` / `hauteur_m` | **R+1** / 2 / **6 m** |
| Emprise constructible au sol | `emprise_constructible_m2` | **2 223 m²** |
| Emprise bâtie max | `emprise_batie_max_m2` | 1 000 m² |
| Surface de plancher brute | `surface_plancher_m2` | **2 001 m²** |
| Surface habitable vendable | `shab_vendable_m2` | **1 278 m²** |
| Logements (au sol / sous-sol) | `logements_au_sol` / `_sous_sol` | **17–18** / 17–18 |
| Régime stationnement | `stationnement_regime` | borné |
| Verdict littéral | `verdict` | « **R+1 · au sol ~17-18 / sous-sol ~17-18 logts** » |

Plus : `residuel` (potentiel résiduel = capacité max × bâti existant) → **SDP résiduelle 1 968 m²**, « terrain nu — potentiel quasi intégral », sous-densité (taux d'emprise 1 %).

**La donnée la plus riche = les `steps`** : 11 étapes tracées, chacune `{label, formule, valeur, source, prov}`. Extrait réel :
```
• Emprise au sol — reculs (géométrie réelle) : ~2223 m²   [Art. 7 (séparatif) ; recul voirie en sus]
• Niveaux constructibles : R+1                             [Zone U5c, Art. 10.2, p.~223]
• Surface de plancher brute : ~2001 m²                     [dérivé occupation×hauteur]
• Surface habitable (rendement) : ~1601 m²                 [hypothèse rendement]
• Logements (avant plafonds) : ~20 à 25                    [hypothèse surface logement]
• Plafond de densité (filet de sécurité) : ≤ 18 logts      [hypothèse densité (ex-COS)]
```
Accompagnés de 7 `hypotheses` (« hauteur d'étage 3 m ; niveaux comptés sur hé »…), `avertissements` (« recul voirie 4 m en sus… »), `modulation` (pente/PPR/littoral).

### CE QUE ÇA PRODUIT
Un chiffrage **entièrement tracé** : chaque nombre a sa formule, sa source (article PLU) et son type de provenance (`prov` : `sourcee` / `estimee` / `derive` / `""`). C'est **exactement le matériau qu'une IA pourrait expliquer** : elle n'aurait rien à calculer, seulement à mettre en récit des `steps` déjà chiffrés et sourcés.

### LIMITES
- Beaucoup d'`estimee`/hypothèses (occupation 45 %, rendement 80 %, densité) : le chiffrage est **indicatif**, jamais un certificat. Une explication devrait porter ces réserves.
- Les `steps` sont produits mais **non exposés au client** (cf. §4) ni **jamais transmis à un modèle** (cf. §5) : le moteur explique déjà « pourquoi ce chiffre » dans `formule`+`source`, mais personne ne le lit.

---

## 2. LA CHARGE FONCIÈRE (onglet Bilan)

### CE QUI EXISTE
Deux calculs, tous deux dans `faisabilite/bilan.py`, réutilisant la même arithmétique :

**(a) Bilan promoteur automatique** — `compute_bilan(shab_vendable, surface_terrain, prix, hyp, contexte_eco, bilan_params)`, calculé dans `fiche_payload` dès que la parcelle est constructible. **Bilan à rebours** : `charge foncière = CA×coef − coût construction − VRD`.
- **Entrées LABUSE (sourcées/dérivées)** : `shab_vendable` (du moteur faisa), **prix de sortie DVF** (`sector_price`, ventes comparables secteur, avec fiabilité fiable/fragile), surface terrain, secteur PLU, prescriptions (mixité sociale Art. 2, eaux pluviales, vue mer).
- **Entrées paramétrées (estimées, éditables par secteur)** : coût construction €/m² plancher, VRD base + majorations pente/assainissement, honoraires, frais financiers, marge cible, prix LLS.
- **Sortie** : `ca {bas,central,haut}`, `charge_fonciere {bas,central,haut,par_m2_terrain}`, `verdict`, `steps` (8, avec `prov`), `params`, `avertissements`.

**Exemple réel (EL0387)** :
| Étape (bilan) | Valeur réelle | prov |
|---|---|---|
| SHAB vendable | ~1 278 m² | derive |
| Prix de vente (DVF La Saline) | 6 000 €/m² (médiane ; min 1 333 / max 4 710) — **fragile** | sourcee |
| CA pondéré (mixité déclenchée) | 5 070 €/m² médiane pondérée | estimee |
| VRD / viabilisation | ~330 k€ | estimee |
| Chiffre d'affaires potentiel | ~6,5 M€ | derive |
| Coût de construction | ~3,1 M€ | estimee |
| Marge + frais | 24 % du CA | estimee |
| **Charge foncière acceptable** | **médiane 1,5 M€ ≈ 513 €/m² terrain** | derive |
→ verdict : « Simulation indicative (prix de sortie **fragile**) — CA ~6,5 M€ · charge foncière médiane ~1,5 M€ ».

**(b) Calculette éditable client** — `compute_calculette(shab_vendable, surface_terrain, prix, cout_construction_m2, marge_frais_pct, prix_demande_eur)`. **Ligne rouge assumée dans le code** : SDP vendable et prix DVF viennent du moteur (sourcés) ; **le coût de construction et la marge sont SAISIS par le promoteur** (jamais estimés par LABUSE). Sortie = charge foncière « selon vos hypothèses » + **verdict d'achat** (`supportable` si charge foncière médiane ≥ prix demandé, `ecart_eur`/`ecart_pct`). Servie côté fiche (recalcul serveur) et injectée au PDF.

### CE QUE ÇA PRODUIT
Des **chiffres bruts tracés** (steps + provenance + verdict littéral court), pas une explication en prose. Le `verdict` est une phrase, mais **figée et dense** (« Simulation indicative (prix fragile) — CA ~6,5 M€ · charge foncière médiane ~1,5 M€ (fourchette …) »), pas une explication pédagogique du bilan à rebours.

### LIMITES
- Le bilan **dépend d'hypothèses** (coût, marge, VRD) et le prix DVF est souvent **fragile** (échantillon insuffisant → repli appart+maison) : toute explication doit marteler « ordre de grandeur, pas bilan ferme » (déjà dans `avertissements`).
- Les 8 `steps` du bilan (le raisonnement CA − coûts − marge) **ne sont pas racontés** : le client voit le résultat, pas le « pourquoi 1,5 M€ ».

---

## 3. LE COPILOTE PROJET (objet Projet + entretien de cadrage)

### CE QUI EXISTE
- **Objet Projet** (`models.py:635`, table `projets`, DDL `api/projets.py`) : `{nom, fiche (JSONB), filtres (JSONB dérivé), programme (JSONB), statut, derniere_execution_at}`. **Exemple réel en base** (projet id 22) :
  ```json
  nom: "LES LILAS"
  fiche: {"type_programme":"etudiant","ampleur":{"logements":40},
          "perimetre":{"mode":"secteur","secteur":"Ouest"},"criteres_libres":"Budget serré"}
  filtres: {"sdpMin":2760,"communes":["Le Port","La Possession","Saint-Paul","Les Trois-Bassins","Saint-Leu"]}
  programme: {"type":"etudiant","niveaux":2,"batiments":1,"logements_par_batiment":40,"surface_unite_m2":60}
  ```
- **Entretien de cadrage** (`ProjetEntretien.tsx` → `POST /ia/entretien`, `ia.py:595`) : dialogue IA **haiku** qui, à chaque tour, **RECUEILLE** une dimension manquante (périmètre → type → ampleur → gabarit → contraintes → budget), renvoie `{fiche mergée, reformulation neutre, questions (chips), nom, pret}`, validé par `ENTRETIEN_SCHEMA`. Un **garde-fou doctrine** (`_neutralise_opinion`) purge toute opinion de marché (« plus porteur », « je recommande »).
- **Dérivation 100 % déterministe** (`api/projets.py` : `derive_filtres`, `derive_programme`, `derive_sdp_besoin`) : fiche → filtres SQL + programme M22. `sdp_besoin = logements × 60 × 1,15`.
- **Confrontation aux parcelles** : `/projets/apercu` → si programme défini, **M22 sens 2** (`modules.py:743`, `faisabilite_sens2`) : SDP résiduelle ≥ sdp_min, hauteur PLU ≥ hauteur_min → top parcelles ; sinon `_q_v2_list` (run servi).

### CE QUE ÇA PRODUIT — la « restitution » actuelle
Chaque parcelle du top porte un **« pourquoi »** = 3-5 **lignes assemblées par le moteur** (`_pourquoi_lignes`, `projets.py:207`), **pas une prose IA** :
```
· Chaude v2 · qualité 72/100
· SDP résiduelle 1 968 m² pour 2 760 m² requis — 71 % du besoin
· Hauteur PLU 6 m (à instruire), zone U5c
· Commune carencée SRU — forte demande de logement social
```
Affiché dans la restitution web (`App.tsx`, `data-ia-pourquoi`) et le **PDF projet** (`pdf_projet.py`), avec la mention explicite : « le "pourquoi" est assemblé depuis le moteur déterministe ; **l'IA n'en produit aucun** [chiffre] ».

### Part IA vs déterministe
| Étape | Qui |
|---|---|
| Détecter l'intention projet, mener l'entretien, proposer un nom | **IA (haiku)** — recueille, ne calcule jamais |
| Valider la fiche (schéma), dériver filtres/programme, M22, « pourquoi » | **Déterministe** (SQL + formules fixes) |

### LIMITES
- **Il n'existe AUCUNE restitution en langage clair d'un CHIFFRAGE** : le « pourquoi » est une **liste de puces factuelles** (verdict, SDP vs besoin, hauteur, SRU), pas une explication rédigée d'un calcul de faisabilité/bilan. L'IA du copilote **cadre le besoin**, elle **n'explique pas le chiffrage** d'une parcelle.
- L'entretien tourne en **repli** sans clé Anthropic (`fallback:true`).

---

## 4. L'AFFICHAGE ACTUEL (comment le client voit le chiffrage)

### CE QUI EXISTE (`frontend/src/components/fiche/Fiche.tsx`)
Le chiffrage vit dans l'**onglet « Bilan »** de la fiche (`BilanTab()`, ~l.705), en **sections énumérées** (pas un tableau de steps) :
1. **CAPACITÉ** : verdict, niveaux, emprise bâtie max, SDP, SHAB vendable, stationnement, bandeau, flag zone non calibrée.
2. **MARCHÉ — prix de sortie** : médiane DVF €/m², n ventes, rayon, fiabilité, fraîcheur.
3. **CALCULETTE DE CHARGE FONCIÈRE** (`Calculette()`, ~l.507) : **interactive** — champs éditables `Coût construction €/m²` + `Marge & frais %` (`HypInput`), recalcul serveur (~350 ms), résultat « Charge foncière supportable — selon vos hypothèses » (central € + fourchette + €/m² terrain), + **verdict d'achat** si `Prix demandé` saisi (✓ Supportable / ✗ trop cher + écart), + avertissements.
4. **FISCAL & LEVIERS** (QPV, TVA, prime vue mer), **RTAA DOM**.

**Prose IA existante sur la fiche** : la **barre IA `AskBar`** (M11 Surface A) et le **panneau IA** (`IAPanel` : Synthèse / Pourquoi ce score). Les **chips de provenance** (`ProvChip` : Sourcé/Estimé/Absent) n'apparaissent **que sous la réponse de l'AskBar**.

### CE QUE ÇA PRODUIT
Le client voit des **chiffres clés + une calculette interactive**, jamais le détail des étapes. La provenance (`prov` du moteur : sourcee/estimee/derive) **n'est pas affichée sur les chiffres de faisabilité/bilan** eux-mêmes — elle n'existe visuellement que dans la barre IA.

### LIMITES / où une explication IA se poserait
- **Aucune prose n'explique le chiffrage** : pas de « voici pourquoi 17-18 logements et 1,5 M€ de charge foncière ». Les `steps` (le raisonnement) ne sont **pas rendus** (ni en tableau, ni en prose).
- **Emplacements naturels d'une explication** : (a) dans l'onglet Bilan, sous la CAPACITÉ / sous la Calculette ; (b) via l'**AskBar** déjà présente sur la fiche (« Combien je peux construire ? » est déjà un chip) ; (c) le PDF one-pager de comité.

---

## 5. LE SOCLE — le chiffrage peut-il alimenter `core.complete` ?

### CE QUI EXISTE — **oui, et c'est déjà branché en partie**
Trois chemins passent déjà par le socle et **touchent le chiffrage** :

1. **Barre de fiche (Surface A, `fiche_ask.py`)** — `POST /parcels/{idu}/ask`. Son contexte autorisé inclut un **Fact `faisabilite` (ESTIME)** = résumé `{zone_resolue, niveaux, hauteur_m, surface_plancher_m2, logements_au_sol, charge_fonciere_centrale, bilan_fiable}`, et **route vers sonnet** pour toute question de faisabilité/charge foncière. Grounding + validation des chiffres (couche 2) du socle actifs. **Appel réel sur EL0387** (« Combien je peux construire et quelle est la charge foncière ? ») :
   > « La parcelle de **2 937 m²** en zone **U5c** permet d'estimer une surface de plancher d'environ **2 001 m²** en **R+1** (hauteur max. **6 m**), soit entre **17 et 18 logements** — ces chiffres sont estimés… La charge foncière ressortant du bilan est estimée à **1 500 000 €**… »
   *(sources citées : faisabilite, zone_plu, reglement_regles, dvf_prix_m2_bati, icd_bande, statut_tier.)*
   → **Une IA explique DÉJÀ le RÉSULTAT du chiffrage**, sourcé et validé, à la question de l'utilisateur.

2. **Assistant « Expliquer cette parcelle »** (`assistant.py`, `kind="explain"`, endpoint `GET /parcels/{idu}/explain`) — prose de synthèse groundée sur `assistant_facts`, qui inclut un **bloc `faisabilite` (résumé) + `bilan_promoteur` (verdict, charge_fonciere, fiable)**. Repli déterministe `rules_summary` sans clé.

3. **Entretien projet** (`kind="entretien"`) — cadrage, ne chiffre pas (cf. §3).

Le socle sait donc **déjà** produire une prose sourcée + valider les chiffres (aucun nombre inventé) à partir d'un résultat déterministe.

### CE QUE ÇA NE FAIT PAS (encore)
- Ce qui est donné au modèle = le **RÉSUMÉ** du chiffrage (6-7 champs), **jamais les `steps` détaillés** (grep : aucun `steps` dans `fiche_ask.py`/`assistant.py`). Donc l'IA peut **restituer le résultat** mais **ne peut pas expliquer la DÉRIVATION** (« emprise 2 223 → occupation 45 % → SDP 2 001 → rendement → 17-18 logts ; puis CA 6,5 M€ − coûts − marge → 1,5 M€ »), faute d'avoir les étapes/formules/sources en contexte.
- L'endpoint `/explain` existe côté backend mais **le front ne l'appelle nulle part** (grep front vide) — **orphelin**.
- La provenance moteur (`prov` des steps) n'est pas mappée vers les étiquettes du socle (Sourcé/Estimé) pour les chiffres de faisabilité.

### LIMITES
Le « répondre sans halluciner sur un chiffrage » est **déjà couvert** (contexte autorisé + validation des nombres). Ce qui manque = **donner les `steps` (déjà tracés, sourcés, avec `formule`/`source`/`prov`) au contexte** pour passer d'une **restitution du résultat** à une **explication de la dérivation** — le moteur produit ce matériau, personne ne le lit encore.

---

## Synthèse des limites (sans reco)
1. **Le moteur trace déjà tout** (steps `formule`/`source`/`prov`, hypothèses, avertissements) — faisabilité (11 steps) et bilan (8 steps) — mais ce matériau **n'est ni affiché au client ni transmis à une IA**.
2. **L'affichage** montre des chiffres clés + une calculette interactive ; **aucune prose n'explique le chiffrage**, et la provenance moteur n'est pas visible sur ces chiffres.
3. **Le copilote projet** cadre le besoin (IA recueille, moteur dérive) et restitue un **« pourquoi » en puces déterministes** — pas une explication rédigée d'un chiffrage.
4. **Le socle explique déjà le RÉSULTAT** d'un chiffrage (Surface A AskBar + `/explain`), sourcé et validé — mais depuis un **résumé**, jamais depuis les **steps** ; expliquer la **dérivation** reste à faire, et `/explain` est orphelin côté front.

*Aucune reco, aucune modif. Fin de l'audit.*
