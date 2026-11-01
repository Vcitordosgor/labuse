# MANDAT AUDIT-NU-3 — Lot G : Parcours clients (trois journées)

**Registre.** Audit LECTURE SEULE joué le 2026-11-01. Branche `audit/nu-3-g`, worktree `~/Desktop/labuse-nu3-g`, API 9280 (venv PDF-capable de `~/Desktop/labuse-main/.venv` + `PYTHONPATH` du worktree → le code servi est bien celui de `audit/nu-3-g`, HEAD `67d4233c2`), front 6480 (`vite`, `npm ci` réel), run servi `q_v20`, base Mac `labuse` (== données prod en lecture). Aucune écriture base hors ce que l'app écrit elle-même (1 projet + 1 entrée CRM + 1 suivi créés via les boutons de la fiche), aucun merge, aucun accès prod.

> Intendance : les trois journées ont été jouées dans le navigateur (Playwright) comme un utilisateur neuf, chaque chiffre affiché recoupé entre écrans et, quand c'était faisable, recalculé depuis les tables (PostGIS/DVF/SITADEL/barème). Les captures `captures/` ne sont pas versionnées (politique MENAGE-1, `**/captures/` ignoré) ; les preuves chiffrées sont les payloads `GET /parcels/{idu}`, les PDF extraits (`pdftotext`) et les requêtes SQL citées.
>
> Contrainte respectée : aucun des 12 témoins de NU-1 ni Saint-Denis / Cilaos / Salazie / Saint-Philippe. Nouveaux témoins tirés au sort dans Saint-Paul (97415), Le Tampon (97422), Saint-Pierre (97416), Saint-André (97409), Sainte-Rose (97419), Les Avirons (97401), Petite-Île (97405).

---

## Les cinq chiffres

| Chiffre | Valeur |
|---|---|
| **Scénarios joués** | **~70** : 3 journées complètes au navigateur (promoteur, investisseur, élu) ; 12 fiches promoteur (Saint-Paul) ; comparateur 3 parcelles + comparatif PDF ; assemblage 2 parcelles + Étude de faisabilité (2 variantes stationnement) ; Dossier/Gabarit/Apporteur/Pré-dossier/Comparatif/Étude-zone/Estimation PDF générés & relus ; 3 estimations par adresse (maison/appart/terrain) + export PDF ; 5 questions Copilote ; Taxe 4 logements écran+API+recalcul ; Permis/Successions/Solaire/Communes ; projet+CRM+courrier+suivi+cloche ; tests back/forward, reload, lien profond onglet neuf. |
| **Bloquant** | **0** |
| **Majeur** | **8** |
| **Mineur** | **7** |
| **Dette / note** | **4** |

