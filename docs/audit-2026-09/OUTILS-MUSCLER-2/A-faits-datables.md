# Lot A — inventaire des faits datables (lecture seule, base labuse, 07/09/2026)

**1. Ventes** — `dvf_mutations_parcelle` (2021→2025) + `dvf_mutations_histo` (2014→2020, `INTERSECT id_mutation` = 0, aucun recouvrement).
Champ `date_mutation`, maille **jour** (0 NULL, 0 forcée au 01/01). Jointure directe `id_parcelle` = IDU : 37 868 + 45 089 parcelles.
Multi-lignes : 102 551 lignes → 43 698 mutations (dédup `id_mutation`, idiome FIX-4/B3 `moteurs.py:561-571`). Rien ne se perd en jointure.
SQL : `SELECT DISTINCT id_mutation, date_mutation, max(valeur_fonciere), ... FROM dvf_mutations_parcelle WHERE id_parcelle=:idu GROUP BY 1,2`.

**2. Changements de propriétaire** — PM seules : `pm_proprietaires_millesimes` (2019→2024) ∪ `parcelle_personne_morale` (2025), lecteur
existant `proprietaire_historique.historique()` (`proprietaire_historique.py:44`). **Pas datable au jour** : un changement est DÉDUIT d'un
écart de SIREN entre deux millésimes (situation au 1ᵉʳ janvier) → **maille = millésime** (« entre le 1ᵉʳ janv. N et le 1ᵉʳ janv. N+1 »).
24 434 changements de SIREN sur 370 049 paires consécutives ; 72 709→81 161 parcelles par millésime. Particuliers : hors périmètre (jamais servis).

**3. Permis** — `sitadel_permits`, jointure `idu_codes ? :idu` (GIN, 48 761 parcelles ; 50 545 permis, 100 % avec IDU). Trois dates :
`date` = **autorisation**, maille **jour** (1 seule au 01/01 sur 50 544 ; `permits_sdes.py:135`) ; `date_depot`, maille **année à 83 %**
(41 642/50 144 au 01/01 — constat FIX-4/A3 confirmé) ; `raw->>'daact'`, maille **jour**, remplie à 41,5 % (20 963). État : codes
bruts 2/4/5/6 → libellés existants `_ETAT_LABELS` (`modules.py:561`). Chiffres : `nb_lgt`, `surf_hab` (raw, déclaratif Sit@del).

**4. Découpes cadastrales** — **datable** : `dfi_filiation` (source enregistrée « DFI — documents de filiation informatisés (DGFiP) »),
409 623 lignes, `date_validation` maille **jour** (0 NULL, 0 au 01/01), 1989-12-06→2025-12-29, `nature` réelle (document d'arpentage,
lotissement, remaniement…). Jointure `idu_fille = :idu` (création de la parcelle : 311 986 filles vivantes) ou `idu_mere = :idu`
(division : 108 mères encore vivantes — les mères meurent en se divisant). ⚠ Table aujourd'hui SANS lecteur dans `src/labuse`
(ingérée, jamais servie) — la frise est son premier service. SQL : `SELECT nature, date_validation, idu_mere, idu_fille FROM
dfi_filiation WHERE idu_fille=:idu OR idu_mere=:idu ORDER BY date_validation`.

**Verdict (3 lignes).** Les quatre familles sont servables sur la frise : ventes, permis (autorisation, DAACT) et découpes à la maille
**jour** ; changements de propriétaire PM à la maille **millésime** (écart constaté, jamais une date) ; le dépôt de permis s'affiche à
l'**année** quand la source ne donne que ça (83 %). **Aucune famille écartée** — les découpes, pressenties non datables, le sont (DFI).
