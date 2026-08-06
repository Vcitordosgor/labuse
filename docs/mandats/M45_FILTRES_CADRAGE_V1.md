# M45 — FILTRES LABUSE : liste complète de cadrage (v1, 06/08/2026)

> Document de cadrage Vic + Claude — FAIT FOI pour le mandat M45. Principe directeur : un
> filtre = une DÉCISION que le promoteur prend, pas une colonne qui existe. Chaque filtre
> servi est étiqueté (Sourcé/Estimé) et ne peut pas mentir.
> Architecture : 2 voies (« Je filtre moi-même » / « L'analyse LABUSE ») + compteur en
> direct + vues préréglées.
> Arbitrages rendus (06/08) : barre niveau 1 = les 7 ci-dessous · vue par défaut = analyse
> LABUSE ACTIVE (l'interrupteur coupe vers la voie manuelle) · presets de lancement = les 6
> nommés · curseur mode B (travaux + loyer M44) = une valeur de session unique partagée
> fiche/filtre · tier « Réserve foncière » renommé « Potentiel long terme » sur toutes les
> surfaces.

## NIVEAU 1 — TOUJOURS VISIBLE (la barre de base, 7 filtres)

| Filtre | Valeurs | Notes |
|---|---|---|
| Commune / secteur | multi-sélection + dessin sur carte (polygone) | |
| **Constructibilité calibrée** | constructible aujourd'hui · AU conditionnelle (par opération / par état tiers) · fermée · inconstructible · RNU / hors-PLU-outillé | LE filtre différenciant — dérivé de la calibration 24 communes et des motifs de déclassement, PAS de la zone brute |
| Surface parcelle | min / max m² | |
| SDP résiduelle | min / max m² | La vraie question avant la taille du terrain |
| État du sol | nu · bâti marginal divisible · bâti saturé · bâti révélé | Passerelle mode B |
| Capacité logements | ≥ N estimés | Étiquette Estimé sur le filtre lui-même |
| **Analyse LABUSE** | interrupteur : appliquer le classement + choix des tiers | ACTIVE par défaut. Le moment de bascule affiche le contraste (« 3 847 → 47 ») |

## NIVEAU 2 — TIROIRS PAR QUESTION (dépliables)

### « Puis-je construire ? » (droit du sol)
Zone PLU exacte (multi, par commune) · type de zonage U/AU/A/N · statut AU détaillé
(ouverture par opération / état tiers / inconnu 90-180 j) · plancher de densité applicable
(Saint-Leu, Trois-Bassins, L'Étang-Salé) · EBC partiel (avec/sans) · emplacement réservé
(avec/sans) · 50 pas géométriques · Parc national (aire d'adhésion) · sol naturel/ZAN ·
fraîcheur PLU de la commune (à jour / procédure en cours — radar M41)

### « Combien ça coûte, combien ça rapporte ? » (économie)
Charge foncière médiane €/m² (tranches) · prix marché secteur €/m² DVF + fiabilité (n≥3 /
échantillon limité) · bilan indicatif CA (tranches) · prix d'achat max ≤ budget (calculette
M22-A en filtre) · **mode B rentable au paramètre courant** (curseurs travaux + loyer
partagés session) · sous-densité (avec/sans)

### « Ça va muter ? » (le cœur — voie analyse)
Tier (brûlante / chaude / à creuser / potentiel long terme / déclassées / écartées) ·
probabilité de mutation ×N (seuil) · rang ≤ N (têtes seulement, cohérent Q3-M36) · entrée
en tête récente (signal dette #9) · segment Renouvellement (⚠ vérifier le rebuild N°3
train 5 avant d'exposer) · segment Division en or (O12) · activité de permis du secteur
(autorisés récents / dépôts 36 mois, M38-M42)

### « À qui c'est, puis-je l'acheter ? » (propriété)
Type de propriétaire : PM identifiée (SIREN) / bailleur / PP non déterminable · état de la
société (procédure collective / cessée / radiée — M43, factuel) · assemblage même
propriétaire (×N contiguës) · acquérabilité (même proprio PM / distincts / non déterminable)
· copropriété (RNIC avec/sans) · dossier propriétaire disponible
⏳ dormance/succession : ABSENT (attend avocat + M43-suite)
🚫 gérant âgé : JAMAIS un critère de requête (RGPD, dossier avocat)

### « Quels risques, quelles contraintes ? » (terrain)
PPR (présence/niveau) · aléas (niveau) · bruit routier (classes) · SIS/pollution ·
pente (tranches) · accès voirie (identifié / non identifié — étiquette : limite BD TOPO,
dette #12) · viabilisation (probable / confirmée par les faits) · assainissement/ANC ·
vigilances (aucune / ≥1 / par type, dont piscine M39) · géométrie exploitable (drapeau)

### « Veille & niches » (les différenciants)
**Motif de déclassement (multi)** — explorer les écartées : la veille sur les futures
ouvertures AU · veille AU du radar M41 (commune en procédure) · potentiel solaire (PVGIS,
parkings APER ≥1000 m²) · proximité NPNRU/QPV · adresse disponible / absente (BAN)
⏳ enquête publique fine : couvert par le radar M41, rien de plus

## VUES PRÉRÉGLÉES (l'anti-60-checkboxes) — les 6 du lancement
« Terrain nu constructible » (constructible aujourd'hui + nu + SDP > 100 m²) ·
« Prêt à démarcher » (chaud+ · accès identifié · proprio PM identifié) ·
« Division en or » (segment O12) ·
« Réhab rentable » (bâti saturé/révélé + mode B positif au paramètre courant) ·
« Veille AU » (écartées zone fermée/AU conditionnelle, par commune) ·
« Mon budget » (prix d'achat max ≤ X + commune)
+ vues sauvegardées par l'utilisateur (nom + combinaison, côté compte).

## 🚫 ANTI-FILTRES — exposés nulle part
Score d'Opportunité (retiré M36) · Complétude (retirée M36) · ICD (gardé en fiche, non
discriminant en filtre) · statut matrice historique (rail éteint M37) · rang au-delà des
têtes · **gérant âgé / tout critère sur personne physique** (RGPD) · **v_signal (Score V)
→ arbitrage rendu : PAS un filtre** — Score V est retiré du scoring (RR 0,51) et de
l'affichage (M35) ; filtrer sur un signal mort est un vestige, retirer le param du front.

## RÈGLES TRANSVERSES
1. Un filtre ne peut pas mentir : P0 = inventaire, corrections avant tout ajout.
2. Compteur en direct à chaque ajustement.
3. Tout montrer : écartées consultables avec motif, jamais masquées.
4. Chaque filtre porte étiquette (Sourcé/Estimé) et limite (voirie BD TOPO, DVF n<3,
   capacité Estimé).
5. Plancher « délaissé » : sous ~40 m² (seuil à confirmer par la distribution en P0,
   anomalie AI1886 : bilan R+6 servi sur 9 m²), pas de bilan déroulé.
6. Les pièges dormants identifiés au préliminaire (branche /parcels sans source qui ignore
   les filtres, param statuts sur matrice morte, alias brulantes) : à neutraliser
   proprement (404 ou suppression), pas à laisser dormir.
