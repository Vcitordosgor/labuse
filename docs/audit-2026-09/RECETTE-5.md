# RECETTE-5 — rapport

**Branche** `feat/recette-5` (worktree `~/Desktop/labuse-recette5`), depuis `main`. **Rien mergé, rien basculé, aucun rescoring, aucune ingestion, aucun batch.** Un commit par lot.

**Étape 0** : pwd = worktree recette-5 · branche `feat/recette-5` · arbre propre · `.env` présent (DB `labuse`). App montée en isolé : API `:8030` (PYTHONPATH worktree), front `:5176`. Tout vérifié dans un vrai navigateur (Playwright), sur chaque chemin concerné. Preuves (captures) dans `docs/audit-2026-09/RECETTE-5-preuves/`.

**Commits** : `84b45caa` (lot 1) · `d19b7bec` (lot 2) · `111143ef` (lot 3) · `ffca8218` (lot 4) · `87b31f79` (lot 5) · lot 6 (ce rapport, lecture seule).

---

## Tableau des 23 points

| # | État | Constaté au navigateur | Preuve |
|---|------|------------------------|--------|
| **V1** | ✅ corrigé | Voile gris retiré sur **les deux** chemins. Chemin factuel « Voir les parcelles » : le remplissage passe de la surbrillance grise `#8FA69A`/0,42 (qui, sans filtre, lavait toute l'île) à la trame cadastrale neutre `#22302A`/0,28 ; les parcelles restent délimitées par leurs contours et cliquables. Mode analyse : déjà sans voile (opacité uniforme 0,72, coloré). | `v1-factual-before/after.png`, `v1-analyse-after.png` |
| **V2** | ✅ corrigé | Tri factuel par défaut = **Adresse** (adressées d'abord, puis surface décroissante — que du fait cadastral). « Potentiel » (SDP résiduelle = calcul LABUSE) retiré de la vue factuelle. Client (mode commune) + serveur (`/filtre?sort=adresse` → 200, adressées en tête, mode île). | pills Adresse/Surface |
| **V3** | ✅ corrigé | Fiche de synthèse piscines (total + par commune) affichée d'emblée (7 821) ; « Voir les parcelles » dessous ; au clic la fiche se replie (une ligne dépliable) et le listing prend la place (200 lignes). | `v3-piscines-listing.png` |
| **V4** | ✅ corrigé | En-tête à **8 tuiles** (maquette v2) : surface · zone · pente · [vue mer omise, cf. V8] · terrain nu €/m² · bâti ancien €/m² · taxe foncière part communale · SDP restante ; chacune avec un « i » de source. Sur 97418000AD0191 : 273 m² · UA constructible · 1,7° plat · 221 €/m² (3 ventes) · 1 870 €/m² (18 ventes) · **43,9 % part communale** · SDP « — ». TFPB ajoutée au payload parcelle (même producteur que la fiche commune, REI DGFiP). | `v4-entete-final.png` |
| **V5** | ✅ corrigé | Étiquettes **sous la grille** : Préemption urbaine · Bruit — zone D · Particulier propriétaire. | idem |
| **V6** | ✅ corrigé | Accordéon « Le reste des faits » : dernière vente · valeur au prix du secteur · **302 m² · 2 bâtiments** · taxe d'aménagement (taux communal à saisir) · zonage d'investissement B1 · transport (29 m — Source (Citalis)) · fibre (raccordable). Ensoleillement omis (non servi sur la fiche parcelle, jamais inventé). | idem |
| **V7** | ✅ corrigé | Valeur inconnue = « — » + raison (« pas assez de ventes », « zone non constructible », « taux non ingéré »), jamais un zéro. | idem |
| **V8** | ✅ corrigé | Tuile « vue mer » câblée seulement si un verdict favorable est servi. Non calculé (cf. V23, lecture seule) → tuile **omise** ; la grille est complétée par une cellule de remplissage au même fond (pas de tuile vide). | idem |
| **V9** | ✅ corrigé | Marges fiche : un libellé n'est plus écrasé à 0 px (« Nature du toit » = 83 px). Cause : une valeur longue (DPU/PEB) en `nowrap` happait toute la largeur ; colonne libellé en `auto`, valeur qui retombe à la ligne. | mesure DOM |
| **V10** | ✅ corrigé | Pastilles du listing lisibles au survol : fond opaque sombre + texte clair (au lieu du fond translucide + encre forcée, illisible sur l'aplat mint, surtout au scroll). | `v10-hover-before/after.png` |
| **V11** | ✅ corrigé | Panneau Cartes : plus de grand vide noir. L'état « deux sections rétractées » n'est légitime que sous un vrai listing (verdict) ; sinon Couches est ouverte par défaut. | `v11-no-void.png` |
| **V12** | ✅ corrigé | Flèche d'accordéon : fermé → **gauche** (◂), ouvert → bas (▾). Corrige le `-90°` (pointait à droite) en `+90°`. | classe `rotate-90` |
| **V13** | ✅ corrigé | Accueil : 5e porte **« Remonter le temps »** (module `temps`, photos aériennes IGN) sous les quatre entrées. | 5 cartes |
| **V14** | ✅ corrigé | Fiche commune ↔ fiche parcelle se ferment **mutuellement** (vérifié dans les deux sens : ouvrir l'une ferme l'autre). | DOM (contexte-panel / fiche-idu) |
| **V15** | ✅ corrigé | Carte rouge : l'écartée ET l'étage 0 étaient peints en braise `#E8695A` — **la même teinte que la Priorité**. Invisible tant que les écartées étaient à 0,04 d'opacité, mais RECETTE-2 a rendu l'opacité uniforme (0,72) en analyse → toute l'île (majorité écartée/étage 0) virait au rouge. Retour à la teinte muette du vocabulaire PALIERS-1 (`#4A5A52`) : le rouge reste réservé à la Priorité, carte et légende redisent la même chose. | `v15-carte-non-rouge.png` |
| **V16** | ✅ corrigé | « Bâti à densifier » → **« Déjà construit, le PLU autorise encore du plancher »**. | listing (109 855) |
| **V17** | ✅ corrigé | « Finance » → **« Dossier financier »** : bouton de fiche, titre du PDF (page de garde), nom de fichier téléchargé (« Dossier financier — FI-….pdf »). | bouton (navigateur) + titre dans le PDF généré |
| **V18a** | ✅ corrigé | `<strong>Charge foncière supportable</strong>` ne s'imprime plus avec ses balises (la clé était échappée par `ligne_kv`). Clé en texte simple, montant en gras (valeur HTML). | PDF généré (pas de balise littérale) |
| **V18b** | ✅ corrigé | Tant qu'un élément indispensable manque, le Dossier financier **ne se génère pas** : `/financier/….pdf` → **422** `{ manques: [Programme constructible, Prix de vente prévu, Régime de TVA] }`, l'écran dit lesquels ; le PDF ne sort que quand tout est là (3 pages de vrai bilan, plus de tableau « non chiffré »). | fetch 422 (navigateur) + PDF établissable généré |
| **V19** | ✅ corrigé | Questionnaire : chaque question porte un « i » (ce qu'on attend) ; les deux indispensables au calcul (**prix de sortie**, **régime de TVA**) bloquent tant qu'ils sont vides ; les autres marqués « facultatif ». (Liste ci-dessous.) | `v19-questionnaire.png` |
| **V20** | ✅ corrigé | Brief apporteur : (a) « 0 m² de plancher restant » ne s'imprime plus (garde `sdp > 0`) ; (b) voisines + dernière vente + propriétaire présents en page 1 ; (c) plan borné en hauteur → **4 pages** et non 5 (pypdf) ; (d) « Document à jour du GPU — c'est celui qui fait foi » retiré de la ligne Zone. | PDF généré (pypdf 4 pages, phrase absente) |
| **V21** | ✅ corrigé + réponse | Emprise 302 m² sur 273 m² : cause = **double-compte de deux polygones bâtiment BD TOPO qui se chevauchent** (pas un débord voisin). Garde `ST_Union` avant `ST_Area` → emprise = 151 m². **20 440 parcelles** affichaient emprise > contenance. (Réponse détaillée ci-dessous.) | mesure DB + `le_bien_block` (151 m²) |
| **V23** | 📝 réponse (rien codé) | Vue mer instruite en lecture seule. **Constat majeur : le MNT d'élévation (RGE ALTI) n'est PAS ingéré** — seul le raster de PENTE 5 m l'est. Une vraie ligne de vue n'est donc pas calculable aujourd'hui. Instruction + coût + 20 parcelles (proxy) ci-dessous. Rien branché, rien servi. | 20 parcelles Saint-Leu (proxy) |

---

## V19 — la liste des indispensables et des facultatifs (rendu de compte)

**Indispensables au calcul** (bloquent la génération / le passage à l'écran suivant tant qu'ils sont vides) :
- **Prix de vente prévu des logements** (`prix_sortie_saisi_eur_m2`) — c'est le chiffre d'affaires du bilan à rebours ; aucun pré-remplissage (personne ne peut le deviner à la place du porteur).
- **Régime de TVA** (`regime_tva_saisi`) — décide si le bilan travaille HT ou TTC.
- (+ le **programme constructible** — surface vendable — indispensable aussi, mais il vient du POTENTIEL de la parcelle ou du repli « logements × typologie », pas du questionnaire ; son absence est signalée à part par `manques`, cf. V18b.)

**Facultatifs** (pré-remplis sourcés ou secondaires — n'empêchent rien) : scénario, logements visés, typologie moyenne, part sociale, prix demandé du terrain, frais d'acquisition, coût de démolition, dépollution, coût de construction, honoraires techniques, VRD, coût par place de stationnement, provision aléas, taxe d'aménagement, prix de vente au bailleur social, marge visée, durée de portage, taux d'emprunt.

---

## V21 — l'emprise impossible : cause, compte, garde (réponse écrite)

**Le cas** : la parcelle 97418000AD0191 (Sainte-Marie), contenance cadastrale **273 m²**, affichait une **emprise bâtie de 302 m²** — impossible (le bâti ne peut pas couvrir plus que la parcelle).

**La cause — mesurée, ce n'est PAS un débord sur la voisine.** L'emprise était calculée par `SUM(ST_Area(ST_Intersection(bâtiment, parcelle)))` : la SOMME des aires d'intersection, bâtiment par bâtiment. Or la BD TOPO porte **deux polygones bâtiment qui se chevauchent** sur cette parcelle (mur mitoyen, ou un bâtiment scindé en plusieurs faces qui se recouvrent). La zone de chevauchement est comptée **deux fois**. Mesure sur la parcelle :
- `SUM` des intersections = **301,7 m²** (le chiffre servi, > contenance) ;
- `ST_Union` des mêmes empreintes (fusionnées) = **150,8 m²** (l'empreinte réelle) ;
- soit **150,8 m² de double-compte** — l'écart exact. L'empreinte réelle (151 m²) tient largement dans les 273 m².

**Combien de parcelles.** Mesure sur tout le parc (parcelles à ≥ 2 bâtiments) :
- **20 440** parcelles affichaient une emprise **supérieure à leur contenance** (le chiffre impossible) ;
- **144 365** parcelles portaient un double-compte (chevauchement de polygones bâtiment), qu'il dépasse ou non la contenance ;
- sur 250 731 parcelles à ≥ 2 bâtiments.

**La garde posée** (`src/labuse/bati.py`, `le_bien_block`) : `ST_Area(ST_Union(ST_Intersection(...)))` au lieu du `SUM`. `ST_Union` fusionne les empreintes AVANT de mesurer l'aire → plus de double-compte, et le résultat est **naturellement borné par la géométrie de la parcelle** (une intersection ne sort jamais de la parcelle). Vérifié : l'emprise de 97418000AD0191 passe de 302 à **151 m²**, la surface libre de −29 à 122 m². Le producteur `le_bien_block` étant la source unique consommée par la fiche (tuile « Bâti au sol ») et par les documents (Dossier), le correctif se propage partout.

*Note (hors périmètre V21)* : `stats_batch` (l'indice `taux_emprise` du scoring/segments) partage le même `SUM`, mais borne son ratio à 1,0 (`LEAST`) — aucun « chiffre impossible » n'y transparaît, et c'est une valeur **matérialisée par batch** (rebuild non exécuté ici). À aligner sur `ST_Union` au prochain rebuild.

---

## V23 — vue mer : instruction en lecture seule (rien branché, rien servi)

### Ce qu'apporte la hauteur du bâti de la BD TOPO, ajoutée au relief

Une ligne de vue calculée sur le seul MNT (modèle de **terrain** nu, RGE ALTI) annoncerait « vue mer » à une parcelle en réalité masquée par un immeuble : le terrain est dégagé, mais un bâtiment de 12 m entre la parcelle et l'océan coupe la vue. La **hauteur du bâti BD TOPO** (`attrs.hauteur`, déjà servie sur la fiche via `le_bien`) rétablit la vérité de deux façons :
1. **En obstacle** : on ajoute la hauteur des bâtiments au relief le long du rayon → un bâtiment devant la parcelle bloque la vue même quand le sol est plat.
2. **En belvédère** : on ajoute la hauteur du bâti **de la parcelle observatrice** au point de vue → les étages hauts voient par-dessus un obstacle que le rez-de-chaussée ne franchit pas (une « vue mer du 3ᵉ » réelle et fréquente à La Réunion).

### Ce que ça ne verra jamais (les trous à dire au client)

- **La végétation** : un rideau d'arbres masque l'océan sans figurer ni dans le MNT ni dans la BD TOPO. La ligne de vue le traversera comme s'il n'existait pas.
- **Les constructions à venir** : le voisin bâtit, la vue meurt. Le calcul photographie un état, pas un droit acquis.
- **Les trous et approximations de la BD TOPO** : bâtiments manquants (levés incomplets), hauteurs arrondies (au mètre, parfois estimées par nombre d'étages), emprises généralisées — chaque manque fausse l'obstruction dans un sens ou l'autre.
- **Le lissage du MNT** : à 1 m ou 5 m de résolution, un rempart, un muret, un rebord fin passent sous la maille — le relief servi est plus doux que le vrai.

### ⚠ Le trou de données constaté (le préalable)

**Le MNT d'élévation (RGE ALTI) n'est PAS en base.** Le seul raster présent est `rgealti_pente_5m` — la **PENTE** dérivée à 5 m (band unique, valeurs 0–87°, celle qui alimente `terrain.pente_moy_deg`). Aucun raster d'altitude, aucune colonne d'élévation ailleurs (vérifié : `raster_columns` ne liste que la pente ; aucune colonne `altitude/elevation/z` exploitable ; le bâti porte sa hauteur relative, jamais l'altitude du sol). **Une vraie ligne de vue est donc impossible à calculer aujourd'hui** : il faut d'abord **ingérer le MNT RGE ALTI** (5 m suffit pour un premier jet, 1 m pour le fin), ce qui est un batch — non fait ici.

### Le coût d'un batch sur 430 663 parcelles, et s'il est rejouable

Une fois le MNT en base, la ligne de vue par parcelle échantillonne le relief (+ hauteur du bâti) le long de plusieurs azimuts vers le secteur océan, à un pas de ~5–10 m sur ~2–5 km. Ordre de grandeur : ~8–16 rayons × ~300–1 000 points × un `ST_Value` chacun = quelques centaines de milliers de lectures raster par parcelle. À l'échelle de l'île, c'est un batch **lourd mais borné** : de l'ordre de **1 à quelques heures** parallélisé sur plusieurs workers (chaque parcelle est indépendante), à la manière des autres batches géométriques (blocs, geom_simple). Il est **entièrement rejouable et idempotent** — déterministe pour un MNT + une BD TOPO donnés ; on le relance quand l'un des deux millésimes change (nouveau bâti = nouvelle obstruction). Prérequis : ingestion du MNT (le vrai coût d'entrée), puis un index raster + le découpage par commune côté mer.

### Trois états honnêtes, avec la phrase qui dit sur quoi c'est calculé

Plutôt qu'un oui/non binaire :
- **Dégagée** — l'océan est visible sans obstacle sur un large secteur.
- **Partielle** — une échancrure de mer, ou une vue coupée par le relief/le bâti sur une partie du champ.
- **Aucune** — le relief ou le bâti ferme la vue.

Phrase servie sous la tuile : *« Vue calculée sur le relief (RGE ALTI 5 m) et la hauteur du bâti (BD TOPO) — hors végétation et constructions à venir. À confirmer sur place. »*

### 20 parcelles avec leur verdict — commune de Saint-Leu (⚠ PROXY, pas la vraie ligne de vue)

**Faute de MNT, ces verdicts ne sont PAS une ligne de vue** : ils sont un **proxy** calculé sur les seules données disponibles — distance à la côte (offset vers l'est depuis le trait de côte ouest, Saint-Leu faisant face à l'ouest), pente RGE ALTI, et obstruction par le bâti BD TOPO ≥ 7 m dans le secteur mer (≤ 100 m). Il ignore le relief entre la parcelle et l'océan : **il ne sait pas créditer une parcelle haute et reculée d'une belle vue** — c'est précisément ce que seul le MNT réparerait. Il est fourni pour montrer la forme du pipeline et pour que Vic éprouve les 3 états sur des parcelles qu'il connaît.

| IDU | surface | dist. mer (m) | pente | obstru. mer | verdict (proxy) |
|---|---|---|---|---|---|
| 97413000CA0057 | 6 333 | 52 | 12,5° | 0 | **dégagée** |
| 97413000CD0285 | 4 657 | 263 | 8,7° | 0 | **dégagée** |
| 97413000CD0697 | 492 | 330 | 6,0° | 0 | **dégagée** |
| 97413000CD0114 | 701 | 387 | 7,8° | 0 | partielle |
| 97413000CD0375 | 626 | 451 | 4,7° | 5 | aucune |
| 97413000CD0237 | 882 | 505 | 1,1° | 9 | aucune |
| 97413000CD0308 | 621 | 549 | 4,5° | 4 | aucune |
| 97413000CD0314 | 624 | 606 | 2,9° | 6 | aucune |
| 97413000CD0246 | 2 972 | 669 | 2,5° | 2 | aucune |
| 97413000CD0031 | 797 | 740 | 13,2° | 1 | partielle |
| 97413000CA0205 | 54 712 | 796 | 5,5° | 0 | partielle |
| 97413000CD0440 | 483 | 836 | 4,0° | 10 | aucune |
| 97413000CD0587 | 4 614 | 880 | 8,3° | 3 | aucune |
| 97413000CD0526 | 438 | 910 | 9,9° | 5 | aucune |
| 97413000CD0531 | 653 | 945 | 13,4° | 0 | aucune |
| 97413000CD0508 | 512 | 979 | 3,7° | 6 | aucune |
| 97413000CA0254 | 1 946 | 1 044 | 10,7° | 2 | aucune |
| 97413000CD0595 | 189 573 | 1 215 | 9,4° | 0 | aucune |
| 97413000CB0113 | 16 463 | 1 328 | 9,7° | 0 | aucune |
| 97413000CZ0059 | 321 | 1 394 | 0,9° | 0 | aucune |

**Décision laissée à Vic** : au vu de ces 20 (et du trou MNT), trancher s'il vaut d'ingérer le RGE ALTI pour brancher la vraie ligne de vue. **Rien n'a été branché ni servi** — la tuile « vue mer » (V8) reste omise tant qu'aucun verdict favorable n'est calculé.

---

*Fin du rapport RECETTE-5. Rien mergé, rien basculé.*
