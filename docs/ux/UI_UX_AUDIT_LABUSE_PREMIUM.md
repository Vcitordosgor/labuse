# Audit UI/UX LABUSE — niveau produit premium B2B

> Audit design **chirurgical**, exigence « SaaS B2B vendable », pas démo technique. **Audit seul —
> aucune modification de code/DB, aucune correction** (rapport versionné docs-only après décision).
> Réalisé le 2026-06-28 sur `main = c0a623e`.
> Screenshots réels (desktop 1440/1920, tablette 768, mobile 390, fiches, carte+Radar, états vides).
> Note env. : le fond de carte CartoDB est **bloqué par le bac à sable** → carte sur fond noir ; en
> prod il se charge. L'audit en tient compte mais souligne la dépendance au basemap.

## 1. Verdict global : ⚠️ **ATTENTION (design)**

LABUSE est **fonctionnel, crédible et professionnel**, mais il lit aujourd'hui comme un **« outil
expert sérieux »** plus que comme un **« SaaS premium vendable »**. Rien ne bloque l'usage (0 P0), et
la matière (données sourcées, prudence, multi-commune, Radar) est un vrai atout. Mais une poignée de
frictions visuelles (carte vide/noire, contraste « à creuser », rupture de thème fiche, empty-state
trompeur, fuites « dev/démo ») l'empêchent de **paraître premium**. **Pas besoin d'une refonte
complète ni d'une nouvelle direction artistique** : des **quick wins + une refonte légère** suffisent.

## 2. Notes /10

| Axe | Note | Commentaire |
|---|---|---|
| **Crédibilité** | **8** | tags SOURCÉ/ESTIMÉ, « jamais garanties », badges gold/partielle/non-évaluée, données métier structurées = très crédible |
| **Clarté** | **6,5** | bonne structure mais densité forte, carte surchargée en couleurs (calques cumulés), fiche longue/redondante, empty-state trompeur |
| **Premium** | **6** | dark + or sobre et pro, mais carte noire/vide, rupture de thème fiche, fuites dev, contraste « à creuser » → « power tool », pas « premium SaaS » |
| **UX promoteur** | **7** | shortlist + fiche + Radar = forte valeur ; mais valeur-en-10 s freinée, shortlist sous la ligne de flottaison (desktop), fiche très longue |
| **Responsive** | **8** | mobile/tablette soignés (KPI à bord coloré, chips qui wrappent, 0 overflow) ; nit : sélecteur derrière l'onglet « Liste » |
| **Design system** | **6,5** | dark + or/violet cohérent, typo correcte ; mais fiche claire dans app sombre, contrôles dispersés, double légende |
| **GLOBAL** | **~7/10** | base solide, polish ciblé requis |

## 3. Ce qui est déjà bon

- **Identité dark + or** sobre, sérieuse, adaptée à un « radar ». Le violet Radar Mutation est bien
  distinct des couleurs de verdict.
- **Crédibilité métier** : chaque donnée porte SOURCÉ ou ESTIMÉ ; disclaimer « jamais garanties » ;
  badges de fiabilité commune (gold / partielle / non évaluée) → transparence rare et vendeuse.
- **Fiche dense et utile** : zonage, occupation, capacité constructible, charge foncière, contraintes
  « lever d'abord », synthèse structurée — exactement le vocabulaire promoteur.
- **Shortlist promoteur** : parcelles + score + surface + badge = actionnable.
- **Responsive mobile/tablette** réellement soigné (mieux que le desktop par endroits).
- **Multi-commune** : sélecteur clair, 24 communes, statuts différenciés, états vides gérés sans crash.

## 4. Ce qui fait encore « démo / dev »

- **« Démo guidée · 8 cas »** en action rapide proéminente → signale « ceci est une démo ».
- **« Analyse IA enrichie disponible sur activation (clé API côté serveur) »** dans la fiche → jargon
  technique exposé au client.
