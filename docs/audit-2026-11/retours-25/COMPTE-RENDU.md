# RETOURS-25 — recette des outils (suite)

Branche `fix/retours-23` (même branche), worktree `~/Desktop/labuse-outils`, ports 10010/7210.
Pas de merge, aucun accès prod. Vérifié dans **WebKit** (playwright 1.49.1, webkit-2104, reducedMotion) —
captures dans `captures/`. Hook vert : `tsc -b` 0, vitest **310/310**, build OK, scan secrets OK, pytest
unitaires (courrier/assemblage/taxe/moteurs) verts.

---

## Assemblage

**Étude de faisabilité — de bout en bout + depuis Docs** : le bouton « Étude de faisabilité de cet
assemblage → » appelle `ouvrirEtude(msel)` → `etudeIdus` → overlay `EtudeEcran`/`EtudeV6`. Vérifié
WebKit : `ouvrirEtude([…])` ouvre l'overlay (`[data-etude-ecran]`) **et** le chemin Docs (carte « Étude
de faisabilité ») ouvre le MÊME overlay. Les deux convergent sur `ouvrirEtude`.

**« 8 parcelles maximum » disparaît sous 8** : l'effet `[msel]` remet `max8=false` dès que
`msel.length < ASM_MAX`, quelle que soit la voie de retrait (puce ×, « Retirer les vides », clic carte) —
avant, « Retirer les vides » ne le remettait pas à false et le message collait.

**« vs meilleure seule » retirée** (tuile `data-asm-kpi="ratio"` supprimée).

**Répétitions supprimées** : « · surface totale … » retiré de l'en-tête (la surface vit UNE fois, dans
la tuile « Surface d'assiette ») ; les chips « d'un seul tenant » + « N interlocuteurs » retirées
(doublons : « contiguës » dit déjà le seul tenant ; les interlocuteurs sont dans « approche propriétaire »).

**Bilan réduit à 4 lignes** : *Charge foncière estimée · Prix de sortie · Marché de la zone · Parcelles
chiffrables*. Le texte d'explication (bilan à rebours, hypothèses, CA cumulé, note d'union) part dans le
« i » du titre « Bilan ». La ligne **« Prix de sortie »** (€/m² habitable) est NEUVE : le prix de sortie
était calculé puis jeté (`_ps` de `compute_bilan_servi`) ; exposé côté back (`assemblage.py` → `moteurs.py`,
`prix_sortie_eur_m2`). Tests Assemblage mis à jour. Capture : `p14-assemblage-resultat.png`.

## Pièges et risques
Phrase d'intro « Ce qui peut bloquer un projet… » retirée. L'accordéon « Méthode et limites » est remplacé
par UNE ligne en bas « **Non couvert : …** » (la liste `non_couvert`, discrète). Adresse complète : via la
règle « adresse/IDU jamais coupée » (ci-dessous). Capture : `p02-pieges.png`.

## Règle « Changer de parcelle » — bouton vert de la DA partout
`EntreeParcelle` (Pièges, Histoire, Gabarit, Taxe, Solaire…) : déjà vert (RETOURS-23). Restaient deux liens
nus soulignés → passés au `Bouton niveau="lien" ton="vert"` : **Estimer** (« Changer de parcelle ») et
**Scan patrimoine** (« changer »).

## Règle adresse / IDU — jamais de texte coupé
`EntreeParcelle` (parcelle choisie) ne `truncate` plus : soit l'**IDU seul**, soit l'**adresse ENTIÈRE**
(qui passe à la ligne) **+ l'IDU** dessous. S'applique partout (Gabarit, Taxe, Pièges, Solaire…).

## Étude de zone
Retirés : sous-titre « une parcelle + un rayon en km », ligne « Parcelle : DR 0305 », sous-titre
« population · économie · … · dynamique », titre « Zone de N km autour de … ». Capture : `p05-zone.png`.

## Estimer
Entrée « Un lien d'annonce » retirée + titre « Une adresse » (l'outil s'ouvre sur UN seul champ ; le lien
reste analysable via le pont Radar, l'erreur éventuelle s'affiche). Lien « Ouvrir la fiche parcelle »
retiré. « Dernière vente : aucune depuis 2014 » → « **Aucune vente enregistrée (DVF depuis 2014)** ». Un
clic sur une AUTRE parcelle de la carte **relance l'estimation** (effet `selectedIdu`). Capture :
`p06-estimer.png`.

