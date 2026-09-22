# RAPPORT M56-B6 — Fiche : tiroirs en cartes autonomes (référence v6)

Branche `feat/m56-b6` (partie de `main`, qui contient déjà M56 A→E + B2→B5 mergés
par Vic). **NON mergé** (doctrine : CC ne merge jamais).

## Source de vérité
`docs/DA-FICHE-v6.html` (copiée depuis le fichier fourni) : nouvelle référence
visuelle de la fiche, qui **remplace la section 4** de `docs/DA-LABUSE.html`.
Classes transcrites telles quelles (scopées sous `.fiche-v6` pour ne pas heurter
les `.stats`/`.stat`/`.legal` globales), vraies données versées dedans.

## Le changement de fond (fait)
Les 7 tiroirs ne sont plus regroupés dans deux `.gcard`. **Chaque tiroir est une
CARTE AUTONOME** (`.tiroir` : fond `--f-card #121815`, bord `--f-linecard #253029`,
rayon 12, écart 9px) posée sur un fond de panneau **plus sombre** (`--bg-0 #0A0C0B`,
via `.fiche-v6`). Chaque tiroir porte une **pastille d'icône 32×32** (`.t-ico`,
fond `--line`, icône 15px grise) — l'ancien prop `icon` (ignoré depuis M55-L) est
RÉACTIVÉ, en réutilisant la bibliothèque `IC` existante. Les libellés
LE TERRAIN / LE CONTEXTE deviennent **un texte + un filet** (`.sec`), sans conteneur.

## Structure alignée v6 (fait)
- **En-tête** en carte `.head` (fond `--bg-2`) : `.eyebrow` + `.ref` (mono + copier
  sans cadre) + `.addr` + `.addr-link` + 3 `.hbtn` (26px) ; `.stats` 4 colonnes
  (valeur absente → `.stat-v.vide`).
- **Bouton d'analyse** `.cta` pleine largeur (40px) + `.cta-sub`.
- **Bandeau d'attention** `.band` (fond `--f-amberband #1C1509`, filet 2px `--amber`,
  texte `--f-ambertxt`), replié une ligne + « i » (texte intégral dans l'infobulle).
- **Boutons IA** `.ia-btn` (34px), icônes SVG existantes conservées.
- **Tiroirs** `.tiroir` fermés + ouverts (`.is-open` → coins bas carrés, `.t-open`
  prolonge la carte). Sous-titre `.t-sub` tronqué UNE ligne ; valeur `.t-val`
  (absente → `.t-val.absent`) ou pastille `.pill-amber`/`.pill-mint`.
- **Actions** `.actions` → `.act-crm` / `.act-proj` / `.act-cmp` (PipelineButton,
  ProjetButton, Comparer).
- **Exports** carte `.exports` : grille 4 colonnes `.exp` (PDF, Dossier, Finance,
  Cadastre, 1950, Maps, Courrier, One-pager) + bandeau large `.exp-wide`
  (Pré-dossier PC). Les 9 exports CONSERVÉS (tuiles conditionnelles f.coords
  inchangées). DossierTile / BanquierButton / PreDossierTile reskinnés en `.exp`.
- **Mention légale** `.legal`.

## Règle v6 « pas de pourcentage nu » (fait)
« Données et méthode » ne montre plus « 90 % » nu à droite : la couverture ICD passe
dans le sous-titre (« N sources · couverture 90 % »), la colonne droite ne porte que
le chevron.

## Périmètre respecté
Présentation uniquement. Accordéon exclusif, verdict à la demande, calculs, routes,
exports PDF : intacts. Icônes : bibliothèque existante conservée (tailles alignées
15px). Tokens NOUVEAUX (fiche v6) : `--f-card/linecard/linehead/icotxt` +
`--f-amberband/ambertxt/amberico`, dans `:root`.

## Superposition (méthode imposée)
Fiche **97418000BE0256** (Sainte-Marie) ouverte à côté de `DA-FICHE-v6.html` :
superposable. En-tête carte, 4 chiffres (1 171 m² / N / 647 m² / 301 €/m²), CTA,
bandeau « Marché peu actif à Sainte-Marie », 2 boutons IA, LE TERRAIN (Urbanisme
9 m max, Constructibilité « non calculable » faint, Risques « 3 vigilances » pastille),
LE CONTEXTE (Marché 301 €/m², Réseaux « probable », Propriétaire privé, Données),
actions, EXPORTS. Tiroir ouvert : la carte s'ouvre en continu, contenu plat.

## À reporter dans docs/DA-LABUSE.html (fait)
- §4 : bandeau de RENVOI vers `DA-FICHE-v6.html` (4/4b/4c conservées « pour mémoire »).
- Règle 1 (§2) mise à jour : sur la fiche, un tiroir est une carte autonome, pas une
  rangée dans un groupe encarté ; le relief vient du contraste fond/carte.

## Garde-fous
tsc 0 · vitest 32/32 · build OK · console **0 erreur** sur les 4 parcelles M55-O
**+ 97418000BE0256** · export PDF premium CT1389 = **HTTP 200 `application/pdf`
67 Ko** (inchangé).

## STOP
Mandat M56-B6 livré. **Branche `feat/m56-b6` non mergée.** Fin.
