# ECARTS-3 — AUDIT-CHIRURGICAL-3 (écrans, outils, mails)

> Chasse aux bugs et incohérences, **LECTURE SEULE**. Aucune correction, aucune prod, aucun run, aucune écriture base.
> Branche `audit/chirurgical-ecrans`. API live `:7460`, front `:10260` (env=local, auth désactivée).
> Échantillon : 6 parcelles — 97422000AD0887 (Le Tampon, constructible Ud), 97416000HT0538 (Saint-Pierre, constructible, 0 place stationnement), 97404000AM0838 (L'Étang-Salé, **non constructible** « habitat interdit », **grande** 20 336 m², PPR rouge), 97417000AO0050 (Saint-Philippe, **RNU**), 97422000AL1201 (Le Tampon, **grande** 50 022 m² agricole), 97411000ES0054 (Saint-Denis, **copropriété** 860 lots).
> Méthode : écrans + outils au navigateur piloté (1440×694 et 1920×1080) par l'auteur ; profondeur endpoint/données des 16 outils + 11 documents + 21 mails déléguée à 5 sous-agents en lecture seule (curl + lecture de code + rendu/pdftotext). Preuves : captures `~/Desktop/chasse-1/_ecrans/` (54), documents `~/Desktop/chasse-1/_documents/`, mails rendus `~/Desktop/chasse-1/_mails/` (63), rapports outils `~/Desktop/chasse-1/_outils_*/`.

Classement : **faux** (valeur fausse) · **contradictoire** (deux sources, deux valeurs) · **trompeur** (exact mais induit en erreur) · **cosmétique** · **latence** (> 5 s).

---

## Résultat d'ensemble

**Santé technique forte.** Sur toute la session navigateur (12 écrans + 16 outils + Copilote + Docs + Bilan, aux deux tailles) : **0 erreur console, 0 warning** (55 messages, tous bénins). Aucun chargement sans fin, aucun bouton mort (hors E114), aucun texte superposé. Les faits servis en direct (surface, zone, SDP, risques, prix, score) concordent entre **recherche, liste, carte, fiche, Comparatif, Bilan, Permis, Sources** — les conformités de chirurgical-1 tiennent et s'étendent aux écrans/outils jamais ouverts.

**Un thème transversal domine les écarts de fond.** La règle interne « la **famille U** d'une zone est constructible » est juste pour le zonage, mais quand une parcelle est non constructible pour une **autre** raison (habitat interdit en UE, PPR rouge), plusieurs surfaces racontent la mauvaise histoire ou l'ignorent : **E101** (fiche), **E104** (Calculette modèle `non_constructible_pct=0`), **E105** (Estimer RNU), et la ligne latente I1 du Comparatif. La parcelle AM0838 (20 336 m², surtout vide, mais habitat interdit + 43 % PPR rouge) est le révélateur.

**Un document se distingue en mal.** **E102** : l'Étude de faisabilité (M22) est le **seul** des documents à ne pas refuser une parcelle inconstructible — elle titre « au mieux ~95 logements en R+4 » sur AM0838 (en 108 s), là où le Dossier, le Gabarit et le Pré-dossier refusent. Prolonge le constat « deux moteurs 614 vs 888 » des mémoires antérieures.

**Le mandat email_change est tranché : CONFIRMÉ — aucun déclencheur (E109).**

---

## ÉCARTS NOUVEAUX (comptés)

### E100 — COSMÉTIQUE/TROMPEUR — Copropriété : code RNIC brut affiché au client
- **Parcelle** : 97411000ES0054 (copropriété « LES TOURTEREAUX », 860 lots).
- **Fait** : le tiroir Identité affiche « …`DE_2001_A_2010` · syndic professionnel · CITYA SAINT DENIS… » — la **période de construction** est l'énumération brute de la base RNIC, non formatée (attendu : « 2001–2010 »).
- **Où le lire** : fiche ES0054 → Identité (capture `E_ES0054_identite_DE_2001_A_2010_1440.png`). **Aussi dans le PDF premium.**
- **Cause** : `frontend/src/components/fiche/CoproprietesBlock.tsx:20` (`bouts.push(c.periode_construction)` brut) ET `src/labuse/api/pdf_premium.py:945` (`f" · {c['periode_construction']}"`). Aucun formatage de l'enum.

### E101 — TROMPEUR + LOT B — La fiche jette la vraie cause de non-constructibilité
- **Parcelle** : 97404000AM0838 (et toute parcelle non retenue de bande ≠ NC).
- **Deux récits** : l'API calcule `analyse_labuse.cause_libelle = « Non retenue — habitat interdit en zone UE. »` La **liste** (`ResultsSection.tsx:446`) l'affiche. La **fiche** (carte Analyse LABUSE) ne l'affiche PAS : pour une bande ≠ NC elle ne montre que la contribution « **aucune SDP résiduelle exploitable** » — ce qui est **faux** ici (20 336 m² surtout vides, emprise 1 252 ; il y a de la place, c'est l'habitat qui est interdit).
- **Où le lire** : fiche AM0838 → Analyse LABUSE (capture `E_AM0838_fiche_analyse_cause_1440.png`) vs liste Étang-Salé.
- **Cause** : `frontend/src/components/fiche/AnalyseLabuseCard.tsx:64-80` — `cause`/`cause_libelle` n'est rendu que si `bande === 'NC'` ; sinon seules les `contributions` s'affichent. Le `cause_libelle` fourni par l'API est perdu sur la fiche.

### E102 — TROMPEUR + LATENCE — L'Étude de faisabilité ne refuse pas une parcelle inconstructible
- **Parcelle** : 97404000AM0838 (habitat interdit UE + PPR rouge 43 %, capacité servie nulle).
- **Fait** : `POST /modules/etude/pdf` sur AM0838 → **108,4 s**, PDF 11 pages titrant « **au mieux ~95 logements en R+4** », jauge « esquisse d'implantation atteint 8 125 m² ». Le Dossier (« non retenue, capacité nulle »), le Gabarit (refus) et le Pré-dossier (422) refusent tous ; l'Étude est le **seul** à mettre en avant le gros chiffre. Les garde-fous existent en page 1 (« plancher 8 125 m² dépasse la capacité servie 0 m²… pas exploitable », « PPR zone rouge ») mais le **titre et la jauge annoncent 95 logements d'abord**.
- **Où le lire** : `~/Desktop/chasse-1/_documents/` (PDF Étude AM0838).
- **Cause** : moteur Étude M22 (prolonge « deux moteurs 614 vs 888 »). Latence : `etude_grille_garde_fou_s=100` (`config.py:97`) sur une assiette lourde → ~108 s pour aboutir à ce qui aurait dû être un refus rapide.

### E103 — FAUX — Calculette foncière / Bilan : champ TVA non borné
- **Parcelle** : toutes (ex. 97422000AD0887).
- **Fait** : `POST /bilan/{idu}/calcul` avec `tva: 20` (lu comme 20 %, pas 0,20) → HTTP 200, `ca_ttc` correct mais **`ca_ht = 136 714 €`** et TVA ≈ 95 % (au lieu de `ca_ht = 2 392 500`). Le champ attend une **fraction** (0,20) et n'est ni borné ni validé ; un `20` passe en 200 et produit un bilan absurde.
- **Reproduire** : `curl -s -X POST http://127.0.0.1:7460/bilan/97422000AD0887/calcul -H 'Content-Type: application/json' -d '{"programme":{"terrain":1703},"produits":[{"lots":10,"suv":600,"prix_ttc_m2_suv":4785,"tva":20}]}'`
- **Cause** : `src/labuse/bilan/moteur.py:54-58` — `ca_ht = ttc / (1 + self.tva)`, `tva` non borné (contraste avec la taxe d'aménagement explicitement bornée en 422). **Impact réel dépend de ce que le front transmet (fraction vs %) — à vérifier côté front.**

### E104 — TROMPEUR — Calculette (modèle) présente AM0838 comme 100 % constructible
- **Parcelle** : 97404000AM0838.
- **Fait** : `GET /bilan/97404000AM0838/modele` sert `sourcee.non_constructible_pct = 0` et `zonage_parts = [{UE, U, 100 %}]`, alors que la fiche classe la parcelle **entièrement non constructible** (habitat interdit) avec **43 % de PPR zone rouge inconstructible**. Le préremplissage Bilan la présente 100 % constructible.
- **Reproduire** : `curl -s http://127.0.0.1:7460/bilan/97404000AM0838/modele`
- **Cause** : `non_constructible_pct` ne reflète que la part A/N du zonage (UE = famille U → 0), ignore PPR rouge et l'interdiction d'habitat. **Même famille que E101.**

### E105 — TROMPEUR — Estimer : « zone non constructible (Pas) » sur une commune RNU
- **Parcelle** : 97417000AO0050 (Saint-Philippe, commune sans PLU).
- **Fait** : `POST /radar/annonce/estimation3/97417000AO0050` → `note_terrain` = « Pas d'estimation : zone non constructible **(Pas)** ». Le libellé de zone d'une commune RNU commence par « Pas de PLU local » ; le premier mot « Pas » est pris et imprimé entre parenthèses comme un **code de zonage**.
- **Reproduire** : `curl -s -X POST http://127.0.0.1:7460/radar/annonce/estimation3/97417000AO0050`
- **Cause** : `src/labuse/pige/estimer3.py:382-384` (`_zone_code` : « Pas » ≤ 5 lettres passe la regex de code PLU), déclencheur `estimer3.py:777`. Touche le JSON et tout PDF Estimer sur une parcelle de commune RNU.

### E106 — TROMPEUR — Scan patrimoine : faux signal « succession/sommeil » sur une ASL
- **Fait** : scan sur l'ASL « LES TOURTEREAUX » (`siren=U23889204`, identifiant **non-entreprise**) → `inpi_sans_dirigeant: true` → le front affiche « succession ou société en sommeil probable ». Une ASL n'a par nature aucun dirigeant INPI et ne « tombe pas en sommeil ».
- **Cause** : `src/labuse/api/modules.py:365-366` — la garde ne vérifie pas que `siren` est numérique à 9 chiffres avant d'en déduire l'absence de dirigeant.

### E107 — CONTRADICTOIRE — Gabarit vs Fiche/Dossier sur une même parcelle constructible
- **Parcelle** : 97422000AD0887.
- **Fait** : l'outil **Gabarit** affiche « Calcul incomplet — donnée réglementaire manquante » (limites non qualifiées) ; la **fiche** à côté affiche « Ud · constructible · 719 m² SDP · Potentiel R+1 » ; le **Dossier** donne l'enveloppe Ud (11 m/7 m, emprise 30 %). Le client voit « constructible, emprise 30 % » dans un document et « non calculable » dans l'autre, côte à côte.
- **Où le lire** : capture `T11_gabarit_AD0887_1440.png` (outil + fiche visibles) ; `~/Desktop/chasse-1/_documents/D3_gabarit_AD0887.*`.
- **Cause** : `src/labuse/api/gabarit.py:115-129` (`build.blocking` sur arête non qualifiée → `status:"incomplete"`, `emprise_pct:null`). Refus géométrique défendable en soi, mais l'incohérence inter-vues reste. Cosmétique associé : message à **deux-points doublés** « …ne porte pas d'enveloppe constructible : Gabarit non calculable… : donnée réglementaire manquante » (`exports/builder.py:467`).

### E108 — CONTRADICTOIRE (à confirmer) — Compte de parcelles d'un même bloc : 198 vs 118
- **Fait** : le bloc CBO TERRITORIA (Saint-Paul) s'affiche « **198 parcelles · 278,21 ha** » dans Scan patrimoine (blocs contigus) et « **118 parcelles · 2 782 076 m²** » (= 278,2 ha, **surface identique**) dans Blocs fonciers.
- **Où le lire** : captures `T04_patrimoine_CBO_1440.png` et `T14_blocs_1440.png`.
- **Cause probable** : définitions divergentes (assiettes vs parcelles, inclusion des slivers/voies à aire ≈ 0 expliquerait l'aire identique avec 80 parcelles de plus). **À trancher** — déroutant pour le client qui lit deux comptes pour le même bloc.

### E109 — TROMPEUR (code mort) — Mail « changement d'e-mail » : aucun déclencheur. **CONFIRMÉ.**
- **Fait** : recherche exhaustive (`email_change`, `ANCIEN_EMAIL`, `NOUVEL_EMAIL`, `UPDATE utilisateurs SET email`, routes compte, front) : **zéro appel** d'envoi, **aucune route ne mute l'e-mail de connexion**, **aucune UI** de changement d'adresse. Le builder `_email_change` et le template Brevo 18 existent (envoyables en théorie via l'endpoint admin générique avec params fournis à la main) mais **ne sont câblés à aucun événement** — qui n'existe pas dans le produit. À vide, le corps rend « passée de  à . » (trou, non bloquant au rendu, bloqué par la garde file si envoyé).
- **Cause** : `mails_contenu.py:289` (builder), `brevo.py:92` (template) sans producteur d'événement.

### E110 — TROMPEUR — Les gabarits Brevo (tpl 4-20) sont morts mais toujours « vérifiables »
- **Fait** : depuis MAILS-1, **tout** le contenu des 21 mails est rendu dans le dépôt (`mails_contenu.py` + `gabarit_mail.py`) ; Brevo n'est plus qu'un transport. Pourtant `verifier_templates` (`brevo.py:170`) et l'aperçu `apercu_template` (`brevo.py:246`) lisent toujours le HTML **chez Brevo**, qui n'a plus aucun effet sur le mail réellement envoyé. Un admin « vérifie » un gabarit sans effet.
- **Gravité** : fausse assurance (moyenne).

### E111 — À TRANCHER (tarifaire) — Courrier : coût unitaire > prix client
- **Fait** : `cout_lettre_eur = 2,69` (`config.py:245`) > `prix_client_eur = 2,50` (`config.py:249`) = **perte 0,19 €/courrier**. La `marge = 1,5` existe mais n'est pas appliquée (prix client en dur). Vérifié en live (`/courrier/admin/config` sert 2,69 ; `/courrier/statut` et l'écran Courrier servent 2,50). **Décision tarifaire, pas un bug** — reconfirmé depuis l'audit antérieur.

### E112 — COSMÉTIQUE — Comparatif : cause brute + chips contraintes en double
- **Parcelle** : 97404000AM0838.
- **Fait** : (a) « Plancher possible · bâti conservé : 0 m² · **habitat interdit:UE** » — code `habitat_interdit:UE` à peine formaté (deux-points + code zone). (b) « Contraintes relevées » répète les mêmes libellés : « Aléa mouvement de terrain » ×3, « Aléa inondation » ×2, « Prescription PLU » ×2, « PPR inondation et mouvement de t… » ×2 (probablement une entrée par niveau/source, lue comme doublon).
- **Où le lire** : captures `T06_comparer_AM_AD_1440.png`, `T06b_comparer_scroll_1440.png`.
- **Note** : le champ JSON `zone_constructible=true` d'AM0838 (I1 du sous-agent) **ne** se manifeste **pas** par une ligne « Zone constructible : oui » visible — l'UI affiche « 0 m² · habitat interdit:UE », correct. I1 reste un écart de **données latent**, pas d'écran.

### E113 — COSMÉTIQUE — CRM : note longue non tronquée, carte/colonne étirée
- **Fait** : une note de carte très longue (note test « [GB-TEST] AAAA… » sur 97404000BA0005) n'est ni tronquée ni repliée → la carte s'étire sur toute la hauteur et déforme la colonne « Repérée ». Aucune garde `max-height`/clamp sur l'affichage des notes ; tout client collant un long texte reproduit le défaut.
- **Où le lire** : capture `A16_crm_1440.png`.

### E114 — COSMÉTIQUE/UI — Export projet : CSV orphelin, PDF retiré, aucun bouton d'écran
- **Fait** : sur l'écran Projet (3 colonnes À trier/Retenues/Écartées + « → CRM » + « Courrier ») **aucun bouton d'export**. `projetCsvUrl` (`frontend/src/lib/api.ts:2938`, `/projets/{id}/export.csv`) n'a **aucun appelant** ; l'export PDF `/projets/{id}/export.pdf` est **retiré (410)**. L'endpoint CSV **répond** (200, `~/Desktop/chasse-1/_documents/D10_projet243.csv`) mais n'est lançable depuis aucun écran. Les D10/D11 de l'INVENTAIRE ne sont plus des « documents lançables depuis l'écran ».
- **Où le lire** : capture `A15_projet_detail_1440.png`.

### E115 — COSMÉTIQUE — Radar : porte « Leboncoin », annonces vers bienici.com
- **Fait** : la porte marché du Radar annonce « Les biens en vente sur **Leboncoin** » mais les annonces affichées lient vers **bienici.com** (la pige agrège plusieurs portails). Source unique nommée inexacte.
- **Où le lire** : capture `A12_radar_marche_1440.png`.

### E116 — COSMÉTIQUE (à trancher) — Signature des mails ≠ doctrine affichée
- **Fait** : `gabarit_mail.py:43-46` signe « Victor Lagane, **Gestionnaire relation entreprise** », alors que les docstrings du même fichier et de `mails_contenu.py:12` promettent « Victor Lagane, **fondateur de LABUSE** ». Visible dans tout mail personnel rendu (`~/Desktop/chasse-1/_mails/essai.txt`, etc.). À trancher par Vic (titre volontaire ou oubli).

### E117 — COSMÉTIQUE — Taxe (prefill) : `deja_batie=false` sur une parcelle bâtie
- **Fait** : `GET /outils/taxe-amenagement/prefill?idu=97404000AM0838` → `deja_batie=false`, `sdp_gabarit_m2=null` alors que l'oracle donne 1 252 m² de bâti. Cause : `src/labuse/api/app.py:3677` lit `parcel_residuel` non peuplé pour une parcelle inconstructible → null → false. Impact limité (parcelle non constructible, pas d'usage taxe réel).

