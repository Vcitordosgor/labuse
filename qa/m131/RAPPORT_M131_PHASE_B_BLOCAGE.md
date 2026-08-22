# M131 — Phase B : blocage structurel avant gravure (STOP, arbitrage)

Branche `feat/m131-dette-hauteur`. **Aucune gravure écrite, `plu_rules.py` non
touché.** Un blocage de schéma empêche de tenir les DEUX contraintes du mandat à
la fois. Je le remonte plutôt que de le contourner en douce.

## Le point 1 (incohérence de page) — tranché

Imprimée **p.83 = OUVERTURE du chapitre `ZONE AUindicée`** (« Cette zone couvre
des espaces réservés à l'urbanisation future … il convient de se reporter … au
règlement des zones urbaines correspondantes »). C'est bien le chapeau du
chapitre, qui **énonce le principe de renvoi** → citation **acceptable**.
L'article de hauteur précis est `ARTICLE AUindicée 10` (imprimée **p.86**).
**Retenu** : aligner les 2AU sur le libellé des 1AU — `via renvoi (ZONE
AUindicée, p.83)` — pour un libellé unique. (Offset PDF↔imprimée = +2 sur ce
document ; imprimée 83 = PDF 85, imprimée 86 = PDF 88.)

## Le blocage (points 2)

Objectif du mandat, pour Us et chaque 2AU :
1. **servir la hauteur** (résolue en direct par `resolve_zone`) ;
2. **conserver le gel** — `constructible_neuf=False` **inchangé** ;
3. **`git diff plu_rules.py` vide**.

Ces trois-là ne sont **pas** simultanément tenables avec le schéma actuel :

- Toutes les cibles (Us, 2AUa–e) sont **gelées** : leur `constructible_neuf=False`
  vient **uniquement** de la branche `zones_au_st` de `plu_rules` (`au_statut.py`
  et le moteur lisent tous `resolve_zone().constructible_neuf` — pas de signal
  de gel indépendant, vérifié).
- Pour **servir une hauteur par zone** (2AUa=21/25 ≠ 2AUb=13/17 …), il faut une
  **entrée `zones:` propre** (le bloc `zones_au_st` ne porte qu'**un seul**
  `hauteur_max_m` pour toute la liste — impossible d'exprimer des valeurs
  différentes par indice).
- Mais `resolve_zone` **étape 1 (`zones:`) l'emporte sur l'étape 2
  (`zones_au_st`)**. Dès qu'une zone a une entrée `zones:`, la branche `zones_au_st`
  n'est **jamais atteinte** → le gel disparaît.
- Et `_to_rules` **n'écrit PAS `constructible_neuf`** depuis le YAML (vérifié
  empiriquement : une entrée `zones:` avec `constructible_neuf: false` ressort
  quand même `constructible_neuf=True`). Une entrée `zones:` graverait donc la
  hauteur **mais rendrait la zone constructible** → capacité modifiée.

**Conclusion** : graver une hauteur PAR ZONE sur une zone gelée, en conservant
`constructible_neuf=False`, **exige une modification de `plu_rules.py`** — ce que
le contrôle « `git diff plu_rules.py` vide » interdit. Blocage réel, pas un détail.

*Note :* au **rendu** du PDF projet seul, une entrée `zones:` sans gel « passerait »
(la ligne SDP vient du **cache** `parcel_residuel`, pas de `resolve_zone` en
direct → elle resterait « aucune »). Mais `constructible_neuf=True` **en direct**
modifie la capacité pour la fiche, le dossier et le **prochain recalcul batch** —
c'est exactement ce que le mandat interdit (« constructible_neuf=False
inchangé »). Je ne prends pas ce raccourci.

## Options (à ton arbitrage)

1. **Autoriser une modification MINIMALE de `plu_rules.py`** (2 lignes) : faire
   lire `constructible_neuf` par `_to_rules` (`v.get("constructible_neuf", True)`).
   Elle **ne réintroduit AUCUN défaut** (le repli 4 m de M130-12 reste supprimé) —
   elle honore une valeur YAML explicite. Puis graver Us + 2AU en entrées `zones:`
   avec `he_m/hf_m` + `hauteur_src` + `constructible_neuf: false`. Le gel est
   conservé, la hauteur servie. **`git diff plu_rules.py` ne serait PAS vide**, mais
   le correctif M130-12 reste intact. → mon **choix recommandé** ; il te faut lever
   explicitement le contrôle « diff vide » pour ce cas précis.
2. **Étendre `zones_au_st` à des hauteurs par zone** — nécessite aussi une
   modification de `plu_rules` (lecture par zone). Même verrou.
3. **Laisser Us/2AU « non renseignée »** — mais le règlement PORTE la règle
   (Us3 §5 p.134 ; AUindicée 10 p.86 → indice). Ce serait un trou alors qu'on a
   lu la donnée — contraire à l'esprit de M131.

## Ce que je n'ai PAS fait

- Aucune entrée gravée (ni Us, ni 2AU).
- `plu_rules.py` intact.
- **Phase C (renvois Uazi/Ucm) tenue avec B** (« même passe ») — je l'applique
  une fois l'option de gravure tranchée, pour une seule vérification au rendu.

Dis-moi l'option. Je n'écris rien tant que le verrou `plu_rules` n'est pas levé
(ou l'option 3 confirmée). CC ne merge pas.
