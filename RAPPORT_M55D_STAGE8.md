# RAPPORT M55-D — stage 8 : synchro du compteur, texte du funnel, page d'accueil

Branche `feat/m55-d-stage8` (base `main` d405f0ef, **stage 7 mergé — précondition vérifiée**).
Front seul — aucun endpoint, aucun moteur. tsc 0, vitest 32/32, build vert.

## 1. Un seul nombre, partout, en même temps ✅
Le constat (compteur « 3 » vs bandeau/bouton « 6 312 ») venait de **trois sources parallèles** :
le compteur vivant (stage 7), `parcQ` (parc du périmètre, requête distincte) et l'accroche
chiffrée de FiltresSection (une 4ᵉ requête). **Point de calcul unique appliqué à l'écran** :
- compteur, bandeau (« N parcelles notées par LABUSE — classement du 12/07/2026 »), bouton et
  phrase de la Révélation dérivent **tous du même état `live`** (le /filtre count du stage 7,
  debounce 400 ms + AbortController) ;
- `parcQ` et l'accroche chiffrée **supprimés** (plus aucun second chiffre possible) ;
- pendant le fetch, **l'opacité baisse partout en même temps** (`liveLoading` partagé) ;
- la **date** du classement reste au bandeau — elle ne dépend pas des filtres.

**Test de synchro** (automatisé) : 5 changements de filtres, échantillonnage toutes les ~90 ms →
**70 échantillons, 0 désaccord** compteur↔bandeau. Égalité constatée : 9 822 == 9 822.

## 2. Texte du funnel ✅
- Compteur : « **9 822 parcelles correspondent à vos critères** ».
- Bouton avec filtres : « **Les faire analyser par LABUSE →** » (renvoie au nombre affiché
  au-dessus — pas un second chiffre qui pourrait diverger) ; zéro filtre : « **Analyser les
  431 663 parcelles** » (parc du périmètre, compteur masqué).
- Rituel **3,00 s** intact ; phrase mesurée : « *LABUSE a analysé les 9 822 parcelles de
  Saint-Paul. Selon vos critères (Saint-Paul, > 2 000 m²) : 703 retenues — dont 0 brûlante,
  17 chaudes, 276 en potentiel long terme.* »

## 3. Un seul appel à l'action ✅
- **Le bouton du panneau est l'unique CTA d'analyse** — `data-verdict-on` supprimé, grep : 0
  CTA d'analyse hors panneau.
- **L'accueil devient une page de présentation** (`CLIENT.accueil`, strings.ts) : l'intro
  conservée (« le cadastre entier est sous vos yeux… ») + 6 points **sobres et factuels**
  (431 663 parcelles / 24 communes calibrées sur les PLU réels · classement daté versionné ·
  8 signaux de vie · documents en un clic · Marché/veille/CRM · conçu à La Réunion) + la
  doctrine (« rien n'est masqué, chaque chiffre porte sa source ») + **un lien « Commencer → »**
  qui ouvre la section Filtres.
- **Ne réapparaît pas après le premier geste** de la session (`accueilVu` : Commencer, ouverture
  d'une section Couches/Filtres, analyse allumée — état de session, non persisté).

## Non-régression (vert)
5 combinaisons `/filtre` identiques (9822 · 188 · 1710 · 3770 · 51129) · vieux lien
`tv=chaude&smin=2000` → 0 erreur, analyse héritée · rituel 3,0 s · égalité
compteur↔bandeau↔bouton · mobile vérifié. Captures `s8_accueil`, `s8_panneau_sync`, `s8_mobile`.

CC ne merge jamais.