### E118 — LATENCE (> 5 s) — Générations de documents et premier lecteur à froid
- **Mesuré (curl, un seul lecteur)** : Dossier `/dossier/{idu}.pdf` jusqu'à **16 s** ; Pré-dossier `/pre-dossier/{idu}.zip` **24–33 s** ; Estimer `/analyse-annonce/{idu}.pdf` **12,5 s** ; Étude M22 **108 s** (voir E102) ; `GET /communes/{nom}/contexte` **42,8 s à froid** (reconstruction de cache après invalidation de fraîcheur — `app.py:2693` ; 2ᵉ appel 0,015 s) ; `POST /outils/etude-zone` **5,6 s à froid**. Au navigateur, les chargements d'écran/outil sont restés < 3 s ; la latence est concentrée sur la **génération de documents** et le **premier lecteur après recalcul de nuit**.

### E119 — FAIBLE — `radar_digest` (tpl 12) : aucun déclencheur live (legacy)
- **Fait** : `mails_contenu.py:315` / `brevo.py:72` définissent `radar_digest`, mais le job digest réel envoie `smtp_digest_notifications` (`events.py:1480`). `radar_digest` n'est atteignable que par l'alias admin — confirme le « RETIRÉ legacy » des mémoires. À vide : « Le point Radar **du aujourd'hui** » (grammaire).

