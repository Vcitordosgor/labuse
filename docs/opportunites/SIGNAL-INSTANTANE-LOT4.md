# Signal mesurable — instantané mensuel + protocole forward (lot 4)

Opérationnalise le **protocole forward** de VERITE-TERRAIN-2 volet E
(`docs/audit-2026-10/verite-terrain-2/SIGNAL-BACKTEST.md`). Le Signal servi
(`score_labuse.signal_p` = P(vente dans 12 mois)) **sépare** (lift ×2,29 au décile haut), mais
l'instantané réellement livré n'est **pas jugeable** tant que DVF n'a pas avancé au-delà de sa date de
calcul. La seule façon honnête de le juger un jour : **figer aujourd'hui** la prédiction datée, puis la
**rejouer** contre les ventes DVF postérieures.

## Le job mensuel — `signal-instantane`

Déclaré au registre (`labuse jobs`), **mensuel le 1er à 06:00 (Réunion)**, touche *exploitation*.
Chaque mois il **fige** une copie datée du Signal servi dans **sa seule table** `signal_instantanes`
(`snapshot_le`, `run_label`, `parcel_id`, `idu`, `signal_p`, `signal_niveau`, `bande`, `score_computed_at`).

- **N'écrit QUE `signal_instantanes`** (garde vérifiée par test). **N'envoie aucun mail.**
- **Idempotent** : clé `(snapshot_le, parcel_id)` + `ON CONFLICT DO NOTHING` → relancé le même jour, il
  ne duplique rien et ne modifie rien.
- Run figé = le run servi vivant (`config/served_run.txt`, override `LABUSE_SCORE_RUN`), tracé dans la ligne.

Lancement manuel : `labuse jobs run signal-instantane` · ou `PYTHONPATH=src python -m labuse.signal_instantane figer [--date YYYY-MM-DD] [--run q_vXX]`.

## Le juge forward — `rejouer` (lecture seule)

Quand DVF a publié des mutations postérieures à un instantané T₀ (retard usuel 6-12 mois) :

    PYTHONPATH=src python -m labuse.signal_instantane rejouer --date <T0> [--horizon-mois 12]

Pour l'instantané figé à T₀, mesure le **taux de vente DVF observé APRÈS T₀** par **niveau** (fort/moyen/
faible) et par **bande**, avec **lift vs base** et **IC de Wilson 95 %** — exactement la grille du volet E.
**N'écrit rien** (garde vérifiée par test). On compare alors la séparation forward au rejeu 2025 du
volet E : tient-elle hors échantillon, sur le millésime réellement servi au client ?

## Ce que le lot ne fait pas

Ne modifie ni le modèle, ni le Signal servi, ni le scoring. Ne touche aucune table existante. C'est une
**mesure**, pas une règle — cohérent avec le STOP du lot 2 (les règles attendent la décision de Vic).
