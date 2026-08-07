# M52-P0 — Maquette fiche v2 : choix argumentés (STOP validation Vic)

Maquette statique : **`qa/m52/maquettes/M52_maquette.html`** (ouvre dans un navigateur). 3 parcelles
RÉELLES du run servi `q_v8_calibre` : brûlante riche `97418000AT2379` (Sainte-Marie, ×22,1, rang 7),
déclassée mode B `97416000EY1406` (Saint-Pierre, ×13,2, bâti révélé), écartée simple `97416000IL0307`
(Saint-Pierre, ×1,3, rang 44 245). **0 tier, 0 calcul** — présentation de chiffres existants.

## LOT 1 — Lisibilité du scoring
**1.1 Échelle verbale.** Bandes proposées (en config, pas en dur) : ×10+ « très forte probabilité
relative » · ×4–10 « forte » · ×2–4 « nettement au-dessus de la moyenne » · ×1–2 « proche de la
moyenne » · <×1 « en dessous ». Le chiffre RESTE, le mot l'accompagne. *(Fichier proposé :
`config/echelle_verbale_score.yaml`.)*
**1.2 ⓘ explicatif.** Texte sobre (famille M36) : mesure la probabilité RELATIVE de VENTE à court
terme vs moyenne île, modèle backtesté DVF ; n'est ni garantie, ni prix, ni certitude ; la
performance varie par commune. → renvoie au Lot 4.
**1.3 Fréquence mesurée par tier.** Source = `qa/audit-rr/c1_monotonie.csv`, mesure **`strate_fold`**
(backtest OUT-OF-SAMPLE, walk-forward) : brûlante-band **~20/100** [IC 9,4–19,2×], chaude **~9/100**
[4,8–7,1×], à-creuser **~3/100** [1,9–2,2×], base île **~1,5/100**. ⚠ **Décision à valider** : la
mesure `tiers_servis` (les brûlantes SERVIES) donne une brûlante à RR 1,12 **IC[0,28;4,42] qui inclut 1
→ NON fiable** (seulement 2 mutés/118, censure forward). Donc **pour la brûlante, on affiche la bande
backtest (fiable), pas le taux des servies (non fiable)** — conforme à ta règle « si un tier n'a pas
d'IC fiable, la phrase n'apparaît pas ». **OK pour toi ?**
**1.4 Réglette.** Barre « moyenne → très forte » + curseur (percentile réel : brûlante 100, écartée
89,7). **PAS de note /100, PAS d'étoiles** (doctrine : le score d'Opportunité est mort pour ça).
**1.5 Pourquoi ce score.** Dépliable, top5 traduites — les `phrase` existent déjà (`libelles_client`) :
« permis de construire récent (moins de 2 ans) · rotation du foncier nu élevée · parcelle peu boisée ·
mutation et permis récents combinés · terrain nu constructible » (vraies, parcelle brûlante). Ouvert
par défaut sur brûlante/déclassée, replié sur écartée. Contribution sans phrase → affichage technique.
**1.6 Vocabulaire.** « muter » → « être vendue » partout — point unique `frontend/src/lib/strings.ts`
(+ Fiche.tsx:1278, ScoringV2, FiltreLabuse « Ça va muter ? »). DVF mesure la VENTE.

## LOT 2 — Hiérarchie
**Ordre (logique de décision promoteur)** : ① verdict+score → ② droit du sol (zonage M40, procédure
M41) → ③ économie (capacité, mode B M44) → ④ contexte (voisinage M42, historique) → ⑤ propriété
(société M43, signaux vendeur) → ⑥ risques/vigilances → ⑦ outils (annuaire M51) → ⑧ **Les données**.
*Argument : on répond dans l'ordre des questions du promoteur — « ça vaut le coup ? » (score), « j'ai
le droit ? » (sol), « ça rapporte ? » (éco), « c'est où et à qui ? » (contexte/proprio), « quel
risque ? », puis les outils.*
**Dépliables** : ouverts à l'arrivée = verdict+score, droit du sol, économie (l'essentiel sans scroll) ;
repliés = contexte, propriété, risques, outils, données (un clic). L'écartée simple n'ouvre que
verdict.
**2.3 Théâtre** : compteur « 431 663 parcelles analysées » 0→N en ~700 ms au chargement, puis fige.
Sobre, une ligne.

## LOT 3 — « Les données » (fin de fiche)
Réutilise `data_sources` (nom, millésime, ce qu'elle apporte) + l'ICD. Sources utilisées sur CETTE
fiche ; les **absentes DITES** (« année de construction : non disponible en open data → ABSENTE »).
Lien vers la qualité commune (Lot 4). **Zéro nouvelle donnée.**

## LOT 4 — Qualité par commune, DITE
Mesure réelle (`qa/audit-rr/b_commune_rr.md` + couverture) : ex. **Saint-Pierre RR 9,3 (n 42 045,
propre)** ; **Sainte-Marie RR 6,7 ⚠ <5 positifs** ; **Salazie RR 6,1 ⚠ <5 positifs (marché peu actif,
base 0,87 %)** ; **Cilaos RR 0,0 ⚠ (pas de signal mesurable)**. Encart par fiche commune + rappel
discret en fiche parcelle quand dégradée : « Sainte-Marie : marché peu actif — le classement reste
fiable, la fréquence exacte est indicative (échantillon limité) ». Honnête, jamais d'excuse vague.
*(À compléter en P1 : couverture DVF n ventes, BAN %, calibration calibrée/RNU/hors-PLU par commune.)*

## LOT 5 — Vues sauvegardées (reste M45)
Barre de filtres : nom + combinaison de filtres, stockage **côté compte**, listées (appliquer /
renommer / supprimer). Rien de partagé entre comptes.

## Questions ouvertes pour ta validation (sur pièce)
1. **Lot 1.3** : afficher la bande **backtest** pour la brûlante (fiable) plutôt que le taux des
   servies (IC inclut 1) — **valides-tu** ce choix de source ?
2. **Échelle verbale** : les 5 bandes + libellés ci-dessus te vont, ou tu ajustes les mots/seuils ?
3. **Ordre des blocs** (Lot 2) : l'ordre proposé te convient, ou tu déplaces ?
4. **États dépliés** par défaut : verdict+sol+éco ouverts, reste replié — OK ?
5. **Réglette** : barre+curseur (percentile) ou tu préfères une autre forme (sans note/étoiles) ?

**STOP — aucun code front avant ton feu vert. Je corrige la maquette sur tes retours.**
