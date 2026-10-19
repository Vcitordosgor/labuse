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
- **5.1 Badge « Sources modifiées depuis »** ✅ **FAIT côté front** (détail dans la section « Lot 5.1 » ci-dessous) — comparaison localStorage éditeur↔génération, badge existant réutilisé, garde vitest. (Initialement signalé comme décision UX de Vic ; implémenté à sa demande.)

## Notes

- **Moteur d'implantation NON optimisé** (hors mandat) : E-04 pose seulement une borne de temps + un message honnête ; le moteur tourne dans un thread à session propre, abandonné à 30 s (le thread finit en arrière-plan, résultat ignoré).
- **Gardes E-05/E-09 affinées** : les heuristiques initiales du banc testaient une comparaison brute dominante↔faisabilité ; elles testent désormais le VRAI invariant post-correction (à-cheval → zone nommée avec sa part ; constructibilité cohérente Dossier↔Comparer).
- Le Gabarit document reste en 422 honnête (« non établissable ») sur 5/10 parcelles — inchangé, c'est le refus légitime quand le calcul est incomplet.

---

## Vérifications pré-merge (4 points demandés)

**#1 — Affinage des gardes E-05/E-09.** Seule **g09** a été modifiée (g05 inchangé — `git diff audit..fix` ne la touche pas). **L'ancienne g09 NE PASSE PAS sur le code corrigé** (prouvé empiriquement) : valeurs servies `dom=N`, `z_fai="Ud sur 46 %"`, `z_cmp=N` → ancienne condition `z_fai≠dom ET z_cmp==dom` ⇒ **ECART (faux positif)**. Elle était **fausse** : elle exigeait que la faisabilité nomme la zone DOMINANTE (ou que Comparer ne la nomme pas), ce qui contredit à la fois le design anti-liseré (DOCS-FIX-1 : Comparer sert la dominante) ET le mandat (« la portion constructible fait foi, nommée avec sa part »). La nouvelle g09 teste le VRAI invariant : sur une parcelle à cheval, `capacite.zone` doit porter sa part (« Ud sur 46 % »).

**#2 — Caveat AU dans l'Étude de faisabilité.** NON, il manquait (`service.py` : ni `au_ouverture` ni `au_differe`). **Ajouté** : `modules.py:_attach_au_ouverture` attache `au_ouverture` au payload de `POST /modules/etude` ET `/etude/pdf` (même source que la fiche §4, `parcel_au_statut`) ; le PDF l'imprime en tête (`etude_faisabilite.py`). Preuve : HK0130 → payload `au_ouverture.statut="constructible sous condition d'une opération d'aménagement d'ensemble"` ; PDF « Zone à urbaniser (AU) — … ». **Garde E-19** ajoutée au banc.

**#3 — Part de zone à cheval : une seule source.** ÉCART CONFIRMÉ : la part divergeait entre le Dossier (zonage : Ud 45,6 %) et le Gabarit (recalcul géométrique sur dessin : 43 % ; 2318 m² ≠ 45,6 %×5391=2458). **Corrigé** : `api/gabarit.py` tire `pctPortionZone` + `surfaceNote` de la SOURCE UNIQUE `faisabilite.zone_servie.zone_dominante` (la même que fiche/Comparer/Copilote), plus de recalcul sur dessin. L'Étude, elle, travaille sur la contenance et clippe en interne (pas de « % » concurrent). **Garde E-18** ajoutée (Dossier % = Gabarit % = m² de surfaceNote). Après correction, AV0110 : Dossier 57,5 % = Gabarit 58 % = 397 m².

**#4 — Message client sur Étude > 30 s.** ÉCART FRONT CONFIRMÉ : sur un 503, le client lisait **« L'étude a échoué — réessayez »** (générique + bouton réessayer). Double cause : `api.ts` ne gardait `detail` que s'il était une CHAÎNE (le 503 est un objet `{message}` → message perdu) ; `M22Programme.tsx` ne traitait le message exact que pour les 400. **Corrigé** : `api.ts` extrait `.message` d'un detail objet ; `M22` traite 400 ET 503 comme terminaux (message exact, SANS réessayer). **Capture** `docs/audit-2026-10/chasse-docs-fix/captures/E04-etude-message-503.png` : l'écran Docs/Étude (EV0324) affiche « Étude trop lourde pour cette parcelle, non générée… » sous « Générer les scénarios », sans bouton réessayer.

## Lot 5.1 — badge « Sources modifiées depuis » réagit aux saisies (front)

Implémenté **entièrement côté client** (aucun composant nouveau, DA existante) : `lib/empreinteDoc.ts` fige l'empreinte des hypothèses à la **génération** (`noterGeneration`) et suit l'**éditeur** (`noterEditeur`). Câblé dans `BilanEcran.tsx` (hypothèses au recalcul + à la génération), `M22Programme.tsx` (config de l'Étude au run + à la génération PDF), et `DocumentsView.tsx` (le badge EXISTANT « Sources modifiées depuis » s'allume si `editeurModifie(doc_type, idu)`). **Garde** = `src/lib/empreinteDoc.test.ts` (vitest, 6 cas : génération→à jour, édition→modifié, ré-édition d'origine→à jour, régénération→à jour, pas de faux positif sans génération suivie) — **la garde adaptée à une logique localStorage est un vitest, le banc HTTP ne pouvant pas l'observer**. `tsc -b` propre ; vitest 11/11 (empreinteDoc 6 + Étude 5). Capture avant/après du badge non produite : « Mes documents » exige une session authentifiée + des documents persistés, indisponibles dans le harnais local (POST /bilan/generer → 401 « Session requise »). Repro manuel : générer un Bilan, changer une hypothèse sans régénérer, ouvrir « Mes documents » → badge ambre « Sources modifiées depuis ».

## Banc final

**`scripts/coherence/chasse_docs.py` : 19 gardes → 19 OK · 0 ECART · 0 SKIP** (E-18 #3 + E-19 #2 inclus). Front : `tsc -b` 0 erreur, vitest 11/11.
