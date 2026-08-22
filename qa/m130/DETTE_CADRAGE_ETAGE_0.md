# DETTE — Le cadrage Projet retient l'étage 0 (parcelles non exploitables)

**Statut : dette consignée (M130-4 §F.1). Mandat APP, pas PDF. Non traité ici.**

## Constat

Le cadrage d'un projet (`_run_cadrage` → `_q_v2_list`) retient des parcelles de
l'**étage 0** — non constructibles / faux positifs — ainsi que des zones A/N
entières et des micro-parcelles :

- **P3** (Saint-Pierre) sert des parcelles de **5, 6, 10 m²** et des zones **A**
  entières (le cadrage test force `tiers:[ecartee]`, mais le fond du problème est
  que ces parcelles restent *cadrables*).
- **P1** (toute l'île) : le compteur « **~ 285 781 retenues** » est **exact mais
  gonflé** — il inclut une large part de parcelles non exploitables (mesuré
  ailleurs : ~79 % d'étage 0 sur l'univers carte). Le vivier *figeable*
  (`_vivier_figeable`, hors étage 0) est le dénominateur honnête, mais le
  cadrage lui-même ne filtre pas ces parcelles en amont.

## Effet

Le PDF projet (M130-4) **neutralise l'effet à l'affichage** : famille A/N → « SDP
aucune (zone fermée à l'urbanisation) », multi-zone dite, ligne d'état de liste
inconditionnelle. Mais la **source** (le cadrage retient l'étage 0) n'est pas
corrigée : la shortlist figée peut contenir des parcelles non exploitables, et
les compteurs « retenues » restent gonflés.

## À traiter (mandat app)

- Décider si le cadrage Projet doit **exclure l'étage 0 par défaut** (comme la
  carte l'exclut déjà du vivier figeable), et si les micro-parcelles
  (< `MIN_DISPLAY_SURFACE_M2`) doivent être écartées du figeage.
- Aligner le **dénominateur** servi (vivier figeable) et la **population figée**
  (`_run_cadrage`) pour qu'un cadrage à `tiers` explicite ne produise pas un
  `total` incohérent (cf. P3 : liste 60, vivier 0).

Référence : `src/labuse/api/projets.py` (`_run_cadrage`, `_vivier_figeable`,
`_figer_shortlist`), `src/labuse/api/app.py` (`_q_v2_list`, `_ETAGE0_SQL`).
