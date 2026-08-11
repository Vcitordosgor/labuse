# RAPPORT M55-G — Résultats & parcours : le polish final (13 points, 12/08/2026)

**Branche** : `feat/m55-g` (base : main `62b5e162`, M55-F mergé — précondition vérifiée au git log).
**13 commits, un par point** (`46c739f1` → `a90272d3`). CC ne merge jamais.
**Captures** : `reports/m55-g/captures/{avant,apres}/` (harnais `frontend/qa/m55g_captures.mjs`,
rejouable : `node qa/m55g_captures.mjs avant|apres`).

---

## Point 1 — Contrôles d'entête : UN patron
`ChevronSection.tsx` refondu : boîte CONSTANTE `h-7 w-7 rounded-md` avec bordure visible
hors survol (le constat « flottent, sans boîte » venait du fond apparaissant seulement au
hover), gabarit unique croix/chevrons (la variante `petit` h-6 supprimée), seule la flèche
tourne, hover franc. Nouveau `CroixEntete` appliqué aux trois croix (panneau desktop, tiroir
mobile, modale). Tous flush à droite → une colonne. Captures `p1_*` avant/après.

## Point 2 — Les deux boutons de fin de filtres
« **Voir les N parcelles** » passe en premier (sobre) ; le CTA mint passe second et devient
« **Révéler les opportunités →** » (le mot reste vrai : le classement est pré-calculé, run
servi versionné — commentaire posé dans strings.ts). `boutonParc` retiré (0-caller depuis
stage 8). La carte ne bouge toujours qu'au geste. Capture `p2_deux_boutons_zoom`.

## Point 3 — Barre TRIER
Segmented control net : conteneur `rounded-lg p-0.5`, pills `rounded-md px-3 py-1` (padding
constant), état actif FRANC (rempli mint, texte encre — fini le mint/15 flottant), « i »
15 px aligné sur la ligne TRIER. Capture `p3_tri_bar_zoom`.

## Point 4 — « pourquoi ? » → « comprendre le classement → »
**Arbitrage consigné** : le mandat dit « (ouvre la même modale) » — l'ancien « pourquoi ? »
ouvrait l'entonnoir par motif (un panneau en flux, PAS une modale), et le nouveau libellé
est exactement celui du bouton du bandeau. J'ai donc câblé le lien sur la **modale
AlgoExplainer** (état partagé `store.algoOpen`) : une étiquette = une destination — deux
liens homonymes vers deux cibles différentes auraient été pire que le constat. Conséquence :
le panneau entonnoir par motif n'a plus de déclencheur et a été retiré (les motifs de
déclassement restent servis par les chips « Déclassées · motif » du panneau + la fiche de
chaque écartée ; l'endpoint `/stats/entonnoir` et `getEntonnoir` restent en place, non
touchés). Si Vic voulait l'autre lecture (même panneau, juste renommé), c'est un revert
d'un commit. Preuve : clic → modale ouverte (sonde), capture `p4_ligne_comprendre_zoom`.

## Point 5 — Ligne propriétaires retirée
Le bloc `data-dossiers-detail` (« soit N parcelles avec dossier propriétaire… N personnes
physiques ») quitte la zone résultats. **0-caller prouvé** (grep : seules subsistent les
déclarations de type API `opportunites_avec_dossier`/`dossiers_opportunites`/
`opportunites_sans_identite`, contrat serveur inchangé). L'info vit en fiche.

## Point 6 — Modale « Comment LABUSE classe » : mesuré PUIS resserré
**Mesures (modèle servi q_v8_calibre, vérifiées en base le 12/08)** :

| Affirmation de l'ancienne modale | Mesure | Verdict |
|---|---|---|
| « Le plafond est ×64 … certitude maximale » | AUCUN plafond codé (`p_v2/pipeline.py:424` : `mult_base = p/taux_base`, jamais clippé) ; max MESURÉ **×64,36**, **3 parcelles** / 431 663 | FAUX (pas un plafond — un sommet) |
| « procédures, succession, dirigeant » dans l'entraînement | Features réelles du modèle P (`p_model/features.py`) : tenure_bin (âge de détention), permis_bin, friche/végétation/emprise (état du bâti), zone_plu, marché DVF du secteur, Filosofi, pente, équipements. BODACC/succession/dirigeant = signaux du **Score V**, PAS du modèle P | FAUX |
| « ventes, divisions, changements d'usage » | Aucune feature divisions / changement d'usage | Imprécis |
| Période | Entraîné sur les mutations **2023**, validé sur **2024** (`scripts/m3-p-model/train.py:60-63`, `FREEZE.json` : train "2023", gel 12/07/2026) | précisé |
| « 431 663 parcelles » | `count(*) = 431 663` (run q_v8_calibre) | ✓ |