## Gabarit réglementaire
Phrase d'intro retirée ; indication « Ctrl + glisser… » retirée. **Les DEUX hauteurs sont écrites sur la
vue 3D** : « enveloppe (règle) X m · bâti existant Y m » (`data-gabarit-3d-hauteurs`). Capture : `p07-gabarit.png`.

**Pourquoi le bâti paraît plus bas que l'enveloppe** (capture de Vic) : l'enveloppe est extrudée à la
hauteur **MAXIMALE réglementaire** (ex. 12 m) ; le bâti existant est extrudé à sa hauteur **RÉELLE**
mesurée (LiDAR HD, ex. 6 m). Les deux partent du MÊME socle plat. Le bâti est donc plus bas parce qu'il
EST plus bas que le maximum autorisé — ce n'est pas un défaut, c'est « ce qui est là » vs « jusqu'où on
peut monter ».

**« Le volume suit le terrain (dalles) » — non livré dans cette passe, explication** : la « 3D » de l'app
est une **extrusion `fill-extrusion` sur socle PLAT** — il n'y a PAS de maillage de terrain maplibre
(aucun `setTerrain`/`queryTerrainElevation`/`raster-dem` dans le code), et la réponse Gabarit ne porte
AUCUNE grille d'altitude par point. Faire « suivre le terrain » (découper la zone en dalles, chacune à sa
cote) demande donc un **nouveau pipeline d'altitude** : une grille RGE ALTI par point servie par le back +
une extrusion par dalle (base = cote locale, hauteur = cote + hauteur règle) côté front. C'est une
fonctionnalité à part entière, pas un ajustement de recette ; proposée en suite. Les deux autres volets
(hauteurs écrites sur la vue · explication du « bâti plus bas ») sont faits.

## Bug légende (superposition)
Deux panneaux « Légende » flottaient **indépendamment** en bas à droite et se **superposaient** : la
légende des COUCHES (`TuyauLegend`, `bottom-10`) et la légende de PEINTURE (`Legend` verdict/zonage,
`bottom-4`). Fix : **UN SEUL panneau** (`[data-legendes]`, un `.floating` unique) qui EMPILE les deux
sections (flex-col + `divide-y`) ; chacune se masque seule quand vide. `TuyauLegend` exportée et rendue par
MapView (avec la Légende) ; leurs cadres propres retirés. Captures avant/après : `p08-legende-avant.png`,
`p08-legende-apres.png`.

## Prospection solaire
« Deux métiers, deux entrées. » retiré. Écran **Ensoleillement** vérifié (utile / vrai / sans doublon) —
**retraits** : (1) ligne « Nature du toit : {statut} — {méthode} » RETIRÉE (doublon de la tuile « Nature
du toit » qui porte déjà la valeur + la provenance « Estimé ») ; (2) phrase « La lecture LiDAR de la
toiture (ci-dessus) se vérifie sur cette photo. » RETIRÉE de la légende photo (filler ; on garde la
légende de la rosace et la levée d'ambiguïté « pente du terrain ≠ pente du toit »). Le reste (KPI
sourcés/estimés, hypothèse kWc/m², exclusion EnR, piscine, profil mensuel) : utile et vrai, conservé.
Captures : `p09-solaire-accueil.png`.

## Taxe d'aménagement
Textes vérifiés : ce sont des **repères légaux sourcés** (CGI art. 1635 quater, provenances DGFiP) — utiles
et vrais, conservés. **Retrait** : le détail de l'abattement (« … premiers m² de CHAQUE logement ») était
écrit DEUX fois — sur la case « Résidence principale » ET sur le champ « Nombre de logements » ; il ne reste
qu'une fois (sur le champ), la case ne dit plus que l'effet. Le visuel viendra avec la refonte.
Capture : `p10-taxe.png`.

## Blocs fonciers
Phrase d'intro « Les parcelles contiguës d'un même propriétaire… » retirée ; date (millésime / « au … »)
retirée ; « Réinitialiser les filtres » passé au **vert**. Capture : `p11-blocs.png`.

