# MANDAT SOURCES-1 — Vingt-deux sources entrent par le Circuit

Branche : `feat/sources-1`, worktree `~/Desktop/labuse-audit`, depuis `main` à jour (CIRCUIT-0→5b, FICHE-1 mergés).
Compte-rendu : `docs/CIRCUIT/COMPTE-RENDU-SOURCES-1.md`, un chapitre par lot. Captures dans `docs/CIRCUIT/RECETTE-SOURCES-1/`.
Référence : `docs/CIRCUIT/SOURCES-CANDIDATES.md` et le rapport de vérification du 06/09/2026 (fiches 1 à 20 : URL testées, formats, licences, sondes, pièges), tous deux à poser dans `docs/CIRCUIT/` au premier commit. Les URL de ce rapport sont le point de départ ; toute URL qui ne répond pas est notée, jamais devinée.

Objectif : vingt-deux sources qui manquent entrent dans l'app **par la porte du Circuit** — ligne au catalogue, sonde, cadence, filtre, registre — et nourrissent d'un coup ce qui doit les lire : la fiche parcelle, la fiche commune, la carte (une couche par source géographique), les outils, les PDF, la cascade. Ce qui n'est publié qu'en partie entre en partie, avec l'état « non publié » là où ça manque : le circuit le montrera et les agents iront revoir.

## Autonomie

Mêmes règles que CIRCUIT-1 à 5 : aucune question à Vic, doutes tranchés par l'option la plus sûre et écrits dans « Décisions prises en autonomie », une source introuvable ou incomplète est notée et le mandat continue, branche jamais rouge, un commit et un push par lot, rien mergé, **aucun run basculé**. Le mandat se joue d'une traite ; une session qui reprend repart seule au premier lot non clos via « continue SOURCES-1 depuis docs/CIRCUIT/COMPTE-RENDU-SOURCES-1.md ». Le crédit API est nécessaire pour les agents du lot 8 ; s'il manque, le lot le dit et passe.

## Règles

