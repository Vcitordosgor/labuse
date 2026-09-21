# DONNEES-5 — historique_permis_liste : aligner le Dossier sur la source de l'écran

Branche `feat/donnees-5` depuis main **3d432ddc** (après merge de feat/donnees-4). Un commit.

## Le bug (signalé en DONNEES-4 par l'oracle)
L'extracteur du Dossier `_c_permis_parcelle` lisait `f.depots.parcelle` ; la fiche React
(`HistoriqueSiteBlock`) — et le producteur DÉCLARÉ de la donnée (`app.py:_historique_site`) —
lisent `f.historique_site.permis` (permis rattachés à l'IDU, `sitadel_permits.idu_codes ? idu`).
Deux chemins → deux listes : sur une parcelle à permis, le Dossier montrait « 0 permis » quand
l'écran en listait 4.

## Le correctif (un commit)
- `robinet_fiche.py` : `_c_permis_parcelle` lit désormais `f.historique_site.permis` — la MÊME
  source que l'écran (et que le producteur déclaré de la donnée).
- `miroir.py:_r_permis_liste` : rend désormais la **liste datée** des permis (type · déposé ·
  autorisé), 6 max comme la fiche + le reste compté — au lieu d'un simple total. Le Dossier montre
  ainsi les MÊMES permis que l'écran, pas juste leur nombre.
- L'oracle (`oracle_dossier.ORACLE`) porte déjà `historique_permis_liste → historique_site.permis`
  (ajouté en DONNEES-4) : il confronte le Dossier à la source de l'écran.

## Preuve — même liste écran et PDF
Les 4 témoins (AN0347, BO0765, BO0852, AB0346) n'ont **aucun permis sur la parcelle** : écran et
PDF vides tous les deux → `historique_permis_liste : ABSENTE DITE`, **0 écart** partout.

Sur une parcelle à permis, **97401000AM0112** (4 PC) — `DONNEES-5-preuve.txt` :
- **Écran** (`historique_site.permis`) : PC déposé 2018-10-15 (autorisé 2017-08-25) · PC 2017-12-28 ·
  PC 2016-01-01 · PC 2015-01-01.
- **PDF** (pdftotext) : « Sur cette parcelle (permis) — 4 permis sur la parcelle (Sitadel) — PC —
  déposé 2018-10-15, autorisé 2017-08-25 ; PC — déposé 2017-12-28… » → **la même liste**.
- Recette : `historique_permis_liste : IDENTIQUE`, **0 écart**.

L'oracle indépendant confirme le bug et sa correction sur AM0112 :
```
AVANT (f.depots.parcelle)        : historique_permis_liste MUET (oracle a 4 permis, extracteur None)
APRÈS (f.historique_site.permis) : 0 muet
```

## Portes de recette
- **tsc -b** vert (aucune modif front).
- **circuit verrous -w G8** vert (V5d compris).