**Fix** : version resserrée de Vic posée avec les faits corrigés (période « année 2023,
vérifié sur les ventes 2024 » ; signaux réels « âge de détention, permis, état du bâti,
marché du secteur, règles PLU » ; ×N « la tête du classement culmine à ×64 — trois parcelles
sur toute l'île : un sommet mesuré, pas un plafond fixé par le modèle »). **« dirigeant »
retiré de la liste publique** (avis avocat P2-34 en attente). La même affirmation fausse
vivait aussi dans l'infobulle ×N des cartes (`CLIENT.mult.tip`) — corrigée à l'identique.

## Point 7 — État post-analyse nettoyé
**Mesure** : « Quels risques ? » n'existait déjà plus (retiré au stage 7) — restaient
**4 tiroirs** (Combien ça coûte / Ça va se vendre / À qui c'est / Veille & niches). La
« phrase dupliquée » : la phrase de Révélation n'est rendue qu'une fois DANS le panneau
(sonde DOM : 1 occurrence), la duplication vue par Vic est panneau ré-ouvert + récit de la
zone résultats juste dessous. **Fix** : la phrase ne vit plus qu'au moment du reveal
(`phase === 'revealed'`) ; les 4 tiroirs retirés (composants `Tiroir`/`ModeBCurseur` et
constantes 0-caller supprimés — le curseur mode B de session reste au store, la fiche le
lit toujours). **Gardé** : chips tiers, motifs, constructibilité, potentiel, SDP, capacité,
veille, copros + « Relancer l'analyse » / « désactiver l'analyse ». Les champs experts des
tiroirs (budget, ×N, rang, propriété…) gardent leurs clés URL — vieux liens compatibles.

## Point 8 — Le mode factuel l'est vraiment (décision Vic)
**Mesure avant** (capture + code) : le mode « Voir les parcelles » affichait TOUT l'appareil
d'opinion — chips de tier colorées (Brûlante·1…), ×64.4, ventilation « 118 brûlantes ·
1038 chaudes · 2964 potentiel », barre de tiers, ligne « 431663 analysées → 1156
opportunités », 3 tris dont 2 d'opinion, carte peinte en palette tiers + lisérés + marqueurs
communes « chauds », légende Verdict disponible.
**Fix** :
- liste NEUTRE (référence, adresse, surface, commune — zéro badge, zéro ×N, zéro liseré) ;
- tri **Surface** seul (bascule automatique du tri au changement de mode) ;
- carte : surbrillance NEUTRE `#8FA69A` des parcelles correspondantes ; lisérés
  promues/brûlantes et marqueurs « chauds » éteints ;
- nouvelle couche Couches « **Verdict (couleurs du classement)** » (`couleurs_verdict`,
  OFF par défaut) : l'avis LABUSE reste activable manuellement, jamais imposé ;
- bandeau « Tri factuel — sans analyse » conservé ; la FICHE ouverte reste complète
  (verdict inclus) — rien n'est caché.
**Preuve (sonde)** : factuel = 0 chip, [Surface], 0 ×N, fill `#8FA69A`, 0 ventilation ;
bascule analyse = 200 chips, 3 tris, palette STATUS restaurée. 1ʳᵉ carte factuelle =
BN 0004, 28 174 868 m², Saint-Philippe (tri Surface desc correct).

## Point 9 — Reset
« **Réinitialiser les filtres** », contour `st-ecartee/40` discret (pas un pavé), hover
rouge léger. Geste inchangé (deux étages + interrupteur), le `title` le dit toujours.

## Point 10 — Légende conditionnelle
Nouveau canal store `mapPeint` (écrit par MapView : parcelles peintes = couche active ET
(commune OU z ≥ 10, le seuil du bandeau « Zoomez… ») ; équipements = z ≥ 12, leur minzoom ;
zonage = remplissage famille effectif). La légende (`Legend.tsx`) ne rend une section que si
ses couleurs sont À L'ÉCRAN ; le panneau entier disparaît s'il n'a rien à dire. Verdict :
jamais en mode factuel (P8), jamais sur l'île sans parcelles peintes ; repliée par défaut
(inchangé). **Sonde 4 états** : île initiale 0 · factuel 0 · analyse dézoomée 0 · analyse
z=12 → 1, repliée. Équipements et zonage suivent la même règle.

## Point 11 — Signaux de vie : larges devant, niches derrière
**Mesure préalable** (SQL, univers /filtre, run servi) — nouveau signal « Détenu par une
société » = parcelle de PM privée (groupe MAJIC 0, même arbitrage que nu_pm), nu ET bâti :
**33 622 île / 7 460 servables** (hors étage 0) → sous le plafond ~100k, implémenté.
- **Niveau 1 (larges)** : Détenu par une société (nouveau) · Procédure collective ·
  Permis actif · Permis abandonné · Friche.
- **Niveau 2 (« Plus de signaux ⌄ »)** : Nu détenu par société (conservé tel quel) ·
  Sortie de défisc · Cession de fonds · Assemblage même proprio. Ouvert d'office si une
  niche est active (restauration URL : jamais un filtre actif invisible).
- Backend : UNE entrée ajoutée au dict `_SIG_SQL` de /filtre (`pm_privee`) — la création
  demandée par le point ; aucun nouvel endpoint. Vérifié : `/filtre?signaux=pm_privee`
  → 33 622 ; `procedure` → 658 (inchangé). ⚠ le serveur uvicorn (sans --reload) a été
  redémarré pour charger l'entrée.
- « i », OU de groupe, persistance URL (`sv=`) : inchangés — clé ajoutée au schéma existant.

**Candidats larges supplémentaires (volumétrie mesurée — Vic tranche)** :

| Candidat | n île | n servables | Avis |
|---|---|---|---|
| Vendue récemment (mutation DVF < 36 mois) | 17 218 | 4 459 | bon candidat large |
| Bâti en sous-densité (parcel_residuel) | 63 917 | 38 670 | large, très volumineux mais < 100k |
| Bailleur social (HLM/SEM, groupes 5-6) | 11 697 | 2 781 | candidat (démarche dédiée) |
| Foncier public (État/collectivités, grp 1-4,9) | 36 379 | **0** | tout en étage 0 — utile en voie factuelle seulement |
| DPE passoire F/G rattachée | **2** | 0 | gadget (< 50) — rattachement parcelle quasi vide, à écarter |

## Point 12 — Communes
« tout » → « **Ajouter tout** », « rien (toute l'île) » → « **Retirer tout** » (libellés
d'action ; le sous-titre « tout coché = toute l'île » garde le sens du vide).

## Point 13 — Feedback d'appui zoom
Patron `BoutonCarte` (MapView) : au clic, flash mint 180 ms puis retour — un accusé d'appui,
pas un état. Appliqué aux « + / − ». **Arbitrage** : les autres boutons de carte (fond, 3D,
outils de mesure) sont des bascules À ÉTAT — leur feedback est l'état persistant lui-même ;
le patron est réservé aux boutons momentanés (et prêt pour une future boussole).

---

## Non-régression
- **5 combinaisons /filtre identiques** (avant = après, mêmes chiffres qu'au constat M55-F) :
  sans filtre 431 663 (118/1038/2964/29978/354355) · Saint-Denis 38 138 ·
  tiers=brûlante,chaude 1 156 · signaux=procédure,friche 2 458 ·
  surface 1000-5000 + nu + Saint-Paul 948.
- **Rituel 3,0 s intact** : clic → « Voir les parcelles » mesuré à 3 345 ms (3 000 ms
  d'animation + réseau).
- **Synchro M55-F préservée** : le point unique `getFiltre(filters)` alimente toujours
  compteur vivant, Révélation et zone résultats — la phrase n'existe plus qu'au reveal,
  le récit permanent est celui de la zone résultats (un seul récit).
- **Vieux liens** : `#f=1&sv=nu_pm,procedure&mm=5&bud=500000&smin=1000&al=1` (clés des
  tiroirs retirés incluses) s'ouvre sans erreur, chips restaurées, niche auto-ouverte,
  compteur vivant actif. Aucune clé URL retirée.
- **tsc 0 · vitest 32/32 · build vert** (warning chunk > 500 kB préexistant).
- **Mobile vérifié** (375 px) : tiroir, accueil, nouvelle couche Verdict listée ;
  la légende inline suit la même règle conditionnelle.
- **0 erreur console** sur toutes les sessions de capture.

## Périmètre
Front + mesures, PLUS l'entrée `_SIG_SQL.pm_privee` dans `src/labuse/api/app.py`
(explicitement demandée par le point 11 — « nouveau signal à créer ») ; aucun nouvel
endpoint, aucun changement moteur/scoring. CC ne merge jamais — branche `feat/m55-g` en
attente de Vic.

---

# SUITE — Ajustements Vic (11/08, sur captures) · livrés le 12/08

**Même branche `feat/m55-g`, 8 commits (un par point)** (`5f5cd61a` → `4492a58c`).
Captures : `reports/m55-g/captures/suite/`.

## 1. Carte raccordée à la liste — MESURÉ puis corrigé
**Mesure** : le filtre carte n'encodait que le sous-ensemble « client » (communes, tiers,
surface, SDP min, événement, veille, copro) — signaux de vie, état du sol, constructibilité,
propriété, économie… étaient IGNORÉS par la carte. Repro : Salazie + Procédure collective →
liste 1 parcelle, carte = toute la commune en palette (filtre observé : communes seul).
**Fix** : `/filtre` gagne `idus=1` (les IDU du résultat, mêmes critères, plafond 20 000 +
drapeau tronqué — pas un nouvel endpoint) ; quand un critère hors-tuiles est actif en mode
analyse, la carte restreint la palette (remplissage + lisérés promues/brûlantes) aux IDU du
résultat, le reste passe en TRAME NEUTRE (nouvelles couches base). Au-delà du plafond :
repli sur l'expression + toast (no-silent-caps). La couche Couches devient « **Verdict —
toute l'île (indépendant des filtres)** » et peint tout le classement quand cochée.
**Test exigé** : Salazie + procédure → liste N = 1, parcelles peintes = 1, filtre carte
`in idu [97421000AV1151]`, trame neutre visible. ✓

## 2. TRIER une ligne
« Opportunités · Mutation · Surface » — les libellés longs (« Meilleures opportunités »,
« Plus susceptibles de se vendre ») vivent dans le « i » et les tooltips des pills.

## 3. Post-analyse : les deux boutons, rien d'autre
Tout le contenu de l'état allumé retiré (chips verdict/tiers, motifs, constructibilité,
potentiel, SDP, capacité, veille, copros, notes — composants BoolChip/Section et constante
CONSTRUCTIBILITE devenus 0-caller, supprimés). Restent « Relancer l'analyse » et
« désactiver l'analyse ». Conséquence actée : le filtrage par tier post-analyse quitte ce
panneau ; les champs gardent leurs clés URL (vieux liens compatibles). Sonde DOM : Relancer
présent, chips absentes, phrase absente. ✓

## 4. Signaux : un seul niveau, 7 signaux
Détenu par une société · Procédure collective · Permis actif · Permis abandonné · Friche
recensée · Assemblage même proprio · Sortie de défisc. « Plus de signaux » et le niveau 2
retirés ; « Nu détenu par société » et « Cession de fonds » SUPPRIMÉS de l'UI (labels/infos
0-caller). Clés URL : `SIGNAUX_VALIDES` dans filters.ts — un vieux lien
`sv=nu_pm,cession,procedure` s'ouvre sans erreur et compte 207 (= procédure seule dans
l'univers d'analyse ; si les clés supprimées passaient encore : 2 759). Backend intact
(`_SIG_SQL` conserve nu_pm/cession).