**Verdict de synthèse.** L'arithmétique élémentaire et la plupart des corrections d'audits précédents tiennent : la **SDP ne se contredit plus** (en-tête fiche == Potentiel == comparateur == comparatif PDF == Dossier, sur 12 témoins — le bloquant NU-1-A-001 n'est pas reproduit) ; le **comparateur écran == comparatif PDF au chiffre près** ; l'**Estimer compare maison↔maison** (fin du « maison au prix d'appart ») et **refuse honnêtement** d'estimer un terrain nu sans comparables ; la **Taxe d'aménagement** tombe au centime (écran == API == recalcul barème 2026) ; les **compteurs Permis** sont exacts (recalcul SITADEL) ; **0 erreur console, 0 HTTP 500** sur toute la session. Le danger de ce lot est ailleurs : **(1) le même « prix du marché » prend trois valeurs différentes selon l'écran** (Estimer vs fiche vs Dossier), **(2) l'Assemblage vend un potentiel que l'Étude du même assemblage juge impossible**, **(3) le Copilote affirme, sur des sujets sensibles, le contraire de ce que montrent fiche/Estimer/Dossier** (aléa nié, loyer d'une mauvaise commune), et **(4) le routing par hash ne réhydrate pas l'état** (une recherche carte filtrée, partagée ou rechargée, perd ses filtres).

---

## Témoins (tirés au sort, communes autorisées)

| rôle | IDU | commune | note |
|---|---|---|---|
| promoteur (zone U > 800 m² sans PPR) | 97415000DX0049 | Saint-Paul | 907 m² (contenance), U6c, bâti, PM Commune de Saint-Paul — **référence promoteur** |
| promoteur | 97415000AW1118 / CR1002 / DE0804 / CL0870 / … | Saint-Paul | 10 autres fiches (U, 800–7250 m²) |
| assemblage | 97415000DX0049 + 97415000DX0050 | Saint-Paul | contiguës, 2 319 m² |
| maison (DVF 2025) | 97422000DK0311 | Le Tampon | vente 220 000 € 05/2025, bâti 98 m², terrain 948 m² |
| appartement / copro | 97416000EI1094 | Saint-Pierre | copro 77 lots RNIC, vente 02/2025 |
| terrain nu (terrain à bâtir) | 97422000CK1493 | Le Tampon | Uc, 435 m², vente terrain à bâtir 160 230 € 12/2025 |
| taxe 4 logements | 97422000CK1493 | Le Tampon | taux communal 5 % |
| élu — recalculs | Saint-Paul 97415 / Le Tampon 97422 | — | fiche commune, permis, étude de zone, successions, solaire |

Méthode de recoupement : chaque chiffre servi par `GET /parcels/{idu}?source=q_v20` recoupé entre fiche / comparateur / assemblage / Estimer / Dossier / PDF ; recalculs SQL sur `parcels`, `parcel_zone_plu`, `dvf_mutations_parcelle`, `sitadel_permits`, `spatial_layers`, et sur le barème `outils/taxe-amenagement/config`.

---

## Trouvailles

### NU-G-001 — MAJEUR — Impossible de filtrer « zone U sans PPR » : la carte n'a aucun filtre risque/PPR

- **Où** : panneau Filtres > « Affiner la recherche » (frontend carte, socle).
- **Repro** : Carte → Filtres → Saint-Paul + surface ≥ 800 + zone U → « Affiner la recherche » propose : Copropriété, Hauteur du bâti (LiDAR), Emprise bâtie, ZFANG, FRR, Signaux de vie (société / procédure / permis / friche / succession…). **Aucun filtre PPR, aléa ou risque.**
- **Affiché vs juste** : la fiche commune de Saint-Paul met pourtant « **PPR sur 34,5 % des parcelles** » en signal de tête, et le premier besoin du promoteur (« terrains en zone U **sans PPR** ») n'est pas réalisable. Il doit ouvrir chaque fiche à la main → impasse du parcours.
- **Proposition** : ajouter un filtre risque (exclure PPR rouge / tout PPR / aléa fort), cohérent avec le signal commune déjà calculé.

### NU-G-006 — MAJEUR — Étude « Impossible POUR CAUSE ÉTABLIE »… sans cause établie, et message figé qui parle de stationnement aérien même en sous-sol

- **Où** : moteur d'implantation, `POST /modules/etude` (et l'écran Étude de faisabilité).
- **Repro** : Étude de l'assemblage DX0049+DX0050, collectif, programme 6 logements (2 T2 + 4 T3, 392 m² SDP). Verdict écran **et** API : « **Impossible pour cause établie** » / `statut_global = "simulation impossible"`.
- **Affiché vs juste** : le `message` est une chaîne **figée** — « …aucune implantation ne passe tous les contrôles durs sur cette assiette (zone trop étroite, reculs, **ou stationnement aérien impossible**) » — servie **à l'identique** que je choisisse stationnement **Aérien** ou **Sous-sol** (les deux testés). Elle parle d'« aérien » alors que sous-sol est sélectionné. Le payload : `facteur_limitant = null`, `facteur_limitant_detail = null`, `facteurs_limitants = []`, `scenarios = []`, `capacite_maximale = null` → **aucune cause réellement établie**, en contradiction avec le titre « pour cause établie ». Le promoteur n'a aucun levier (quelle règle ? quelle dimension ?).
- **Nuance honnête** : sur une bonne parcelle seule (97415000DE0804, 7 250 m²), l'Étude produit bien « Exploitable sous hypothèses » avec 1 scénario — le moteur n'est pas cassé ; c'est le verdict d'échec qui n'explique rien.
- **Proposition** : nommer la dimension bloquante réelle, adapter le message au mode de stationnement choisi, et ne pas écrire « cause établie » quand `facteur_limitant` est nul.

### NU-G-007 — MAJEUR — L'Assemblage vend « SDP terrain libéré 1 253 m² ×1,67 +67 % » là où l'Étude du même assemblage est « Impossible » et 40 % de l'assiette est hors zone constructible

- **Où** : outil Assemblage (`/assemblage/study`) et son bouton « Étude de faisabilité de cet assemblage → ».
- **Repro** : Assemblage DX0049+DX0050 → carte de tête « Surface d'assiette **2 319 m²** · SDP estimée cumulée · terrain libéré **1 253 m²** · vs meilleure seule **×1,67 +67 %** ». En cliquant le bouton dédié, l'Étude du **même** assemblage renvoie `bilan_surfacique` : zone constructible **1 400 m²**, **hors zone 918,6 m² (40 % de l'assiette)** → verdict « Impossible ».
- **Affiché vs juste** : `capacite.sdp_m2 = 1253` est une **simple agrégation** (la note en petits caractères dit « reculs/géométrie à valider »), mais le gros chiffre ×1,67 +67 % ne dit pas que **40 % est hors zone constructible** ni que rien ne s'y bâtit. Le promoteur passe d'un écran encourageant à un verdict d'impossibilité, par un bouton qui relie explicitement les deux.
- **Proposition** : borner la SDP cumulée à la part en zone constructible, afficher le % hors zone, aligner le ton Assemblage↔Étude.

### NU-G-009 — MAJEUR — Trois « prix du marché » différents pour le même bien selon l'écran (Estimer vs Dossier vs fiche)

- **Où** : outil Estimer (`/radar/annonce/estimation/{idu}`), fiche (`prix_ancien` / `marche_synthese`), Dossier PDF (`/dossier/{idu}.pdf`).
- **Repro — maison 97422000DK0311** (Le Tampon) :
  - **Estimer** : **2 205 €/m²** (29 ventes maison, rayon 1 000 m, 2021–2025, « comparée aux ventes de maisons », ±26 %).
  - **Dossier**, ligne « Maison » : **2 064 €/m²** (8 ventes · secteur cadastral).
  - **Fiche + Dossier**, tête « Prix ancien médian » : **2 087 €/m²** (mixte appart+maison, 27 ventes, rayon 1 000 m).
- **Repro — appart/copro 97416000EI1094** (Saint-Pierre) : **Estimer 3 877 €/m²** (39 ventes appart, rayon 500 m) vs **fiche `prix_ancien` 2 601 €/m²** (appartement, 50 ventes, rayon 500 m) → écart ~49 %.
- **Affiché vs juste** : deux outils annoncent « €/m² maison » (ou « appart ») avec des **périmètres différents** → chiffres différents de 7 à 49 %. L'investisseur qui passe de l'Estimer à la fiche/Dossier voit plusieurs « prix du marché » pour le même bien. (À porter au crédit de l'app : l'Estimer compare bien maison↔maison — le fix ESTIMER-2 tient ; c'est la **cohérence inter-écrans** du €/m² qui manque.)
- **Proposition** : exposer la même méthode/le même périmètre partout, ou nommer explicitement « estimation locale (rayon N) » vs « médiane de secteur » vs « médiane mixte » pour que les écarts soient lisibles.

### NU-G-010 — MAJEUR — Le Dossier d'un TERRAIN NU met en tête un « Prix ancien médian » qui est un €/m² de bâti (appartement)

- **Où** : `bilan`/`base_plans` imprimé dans `/dossier/{idu}.pdf` (tête section marché).
- **Repro** : terrain nu 97422000CK1493 (Le Tampon, « vente terrain à bâtir » 160 230 € = **368 €/m² réel**). Le Dossier imprime en tête « **Prix ancien médian 1 706 €/m² (18 ventes à moins de 500 m)** » ; plus bas « Terrain nu — secteur — (3 ventes, échantillon insuffisant) » et « Ancien bâti — secteur 1 706 €/m² » (type appartement d'après le payload).
- **Affiché vs juste** : pour un terrain nu, le chiffre phare du Dossier est un prix d'**ancien bâti/appartement** sans rapport avec un terrain à bâtir. L'**Estimer**, lui, refuse honnêtement : « Pas assez de ventes de terrain nu comparables dans le secteur » → **incohérence Estimer↔Dossier** et survente (lignée NU-1-A-002, persistante côté Dossier).
- **Proposition** : sur un bien nu, ne pas mettre un « prix ancien médian » bâti en tête ; servir le €/m² terrain (ou « non estimable »), comme l'Estimer.

### NU-G-011 — MAJEUR — Le Copilote répond « hors zones d'aléas » pour une parcelle que fiche, Estimer et Dossier affichent « 1 aléa (mouvement de terrain, 100 %) »

- **Où** : Copilote (outil PPR/aléas).
- **Repro** : « Y a-t-il un risque PPR sur la parcelle 97416000EI1094 ? » → « Non, cette parcelle n'est pas classée en zone PPR. Elle est située **hors zones d'aléas (ni rouge, ni bleue)** selon la couche PPR servie. (DEAL Réunion — PPR / aléas) ».
- **Affiché vs juste** : le même bien porte `aleas.n = 1` (« Aléa mouvement de terrain — niveau faible sur ~100 % », `ppr = null`), affiché « RISQUES 1 vigilance » sur la fiche, « Risques 1 aléa » sur l'Estimer, « Mouvement de terrain — Faible — 100 % » sur le Dossier. La réponse « pas en zone PPR » est juste, mais « hors zones d'aléas » **nie l'aléa que tous les autres écrans affichent** — sur un sujet de risque.
- **Proposition** : distinguer « pas de PPR réglementaire » de « aléas Géorisques » et mentionner l'aléa mouvement de terrain présent (cohérence avec `n_aleas`).

### NU-G-013 — MAJEUR — Copilote : le loyer d'une parcelle du Tampon est annoncé « à Saint-Denis », à une valeur qui contredit la fiche, avec un préambule interne fuité

- **Où** : Copilote (outil loyers).
- **Repro** : « Quel est le loyer au m² autour de la parcelle 97422000DK0311 ? » (parcelle du **Tampon**) → « **J'ai compris : répondre à votre question — parcelle 97422000DK0311.** Le loyer médian autour de la parcelle **à Saint-Denis** est de **15,09 €/m²** pour un appartement (DHUP 2025). SOURCE · DVF, SITADEL, DHUP (TERRAIN NU) ».
- **Affiché vs juste** : quatre défauts cumulés — **(1)** mauvaise commune (« à Saint-Denis » pour une parcelle du Tampon) ; **(2)** valeur **15,09 €/m² (DHUP)** incohérente avec le loyer de la fiche **9,2 €/m² (OLL 2024, zone 6)** ; **(3)** préambule de raisonnement interne fuité (« J'ai compris : répondre à votre question… ») ; **(4)** étiquette source « …(TERRAIN NU) » sur une question de loyer.
- **Proposition** : ancrer la réponse sur la commune réelle de l'IDU, servir le loyer OLL de la fiche, supprimer le préambule, corriger l'étiquette.

### NU-G-015 — MAJEUR — Lien profond / rechargement d'une recherche carte filtrée : les filtres ne sont pas restaurés (retour à 433 229 parcelles)

- **Où** : routing par hash du socle (carte + filtres).
- **Repro** : charger (onglet neuf ou reload) `…/socle/#f=1&smin=800&cs=Saint-Paul&zf=U&c=Saint-Paul`. Le hash contient bien `smin`/`zf`/commune, **mais** l'écran revient à l'accueil et, panneau Filtres ouvert, le compteur affiche « **Voir les 433 229 parcelles** » (toute l'île) : surface ≥ 800, zone U et commune Saint-Paul **non appliqués**.
- **Affiché vs juste** : le hash des filtres est **écrit en direct** quand on filtre, mais n'est **pas relu au chargement**. Un promoteur qui copie/partage ou recharge l'URL de sa recherche perd tous ses filtres. (En regard : le lien profond fiche `#idu=` fonctionne en onglet neuf.)
- **Proposition** : réhydrater l'état des filtres depuis le hash au montage (`f`/`smin`/`smax`/`zf`/`cs`/état du sol).

### NU-G-002 — MINEUR — Le filtre « 1 · Communes » liste des codes postaux nus, sans nom

- **Où** : Filtres > section 1 · Communes.
- **Repro** : chips « 97400, 97410, 97412, 97413, 97419, 97424, 97460… » = **codes postaux**, sans nom de commune. Un utilisateur neuf ne sait pas que 97460 = Saint-Paul. La carte, elle, offre des boutons nommés (Saint-Paul, Le Tampon…). Incohérence interne + écho NU-1-B (« CP Saint-Leu 97424 ≠ 97436 »).
- **Proposition** : afficher le nom de commune (le CP en secondaire), comme sur la carte.

### NU-G-003 — MINEUR — La surface d'une même parcelle diffère selon l'écran : 907 m² (fiche/comparateur) vs 913 m² (assemblage/omnibox)

- **Où** : fiche / comparateur (contenance cadastrale) vs assemblage / autocomplétion / Estimer (surface géométrique `ST_Area`).
- **Repro** : DX0049 — fiche tuile « SURFACE 907 m² », comparateur 907, Dossier 907 (contenance) ; mais l'assemblage affiche « 913 m² », l'omnibox « 913 m² », l'Estimer « 973 m² » pour DK0311 (contenance 948). DB : `contenance_m2 = 907`, `surface_m2 = 913`.
- **Affiché vs juste** : le mandat demande que « chaque chiffre croisé entre deux écrans soit identique » ; ici la surface de la même parcelle change de notion selon l'écran. (L'Étude, elle, affiche honnêtement contenance ET surface réelle + écart.)
- **Proposition** : servir la même notion de surface partout, ou l'étiqueter (contenance vs géométrique).

### NU-G-004 — MINEUR — La fiche met en avant le €/m² TERRAIN NU ; le Dossier met en avant le €/m² ANCIEN BÂTI

- **Où** : tuile « Marché » de la fiche vs tête marché du Dossier.
- **Repro** : DX0049 (bâti) — fiche tuile « Marché **164 €/m²** » (terrain nu, section cadastrale) ; Dossier tête « Prix ancien médian **2 447 €/m²** » (ancien). Les deux chiffres existent des deux côtés (le comparateur les montre côte à côte, clair), mais le chiffre « phare » diffère entre fiche et Dossier → lecture incohérente de « le prix du marché ».
- **Proposition** : harmoniser le chiffre mis en avant selon la nature du bien.

### NU-G-005 — MINEUR — Le Dossier imprime un prix ancien « mixte (appart+maison) » de fiabilité FRAGILE sans le caveat

- **Où** : `/dossier/{idu}.pdf`, tête marché.
- **Repro** : DX0049 — payload `prix_ancien.type_prix = "mixte (appart+maison)"`, `fiabilite = "fragile"` (repli appartements → appart+maison) ; `marche_synthese` **dit** « (mixte (appart+maison), …) ». Le Dossier imprime « Prix ancien médian 2 447 €/m² (10 ventes à moins de 1 500 m). » — **sans** « mixte » ni « fragile ».
- **Proposition** : reporter le qualificatif de fiabilité (déjà calculé) dans le Dossier.

### NU-G-008 — MINEUR (DA/texte) — « 1retenues » : pluriel et espace manquants dans la fiche projet

- **Où** : page Projets > projet ouvert, carte de stat.
- **Repro** : « **1retenues** » (sans espace, pluriel erroné) alors que la liste des projets affiche « 1 retenue » (correct). Incohérence interne.
- **Proposition** : accord singulier/pluriel + espace.

### NU-G-012 — MINEUR — Le Copilote ne restitue pas le prix médian maison alors que l'Estimer / le Dossier / la fiche commune le calculent

- **Où** : Copilote (outil marché).
- **Repro** : « Quel est le prix médian des maisons au Tampon ? » → « L'outil marche… pas une segmentation par type de bien (maison/appartement) … n'est pas encore interrogeable ici ». Or l'Estimer (2 205 maison), le Dossier (ligne « Maison » 2 064) et la fiche commune (« Prix médian maison … ») servent ce chiffre.
- **Proposition** : étendre la couverture de l'outil `marche` du Copilote à la segmentation par type (déjà disponible ailleurs).

### NU-G-014 — MINEUR — Compteur « Risques » : l'Estimer affiche « 1 aléa » là où la fiche affiche « 2 vigilances » (même parcelle)

- **Où** : tuile Risques de la fiche vs bloc Risques de l'Estimer.
- **Repro** : CK1493 — Estimer « Risques 1 aléa » ; fiche « RISQUES 2 vigilances » / « Risques et environnement … 2 vigilances ». Payload `aleas.n = 1`. La fiche compte des « vigilances » (aléas + autres couches), l'Estimer les « aléas » — mêmes données, deux tallies sous le même libellé « Risques » (lignée NU-1-A-007 / CHASSE C4-002, compteur unique).
- **Proposition** : un seul compteur de risque, nommé pareil partout.

---

## Dettes / notes

- **D-1 — Perf Étude** : l'Étude d'une parcelle seule (DE0804, 7 250 m²) prend **27 s** ; le Pré-dossier ZIP **30,6 s** ; le Dossier PDF 7–14 s. Dans la borne, mais lourd pour un parcours interactif.
- **D-2 — Routing hash en session** : un `#idu=` ou `#m=…` poussé **en cours de session** (module déjà ouvert) n'ouvre pas la cible ; le bouton **Retour** du navigateur désynchronise URL↔vue (hash vidé mais module + fiche encore affichés). Seul le chargement **à froid** d'un `#idu=` (onglet neuf) est fiable.
- **D-3 — Dénominateur commune** : l'outil Communes affiche Saint-Denis « parcelles 38 295 » vs 38 557 (comptage `parcels`) — écart dénominateur déjà noté NU-1-B.
- **D-4 — Session 2 h** : l'auth est **désactivée en local** (`env=local`) → la tenue de session 2 h n'est pas testable de façon représentative ici (pas de cookie/expiration applicative). ~1 h d'utilisation continue sans erreur ni déconnexion observée.

---

## Ce qui est juste (verts notables)

- **SDP enfin cohérente** : en-tête fiche == Potentiel == comparateur == comparatif PDF == Dossier, sur les 12 témoins promoteur (ex. DX0049 = 233 m² partout ; DK0311 = 598 m²). Le bloquant **NU-1-A-001 n'est pas reproduit**.
- **Comparateur écran == comparatif PDF** au chiffre près (907/1 213/1 096 m², U6c/U4b/U3c, classement C/B/C, SDP 233/941/437, terrain 164/422/232, bâti 2 447/3 051/4 273).
- **Classement LABUSE** fiche (`bande`) == comparateur == comparatif PDF.
- **Estimer maison↔maison** (fin du « maison au prix d'appart ») + **fiabilité honnête** (±26 % Moyenne) + **refus honnête** sur terrain nu sans comparables (ESTIMER-2 / BANC-RAYON tiennent).
- **Taxe d'aménagement** exacte à l'écran == API == recalcul barème 2026 : 4 logts, 280 m², résidence principale, Le Tampon → assiette 280×892×50 % = **124 880**, communale 5 % = **6 244**, départementale 2,5 % = **3 122**, **Total 9 366 €**, RAP 0,4 % = 499,52. Taux Le Tampon 5 % sourcé DGFiP DELTA.
- **Permis exacts** : Saint-Paul 329/12 mois == fiche « 329 permis/an » ; Le Tampon 509/24 mois == outil Permis (recalcul `sitadel_permits`).
- **Fiche commune Saint-Paul** cohérente en interne (prix ancien 4 278 == « Le marché » ; PPR 34,5 % signal == risques ; 108 088 hab tête == pop/logement ; 51 359 parcelles == non-disparues).
- **Copilote déterministe & sourcé** quand l'outil porte le fait : « 97416000EI1094 en copropriété ? » → « Oui, 77 lots (RNIC) » ; « 97422000CK1493 constructible ? » → refuse le mot et renvoie PLU/Étude (doctrine COPILOTE-3 / FAISA-REGLES respectée).
- **Courrier propriétaire** : adressage générique RGPD-safe (« aucune identité de propriétaire particulier »), lettre cohérente avec la fiche (objet « DX 0049 », « 1 Chemin Pausé … déjà bâtie »).
- **Chaîne projet→CRM→suivi→cloche** : projet créé (1 retenue == la parcelle), CRM « Repérée », « Suivie — les événements alimentent la cloche », parcelle présente dans la cloche.
- **Robustesse** : **0 erreur console**, **0 HTTP 500**, **0 traceback** sur toute la session ; tous les exports PDF/ZIP en 200 (dossier, comparatif, étude-zone, estimation, gabarit, apporteur, pré-dossier) ; `bilan`/`dossier-banquier` en 422 propre (saisie requise), jamais un crash. Le Gabarit PDF répond 200 (contraste NU-1-D « PDF Gabarit disparue = 500 »).
- **Lien profond fiche** `#idu=<IDU>` en onglet neuf : ouvre la fiche.

---

## Récapitulatif des trouvailles

| id | gravité | une ligne |
|---|---|---|
| NU-G-001 | Majeur | Aucun filtre PPR/risque sur la carte (« zone U sans PPR » infiltrable) |
| NU-G-006 | Majeur | Étude « Impossible pour cause établie » sans cause (facteur_limitant null) + message figé « aérien » même en sous-sol |
| NU-G-007 | Majeur | Assemblage « SDP 1 253 m² ×1,67 » vs Étude « Impossible » (40 % hors zone) |
| NU-G-009 | Majeur | Trois €/m² marché différents pour le même bien (Estimer/Dossier/fiche) |
| NU-G-010 | Majeur | Dossier d'un terrain nu met en tête un prix de bâti/appart (1 706 €/m²) |
| NU-G-011 | Majeur | Copilote « hors zones d'aléas » ≠ fiche/Estimer/Dossier « 1 aléa » |
| NU-G-013 | Majeur | Copilote loyer : mauvaise commune (Saint-Denis), valeur ≠ fiche, préambule fuité |
| NU-G-015 | Majeur | Lien profond/reload d'une recherche filtrée : filtres non restaurés (433 229) |
| NU-G-002 | Mineur | Filtre communes = codes postaux nus sans nom |
| NU-G-003 | Mineur | Surface 907 (fiche/comparateur) vs 913 (assemblage/omnibox) |
| NU-G-004 | Mineur | Fiche met en avant €/m² terrain nu, Dossier €/m² ancien bâti |
| NU-G-005 | Mineur | Dossier imprime un prix « mixte fragile » sans le caveat |
| NU-G-008 | Mineur | « 1retenues » (pluriel/espace) dans la fiche projet |
| NU-G-012 | Mineur | Copilote ne sort pas le prix médian maison (dispo ailleurs) |
| NU-G-014 | Mineur | Compteur Risques : Estimer « 1 aléa » vs fiche « 2 vigilances » |

**Fil rouge.** L'app sait calculer juste (SDP, surface, taxe, permis, estimation maison↔maison) et a refermé plusieurs bloquants de NU-1. Les trous restants sont des **incohérences d'assemblage inter-outils** : un même fait (prix du marché, surface, risque, loyer, SDP d'un assemblage) prend des valeurs ou des verdicts différents selon l'écran par lequel le client y arrive — et le Copilote, sur deux sujets sensibles (aléa, loyer), affirme le contraire de ce que montre le reste de l'app. Le danger n'est pas l'arithmétique, c'est la **parole tenue entre deux écrans**.
