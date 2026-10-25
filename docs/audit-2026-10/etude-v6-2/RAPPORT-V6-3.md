# ÉTUDE V6-3 — recette Vic (rapport court)

Branche `feat/etude-v6`, non mergée. DA existante. Captures `captures/v6-3-*`.

## Écrans
1. **Étape 1** — Continuer déjà sur la barre du bas commune (PiedEtape partagé, vérifié). **Règles PLU
   une fois par zone** pour l'assiette (« PLU de L'Étang-Salé · zone UA · 4 parcelles » + les règles),
   EN PLUS d'une fois par parcelle (`ReglesAssiette`).
2. **Préfixe normalisé** « PLU de [commune] · zone [X] · art. [n°] · millésime » partout : étape 1 (chips),
   étape 2 (stationnement), contrôles (citation reformatée). Chaque règle vient de `regles.charger(insee)`
   = commune de l'assiette. Backend : `regles.commune/millesime`, `regles_plu` porte commune/zone/millésime.
3. **Récap** — « Stationnement PLU » affiche la RÈGLE en clair (`regle_courte`, ex. « 1 pl. T1–T2 · 1,5 pl.
   T3–T4 ») au lieu de « règle vérifiée ».
4. **Survol vert** sur boutons (déjà), puces/chips et cartes (`hover:border-mint`). **Animation de
   chargement** (composant `Chargement`) en overlay pendant « Calcul en cours » et dans le bouton PDF.
5. **Jauge** — vert < 90 % · **orange 90–100 %** (« à la limite, le calcul tranchera ») · rouge au-delà.
6. **Résultat** — onglets Optimisation/Alternative RETIRÉS (un seul scénario « votre programme »), bloc
   « Une alternative concrète » et bouton « Bilan de ce scénario » retirés ; « Recalculer » sur une ligne.

## Cohérence du résultat
7. **Un seul facteur limitant**, calculé une fois : bandeau du haut, « Ce qui limite » n°1 et le message
   rouge disent la MÊME chose. En sous-sol, si c'est la pente → « hauteur sur la pente (relief X m) ».
8. **Bloc fusionné** « Votre programme : N demandés · M tiennent · le terrain accueille au maximum K » +
   UNE seule réserve (remplace Capacité maximale + Ce que le terrain accueille + L'écart).
9. **2 grands chiffres** : Logements tenus/demandés + Surface du programme tenue ; Sol restant / Emprise
   mobilisable / SDP autorisée déplacés dans « Détail des surfaces ».
10. **Sous-sol** : cartouche « stationnement en sous-sol », **plan de principe du niveau −1** (places +
    rampe), rampe dans le détail des surfaces. **Plus aucun nom technique (« votre_programme »)** à l'écran
    ni dans le PDF (planche + pages neutralisées en « retenu »).
11. **« répartition votre répartition »** corrigé → « répartition de votre demande ».

## PDF
12. Le PDF se génère **TOUJOURS**, même quand la demande ne tient pas : `scenario_retenu` retombe sur la
    variante « votre programme » best-effort, le **dépassement est écrit** dans le document. Échec de Vic
    reproduit et corrigé : Étang-Salé, résidence étudiante, **42 T1 aérien → PDF 200 (107 Ko)**.

## Recette finale (Étang-Salé)
- **42 T1 aérien** : ne tient pas (40 au mieux), bandeau=message=limite n°1 « stationnement aérien » ;
  PDF généré. **42 T1 sous-sol** : 42 tiennent / max 45, plan −1 affiché. **23 T2 + 6 T3** : aérien 32,
  sous-sol — limite « hauteur sur la pente (relief 4,5 m) » (bandeau = message = n°1). Aucune phrase
  contradictoire, aucun chiffre en double avec deux valeurs (vérifié).

## Vérifié
tsc 0 · vitest 298/298 · pytest implantation (164+ passed, 2 `test_route_*` pré-existants) ·
chasse_docs 20·0·0 · chasse_donnees 23·0·2 SKIP.