1. **Une source entre entière ou pas du tout** : `data_sources` (id, producteur, mode de remplissage, cadence, sonde réellement appelée ou raison écrite — le seed refuse le reste) · `sources_ingestion.yaml` (la vanne) · un filtre CIRCUIT-3 avec les contrôles universels et ses contrôles propres · carte table → réservoir · données au registre avec type, portée, états · `labuse circuit verrous` vert avant le commit du lot.
2. **Géographique = fiche + couche**, même moteur, même millésime, sondés ensemble par la sonde catégorielle ; le `i` de la couche dit source, millésime, fabrication, en français, et **opposable ou non**.
3. **Une commune qui n'a pas publié n'est pas un zéro** : état « non déterminée — non publié par la commune » ou « non déterminée — inventaire partiel », couverture servie avec la donnée (n communes sur 24, ou part de l'île).
4. **La cascade reçoit des faits, pas des scores** : chaque contrainte devient un motif VIGILANCE ou RÉDHIBITOIRE, seuil écrit comme choix LABUSE dans `regles/` avec sa référence (CIRCUIT-4), effet au prochain run candidat seulement.
5. **Ce qui n'est pas opposable le dit** : SAR, ZPPA, potentiel foncier régional sont des indications — jamais présentées comme une règle, jamais rédhibitoires seules.
6. **Un ordre de priorité si le temps manque** : les lots 1 à 4 avant tout (ce sont des contraintes qui changent des verdicts), puis 5 à 7, puis 8.
7. Preuve, témoins (24 communes, 54 parcelles golden), tests, captures avant/après, rien de mergé.

## Lot 1 — Les prescriptions et périmètres du droit des sols (7 sources)

- **Emplacements réservés** et **espaces boisés classés** (GPU, prescriptions CNIG ; CC vérifie les codes réels dans les données des 24 communes) → réservoirs `gpu_prescriptions_er`, `gpu_prescriptions_ebc` ; couches « Emplacements réservés », « Espaces boisés classés » ; fiche « Dispositifs et périmètres » ; PDF Dossier et pré-dossier PC ; Pièges et risques. Cascade : ER → VIGILANCE, RÉDHIBITOIRE au-delà de 50 % de la parcelle ; EBC → VIGILANCE dès non nul, RÉDHIBITOIRE au-delà de 80 % ; la part EBC est **soustraite de l'assiette** du bloc potentiel (portée `run`).
- **Droit de préemption urbain** (GPU d'abord, SIG communaux ensuite) → `dpu_perimetres` ; couche, fiche ; cascade VIGILANCE ; communes non publiées listées pour la demande de Vic.
- **Plans d'exposition au bruit** de Roland-Garros et Pierrefonds (DGAC/DEAL) → `peb_dgac` ; couche, fiche Risques, Pièges, PDF ; cascade RÉDHIBITOIRE zones A et B, VIGILANCE C et D, référence L112-10.
- **Zonage A/B/C** (arrêté national, DHUP) → `zonage_abc_dhup` ; classe par commune ; fiche parcelle, fiche commune, Communes ; pas de couche ; pas de cascade.
- **Servitudes d'utilité publique du GPU pour le 974** : inventaire par flux Atom catégorie par catégorie (AC1, AC2, AC3, AC4, AS1, A4, A5, EL3, EL7, I3, I4, PM1, PM2, PT1, PT2, T1, T5, T7 — AC1, PM1, T5 sont confirmées publiées) → un réservoir par catégorie publiée, une couche chacune, fiche « Servitudes », PDF ; cascade : AS1 captages et T5 dégagement → RÉDHIBITOIRE selon la servitude, AC2 sites classés → VIGILANCE forte, PT1/PT2 → VIGILANCE ; les catégories absentes du 974 sont listées « non publiées » et surveillées par la sonde Atom.
- **Zones de présomption de prescription archéologique** (Atlas des patrimoines, à vérifier pour le 974) → `zppa_culture` ; couche, fiche ; VIGILANCE ; indication, pas servitude.

## Lot 2 — La nature et l'eau (5 sources)

- **Espaces naturels protégés INPN** (standard ENP, page PatriNat tant que l'INPN est perturbé) → `inpn_enp` avec un type par couche : cœur et aire d'adhésion du Parc national, réserves naturelles, arrêtés de protection de biotope, sites classés et inscrits, Conservatoire du littoral, forêts de protection, Ramsar ; cascade RÉDHIBITOIRE en cœur de parc, réserves, APB ; VIGILANCE ailleurs. Les ENS du Département sont demandés à part (liste pour Vic).
- **Ravines : domaine public fluvial et domaine privé de l'État** (DEAL, fiche Sextant, Lizmap) → `deal_dpf_dpe` ; couche « Ravines et reculs » avec la servitude de marchepied de 3,25 m et la bande de 10 m du code forestier calculées comme tampons ; fiche, PDF ; cascade RÉDHIBITOIRE dans le lit et le marchepied, VIGILANCE dans la bande de 10 m. Si la couche DEAL est inaccessible, repli sur l'hydrographie BD TOPO croisée avec le tableur DEAL, marqué « repli » dans le tampon.
- **Zones humides** (inventaires DEAL, Lizmap/WFS) → `deal_zones_humides` ; couche, fiche ; VIGILANCE forte ; couverture par secteurs dite.
- **Atlas des zones inondables et TRI** (Géorisques) → `georisques_azi_tri` ; couche, fiche Risques, là où le PPR est absent ; VIGILANCE.
- **RPG** (registre parcellaire graphique, IGN/ASP, millésime le plus récent) → `rpg_ign` ; couche « Cultures déclarées » ; fiche ; cascade : zone A cultivée en canne → RÉDHIBITOIRE, zone A absente du RPG → VIGILANCE « friche possible » ; variable candidate scoring notée pour la conversation Scoring.

## Lot 3 — Les sols et le bruit (3 sources)

- **Secteurs d'information sur les sols** (Géorisques, CSV quotidien) → `georisques_sis` ; fiche, PDF, cascade VIGILANCE forte (étude de sols obligatoire), obligation d'information de l'acheteur dite.
- **CASIAS** (anciens sites industriels, export régional) → `georisques_casias` ; fiche, couche ; VIGILANCE.
- **Classement sonore des infrastructures** (arrêtés DEAL de décembre 2023) → `deal_classement_sonore` ; ce qui existe en SIG (cartes de bruit stratégiques, WFS) entre en couche ; les secteurs affectés par catégorie de route sont reconstruits par tampons sur la voirie BD TOPO à partir des largeurs de l'arrêté, marqués « reconstitué » ; fiche Réseaux et accès ; coût d'isolation dans le bilan.

## Lot 4 — Le cadre régional (2 sources)

- **SAR** (DEAL Lizmap / Région) → `sar_region` : espaces naturels remarquables du littoral, coupures d'urbanisation, continuités écologiques, zones préférentielles d'urbanisation, espaces agricoles ; couches et fiche avec la mention « schéma régional, indication non opposable » ; cascade VIGILANCE seulement ; SAR 2050 inscrit à la sentinelle.
- **DVF et potentiel foncier de la Région** (data.regionreunion.com) → `region_dvf`, `region_potentiel_foncier` ; pas de nouvelle donnée servie : le DVF Région entre dans l'échantillon producteur du filtre DVF, le potentiel foncier devient un contrôle de comparaison avec le nôtre, rapport au compte-rendu.

## Lot 5 — La valeur (5 sources)

- **Fibre Arcep « Ma connexion internet »** (immeuble, trimestriel, `/last`) → `arcep_fibre` ; fiche « Réseaux et accès » (raccordable, opérateurs), PDF, Étude de zone.
- **Taux de taxe foncière REI** (DGFiP, annuel) → `dgfip_rei` ; fiche commune, bilan promoteur, Financier. La taxe d'aménagement n'y est pas : sa source reste celle de CIRCUIT-3.
- **ACV / PVD / ORT** (data.gouv, liste du 14/05/2025) → `anct_ort` ; fiche commune et Copilote : éligibilité Denormandie ; les cinq communes ACV sont Le Port, Saint-André, Saint-Joseph, Saint-Louis, Saint-Pierre ; périmètres infra-communaux « non publiés », demandés aux EPCI.
- **Loyers DHUP** (carte annuelle) et **loyers OLL** (ADIL/AGORAH, résultats 2024, agrégés) → `loyers_dhup`, `loyers_oll` ; `loyer_median_eur_m2` prend l'OLL comme source canonique quand elle couvre le secteur, DHUP en repli, règle CIRCUIT-4 mise à jour ; fiche commune, Financier.
- **Coût de construction** (EPTB SDES + jeu CDC) → `cout_construction_sdes` ; la constante d'`engine.py` disparaît ; bilan et Financier ; écart mesuré sur les 4 témoins d'exports.

## Lot 6 — Le foncier et les gens (2 sources)

- **Documents de filiation informatisés** (DGFiP, trimestriel) → `dgfip_dfi` ; fiche parcelle « Historique cadastral » ; **rattachement des permis orphelins par la filiation officielle** (les 2 894 sans localisation de RETOURS-14 sont rejoués, résultat au compte-rendu) ; signal « division récente » pour la conversation Scoring.
- **Recensement IRIS complet** (INSEE RP, dernier millésime) → `insee_rp_iris`, en remplacement de la seule variable égout : âge du bâti, statut d'occupation, **logements vacants**, taille des ménages, âge des habitants ; fiche commune, Étude de zone, fiche parcelle « Autour » ; variables candidates scoring notées.

## Lot 7 — Le catalogue mis d'équerre

- **BDNB** : retirée de la vitrine (`statut = retiree`, raison « ne couvre pas le 974 au millésime courant »), inscrite à la veille agent pour le prochain millésime.
- **Ce qui attend une demande** : zonages d'assainissement, inventaires ZAE, périmètres ZAC, OPAH/PIG, périmètres ORT, ENS du Département, micro-données OLL — une ligne `data_sources` chacune au statut `chantier` avec l'organisme à solliciter, et un document `docs/CIRCUIT/DEMANDE-REGION-EPCI.md` prêt à envoyer : par destinataire (Région, CINOR, TCO, CIVIS, CASUD, CIREST, Département, AGORAH), la liste de ce qu'on demande, pourquoi, sous quel format.
- **Cerema** : `fichiers_fonciers_cerema`, `lovac`, `dv3f` au statut `convention`, avec la note « LOVAC réservé aux collectivités et à leurs prestataires ».

## Lot 8 — Ce que ça déclenche

- Le filtre de chaque source joué sur sa première version ; les vingt-deux apparaissent sur le Circuit avec leur état ; un agent est envoyé sur chaque source partielle (ravines, SAR, zones humides, bruit, OLL) pour dater ce qui existe chez le producteur.
- `labuse registre fiche parcelle` et `fiche autres` régénérés ; `FICHE-PARCELLE-DONNEES.md` ne montre plus « source absente » que là où la source est réellement absente.
- Un run candidat est **produit** (`labuse pompe calculer`) pour porter les nouveaux motifs de cascade et la soustraction EBC, avec sa note de version — **jamais basculé**.
- `labuse circuit verrous --complet` vert ; `CHOIX-LABUSE.md` complété des seuils posés (ER 50 %, EBC 80 %, ravines, RPG, PEB).
- Captures : trois fiches (une en servitude AS1 ou EBC, une en zone humide ou ravine, une en PEB), la carte avec les nouvelles couches groupées « Contraintes » et « Nature », le Circuit avec les réservoirs neufs.

## Ce qui reste à Vic

Lire la note de version et basculer le run candidat depuis la page ; envoyer `DEMANDE-REGION-EPCI.md` ; lire les seuils dans `CHOIX-LABUSE.md` ; engager la convention Cerema par une collectivité mandante.

## Interdits

Rien de mergé, aucun run basculé, aucune donnée affichée hors registre, aucune URL devinée, aucune indication présentée comme une règle, aucun seuil sans référence ni mesure.
