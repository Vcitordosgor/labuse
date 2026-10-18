# Captures AVANT / APRÈS — FIX-PRIX-ET-OPPORTUNITES lot 1

Toute **valeur de parcelle estimée** s'affiche en **fourchette arrondie** avec une **mention
d'incertitude mesurée** (backtest VERITE-TERRAIN-2 vol. E : écart médian 27 %, 37 % des ventes à ±20 %,
biais −5,6 %), jamais en chiffre sec. Les **médianes DVF sourcées** (observations, avec effectif) ne sont
PAS touchées.

Rendues sans base par `scripts/captures_prix_fourchette.py` (fonctions pures + harnais `_FakeDB`), même
parcelle fictive (768 €/m² × 742 m² = 569 831 €, INSEE 97404 = L'Étang-Salé). AVANT = code `main` (source
stashée), APRÈS = ce lot.

| # | Point | AVANT | APRÈS |
|---|---|---|---|
| (b) | Bloc PDF « 5. Marché » (`bloc_marche_*.png`) | `569 831 €` nu | `390 000 € – 750 000 €` + note mesurée |
| (b) | Fiche Marché + Constructibilité (`fiche_*.png`) | `≈ 569 831 €` | `≈ 390 000 – 750 000 €` |
| (b) | Bloc Réhabilitation / Dossier (`rehab_APRES.png`) | *(libellé simple)* | fourchette + mention en note |
| (d) | Prix de sortie neuf — repli île (`labels_*.png`) | `± 12 %` (non mesuré) | `écart médian mesuré ~27 % (backtest DVF)` |
| (e) | Commune nommée par le Copilote (`labels_*.png`) | `Saint-Denis` (parcels.commune erroné) | `L'Étang-Salé` (INSEE officiel) |
| (c) | Charge foncière d'Assemblage (`labels_*.png`) | `450 k€` nu | `(estimée)` + note (bilan à rebours) |

HTML source rendu dans `avant/` et `apres/`.

## Arrondi de la fourchette (b)

Bornes arrondies à un pas lisible (bas vers le bas, haut vers le haut → la fourchette **encadre** la
valeur, l'arrondi ne resserre jamais) : 569 831 ± 30 % = 398 882 – 740 780 → **390 000 – 750 000 €**.
Point unique `estimation_prix.py` / `lib/fourchette.ts`.

## ± 30 % : d'où vient la marge (b, d)

Demi-largeur ±30 % = au moins l'écart médian réellement **mesuré** au backtest (27,4 %). Le backtest
porte sur l'estimateur sobre, qui **majore** l'erreur du produit → fourchette prudente. L'ancien « ± 12 % »
du prix de sortie neuf n'était fondé sur **aucune mesure** : remplacé partout (fiche, score_e, bilan,
rendu read-time) par l'écart médian mesuré ~27 %, en le disant (point d).

## Copilote (a, e)

- (a) Le seul prix *estimé* émis par le Copilote (mission « vérification » : médiane de zone × surface)
  est en fourchette ±30 % et dit « projection arithmétique, PAS une valeur vénale » + l'écart mesuré.
  Les autres sorties sont des faits sourcés (DVF) ou des saisies utilisateur — inchangées.
- (e) La commune affichée par le Copilote (vérification, résumé de parcelle, héros) est désormais dérivée
  de l'**INSEE officiel de l'IDU** (`communes.nom_officiel`), jamais d'un `parcels.commune` texte
  possiblement périmé. Corrige à la racine le « L'Étang-Salé affiché Saint-Denis » — **et** le marché
  comparé (la vérification choisissait sinon le marché de la mauvaise commune).

## Charge foncière d'Assemblage (c) — marquée « estimée », pas de fausse fourchette

Choix : **marquée « estimée »** (pas de ±30 %). La charge = CA − construction : la soustraction
**amplifie** l'incertitude du prix de sortie, un ±30 % la **sous-dirait** (non conservateur). On le dit
plutôt que de fabriquer une précision.

## Hors scope (assumé)

€/m² de marché observés (médianes DVF, avec effectif), ventes DVF réelles (faits). La calculette de charge
foncière en fiche dépend d'hypothèses saisies par l'utilisateur (scénario, déjà étiqueté).
