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
- **5.1 Badge « Sources modifiées depuis »** ✅ **FAIT, empreinte CÔTÉ SERVEUR** (détail section « Lot 5.1 » ci-dessous). Les documents ET leurs hypothèses sont stockés serveur (`documents_generes.hypotheses`) : l'empreinte est donc stockée AVEC le document côté serveur (cross-poste), comparée à l'éditeur vivant (local par nature). Badge existant réutilisé, garde vitest.

## Notes

- **Moteur d'implantation NON optimisé** (hors mandat) : E-04 pose seulement une borne de temps + un message honnête ; le moteur tourne dans un thread à session propre, abandonné à 30 s (le thread finit en arrière-plan, résultat ignoré).
- **Gardes E-05/E-09 affinées** : les heuristiques initiales du banc testaient une comparaison brute dominante↔faisabilité ; elles testent désormais le VRAI invariant post-correction (à-cheval → zone nommée avec sa part ; constructibilité cohérente Dossier↔Comparer).
- Le Gabarit document reste en 422 honnête (« non établissable ») sur 5/10 parcelles — inchangé, c'est le refus légitime quand le calcul est incomplet.

---

## Vérifications pré-merge (4 points demandés)

**#1 — Affinage des gardes E-05/E-09.** Seule **g09** a été modifiée (g05 inchangé — `git diff audit..fix` ne la touche pas). **L'ancienne g09 NE PASSE PAS sur le code corrigé** (prouvé empiriquement) : valeurs servies `dom=N`, `z_fai="Ud sur 46 %"`, `z_cmp=N` → ancienne condition `z_fai≠dom ET z_cmp==dom` ⇒ **ECART (faux positif)**. Elle était **fausse** : elle exigeait que la faisabilité nomme la zone DOMINANTE (ou que Comparer ne la nomme pas), ce qui contredit à la fois le design anti-liseré (DOCS-FIX-1 : Comparer sert la dominante) ET le mandat (« la portion constructible fait foi, nommée avec sa part »). La nouvelle g09 teste le VRAI invariant : sur une parcelle à cheval, `capacite.zone` doit porter sa part (« Ud sur 46 % »).

**#2 — Caveat AU dans l'Étude de faisabilité.** NON, il manquait (`service.py` : ni `au_ouverture` ni `au_differe`). **Ajouté** : `modules.py:_attach_au_ouverture` attache `au_ouverture` au payload de `POST /modules/etude` ET `/etude/pdf` (même source que la fiche §4, `parcel_au_statut`) ; le PDF l'imprime en tête (`etude_faisabilite.py`). Preuve : HK0130 → payload `au_ouverture.statut="constructible sous condition d'une opération d'aménagement d'ensemble"` ; PDF « Zone à urbaniser (AU) — … ». **Garde E-19** ajoutée au banc.

**#3 — Part de zone à cheval : une seule source.** ÉCART CONFIRMÉ (le Gabarit recalculait la part sur le *dessin* `ST_Area`, divergent du zonage). **Avant/après sur la même parcelle (DOSSIER INCHANGÉ — il lisait déjà `zone_dominante`) :**

| Parcelle | Source | AVANT | APRÈS |
|---|---|---|---|
| AV0110 (690 m², Uh/N) | Dossier (`zone_dominante`, part Uh=0,5745) | 57,45 % · 396 m² | inchangé |
| | Gabarit | 55 % · 380 m² (dessin) | **57 % · 396 m²** (`zone_dominante`) |
| | Étude | contenance 690 → clip PPR/reculs → implantation 0 m² | inchangé |
| DY0106 (5391 m², N/Ud) | Dossier (`zone_dominante`, part Ud=0,456) | 45,6 % · 2458 m² | inchangé |
| | Gabarit | 43 % · 2318 m² (dessin) | **46 % · 2458 m²** (`zone_dominante`) |
| | Étude | contenance 5391 → clip PPR rouge 4701 → implantation 342 m² | inchangé |

