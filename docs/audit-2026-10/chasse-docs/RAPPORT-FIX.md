# CHASSE-DOCS-FIX-1 — fermeture des 17 écarts de CHASSE-DOCS-1

**Modèle** Opus · pas de merge · DA existante, aucun nouveau composant.
**Branche** `fix/chasse-docs-1` depuis `audit/chasse-docs-1` · **worktree** `~/Desktop/labuse-chasse-docs-fix` · **ports** 8831/6031.
**Run servi** q_v19 / cascade q_v19_sources / run_seq 16. **Base** Mac `postgresql:///labuse`.

## Résultat

**`scripts/coherence/chasse_docs.py` : 17 OK · 0 ECART · 0 SKIP** (avant correction : 17 ECART).
Preuve avant/après : pdftotext des documents touchés, 10 parcelles, dans `docs/audit-2026-10/chasse-docs-fix/<idu>/` (après) vs `docs/audit-2026-10/chasse-docs/<idu>/` (avant, branche audit).

| Écart | Correction | Fichier | avant → après (preuve) |
|---|---|---|---|
| **E-01** mixité | phrase d'absence de `mixite_clause` reformulée + verdict « déclenchement selon le programme » quand la clause est valide sans programme | `robinet_fiche.py:_c_mixite` + `reste_a_declarer.yaml:120` | « seuils de la zone non renseignés » : présent → **absent** (BO0852) |
| **E-02** dict §Sols | le rendeur fait une PHRASE (jamais `str(dict)`) | `miroir.py:_r_sols` + `_phrase_site_sol` | `{'nom':…,'sur_place':False,…}` → **« Ancien site industriel (CASIAS) Sucrerie Casernes… »** (DY0106) |
| **E-03** courrier PM | PM connue adressée à SON NOM (jamais « À l'occupant ») | `courrier_adressage.py:88` | « À l'occupant » → **« COMMUNE DE SAINT BENOIT »** |
| **E-04** Étude timeout | borne DURE 30 s → **HTTP 503 honnête** (« Étude trop lourde… »), jamais un HTTP 000 | `modules.py:_etudier_borne` (`/etude` + `/etude/pdf`) | timeout silencieux → **503 + message** (EV0324) |
| **E-05** à-cheval non constructible | sur parcelle à cheval constructible, le §10 renvoie à l'Étude (plus « zone non constructible ») | `miroir.py:rendu_sections` (`_acheval_const`) | « zone non constructible » : présent → **absent** (DY0106) |
| **E-06** §10 saturée/surélévation | SDP résiduelle nulle = « saturée » (jamais « Marge SDP non calculée ») ; pas de surélévation positive sous saturation | `app.py:_potentiel` (pct None + sdp≤0 ; `sur={}` si niveau nul) | « Marge SDP non calculée » : présent → **absent** (BO0852) |
| **E-07** gabarit sur exigu | plafond d'emprise + hauteur masqués quand zone d'implantation = 0 | `api/gabarit.py` | plafond 114,7 → **None** (AV0110) |
| **E-08** caveat AU | `au_ouverture` propagé dans Comparer (comme le Dossier §4) | `app.py:/compare` | caveat absent → **porté** (EV0324) |
| **E-09** libellé zone à-cheval | zone constructible nommée AVEC sa part | `modules.py:/faisabilite` | « Ud » → **« Ud sur 46 % »** (DY0106) |
| **E-10** emplois sans nombre | la fourchette d'abord (`libelle` en suffixe, comme le Flash) | `blocs/etude_zone.py:51` | « postes salariés déclarés… » → **« 6 608 à 13 988 postes salariés… »** |
| **E-11** « (0 m) » | distance 0 = « distance non géocodée » | `miroir.py:_r_equipements` | « (0 m) » : présent → **absent** |
| **E-12** gabarit « 40.0 » | format FR par unité (`fmt_pct`) | `blocs/gabarit.py:_regles` | « Emprise maximale : 40.0 » → **« 40 % »** (AD0554) |
| **E-13** dates ISO permis | année de dépôt (« en 2024 »), FR sinon ; jamais ISO ni jour fabriqué | `miroir.py:_date_permis` | « déposé 2024-01-01 » → **« déposé en 2024 »** (EV0324) |
| **E-14** double point | la note servie débarrassée de sa ponctuation finale avant concat | `blocs/etude_zone.py:178` | « chiffre d'affaires.. » : présent → **absent** |
| **E-15** IDU collé | IDU en fin de phrase, suivi de « — » (plus de collage en justification) | `blocs/apporteur.py:417` | « AV0110et » : présent → **absent** |
| **E-16** voisines tronquées | au-delà de 4 → « (voir Assemblage) », jamais « … » coupant la donnée | `blocs/apporteur.py:_a_cote` | « (AN 0350 … …) » → **« (voir Assemblage) »** |
| **E-17** source gabarit dupliquée | le millésime n'est plus recollé dans `provider` (déjà dans `versionDate`) | `gabarit/builder.py:446` | « BD TOPO BD TOPO® » : 2 → **0** (AD0554) |

## Lot 5 — décisions produit de Vic

- **5.2 charge foncière négative** ✅ — chiffre gardé + libellé « — Bilan déficitaire : à ces hypothèses, le foncier ne se paie pas » (`blocs/comparatif.py`). Preuve : BW0102 « -59 €/m² — Bilan déficitaire… ».
- **5.3 Taxe `sdp_gabarit_m2`** ✅ — libellé servi « SDP résiduelle (droits à bâtir restants, bâti conservé) », distincte de la SDP de l'Étude (`app.py:/outils/taxe-amenagement/prefill` → `sdp_gabarit_libelle`). Preuve : BZ1065.
- **5.4 Gabarit à-cheval** ✅ — surface = contenance cadastrale + note « dont ~X m² en zone constructible (parcelle à cheval) » (`contract.py:surfaceNote` + `api/gabarit.py`). Preuve : AV0110 « Contenance cadastrale 690 m² — dont ~380 m²… ».
- **5.1 Badge « Sources modifiées depuis »** ⚠️ **NON FAIT — relève d'une décision UX de Vic (front), pas d'un correctif serveur.** La fraîcheur serveur (`documents_bibliotheque.py:lister`) compare l'instantané des millésimes de SOURCES ; les hypothèses du Bilan et le scénario de l'Étude sont des SAISIES du client (stockées avec le document via `enregistrer`/`_archiver_etude`), sans référence serveur à laquelle les comparer. Faire « réagir » le badge aux hypothèses suppose de comparer, CÔTÉ FRONT, les saisies de l'éditeur vivant à celles figées dans le document sauvegardé — un comportement d'UI à trancher avec la DA, pas une garde serveur. Aucune garde n'a donc été ajoutée (elle resterait structurellement SKIP en local, sans compte authentifié). À arbitrer.

## Notes

- **Moteur d'implantation NON optimisé** (hors mandat) : E-04 pose seulement une borne de temps + un message honnête ; le moteur tourne dans un thread à session propre, abandonné à 30 s (le thread finit en arrière-plan, résultat ignoré).
- **Gardes E-05/E-09 affinées** : les heuristiques initiales du banc testaient une comparaison brute dominante↔faisabilité ; elles testent désormais le VRAI invariant post-correction (à-cheval → zone nommée avec sa part ; constructibilité cohérente Dossier↔Comparer).
- Le Gabarit document reste en 422 honnête (« non établissable ») sur 5/10 parcelles — inchangé, c'est le refus légitime quand le calcul est incomplet.
