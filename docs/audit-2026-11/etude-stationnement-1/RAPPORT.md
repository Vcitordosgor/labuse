# Audit du stationnement dans l'Étude de faisabilité — ETUDE-STATIONNEMENT-AUDIT-1

**Branche** `audit/etude-stationnement-1` · worktree `~/Desktop/labuse-stationnement` · **lecture seule, aucune modification de code.**
Le livrable est ce rapport.

## Cadre et sources (révisé — avec la base locale)

Cette version lit le **texte réel des règlements servis par LABUSE**, dans la base PostgreSQL locale (table `plu_reglement_extrait`, texte verbatim extrait des PDF opposables). **Toutes les citations réglementaires ci-dessous sont VERBATIM de la base.** Plus aucune valeur n'est reprise d'une relecture extérieure dès lors que le texte est lisible en base.

Deux sources distinctes, ne pas les confondre :
- **Barème ingéré** = ce que LABUSE *applique* : feuille `regles.stationnement` des YAML `config/plu_destinations/<insee>_*.yaml` (valeur, statut `propose`/`valide`, citation).
- **Texte opposable** = ce que dit le PLU : `plu_reglement_extrait` (verbatim, article, page).

**Limites honnêtes de la base** (dit, jamais comblé par invention) — le texte de la norme de stationnement **n'est pas servi** pour :
- **L'Étang-Salé (97404)** : extraction partielle (12 pages sur ~97) ; les articles 2.7/2.7.3 ne sont pas dans la table.
- **Saint-André (97409)** et **Saint-Leu (97413)** : **aucune ligne** dans la table (règlement non ingéré).
- **La Plaine-des-Palmistes (97406)** : seule la « Définition » §12.1 est en base ; le barème chiffré renvoie à une **annexe non ingérée**.
- **Saint-Denis (97411)** : le barème général est dans « Dispositions générales — XVII. Stationnement », **non ingéré** comme ligne ; seuls des fragments de zone existent.
- **Saint-Philippe (97417)** : commune au **RNU**, aucun PLU.

