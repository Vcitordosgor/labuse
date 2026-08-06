# M38 — Phase 3 : mesure À BLANC de la « dynamique constructive » redatée sur le dépôt

**Rien de servi n'est modifié.** On reproduit exactement la feature servie (`SitadelLayer`,
config `q_v8_calibre` : rayon 400 m, fenêtre **60 mois**, **PC seuls**, saturation 15,
magnitude = `min(1, n/15)`) puis on remplace la fenêtre par **date de dépôt** (`date_depot`,
fallback autorisation si dépôt absent — 0,7 %) au lieu de la **date d'autorisation** servie.
Script rejouable : `qa/m38/mesure_p3.sql` · résultats bruts : `qa/m38/mesure_p3_resultat.txt`.

## Ce que ça change (parc entier, 431 663 parcelles)

| Grandeur | Valeur |
|---|---:|
| Parcelles touchées par ≥ 1 PC (400 m, une des deux datations) | **392 929** |
| Parcelles dont la **magnitude servie change** | **197 244 (50,2 %)** |
| — dont magnitude **en baisse** | 161 009 |
| — dont magnitude **en hausse** | 36 235 |
| Delta de magnitude moyen (signé, sur les changées) | **−0,085** |
| Delta de comptage PC moyen | **−1,37 PC** (min −27 / max +22) |
| Parcelles qui **PERDENT** le signal de zone (n>0 → 0) | **4 567** |
| Parcelles qui **GAGNENT** le signal de zone (0 → n>0) | 878 |

Communes qui bougent le plus (parcelles à magnitude changée) : Le Tampon 23 510, Saint-Denis
23 009, Saint-Paul 20 812, Saint-Joseph 16 410, Saint-Pierre 15 138… (top 15 dans le résultat).
Le mouvement touche **toutes** les communes, 34–76 % des parcelles touchées selon la commune.

## Pourquoi la redatation DÉGRADE le signal au lieu de le rafraîchir

La prémisse du mandat : « un permis autorisé arrive des mois après le dépôt, le modèle voit un
marché en retard ». On a redaté pour voir si le dépôt donne une image **plus actuelle**. La
mesure dit **non**, pour deux raisons structurelles :

1. **Censure à droite (le point décisif).** Le dataset est *autorisations-seules* : les permis
   **déposés récemment mais encore en instruction ne sont pas publiés**. Sur une fenêtre glissante
   qui finit *aujourd'hui*, redater sur le dépôt ne peut PAS ajouter l'activité récente (elle
   n'existe pas en base) — elle ne fait que **décaler les permis existants ~9 mois plus tôt**, donc
   en sortir au bord ancien de la fenêtre. Mesuré : **10 916** PC déposés dans les 60 mois contre
   **12 257** autorisés dans les 60 mois → la fenêtre dépôt est **plus pauvre**, pas plus fraîche.

2. **Bruit d'anomalie source.** **5 720 PC géolocalisés (16 %)** portent une `date_depot`
   *postérieure* à la date d'autorisation — logiquement impossible, artefact d'enregistrement
   Sitadel. Ce sont eux qui produisent l'essentiel des 36 235 « hausses » : du bruit, pas du signal.

Autrement dit : la date de dépôt corrige bien le biais de **datation historique** (utile en
CONTEXTE de fiche — livré en P2), mais **ne corrige pas** le biais que le mandat visait pour le
scoring (voir l'activité récente), parce que cette activité récente est justement **non publiée**.
Redater la feature servie la rendrait **plus basse ET censurée à droite**, sans gain d'actualité.

## Recommandation à Vic : **PAS de bascule** de la feature servie

- Redater `SitadelLayer` sur le dépôt changerait **50,2 % des parcelles**, très majoritairement
  **à la baisse**, et retirerait le signal de zone à **4 567 parcelles** — un mouvement de tier
  potentiel de grande ampleur, pour un signal **dégradé** (censure droite + 16 % d'anomalies).
- La date de dépôt a de la valeur **en contexte de fiche** (P2 : « activité de dépôt », informatif,
  étiqueté, déjà livré) — PAS en remplacement de la date d'autorisation dans le calcul servi.
- Un éventuel usage servi supposerait de toute façon un **re-fit du modèle P** (hors périmètre M38)
  et une **bascule gardée type-M32** décidée séparément par toi. La mesure ci-dessus est le dossier
  d'instruction : elle **n'incite pas** à l'ouvrir.

> Conclusion « constater avant présumer » : la mesure **infirme** l'hypothèse implicite selon
> laquelle redater sur le dépôt rendrait le signal plus actuel. Le dépôt éclaire la fiche, il
> n'améliore pas la feature servie. Recommandation : **statu quo servi**, contexte en fiche.