---

## CONFIRMÉS (connus de chirurgical-1, reproduits — non recomptés)

- **E1 (surface autocomplétion vs fiche)** : l'autocomplétion de recherche ET tous les sélecteurs de documents (modale Dossier/Bilan, Comparer) affichent le **dessin** (AD0887 1 699 m², AM0838 20 798 m²) ; la fiche, les documents, l'en-tête du Comparatif et le champ Terrain du Bilan affichent le **cadastre** (1 703 / 20 336). Reproduit sur 4 surfaces. Captures `A02`, `T06`.
- **E2 (Apporteur refus en HTTP 200)** : `GET /apporteur/{idu}.pdf` → **200** + PDF 1 174 o « Document non genere / Renseignez le nom de votre société » (compte pilote sans société), pour AD0887 et AM0838. Reconfirmé par le sous-agent documents.
- **Canari HT0538 (0 place de stationnement)** : honnête — Dossier et Étude affichent « stationnement non vérifié / non déduit », pas de faux « 0 place exigée ».

---

## À CONFIRMER / NON COMPTÉS (traçabilité, pas de faux positif)

- **Compte des risques non réconcilié entre écrans** : pour AM0838, Pièges affiche « 1 contrainte relevée », la tuile RISQUES de la fiche « 2 », le Comparatif ~19 chips. Granularités différentes (contrainte bloquante / aléas / intersections) — déroutant mais chacune légitime. À uniformiser ou expliciter.
- **A3 (Solaire)** : `toit_m2=425` (p_model_bati) vs « emprise 345 » de la fiche — probablement deux grandeurs distinctes (toiture vs emprise au sol BD TOPO) ; si confondues, le dimensionnement kWc serait sur-estimé ~23 %. À lever.
- **E108** (bloc 198 vs 118) : voir ci-dessus, dépend de la définition du bloc.
- **Copilote** : interrogé « surface **et** zone de AD0887 », répond la zone (Ud, cohérente fiche) mais **omet la surface** — comportement LLM non déterministe, non compté.
- **Mon compte** : en session locale (dev) « aucun compte connecté » — la gestion complète du compte (changement d'e-mail/mot de passe, facturation) n'est pas testable sans session réelle ; cohérent avec E109 (pas d'UI de changement d'e-mail).