- **Carte sur fond noir** avec parcelles flottant dans le vide (surtout 1440 et communes peu denses)
  → impression « inachevé » au premier coup d'œil.
- **Empty-state non-évaluée** qui parle de « filtres » et propose des boutons qui ne font rien.

## 5. Ce qui empêche de faire premium

1. **Rupture de thème fiche** : app **sombre** → fiche **crème/claire**. Désoriente, casse la cohérence.
2. **Carte = beaucoup de noir** + parcelles « à creuser » **brun très bas contraste** (quasi invisibles
   sur Cilaos). Le « waouh cartographique » attendu d'un outil spatial n'y est pas (dépendance basemap).
3. **Surcharge cognitive** : calques cumulés (verdict + Radar) = 5-6 couleurs simultanées + 2 légendes.
4. **Hiérarchie de valeur** : la **shortlist** (le cœur) est **sous la ligne de flottaison** desktop ;
   dans la fiche, le **Radar (souvent le signal le plus fort, ex. 100/100) est tout en bas**.

## 6. Audit par écran / zone

### Première impression (10 s)
- On comprend « radar foncier La Réunion » + KPIs + shortlist. **Mais** le regard tombe d'abord sur la
  **carte noire à moitié vide** → doute. La proposition de valeur (« trouvez les meilleures parcelles
  à étudier ») n'est pas verbalisée ; il faut la deviner. **Valeur-en-10 s : moyenne.**

### Architecture de l'écran
- Split classique **sidebar gauche (~370 px) / carte**. F-pattern correct (marque → commune → actions →
  KPIs → shortlist). **Problème** : 4 cartes « Actions rapides » + 4 KPIs poussent la **shortlist** (la
  valeur) **hors écran**. Zone morte : grands écrans → la carte gagne de l'espace vide (atténué par
  fitBounds qui remplit mieux en 1920).

### Carte
- Parcelles colorées par verdict lisibles pour **Opportunité (vert)** ; **À creuser (brun) trop sombre**
  → faible affordance. Calque Radar (violet) net **mais** cumulé au verdict = ambiguïté (une parcelle
  verte sous violet = quoi ?). Contrôles **dispersés** (Couleur Verdict/Mutabilité, Mesurer, Assembler,
  icône calques). **Deux légendes empilées**. fitBounds OK. Tooltips OK (vu en QA).