**Le vrai = le Dossier** (zonage `zone_dominante`, la source partagée par fiche/Comparer/Copilote ; cf. `app.py:6181`). **Corrigé** dans `api/gabarit.py` : `pctPortionZone` + `surfaceNote` tirés de `zone_servie.zone_dominante`, plus de recalcul dessin → Gabarit = Dossier (à l'arrondi). **Garde E-18** (Dossier % ≈ Gabarit % et m² de surfaceNote). **À signaler à Vic (hors scope)** : l'Étude ne clippe pas à la zone constructible — elle part de la contenance et clippe par PPR/reculs (pas par le split Uh/Ud) ; sa base (contenance) concorde, mais pour une parcelle où la portion N n'est pas en PPR, l'assiette de l'Étude pourrait l'inclure.

**#4 — Message client sur Étude > 30 s.** ÉCART FRONT CONFIRMÉ : sur un 503, le client lisait **« L'étude a échoué — réessayez »** (générique + bouton réessayer). Double cause : `api.ts` ne gardait `detail` que s'il était une CHAÎNE (le 503 est un objet `{message}` → message perdu) ; `M22Programme.tsx` ne traitait le message exact que pour les 400. **Corrigé** : `api.ts` extrait `.message` d'un detail objet ; `M22` traite 400 ET 503 comme terminaux (message exact, SANS réessayer). **Capture** `docs/audit-2026-10/chasse-docs-fix/captures/E04-etude-message-503.png` : l'écran Docs/Étude (EV0324) affiche « Étude trop lourde pour cette parcelle, non générée… » sous « Générer les scénarios », sans bouton réessayer.

## Lot 5.1 — badge « Sources modifiées depuis » réagit aux saisies (front)

**Question #2 posée : les documents + hypothèses sont-ils enregistrés côté serveur ? OUI** — `POST /bilan/{idu}/generer` insère dans `documents_generes` avec `hypotheses = json.dumps(CalculIn)` ; l'Étude archive sa recette via `_archiver_etude` ; `lister` renvoie `r.hypotheses`. **Donc l'empreinte est stockée AVEC le document côté serveur** (plus en localStorage pour la référence), pour que le badge marche d'un autre poste / pour un collègue.

Mécanique : le front calcule l'empreinte des hypothèses à la génération (`empreinte()`, djb2 sur JSON canonique) et l'ENVOIE au serveur — `genererBilan(idu, entrees, empreinte)` et `etudePdfInit({…, empreinte})`. Le serveur la range sous `hypotheses._empreinte` (`bilan.py:generer_bilan` ; `modules.py:_archiver_etude`, clé uniforme), `lister` la renvoie. Le badge compare cette **empreinte serveur** (`r.hypotheses._empreinte`) à l'empreinte de l'ÉDITEUR VIVANT (localStorage, publiée par l'éditeur via `noterEditeur` — locale par nature : une édition en cours n'existe que là où on édite). `DocumentsView.tsx` : `editeurDiffere(doc_type, idu, r.hypotheses._empreinte)`. Câblé dans `BilanEcran.tsx` et `M22Programme.tsx`. Pas d'empreinte serveur (vieux doc) ou pas d'éditeur ouvert ici → pas de faux positif.

**Garde** = `src/lib/empreinteDoc.test.ts` (vitest, 7 cas, dont « autre poste : empreinte serveur présente mais pas d'éditeur local → pas de badge » et « vieux doc sans empreinte → pas de badge ») — une logique front se teste en vitest, pas dans le banc HTTP. `tsc -b` propre ; vitest 12/12 (empreinteDoc 7 + Étude 5). `_empreinte` est ignoré au reparse `CalculIn` (« Ouvrir » un bilan reste intact). Capture du badge non produite : « Mes documents » exige une session authentifiée + docs persistés (POST /bilan/generer → 401 en local). Repro manuel : générer un Bilan, changer une hypothèse sans régénérer, ouvrir « Mes documents » → badge ambre.

## Banc final

**`scripts/coherence/chasse_docs.py` : 19 gardes → 19 OK · 0 ECART · 0 SKIP** (E-18 #3 + E-19 #2 inclus). Front : `tsc -b` 0 erreur, vitest 11/11.

---

## Correctifs UX pré-merge (Bilan / Étude / « Mes documents »)

**Compte local de test** créé sans toucher aux autres : `badge-test@labuse.test` / `TestBadge2026!` (titulaire · plan integral · actif · marqué test, masqué des chiffres client). Login → page `/login`, « identifiant » = l'email. Flux vérifié end-to-end (login 303, génération Bilan, « Mes documents », et `hypotheses._empreinte` renvoyée = empreinte serveur du Lot 5.1).

- **B — texte saisi en gris sur les cases blanches (Bilan + Étude).** Cause : les inputs portaient `bg-surface` (classe INERTE — aucun token `surface` sans suffixe) → fond **blanc** par défaut du navigateur + texte hérité `--txt` (#B8C4BC, clair) → gris sur blanc, comme le placeholder. Le Bilan est « façon Excel » (cases blanches). **Corrigé** : chaque input reçoit `text-[color:var(--ink)]` (encre `--ink` #071009, token DA existant) + `placeholder:text-txt-mut` (gris #6B776F). Texte saisi foncé/lisible, placeholder gris distinct. 10 inputs (BilanEcran ×5, M22Programme ×5). Preuve : `captures-ux/B-avant-apres-comparaison.png` (T3 « 30 » gris = avant · T2 « 12 » encre = après) + mesure live (texte `rgb(7,16,9)`, placeholder `rgb(107,119,111)`).
- **C1 — survol de ligne vert vif (« Mes documents »).** Cause : `hover:bg-mint hover:text-mint-on` peignait la ligne en vert vif → « Ouvrir » (bouton vert) invisible, badge illisible. **Corrigé** : `hover:bg-surface-3` (fond légèrement éclairci, token DA) ; boutons et badge gardent leurs couleurs. Preuve : `captures-ux/C-avant-survol.png` → `C1-apres-survol.png`.
- **C2 — badge « Sources modifiées depuis » chevauchant « Ouvrir ».** Cause : la ligne « modifiée » a 3 boutons (Ouvrir+Régénérer+Supprimer ≈ 240px) dans une colonne actions de 210px (inner 190px) → débordement de 47px À GAUCHE (justify-end) sur le badge (+14px mesurés à 1280px). **Corrigé** : colonne actions 210→270px (colgroup) + `flex-wrap` sur les actions (filet mobile/étroit : les boutons passent à la ligne au lieu de déborder). Chevauchement 1280px : +14px → **-46px (gap)**. Preuve : `captures-ux/C-avant-badge.png` → `C2-apres-badge.png`.

DA existante, aucun nouveau composant, aucun autre écran. `tsc -b` 0 erreur · vitest 12/12 · banc HTTP 19 OK.
