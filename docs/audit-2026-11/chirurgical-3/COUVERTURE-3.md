# COUVERTURE-3 — AUDIT-CHIRURGICAL-3

> Ce qui a été réellement parcouru : écran/outil × parcelle × taille. LECTURE SEULE.
> **Deux niveaux de preuve** : (1) **navigateur piloté** (auteur) pour l'UI — erreurs console, boutons morts, états vides, texte coupé, chiffre écran≠API ; (2) **endpoint/données** (5 sous-agents en lecture seule, curl + lecture de code + rendu) pour la profondeur par parcelle des 16 outils, 11 documents et 21 mails.
> Règle de budget appliquée (comme demandé) : **tous les écrans et tous les outils sont parcourus** ; là où le temps manquait, c'est le **nombre de parcelles par outil au navigateur** (1–2) et la **seconde taille** qui ont été réduits — jamais la liste. La profondeur multi-parcelles (2–6) est assurée en headless par les sous-agents.
> Captures : `~/Desktop/chasse-1/_ecrans/` (54 PNG). Santé console : **0 erreur / 0 warning** sur toute la session (55 messages).

## Étape 0 — environnement
- `pwd` = `/Users/openclaw/Desktop/labuse-chasse-ecrans`, branche `audit/chirurgical-ecrans`, base `labuse` lisible (434 582 parcelles).
- API `python -m uvicorn labuse.api.app:app --port 7460` (venv `~/Desktop/labuse/.venv`, PYTHONPATH=src worktree, LABUSE_ENV=local → auth OFF).
- Front `LABUSE_API_DEV=http://127.0.0.1:7460 npm run dev -- --port 10260` (worktree sans node_modules → `npm ci` d'abord ; base path `/socle/`).

## Échantillon (6)
| idu | commune | profil |
|---|---|---|
| 97422000AD0887 | Le Tampon | constructible Ud (référence) |
| 97416000HT0538 | Saint-Pierre | constructible, 0 place stationnement (canari) |
| 97404000AM0838 | L'Étang-Salé | **non constructible** (habitat interdit) + **grande** 20 336 m² + PPR rouge |
| 97417000AO0050 | Saint-Philippe | **RNU** |
| 97422000AL1201 | Le Tampon | **grande** 50 022 m² agricole |
| 97411000ES0054 | Saint-Denis | **copropriété** 860 lots |

## LOT A — Écrans (navigateur)
| Écran | 1440×694 | 1920×1080 | Parcelle(s) | Note |
|---|---|---|---|---|
| Carte (couches, fonds, mesures) | ✓ | ✓ | — | A01 ; tuiles + commune focus |
| Recherche + autocomplétion | ✓ | ✓ | AD0887 | A02 ; E1 (1 699 dessin) |
| Fiche + tiroirs (Analyse, Risques, Identité…) | ✓ | ✓ | AD0887 | A03/A05 ; Analyse+Risques |
| Fiche — copropriété | ✓ | — | ES0054 | A06 ; Identité (E100) |
| Fiche — non constructible/grande | ✓ | — | AM0838 | Analyse (E101) |
| Fiche — RNU | ✓ | — | AO0050 | A07 ; bandeau RNU correct |
| Fiche — grande agricole | ✓ | — | AL1201 | A08 |
| Liste (filtres → Analyser avec LABUSE) | ✓ | — | Étang-Salé (8 659) | A10 ; répartition cohérente |
| Filtres (4 groupes) | ✓ | — | — | A23 contexte |
| Fiche commune | ✓ | — | Étang-Salé | A09 |
| Radar — hub | ✓ | — | — | A11 (2 portes) |
| Radar — marché (annonces) | ✓ | — | — | A12 (E115) |
| Veille (parcelles suivies) | ✓ | — | — | A13 |
| Projets (liste) | ✓ | ✓ | — | A14 |
| Projet — détail (kanban) | ✓ | — | projet « JC » | A15 (E114) |
| CRM (pipeline kanban) | ✓ | ✓ | — | A16 (E113) |
| Copilote (+ requête réelle) | ✓ | — | AD0887 | A17/A18 ; zone Ud OK |
| Docs (catalogue + lancement) | ✓ | ✓ | AD0887 | A19/A20/A21 |
| Bilan (calculette, exports) | ✓ | — | AD0887 | A22 ; exports PDF/Excel présents |
| Mon compte | ✓ | — | — | A24 ; session dev |
| Sources (99 sources) | ✓ | ✓ | — | A25 ; 434 582 = base |

## LOT A — Outils (navigateur ; profondeur endpoint par sous-agent)
| Outil | Nav 1440 | Nav 1920 | Parcelle(s) nav | Profondeur endpoint (sous-agent, ≥2 parcelles) |
|---|---|---|---|---|
| PLU | ✓ (T01) | — | liste communes | Instruire : search/communes/pack/verif-procedure |
| Permis | ✓ (T02) | — | AD0887 | Marché : permis/fiche/promesses |
| Communes | ✓ (T03) | — | — | Marché : contexte/velocite |
| Scan patrimoine | ✓ (T04) | — | CBO TERRITORIA | Agir : search/patrimoine + CSV |
| Assemblage | ✓ (T05) | — | saisie | Instruire : etude/parcelles |
| Comparer | ✓ (T06/T06b) | — | AM0838+AD0887 (résultat) | Instruire : /compare (6 parcelles) |
| Pièges et risques | ✓ (T07) | — | AM0838 | Instruire : bloc risques /parcels |
| Étude de zone | ✓ (T08) | — | saisie | Marché : /outils/etude-zone + PDF |
| Estimer un bien | ✓ (T09) | — | saisie | Marché : estimation3 + PDF (E105) |
| Remonter le temps | ✓ (T10) | — | AD0887 | Documents : tuiles ortho (pas d'endpoint /ortho/{idu}/liste) |
| Gabarit réglementaire | ✓ (T11) | — | AD0887 | Instruire+Documents : /outils/gabarit + PDF (E107) |
| Taxe d'aménagement | ✓ (T12) | — | AD0887 | Instruire : prefill + calcul (E103/E117) |
| Prospection solaire | ✓ (T13) | — | entrées | Agir : solaire/piscines (A3) |
| Blocs fonciers | ✓ (T14) | ✓ | — | Agir : /modules/blocs (E108) |
| Successions à venir | ✓ (T15) | — | — | Agir : /modules/successions |
| Courrier propriétaire | ✓ (T16) | — | AM0838 | Agir : adressage/composer (E111) |
| Calculette foncière (caché) | ✓ (via Bilan) | — | AD0887 | Instruire : /bilan/calcul,modele (E103/E104) |
| Mon secteur (caché) | — (replié fiche §Marché) | — | — | Marché : /outils/mon-secteur |

## LOT A — Documents (lancés depuis l'écran + rendus/validés)
| Doc | Lancement écran | Rendu/validation | Résultat |
|---|---|---|---|
| D1 Dossier/Flash | ✓ modale Docs (AD0887) | PDF ×6 parcelles (pdftotext) | OK, latence ≤16 s (E118) |
| D2 Apporteur | — | PDF ×2 | **refus en 200** (E2 confirmé) |
| D3 Gabarit | ✓ outil Gabarit (T11) | PDF ×4 | refus AD0887 (E107) |
| D4 Comparatif | ✓ outil Comparer (T06) | PDF ×2 | OK |
| D5 Étude de zone | ✓ outil (T08) | PDF ×2 | OK (cosmétique) |
| D6a Estimer parcelle | ✓ outil (T09) | PDF ×2 | OK, 12,5 s |
| D6b Estimer lien | — | 422 url bidon/absente | refus honnête |
| D7 Bilan PDF | ✓ calculette (A22) | boutons présents ; 401 via curl (session) | testé au navigateur |
| D8 Bilan Excel | ✓ calculette (A22) | idem | testé au navigateur |
| D9 Pré-dossier ZIP | ✓ catalogue Docs | ZIP ×2 (unzip, CERFA) | OK, 24–33 s (E118) |
| D10 Export projet CSV | ✗ **aucun bouton** (E114) | CSV via endpoint (200) | endpoint OK, UI orpheline |
| D11 Export projet PDF | ✗ retiré (410) | 410 message propre | retiré |
| Étude M22 | ✓ catalogue Docs | PDF ×3 | **E102** (95 logements sur AM0838, 108 s) |

## LOT B — Cohérence inter-écrans (vérifiée)
Concordances confirmées (écran = API/fiche) : **surface** (1 703 fiche/Dossier/Comparatif/Bilan ; dessin 1 699 seulement en autocomplétion/sélecteurs = E1), **zone** (Ud fiche = Copilote = Comparatif ; UE/A/RNU corrects), **SDP/capacité** (719 fiche = tuile = Potentiel = Dossier = Comparatif), **prix DVF** (171 €/m² AD0887, 1 036 ES0054, 88 AO0050), **risques** (PPR/aléas cohérents ; compte non réconcilié — voir ECARTS), **sources** (434 582 parcelles / 99 sources / 24 communes = base). Divergences → ECARTS-3 (E101 fiche vs liste ; E104/E105 ; E108 compte de bloc).

## LOT C — Mails (21, rendus en local sans envoi)
21 mails rendus (`~/Desktop/chasse-1/_mails/`, 63 fichiers : 21 `.txt` + 21 `.html` + 21 `__VIDE.txt`). Zéro `{{…}}`/`None` dans les 42 rendus. Déclencheurs tracés (fichier:ligne). **email_change : aucun déclencheur — CONFIRMÉ (E109).** Autres : E110 (gabarits Brevo morts), E116 (signature), E119 (radar_digest legacy). Désinscription correctement gérée (sécurité/transactionnel sans, récurrents avec `List-Unsubscribe`).

## Non couvert / limites
- **Seconde taille (1920)** échantillonnée sur les écrans à mise en page sensible (Carte, Fiche, CRM, Docs, Projets, Sources, Blocs) — aucune rupture de layout observée ; les autres écrans/outils n'ont la preuve qu'en 1440 (budget).
- **Admin** : hors périmètre client (bouton présent, non audité).
- **Bilan PDF/Excel** : boutons présents à l'écran, export réel non déclenché (nécessite programme+prix saisis ; moteur validé par E103).
- **Parcours réel du Courrier/Apporteur complets** : nécessitent un compte « société » nommé, absent en session dev (E2).
- **Latences** : mesurées en curl mono-lecteur ; sous charge réelle elles peuvent différer (E118).