### Sidebar
- Bien sectionnée (ACTIONS / VUE D'ENSEMBLE / FILTRES / Shortlist), scannable. **Mais** dense et la
  hiérarchie favorise « À CREUSER » (gros chiffre orange) au détriment de « OPPORTUNITÉS » (la valeur).
  « Se déconnecter » collé au disclaimer (placement bancal).

### Fiche parcelle
- Très complète et crédible. **Mais** : **longue** (cartes + synthèse IA + cascade + Radar), la
  **synthèse IA répète** les cartes (Potentiel/Contraintes/Bâti/Économie), le **Radar est relégué en
  bas**, **thème clair** en rupture, et une **fuite jargon** (« clé API côté serveur »). Ce qui manque
  pour décider : un **résumé décisionnel en tête** (verdict + radar + 1 chiffre clé + 1 action).

### Multi-commune
- Sélecteur + badges **gold / partielle / non évaluée** clairs et différenciés (vrai atout produit
  24 communes). **Mais** l'**empty-state non-évaluée (Saint-Philippe)** est **trompeur**.

## 7. Audit du parcours démo promoteur

| Étape | Fluide ? | Friction |
|---|---|---|
| Ouvrir l'app | ⚠️ | carte noire à moitié vide = mauvais « hook » visuel |
| Choisir une commune | ✅ | sélecteur + badge nets |
| Montrer les meilleures parcelles | ✅ | shortlist claire (mais à scroller) |
| Activer Radar Mutation | ⚠️ | calque violet OK, mais cumul de couleurs/légendes |
| Ouvrir une fiche | ✅ | riche, crédible |
| Opportunité vs Mutation | ⚠️ | la distinction est dite, mais le Radar est en bas de fiche |
| Parcelle avec contrainte | ✅ | AB0492 : badge + malus −15 + PPR très lisible (excellent exemple) |
| Commune partielle | ✅ | badge PARTIELLE clair |
| **Commune non évaluée** | ❌ | **empty-state trompeur** (« filtres » + CTA morts) — casse la démo |
| Conclure valeur business | ⚠️ | pas de récap/CTA « passer à l'action » |

## 8. Benchmark externe (résumé)

Patterns des bons SaaS B2B data/carto (Stripe, Linear ; Regrid, Reonomy, Cherre côté immobilier ;
guides dashboard 2026) :
- **Progressive disclosure** : montrer le minimum décisionnel, révéler à la demande (≠ fiche-fleuve).
- **5–9 éléments cœur** max par vue, hiérarchie F-pattern, valeur en haut-gauche.
- **Carte = héros** : fond de carte travaillé, overlays lisibles, **une** légende contextuelle.
- **Sidebar scalable** : sections claires, drill-down sans perte de contexte.
- **Empty states utiles** : expliquer *pourquoi* + proposer la *bonne* action (jamais un cul-de-sac).
- **Design system** tokenisé (espacements, élévation, états hover/focus cohérents).
LABUSE coche : crédibilité, transparence, multi-commune. À rattraper : carte-héros, progressive
disclosure (fiche), empty states, hiérarchie de la valeur, cohérence de thème.

## 9. Problèmes priorisés

**P0 design (bloque l'usage) : AUCUN.**

| ID | Sév | Problème | Pourquoi | Impact business | Reco | Fichier probable | Effort | Risque |
|---|---|---|---|---|---|---|---|---|
| **D1** | **P1** | Carte noire/vide + « à creuser » brun bas contraste | 1ʳᵉ impression « inachevé » ; outil spatial sans waouh carto | doute en démo, sape le premium | éclaircir l'orange « à creuser » (+ contour), fond de carte sobre travaillé, zoom plus serré | `web/app.js` (styleFor/COLORS), `styles.css`, init carte | M | faible |
| **D2** | **P1** | Rupture de thème : app sombre → fiche claire | incohérence, casse l'effet premium | perception « assemblé » | harmoniser la fiche au thème sombre **ou** transition « document » assumée + soignée | `web/styles.css` (fiche), `app.js` renderFiche | M | moyen |
| **D3** | **P2** | Empty-state non-évaluée trompeur (Saint-Philippe) | dit « filtres » + CTA qui ne marchent pas | casse la démo sur 2 communes | message dédié « commune non évaluée — recalcul à venir », retirer les CTA filtres | `web/app.js` updateEmptyState | S | faible |
| **D4** | **P2** | Surcharge couleurs carte (verdict + Radar cumulés) | 5-6 couleurs + 2 légendes simultanées | sémantique floue | mode exclusif (verdict OU radar) ou atténuer le verdict sous radar ; **une** légende contextuelle | `web/app.js` (calques/légendes) | M | moyen |
| **D5** | **P2** | Shortlist sous la ligne de flottaison (desktop) | la valeur est cachée au scroll | valeur-en-10 s ratée | remonter la shortlist OU replier « Actions rapides » par défaut | `web/index.html`, `styles.css` | S | faible |
| **D6** | **P2** | Fiche longue/redondante, Radar en bas | synthèse IA répète les cartes ; signal fort enterré | décision plus lente | **résumé décisionnel en tête** (verdict + radar + chiffre + action) ; remonter Radar ; dédupliquer | `web/app.js` renderFiche | M | moyen |
| **D7** | **P2** | Fuites « dev/démo » (« Démo guidée », « clé API côté serveur ») | jargon/affordance interne exposés | « c'est une démo » | masquer en mode client/prod ; reformuler sans jargon | `web/index.html`, `app.js`, fiche | S | faible |
| **D8** | **P3** | Hiérarchie KPI (À creuser orange domine Opportunités) | l'œil va au tiède, pas à la valeur | priorisation brouillée | hiérarchiser visuellement « Opportunités » (héros) | `web/styles.css` | S | faible |
| **D9** | **P3** | Contrôles carte dispersés | clutter top-right | moins pro | regrouper dans un panneau unique | `web/app.js` controls | M | moyen |
| **D10** | **P3** | Double légende empilée | charge visuelle | — | fusionner / contextualiser | `web/app.js` | S | faible |
| **D11** | **P3** | Sélecteur derrière l'onglet « Liste » (mobile/tablette) | moins direct | mineur | chip commune sur la vue Carte compacte | `web/index.html`, `styles.css` | S | faible |
| **D12** | **P3** | « Se déconnecter » collé au disclaimer | placement bancal | mineur | déplacer dans un menu compte | `web/index.html` | S | faible |
| **D13** | **P3** | Logo perfectible | identité | mineur | affiner la marque | asset | S | faible |

## 10. Plan de refonte recommandé

- **Quick wins (S, risque faible)** : D3 (empty-state), D5 (shortlist en haut / actions repliées),
  D7 (masquer démo/jargon en prod), D8 (héros = Opportunités), D11/D12. → **gros gain de perception
  pour peu d'effort.**
- **Refonte légère (M)** : D1 (contraste carte + fond sobre), D2 (cohérence de thème fiche), D4 (calques
  exclusifs / une légende), D6 (résumé décisionnel en tête de fiche + Radar remonté), D9 (panneau de
  contrôles). → **fait passer de « power tool » à « produit ».**
- **Refonte premium (L)** : design system tokenisé (espacements/élévation/états), carte-héros (style de
  basemap), hero proposition de valeur à l'entrée, progressive disclosure systématique. → **« premium
  SaaS ».** Optionnel, après quick wins + refonte légère.
- **À éviter** : supprimer la densité de données (c'EST la valeur) ; changer la sémantique des couleurs
  de verdict ; refondre l'identité dark + or (bonne) ; toute nouvelle direction artistique complète.

## 11. Screenshots

`01_home_1440`, `09_home_1920` (architecture, vide carte), `02_sidebar_1440`, `03_map_radar_1440`
(surcharge couleurs), `04b_fiche_prioritaire_panel` (fiche claire/longue), `05_fiche_coexistence`,
`06_fiche_contrainte` (bon exemple malus/PPR), `07_cilaos_partielle` (contraste brun), `08_saint_
philippe_vide` (empty-state trompeur), `10/11_tablette_768`, `12/13/14_mobile_390` (responsive soigné).

## 12. Recommandation finale

> **Ni refonte complète, ni nouvelle direction artistique.** L'identité (dark + or), la densité de
> données et la crédibilité sont des **atouts à garder**. Faire **quick wins + refonte légère** pour
> passer de « outil expert » à « SaaS premium vendable ».
>
> **Les 5 corrections à faire en premier :**
> 1. **D3** — réparer l'empty-state des communes non évaluées (message juste, retirer les CTA morts).
> 2. **D1** — éclaircir/contourer « à creuser » + fond de carte sobre travaillé (lisibilité carto).
> 3. **D6** — **résumé décisionnel en tête de fiche** (verdict + Radar + chiffre clé + action) et
>    remonter le bloc Radar ; dédupliquer la synthèse IA.
> 4. **D5 + D7** — remonter la **shortlist** au-dessus de la ligne de flottaison + masquer les fuites
>    « Démo guidée / clé API » en mode client.
> 5. **D2** — harmoniser la **fiche** au thème sombre (cohérence premium).
>
> Verdict : **ATTENTION** — montrable en démo dès aujourd'hui (avec la commune Saint-Paul gold), mais
> ces 5 corrections changent radicalement la **perception premium** avant une vraie campagne de vente.