Setup effectué pour cette session : `.env` copié depuis `~/Desktop/labuse-main` (base via le rôle `openclaw`), dépendances front installées (`frontend/node_modules`). Lecture de la base vérifiée (relecture d'une phrase connue).

---

## 1. Comment le moteur choisit et applique la règle de stationnement

(Inchangé par la lecture en base — confirmé.)

### 1.1 Stockage
Un YAML par commune, feuille `regles.stationnement`, trois formes **déclarées** (`destinations.py:546`) : `par_logement` (scalaire plat), `par_typologie` (lignes bornées par pièces **ou** surface, avec `destination` et `arrondi`), `par_m2_sdp` (place par tranche de m²). Verrou : seule une feuille `valide` **avec citation** sert un verdict « Réussi ».

### 1.2 Lecture — le point dur
`_bareme()` (`regles.py:258-283`) ne construit un barème **que** depuis `par_logement` et `par_typologie`. **`par_m2_sdp` est déclaré mais consommé par aucun code** (`grep` : commentaires seulement). Une règle « 1 place par tranche de N m² » **ne peut structurellement pas être servie** → elle reste `propose/None`, le contrôle tombe en « À confirmer ». C'est exactement le cas de **Saint-Pierre Ud** (§3.2).

### 1.3 Distinctions perdues — trois causes structurelles
1. **Le moteur ne dessine que du collectif** : `poser_barre` (`geometrie.py:278`) empile des modules T1–T4 (`conventions.yaml` : 30/56/70/80 m², 1–4 pièces) ; aucun chemin individuel.
2. **`destination="collectif"` codé en dur** à tous les appels du moteur (`capacite.py:81`, `service.py:336/451/823`). Même quand un `par_typologie` porte une ligne individuelle et une collective, le moteur prend toujours la collective.
3. **Aucune notion de taille d'opération, visiteurs, logement social** dans le barème (seuils réservés à la mixité). Les suppléments « > 5 logements », « 1 visiteur / N m² », « 1 place / 2 logements aidés » des règlements **ne sont jamais appliqués**.

De plus, `par_logement` **force `arrondi="superieur"`** (`regles.py:264`), ignorant le YAML ; seul `par_typologie` lit l'arrondi. Plusieurs textes disent « arrondi à l'entier **inférieur** » (Sainte-Rose, Trois-Bassins), d'autres « **supérieur** » (Sainte-Suzanne, Salazie) : le plat applique toujours supérieur.

### 1.4 Places → surface
`_places_imposees` (`capacite.py:71-87`) somme `n × places_pour(...)` par typologie dessinée puis arrondit → `places_imposees`. Les places **dessinées** (2,5 × 5 m) sont comptées séparément ; surface = places + allées (5 m) + accès (4 m) ; sous-sol 25 m²/place. Contrôle (`controles.py:415-426`) : barème servi ⇒ **Réussi** si `places ≥ places_imposees`, sinon **Échoué** ; **barème non servi ⇒ « À confirmer »** (bloquant pour « Exploitable »). **Le stationnement ne rétroagit pas sur l'esquisse** : le moteur dessine l'enveloppe, puis compte ; barème absent ⇒ 0 place, aucune capacité retranchée.

---

## 2. Les 24 communes — barème ingéré vs texte réel du PLU

**Écart** : **absent** (aucun barème `valide` servi) · **incomplet** (plat servi, distinctions du texte perdues) · **faux** (mauvaise destination/branche appliquée) · **juste** (plat servi = texte, taux uniforme). Jugé pour un **programme collectif** (ce que le moteur dessine). Citations **verbatim de la base** ; quand le texte n'est pas en base, c'est dit et la source du barème reste le YAML.

| Commune | Barème servi | Art. · p. (base) | Texte RÉEL du PLU (verbatim, habitation) | **Écart** |
|---|---|---|---|---|
| **Les Avirons** (97401) | `par_logement` **1,5** | U 12 · p.16 | « 1,5 place par logement. En outre, 0,5 place supplémentaire sur voie par terrain, pour les lotissements de plus de 5 lots. **Dans le cas d'opération d'habitat collectif, la norme 1,5 est ramenée à 1,25 place par logement ou une place par tranche de 35 m² de surface de plancher. La norme produisant le plus de places devra être retenue.** » | **incomplet** — la **règle collective** (1,25/logt **ou** 1/35 m², max) et le supplément > 5 lots **non appliqués** (1/35 m² peut dépasser 1,5 pour les grands logements → sous-compte possible) |
| **Bras-Panon** (97402) | `par_logement` **1,0** | UA/UB/UC/UD 12 · p.21-61 | « Logements aidés : 1 place maximum / logement aidé. Autres logements : **1 place/logt ≤ 100 m² ; 1,5 place/logt ≥ 100 m²**. » (foyers 1/3) | **incomplet** — tranche ≥ 100 m² écrasée à 1,0 ; plafond aidé ignoré |
| **Entre-Deux** (97403) | `par_logement` **2,0** | U12 · p.27 | « Prêt aidé : 1 place max/logt **+ 1 visiteur par tranche de 10 logements**. Autres logements : **2 places/logt + 1 visiteur par tranche de 5 logements ou 5 lots**. » | **incomplet** — part **visiteur** non appliquée |
| **L'Étang-Salé** (97404) | UA `par_typologie` (coll 1-2p=1/3-4p=1,5/5p+=2 ; indiv=2) ; autres zones `propose` | UA 2.7.3 · p.22 *(barème = YAML)* | **Texte NON servi en base** (extraction 12 p./97) — impossible de relire le verbatim | **UA : juste** (typologie, source YAML) · **autres : absent** · *texte non vérifiable en base* |
| **Petite-Île** (97405) | `par_logement` **1,0** | UB/UC/UD/1AU .12 · p.31-96 | « 1 place de stationnement par logement ; LLTS : 0 place ; **toute opération de logements collectifs : 20 % de l'espace de stationnement aérien perméable**. » | **juste** — carve-out LLTS=0 et clause 20 % perméable (pleine terre) non servis (mineur) |
| **La Plaine-des-Palmistes** (97406) | `par_logement` **1,5** | Ua/Ub/Uc/Ur 12 · p.103 *(barème = annexe)* | Base = §12.1 **définition** seule ; le barème renvoie « **cf. annexe du règlement** » **non ingérée** | **juste/incomplet** — valeur « 1,5 (logt > 30 m²) » issue de l'annexe citée (YAML), **non relisible en base** |
| **Le Port** (97407) | `par_logement` **0,3** | Ua…Ud 12.1 · p.29-73 | « 0,3 place par logement. **En outre, 1 place pour visiteur par tranche de 100 m² de surface de plancher.** » (LLTS : 0,2/logt + 8/1000 m²) | **incomplet** — part **visiteur / 100 m²** non appliquée |
| **La Possession** (97408) | `par_logement` **2,0** | UA/UB/AUBM 12 · p.20-78 | « Prêt aidé (LLTS/LLS/PLS) : 1/logt (0,5 si < 500 m TCSP). **Autres ≤ 50 m² : 1/logt + 1 visiteur / 5 logts** ; **autres > 50 m² : 2/logt** ; structures spécifiques 1/3. » | **incomplet** — tranche ≤ 50 m², **visiteur**, social non servis |
| **Saint-André** (97409) | UC `par_typologie` (<50 m²=1/≥50 m²=1,5) ; autres `propose` | UC 12.2 · p.42 *(barème = YAML)* | **Aucune ligne en base** (règlement non ingéré) | **UC : incomplet** (réductions aidé/TCSP non servies) · **autres : absent** · *texte non vérifiable en base* |
| **Saint-Benoît** (97410) | `par_logement` **1,0** | U 12 · p.17 | « Individuel, ≤ 5 logts : 1/logt. **Opération > 5 logts : 1/logt + 1 visiteur par tranche de 5.** Aidés : 1 pour 2. Résidences univ./âgées : 1 pour 3. » | **incomplet** — supplément **> 5 logts** (visiteur), social, résidences non appliqués |
| **Saint-Denis** (97411) | `par_logement` **1,0** | XVII Stationnement · p.19 *(gén. non ingéré)* | Base = renvois de zone + fragments (aidés réhab. 0,8/0,2 ; 1/3 en sous-sol secteurs Uac/d/t). Barème général XVII (« 1/logt < 100 m² ») **non ingéré** comme ligne | **incomplet** — tranche ≥ 100 m² et dispositions de secteur non servies ; *barème général non relisible en base* |
| **Saint-Joseph** (97412) | `par_logement` **1,0 / 2,0** | U1-U5 12.2 · p.24-84 | « 1 (U1,U2,U4) ou 2 (U3,U5) place min/logt. **+ 1 place par tranche de 10 logements** ; prêt aidé 1/logt (0,5 si < 500 m TCSP) ; RPA 0,5/logt aidé + 2 visiteurs/10 logts. » | **incomplet** — supplément 1/10 logts, RPA, TCSP non servis (taux de base juste) |
| **Saint-Leu** (97413) | `par_logement` **2,0** (= indiv) | Art. 11 disp. gén. · p.13 *(barème = YAML)* | **Aucune ligne en base**. Citation YAML du texte : « **Habitat collectif** : chambre 0,5 ; studio-2p 1 ; 3-5p 1,5 ; 6p+ 2. **Habitat individuel 2** » | **faux** — le 2 (individuel) appliqué au collectif ; tableau collectif ignoré · *texte non en base, citation YAML* |
| **Saint-Louis** (97414) | `par_logement` **2,0** (UZ **1,5**) | UA-UD 12.2 · p.22-65 | « Logements sociaux : 1/logt. Autres : 2/logt. **Opérations > 10 logts : + 0,5 place publique/logt.** RPA : 1/3 logts + 1 visiteur/5. » (UZ : 1,5 ; social 1, arrondi supérieur) | **incomplet** — social, **> 10 logts**, RPA non servis |
| **Saint-Paul** (97415) | `par_logement` **1,0-2,0** (par secteur) | 12.2 · p.30-288 | « **Logements aidés : 1/logt aidé.** Autres logements : N/logt (1 en U1a-d ; 1,5/2 selon secteur). » | **incomplet** — ligne **aidé** non servie ; plusieurs zones `propose` → **absent** |
| **Saint-Pierre** (97416) | **Ud/Ucv `propose` (null)** ; Uf/Ug 1,5 ; Up 1,0 | **Ud6 · p.93** | **Ud (cas signalé) : « Logement : 1 place de stationnement par tranche de 75 m² de surface de plancher. 1 place pour les logements locatifs sociaux. 0,5 place/parcelle pour les lotissements d'habitat individuel. »** (tranche comptée entière) | **Ud : absent** — règle **par m² non supportée** (`par_m2_sdp`) → non servie |
| **Sainte-Marie** (97418) | `par_logement` **1,5** | U13 - 13.2 · p.26 | « Prêt aidé : ≤ 1/logt (0,5 si < 500 m TCSP). **Privé < 100 m² : 1/logt.** Privé ≥ 100 m² : 1 logt → 2 ; **plusieurs logts → 1,5/logt**. Hébergement 1/3 chambres. » | **incomplet** — le 1,5 (≥ 100 m² multi) appliqué à tout ; les modules < 100 m² devraient être à **1/logt** (sur-compte), social/TCSP non servis |
| **Sainte-Rose** (97419) | `par_logement` **1,5** | UA-UD 12 · p.15-42 | « Prêt aidé : 1/logt. **Logt < 50 m² : 1/logt.** Logt ≥ 50 m² : **1,5/logt, arrondi à l'entier inférieur**. » | **incomplet** — tranche < 50 m² et social non servis ; **arrondi forcé supérieur** (texte = inférieur) |
| **Sainte-Suzanne** (97420) | `par_logement` **2,0** — **cite « U13 »** | **réel = U15 - 15.2 · p.17** | « Privé < 50 m² : 1/logt (**+ 0,5 publique/logt si opération > 10 logts**). Privé ≥ 50 m² : 2/logt. Aidé ≤ 1/logt. < 500 m TCSP : 1/logt. » (arrondi supérieur) | **incomplet + référence d'article FAUSSE** : le YAML cite **U13** (= continuités écologiques) au lieu de **U15.2** ; tranche < 50 m², > 10 logts, social non servis |
| **Salazie** (97421) | `par_logement` **2,0** | U 12.2 · p.16 | « Aidé/intermédiaire/âgés/univ. : 1/logt. Privé ≤ 50 m² : 1/logt. **Privé > 50 m² : 2/logt.** » (arrondi supérieur) | **incomplet** — tranche ≤ 50 m² et social non servis |
| **Le Tampon** (97422) | `par_logement` **1,0** — **cite « Habitat individuel »** | **Ud12.2 · p.66** | **« Habitat individuel : 1 place/logt. Habitat collectif (hors social) : 0,5/chambre-studio ; 1/logt 2 pièces ; 1,5/logt 3 pièces et plus. Lotissement ou opération > 5 lots ou logements : 1,5 place/logt, arrondi à l'entier inférieur, dont au moins 0,5 à l'extérieur des espaces privatisés. »** (aidé 1 max ; foyer 1/3) | **faux** — règle **individuelle appliquée au collectif** ; barème collectif + règle > 5 ignorés (§3.1) |
| **Les Trois-Bassins** (97423) | `par_logement` **1,5** | Ua/Ub/Uc 12.2 · p.22-50 | « 1,5 place/logt, arrondi inférieur. **+ 0,5 sur voie/parcelle, lotissements > 5 lots. Opération d'habitat collectif : 1,25/logt ou 1/35 m² SP, la norme produisant le plus de places retenue, max 2/logt.** » | **incomplet** — règle collective (1,25 ou 1/35 m²) et supplément > 5 non servis |
| **Cilaos** (97424) | `par_logement` **1,5** | Ua/Ub/Uc 12.2 · p.27-51 | « Pour les constructions à destination d'habitation : 1,5 place de stationnement par logement. » (pas de distinction) | **juste** |
| **Saint-Philippe** (97417) | — | — | **RNU — aucun PLU, aucun zonage** | **absent** (hors périmètre PLU) |

### Synthèse de l'écart (texte réel)

- **« faux » (mauvaise destination appliquée) : Le Tampon** (individuel → collectif, **sous-compte**, confirmé verbatim) et **Saint-Leu** (individuel → collectif, sur-compte ; texte hors base, d'après citation YAML).
- **« absent » : Saint-Pierre Ud/Ucv** (règle par-m² non supportée, confirmé verbatim), Étang-Salé (sauf UA), Saint-André (sauf UC), zones `propose` de Saint-Paul/La Possession, Saint-Philippe (RNU).
- **« incomplet » : la grande majorité** — avec, désormais chiffré au texte : **règle collective propre dropped** (Les Avirons, Trois-Bassins), **visiteurs** (Entre-Deux, Le Port, La Possession, Saint-Benoît, Saint-Joseph), **> 5/10 logements** (Saint-Benoît, Saint-Louis, Sainte-Suzanne), **tranches de surface** (Bras-Panon, Sainte-Marie, Sainte-Rose, Salazie, Saint-Denis), **logement social** (partout où il réduit).
- **« juste » : Cilaos** (uniforme), **Petite-Île** (1/logt, carve-outs mineurs), **Étang-Salé UA** et **Saint-André UC** (typologisés, mais texte non relisible en base).
- **Deux défauts de traçabilité repérés par le texte** : **Sainte-Suzanne cite le mauvais article** (U13 au lieu de U15.2) ; **Le Tampon cite littéralement « Habitat individuel »** sous un barème appliqué au collectif.

**Motif dominant confirmé par le texte réel : presque toute l'île ingère un seul `par_logement` plat** qui ampute des règles explicitement écrites dans les PLU (parfois une colonne « habitat collectif » dédiée, des lignes visiteurs, des seuils d'opération, des taux sociaux). Le modèle `par_typologie` sait les porter ; seules 2 zones l'utilisent.

---

## 3. Recalcul à la main — AD0887 et HT0538 (au texte réel)

### 3.1 AD0887 — Le Tampon, zone Ud (8 logements collectifs)

Programme (mandat) : **8 logements collectifs, 8 places dessinées, « Réussi »**. Étude non stockée (produite au run).

**LABUSE :** barème `par_logement` plat **1,0** ; `places_imposees = arrondi_sup(8 × 1,0) = 8` ; 8 dessinées ⇒ **Réussi**, citation imprimée **« Ud12.2 — "Habitat individuel 1 place par logement" »**. Le verdict certifie un **collectif** en citant la règle de l'**individuel**.

**Texte réel Ud12.2 (verbatim base, p.66) :** l'article porte, dans le même tableau, une ligne **Habitat individuel : 1/logt** (celle que LABUSE a ingérée) ET :
- **Habitat collectif (hors social)** : 0,5/chambre-studio ; **1/logt 2 pièces** ; **1,5/logt 3 pièces et plus** ;
- **Lotissement ou opération > 5 lots ou logements** : **1,5 place/logt, arrondi à l'entier inférieur, dont ≥ 0,5 à l'extérieur**.

**Recalcul (sans valeur extérieure, au texte) :**
- Opération de 8 logements ⇒ **> 5 logements** : ligne dédiée **1,5 × 8 = 12 places** (arrondi inférieur ; dont ≥ 0,5 × 8 = **4 places extérieures**).
- Lecture alternative par la ligne « habitat collectif » avec le mélange par défaut du moteur (T2×4 à 2 pièces → 1 ; T3×3 à 3 pièces → 1,5 ; T4×1 à 4 pièces → 1,5) : 4×1 + 3×1,5 + 1×1,5 = **10 places**.
- **Les deux lectures du texte dépassent les 8 places imposées par LABUSE** (déficit de **2 à 4 places**).

**Esquisse :** « Réussi » injustifié. Il faut **2 à 4 places de plus** (≈ 50–100 m² au sol, ou un sous-sol), **plus** la contrainte « ≥ 0,5 place/logt à l'extérieur des espaces privatisés » non modélisée. Verdict correct : **« À confirmer »**, voire **« À compléter »** si les places ne tiennent pas sans réduire l'emprise ou le nombre de logements.

### 3.2 HT0538 — Saint-Pierre, zone Ud (10 logements collectifs, R+4)

Étude **stockée** (`docs/audit-2026-11/exports-fix-3/COMPTE-RENDU.md:288-313`) : 510 m², **SDP 887,5 m², 10 logements, R+4**, barème indisponible → **0 place dessinée**, verdict **« À confirmer »** (non « Réussi »).

**LABUSE :** barème Ud = `propose`, `places:null` (forme `par_m2_sdp` **non supportée**) ⇒ non servie ⇒ **0 place imposée**, 0 dessinée, enveloppe non bridée.

**Texte réel Ud6 (verbatim base, p.93) :** « Logement : **1 place de stationnement par tranche de 75 m² de surface de plancher** » ; « la place est comptabilisée par **tranche complète** » ; ligne sociale **« 1 place pour les logements locatifs sociaux »** ; « 0,5 place/parcelle pour les lotissements d'habitat individuel ». (Réductions générales : −30 % si > 200 m du TCSP non, à moins de 200 m du TCSP oui ; pas d'obligation < 150 m².)