## Successions
Section explicative (bandeau + « i » méthode) retirée ; date (« au … », « calculé le … ») retirée.
« Réinitialiser les filtres » au vert (cohérent avec Blocs). Capture : `p12-successions.png`.

## Courrier
Phrase « Les parcelles à démarcher — une barre… » retirée. L'intro gagne « **2,50 € par courrier,
impression, enveloppe et affranchissement compris · envoi sous 7 à 10 jours.** » — **lus de la CONFIG**,
jamais écrits en dur : nouveaux réglages `courrier_prix_client_eur = 2.50` et `courrier_delai_jours = "7 à
10"` (`config.py`), servis par `/courrier/statut` (`tarif_unitaire_eur`, `delai_jours`), lus côté front.
> Note pricing : le prix client passe de 4,04 € (coût La Poste 2,69 € × marge 1,5) à **2,50 €** (chiffre
> donné par Vic). Le provider est `stub` (aucune facturation réelle), donc sans impact financier ; à
> confirmer par Vic si le provider réel est activé (2,50 € < 2,69 € coût). Vérifié live : statut sert
> `tarif_unitaire_eur=2.5`, `delai_jours="7 à 10"`. Capture : `p13-courrier.png`.

## Fiche parcelle — largeur des 6 tuiles
Mesuré WebKit : les tuiles étaient RENTRÉES de 14 px de chaque côté (padding horizontal de `.stats`),
donc plus étroites que la carte d'en-tête `.tete-carte` et les sections. Fix : padding de `.stats`
`12px 14px` → `12px 0`. Après : tuiles `[1055 → 1418]` = **exactement** l'en-tête `[1055 → 1418]`.
Capture : `p14-...` (fiche).

## Lenteur après analyse — déchargement du coloriage
**Mesure** : le filtre de palette porte jusqu'à ~20 000 IDU (`['in', idu, ['literal', …]]`) sur
`parcels-fill`/`ile-fill`. Coût d'un `setFilter` mesuré WebKit : **2,2 ms** (lourd) vs 0,2 ms (vide) ; le
coût réel est la ré-évaluation par parcelle à chaque (re)construction des buckets maplibre, surtout à
l'échelle de l'île (50 000 parcelles). L'effet de peinture a `module` dans ses deps → un clic d'outil le
rejoue.
**Fix (déchargé hors carte, rechargé au retour)** : dès qu'un **outil** (`module`) ou une **fiche**
(`selectedIdu`) prend le focus, le filtre de palette est remplacé par un filtre **no-op** (`['==', idu,
' ']`) — maplibre ne scanne plus les 20 000 IDU, il ne colorie rien, les contours restent. Au retour à la
carte nue, le filtre complet est **rechargé** (`resultIdus` intact). `selectedIdu` ajouté aux deps pour
déclencher décharge/recharge.
**Avant/après** : avant, le filtre lourd restait actif sous la fiche/l'outil (ré-évalué à chaque frame) ;
après, zéro travail de coloriage hors carte (filtre trivial), coloriage restauré au retour.

---

## Fichiers touchés
**Front** : `outils/moteurs.tsx` (Assemblage) · `outils/blocB.tsx` (Pièges) · `outils/EtudeZone.tsx` ·
`outils/AnalyserAnnonce.tsx` (Estimer) · `outils/Gabarit.tsx` · `outils/ProspectionSolaire.tsx` ·
`outils/TaxeAmenagement.tsx` · `outils/Blocs.tsx` · `outils/Successions.tsx` · `outils/ScanPatrimoine.tsx` ·
`outils/EntreeParcelle.tsx` · `outils/ModulePanel.tsx` (Courrier) · `map/Legend.tsx` · `map/CouchesTuyau.tsx` ·
`map/MapView.tsx` (légende empilée + déchargement coloriage) · `styles/index.css` (tuiles) · `lib/api.ts` ·
`outils/Assemblage.test.tsx`.
**Back** : `config.py` (prix/délai courrier) · `courrier.py` + `api/courrier.py` (statut) ·
`assemblage.py` + `api/moteurs.py` (prix de sortie).