## 5. Bandeau « notées par LABUSE » supprimé
Bloc contexte + sous-ligne retirés (chaînes 0-caller supprimées). La date du run servi
n'était en réalité PAS encore dans la modale — elle y est maintenant (pied de modale :
« Classement servi du 12/07/2026 — versionné… », champ `gel` du modèle épinglé, ligne
absente si indisponible) : l'affirmation du mandat est rendue vraie, rien n'est perdu.

## 6. CTA : « Demander à LABUSE → » (remplace « Révéler les opportunités → » du point 2).

## 7. Sous-titres de sections retirés
Communes, Le terrain, Signaux de vie (+ le sous-texte du label Zonage) — les explications
vivent dans des « i » au titre (patron TitreSection, mêmes pastilles que les signaux).

## 8. Tri Surface + adresses — MESURÉ
- Tri Surface : fonctionne (1ʳᵉ = 28 174 868 m², Saint-Philippe). Pas d'inversion au second
  clic (le serveur sert un sens par clé) → le SENS est affiché sur la pill active
  (« Surface ↓ », « Mutation ↓ » ; Opportunités = n°1 d'abord, dit par le tip).
- Adresses : **aucune jointure cassée**. La BAN couvre **227 545 parcelles / 431 663
  (52,7 %)** — le « 99,99 % » de la page Sources est le taux de rattachement des ADRESSES
  (339 941 adresses → toutes rattachées), pas la couverture des parcelles : la moitié de
  l'île (naturel, agricole, ravines) n'a pas d'adresse postale, c'est la réalité BAN.
  Le tri Surface remonte précisément les grandes parcelles naturelles → 198/200 sans
  adresse en tête de liste (vérifié en base : 0 adresse BAN pour les 6 premières), contre
  97/200 au tri rang (≈ la couverture globale). « Adresse non disponible » est donc VRAI.
- Référence courte conservée en affichage principal ; l'**IDU complet** est au survol de la
  référence (title) sur les deux variantes de carte, et en fiche.

## Non-régression (suite)
5 combinaisons /filtre STRICTEMENT identiques (mêmes chiffres qu'au rapport initial) ·
rituel mesuré 3 332 ms · un seul récit de nombres préservé · mode factuel P8 préservé
(liste neutre, Surface seul, carte neutre) · vieux liens vérifiés (sv= supprimées ignorées,
compteur exact) · tsc 0 · vitest 32/32 · build vert · mobile vérifié · les deux « 404 »
console de la session de capture sont des tuiles océan IGN (déjà avalées par la carte),
non reproduites au chargement.