**Recalcul :** 887,5 m² / 75 = 11,83 → **12 places** (tranche complète). LABUSE en impose **0**.

**Esquisse :** 12 places requises ≈ 12 × 25 m² ≈ **300 m²** (quasi un niveau de sous-sol) ou une amputation nette de la SDP. L'enveloppe de 888 m² **surévalue** ; la règle **existe au texte** et devrait être servie (`par_m2_sdp`). Le garde-fou EXPORTS-FIX-3 empêche déjà le « exploitable », mais le chiffre lui-même reste non bridé.

**Contraste :** Le Tampon = **faux positif** imprimé ; Saint-Pierre = **règle existante jamais servie** (forme non implémentée). Même cause de fond : le modèle plat ne capte pas la règle réelle.

---

## 4. Les autres contrôles durs — au texte réel (une ligne par commune)

**Méthode.** Emprise (CES), hauteur, pleine terre sont des règles d'enveloppe **indépendantes du type de logement** : « appliquer la valeur de la zone » est correct pour le programme dessiné *si la valeur ingérée est la bonne*. Le risque est l'**absence**. La lecture du texte réel permet désormais de trancher : une couverture manquante est soit **fidèle** (le PLU ne réglemente pas), soit un **vrai manque** (le PLU réglemente, LABUSE n'a pas ingéré).

**Résultat clé : la plupart des « trous » CES signalés dans la V1 sont FIDÈLES au texte** — vérifié verbatim :
- **Le Tampon** : Ua9…Ud9 = **« Non réglementée »** → CES=0 correct (ce n'est pas un défaut).
- **Salazie** : U9/UT9/AUE9 = **« Sans objet »** → CES=0 correct.
- **Sainte-Suzanne** : U7 = **« Sans objet »** (UE7 = 70 %, hors habitat) → CES=0 correct en zone U.
- **Saint-Paul** : U2E/U3E = **« Il n'est pas fixé de règle »** (sauf secteur Usdu, plafond en m² absolus) → CES=0 correct.
- **La Possession** : UA9/UB9 = **« Sans objet »** (UEM9 70 %, AUBM9 60 %) → CES=0 correct pour UA/UB.
- **Entre-Deux** : Ua = **60 %** (ingéré), **Ub/Ue = « Sans objet »** → couverture 1/5 **fidèle**.

**Deux vrais manques confirmés par le texte :**
- **Saint-Denis — PLEINE TERRE : règle existante NON ingérée.** Le texte fixe un % « laissé libre de toute construction ou infrastructure » par zone : **UH 50 %, UJ/UM 35 %, UI 25 %, UD/UU 10 %, Uat 15 %** (art. `.13`). LABUSE sert **PT=0/21** → l'enveloppe n'est pas bridée alors que la règle existe. **Défaut réel.**
- **Saint-Benoît — HAUTEUR : règle existante non servie (mais graphiquement indexée).** Le texte fixe 15/13/10/7/4 m à l'égout **« selon les secteurs repérés sur le document graphique »** (art. U-4). LABUSE sert **H=0/5** : la règle dépend d'un **secteur de hauteur graphique**, non d'une valeur unique de zone — d'où la non-ingestion (défendable), mais **coverage manquante réelle**. Recul voie Saint-Benoît : « non réglementé par défaut » sauf voies nommées (7/5 m) et hors-agglo (75 m) → **recul=0 fidèle**.

| Commune | H | CES | PT | Lecture au texte (une ligne) |
|---|---|---|---|---|
| Les Avirons | 19/20 | 11/20 | 19/20 | couverture large ; CES partiel (à vérifier zone par zone s'il est « sans objet ») |
| Bras-Panon | 14/15 | 14/15 | 14/15 | quasi complète |
| Entre-Deux | 5/5 | 1/5 | 5/5 | CES : Ua 60 % servi, Ub/Ue « sans objet » → **fidèle** |
| L'Étang-Salé | 12/12 | 12/12 | 12/12 | enveloppe complète (trou = stationnement, texte hors base) |
| Petite-Île | 15/15 | 13/15 | 15/15 | complète |
| Plaine-des-Palmistes | 9/10 | 9/10 | 9/10 | complète |
| Le Port | 13/15 | 13/15 | 12/15 | bonne couverture |
| La Possession | 19/23 | 3/23 | 19/23 | CES UA/UB « sans objet » → **fidèle** (les 3 = UEM/AUBM qui le fixent) |
| Saint-André | — | — | — | *texte hors base — non vérifiable* (CES=0 ingéré, à confirmer) |
| Saint-Benoît | **0/5** | 5/5 | 5/5 | **hauteur non servie (secteur graphique 15/13/10/7/4 m) — vrai manque** ; recul voie fidèle |
| Saint-Denis | 17/21 | 16/21 | **0/21** | **pleine terre non servie alors que le texte la fixe (10–50 %/zone) — vrai manque** |
| Saint-Joseph | 24/24 | 24/24 | 22/24 | la mieux couverte |
| Saint-Leu | 18/19 | 17/19 | 5/19 | *texte hors base* ; PT lacunaire à confirmer |
| Saint-Louis | 18/18 | 17/18 | 17/18 | complète |
| Saint-Paul | 31/32 | **0/32** | 29/32 | CES « pas de règle » en U2E/U3E → **fidèle** (sauf Usdu, m² absolus) |
| Saint-Pierre | 26/27 | 25/27 | 21/27 | bien couverte (trou = stationnement Ud, §3.2) |
| Sainte-Marie | 19/19 | 16/19 | 17/19 | complète |
| Sainte-Rose | 9/9 | 9/9 | 9/9 | complète |
| Sainte-Suzanne | 12/12 | **2/12** | 12/12 | CES U7 « sans objet » → **fidèle** en zone U (UE7 70 % hors habitat) |
| Salazie | 10/10 | **0/10** | 10/10 | CES « sans objet » partout → **fidèle** |
| Le Tampon | 20/20 | **0/20** | 13/20 | CES « Non réglementée » partout → **fidèle** (AD0887 : pas d'anomalie d'emprise) |
| Les Trois-Bassins | 9/10 | 9/10 | 9/10 | complète |
| Cilaos | 8/8 | 7/8 | 7/8 | complète |
| Saint-Philippe | — | — | — | RNU — pas d'enveloppe zonale |

**Conclusion §4 :** pour emprise/hauteur/pleine terre, la règle appliquée est celle du texte **là où elle est servie**, et les absences CES signalées en V1 sont pour l'essentiel **fidèles** (les PLU concernés ne réglementent pas l'emprise). **Deux vrais manques** : **Saint-Denis pleine terre** (le PLU fixe 10–50 %/zone, non ingéré) et **Saint-Benoît hauteur** (fixée par secteur graphique, non servie). Le seul contrôle dur **intrinsèquement lié au type de programme** reste le **stationnement** (§2, §3).

---

## 5. Proposition de correction, en lots — du plus grave au moins grave

> Pour chaque lot : ce que LABUSE peut corriger seul vs ce qu'un humain doit valider sur le PLU. La base rend désormais la plupart des textes **directement relisibles** — la validation humaine porte sur l'interprétation (bornes, arrondi, articulation sociale), pas sur la découverte.

### LOT 1 — Faux positif « Réussi » sur la mauvaise destination *(le plus grave)*
**Cibles : Le Tampon (U/AU), Saint-Leu.** Barème individuel servi en plat, appliqué au collectif ⇒ « Réussi » (Le Tampon : sous-compte **dangereux**, confirmé au texte 12 vs 8 ; Saint-Leu : sur-compte).
- **Code (sans ingestion) :** si le programme dessiné est collectif et que la citation servie relève de « habitat individuel », **refuser « Réussi »** → « À confirmer » (ne jamais imprimer la citation individuelle sous un collectif).
- **Ingestion (texte DÉJÀ en base pour Le Tampon) :** ingérer Ud12.2 en `par_typologie` collectif (0,5/chambre-studio ; 1/2p ; 1,5/3p+) **plus** la règle d'opération « > 5 logements : 1,5/logt arrondi inférieur, dont ≥ 0,5 extérieur ».
- **À valider par un humain :** articulation entre la ligne « habitat collectif » et la ligne « opération > 5 logements » (laquelle prime, ou cumul ?) ; pour Saint-Leu, **réingérer le règlement** (actuellement hors base).

### LOT 2 — Règle existante jamais servie, faute de forme supportée
**Cibles : Saint-Pierre (Ud, Ucv : « 1 place / 75 m² SDP »), + toute zone en `par_m2_sdp`.**
- **Code :** implémenter la branche **`par_m2_sdp`** (`places_imposees = arrondi(SDP / m²_par_place)`). Le texte est en base, verbatim.
- **À valider par un humain :** sens d'arrondi — le texte Ud6 dit **« comptabilisée par tranche complète »** (⇒ supérieur) ; articulation avec « 1 place pour les logements locatifs sociaux » (forfait) avant de passer `valide`.

### LOT 3 — Suppléments et réductions jamais appliqués *(incomplet, impact chiffré réel)*
**Cibles (texte en base, lignes précises) :** visiteurs (**Entre-Deux** 1/5 et 1/10 ; **Le Port** 1/100 m² ; **La Possession** 1/5 ; **Saint-Benoît** 1/5 ; **Saint-Joseph** 1/10 + RPA) ; seuils d'opération (**Saint-Benoît** > 5 ; **Saint-Louis**/**Sainte-Suzanne** > 10) ; **règle collective propre** (**Les Avirons**/**Trois-Bassins** : 1,25/logt ou 1/35 m², max) ; logement social (**Saint-Louis**, **Salazie**, **Sainte-Suzanne**, **Bras-Panon**…).
- **Code :** étendre le barème pour porter (a) supplément visiteur (places/tranche de SDP), (b) seuil d'opération (N logements/lots), (c) ligne sociale, (d) « max de deux formules ».
- **À valider par un humain :** transcription exacte de chaque clause (déjà verbatim en base) et sa base de calcul, commune par commune.

### LOT 4 — Tranches de surface/pièces écrasées en un plat
**Cibles : Bras-Panon (≥ 100 m²), Sainte-Marie (< 100 m² = 1 vs plat 1,5), Sainte-Rose/Salazie/Sainte-Suzanne (< 50 m²), Saint-Denis (≥ 100 m²).** Le `par_typologie` existe déjà — **réingérer** en lignes typées (texte en base).
- **À valider par un humain :** inclusion/exclusion des bornes (50/100 m²).

### LOT 5 — Traçabilité, arrondi, couverture d'enveloppe *(le moins grave)*
- **Référence d'article fausse : Sainte-Suzanne cite « U13 » au lieu de « U15.2 »** → corriger la feuille (le texte U15.2 est en base). Vérifier au passage que la *valeur* 2,0 correspond bien à la branche « ≥ 50 m² » et non à un plat.
- **Arrondi :** `par_logement` force `superieur` ; lire un champ `arrondi` (Sainte-Rose/Trois-Bassins = inférieur ; Sainte-Suzanne/Salazie = supérieur).
- **Pleine terre Saint-Denis :** ingérer la règle réelle (UH 50 %, UJ/UM 35 %, UI 25 %, UD/UU 10 %, Uat 15 %) — **vrai manque** confirmé au texte. **À valider :** lecture du % par zone/secteur.
- **Hauteur Saint-Benoît :** la règle est indexée au **secteur de hauteur graphique** (15/13/10/7/4 m) ; servir nécessiterait d'ingérer cette couche graphique. **À valider :** modalité (couche graphique vs valeur de zone).
- **Ne PAS « corriger » les CES absents fidèles** (Le Tampon, Salazie, Sainte-Suzanne, Saint-Paul, La Possession UA/UB, Entre-Deux Ub/Ue) : le texte dit « Non réglementée / Sans objet ». Le bon libellé de contrôle y est **« Non réglementé »** (non applicable), pas « Non effectué ».

### Garde-fou transversal (immédiat, sans ingestion)
Tant que les lots ne sont pas validés : **ne jamais afficher « Réussi » au stationnement quand la citation servie relève d'une destination différente du programme dessiné** (individuel sous un collectif). Supprime le faux positif du Tampon sans toucher aux chiffres.

---

## Annexe — points de lecture et données

- Modèle/application : `regles.py:42-97`/`:258-283` (**pas de `par_m2_sdp`**, arrondi plat forcé), `capacite.py:71-87` (`destination="collectif"` codé en dur), `controles.py:415-426`.
- Programme collectif seul : `geometrie.py:278`, `config/implantation_conventions.yaml:38-44`.
- Barème ingéré : `config/plu_destinations/<insee>_*.yaml`, lecture `destinations.py:673`.
- **Texte opposable (lu ici)** : table `plu_reglement_extrait` (base locale) — verbatim, article, page. Absent pour 97404 (partiel), 97409, 97413, et pour les barèmes en annexe (97406) / dispositions générales (97411).
- HT0538 (étude stockée) : `docs/audit-2026-11/exports-fix-3/COMPTE-RENDU.md:288-325`.

---

## Addendum (ETUDE-STATIONNEMENT-FIX-1, relecture 7) — pistes NON VÉRIFIÉES de ce rapport

Ce rapport d'audit a été écrit avant la mise en place du **contrôle par l'image** (chaque chiffre prouvé sur
la page du PDF officiel). Les constats **de stationnement** ont depuis été **tous vérifiés par l'image**
(1465 règles prouvées, 0 chiffre hors citation). En revanche, les constats **hors stationnement** issus de la
**même extraction par agent de la table `plu_reglement_extrait`, non vérifiée par l'image**, sont des
**PISTES NON VÉRIFIÉES** tant qu'une image ne les confirme pas :

- **Saint-Denis — pleine terre** : les valeurs citées ici (**UH 50 %, UJ/UM 35 %, UI 25 %, UD/UU 10 %, Uat
  15 %**) **sont FAUSSES** — elles ne figurent nulle part dans le règlement en vigueur (05/08/2026). Les
  seules règles réelles sont **UD 30 % et UI 40 %** (vérifiées par l'autre session). Le « 15 % » lu sur une
  image était une **mixité sociale** (15 % de logements aidés, opérations d'habitat collectif de 30+
  logements), pas une pleine terre. → **piste non vérifiée, corrigée.**
- **Saint-Benoît — hauteur par secteur graphique** (15/13/10/7/4 m) : **piste non vérifiée** (non confirmée
  par l'image dans ce travail) ; à vérifier sur le document graphique avant toute ingestion.
- **Tout autre chiffre hors stationnement** de ce rapport (emprises, hauteurs, reculs « manquants »,
  perméabilités) relevant de la même extraction : **piste non vérifiée** jusqu'à confirmation par l'image.

Règle retenue : **un chiffre ne vaut que prouvé par l'image de sa page**. La pleine terre de Saint-Denis l'a
appris à nos dépens ; la méthode est désormais le contrôle de pages (`scripts/stationnement_controle_pages.py`).
