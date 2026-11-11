# Courrier propriétaire

Clé interne : `courriers` (num M09) · composant : `frontend/src/components/outils/ModulePanel.tsx` (fonction `M09`, l.1400) · endpoints : `POST /courrier/adressage`, `POST /courrier/composer`, `POST /courrier/demande`, `GET /courrier/demandes`, `GET /courrier/statut`, `POST /courrier/pdf`, `GET/PUT /courrier/admin/config`, `GET/POST/DELETE /courrier/admin/oppositions` (backend `src/labuse/api/courrier.py`, cœur `src/labuse/courrier.py`, `src/labuse/courrier_adressage.py`, `src/labuse/courrier_compose.py`).

## 1. À quoi il sert, et pour qui
Un agent/foncier prépare un courrier à envoyer aux propriétaires de parcelles qu'il cible, et DEMANDE à LABUSE de l'imprimer, l'affranchir et le poster (le client prépare, LABUSE envoie — jamais d'envoi automatique). Le texte est composé par la machine à partir des seules données publiques de la parcelle ; aucun particulier n'est nommé (pli « À l'occupant »), seules les personnes morales (sociétés, communes) sont adressées à leur nom.

## 2. Le parcours
Parcours GUIDÉ en 3 étapes dans le panneau de l'outil (`M09`, stepper l.1519 : `Destinataires / Relecture / Envoi`) :
- **Bandeau d'intro** (l.1523) : « service d'envoi », + le PRIX et le DÉLAI lus de `/courrier/statut` (« 2,50 € par courrier… · envoi sous 3 à 5 jours », l.1527-1529).
- **État du service** (l.1536) : carte verte « disponible » + plafond du jour SI `disponible:true` ; sinon rien (le provider est un bouchon `stub` → service affiché indisponible, mais la demande s'enregistre quand même).
- **Étape 1 — Destinataires** (l.1559) : l'utilisateur saisit une adresse / IDU / référence (`ParcelInput`, l.1562) ; chaque ajout appelle `POST /courrier/adressage` (l.1447). Un terrain nu / sans adresse / sans canal / inconnu est REFUSÉ à l'ajout (set `AJOUT_REFUSE`, l.1442) avec renvoi au Courrier SPF ; sinon la parcelle devient une « chip » enrichie commune+surface via la fiche (`_enrichir`, l.1432).
- **Étape 2 — Relecture** (l.1516) : aperçu LECTURE SEULE du courrier du 1ᵉʳ destinataire via `POST /courrier/composer` (l.1492) — AUCUNE saisie libre ; le texte (`recto`) est celui que produira le PDF. Un aperçu PDF est téléchargeable (`courrierPdf`, l.1511).
- **Étape 3 — Envoi** (l.1499) : résout l'adressage de TOUS les destinataires ; si une parcelle est bloquée (opposition, nu…), le dépôt est bloqué (`depotBloque`, l.1503). « Demander l'envoi » appelle `POST /courrier/demande` (l.1504) → confirmation avec une référence non séquentielle. Les demandes se consultent ensuite depuis « Projets → Mes courriers » (`GET /courrier/demandes`).

Côté LABUSE (admin, non visible client) : Vic reçoit une notif (cloche + e-mail Brevo, `courrier_demande`, l.158-179) et fait avancer le statut À déposer → Déposé → Envoyé.

## 3. Les données lues
Le courrier n'invente rien : il lit la parcelle, son propriétaire-personne-morale, son adresse postale, sa zone PLU, ses ventes voisines et ses risques.

| Donnée | Source (catalogue) | Table SQL réellement lue | Millésime servi | Cadence |
|---|---|---|---|---|
| Parcelle (section, numéro, commune, surface) | Cadastre (API Carto PCI) / Cadastre Etalab | `parcels` (`courrier_adressage.py` l.63-70 ; `courrier_compose.py` l.73-79) | PCI/Etalab « latest » ingérée | — |
| Parcelle bâtie ? | — (dérivé) | `parcel_filtre_bati` (jointure, `courrier_adressage.py` l.68) | — | — |
| Propriétaire personne morale (dénomination, SIREN) | SIRENE / cadastre PM | `parcelle_personne_morale` (`courrier_adressage.py` l.69) | — | — |
| Adresse du siège social (PM) | SIRENE | `owner_enrichment` (payload SIRENE, `courrier_adressage.py` l.88-91) | Sirene INSEE — état courant (non versionné) | — |
| Adresse postale du bien (BAN) | Base Adresse Nationale / BAN PLUS | `parcel_adresse` (`courrier.py` `adresse_ban_parcelle`, l.170-178) | BAN PLUS maj 27/08/2026, moisson 13/09/2026 | mensuel |
| Zone d'urbanisme | Urbanisme PLU/GPU (API Carto) | `zone_servie.zone_dominante` + `parcel_zone_plu` (libellé) (`courrier_compose.py` l.108-119) | GPU/PLU par commune (révisions en fiche) | — |
| Ventes voisines (nb mutations 500 m / 3 ans) | DVF / valeurs foncières | `dvf_mutations_parcelle` ∩ `parcels.geom_2975` (`courrier_compose.py` l.130-138) | géo-DVF Etalab — 2026-S1 | semestriel |
| Risques « certains » | Cascade de contraintes (run servi) | `dryrun_cascade_results` (`courrier_compose.py` l.153-157) | run cascade résolu courant | — |
| Oppositions (liste rouge) | Registre interne stop@labuse.immo | `courrier_opposition` (`courrier.py` l.207-217) | saisie manuelle Vic | — |
| Nom de l'expéditeur (marque blanche) | Compte client | `comptes.marque` / `comptes.nom` (`api/courrier.py` `_marque_du_compte`, l.445-460) | — | — |

## 4. Les calculs
Cet outil fait peu de « calcul » : l'essentiel est de la SÉLECTION de texte et un petit tarif.

**a) Prix et coût (lus en config, pas calculés sur l'écran)** — `tarif()` dans `src/labuse/courrier.py` l.609-622 :
- Prix CLIENT affiché = `courrier_prix_client_eur`, **valeur 2,50 €** fixée dans `src/labuse/config.py` l.213. C'est un prix PLAT tout compris, pas un calcul. SOURCÉ config.
- Coût prestataire = `courrier_cout_lettre_eur` **2,69 €** (`config.py` l.209) OU la valeur admin datée de `courrier_config` (`cout_lettre_eur`, l.567-571). Servi à `/courrier/admin/config`.
- Marge = `courrier_marge` **1,5** (`config.py` l.210). Le commentaire dit « prix = coût × marge, si prix client non fixé » : 2,69 × 1,5 = 4,035 €. Mais comme `courrier_prix_client_eur` EST fixé, c'est 2,50 € qui est servi — le calcul coût×marge n'est plus utilisé (voir Doutes).
- **Coût total** (chemin d'envoi hérité) = `prix_client_eur × N destinataires`, arrondi 2 décimales (`courrier.py` l.690 `"total_eur": round(t["prix_client_eur"] * len(crees), 2)`). L'outil M09 (demande) n'affiche PAS de total à l'écran : il n'affiche que le prix unitaire. Le total apparaît dans le chemin `/courrier/envois` (dormant, provider stub).

**b) Délai affiché** = `courrier_delai_jours`, **chaîne « 3 à 5 »** (`config.py` l.214, rendu « envoi sous 3 à 5 jours »). Codé en config, pas calculé.

**c) Plafond anti-abus** = `courrier_max_jour` **100** (`config.py` l.215). `reste = max(0, plafond − envoyés_du_jour)` (`api/courrier.py` l.66) ; `envois_du_jour` compte sur `courrier_envois.ts::date = current_date` (horloge DB, `courrier.py` l.625-631). N'affecte que le chemin d'ENVOI direct, pas les demandes.

**d) Choix de l'ouverture du courrier (A→E)** — `choisir_ouverture()` (`courrier_compose.py` l.165-180), première règle applicable :
- **A** (terrain non bâti PM) : PM ET non bâtie ET zone connue ET surface fiable.
- **B** (bâtie, zone calibrée) : bâtie ET `zone_calibree`.
- **C** (secteur actif) : nb mutations ≥ **8** (`SEUIL_SECTEUR_ACTIF`, l.21), rayon **500 m** (`RAYON_DVF_M`, l.20), fenêtre **3 ans** (`X_ANNEES_DVF`, l.19).
- **D** (neutre avec zone) sinon si zone connue ; **E** (neutre) à défaut.
Une donnée manquante fait toujours retomber vers une ouverture plus neutre — jamais une valeur inventée.

**e) Surface affichée** = contenance cadastrale de l'acte (`_surface.surface_terrain`, pas le dessin brut ST_Area ; `courrier_compose.py` l.94) ; surface « incertaine » → les deux chiffres + réserve, jamais une valeur seule.

## 5. Chaque chiffre affiché
| Libellé à l'écran | D'où il vient | Sourcé / Estimé |
|---|---|---|
| « 2,50 € par courrier » | `courrier_prix_client_eur` (config.py l.213), servi par `/courrier/statut` | Sourcé (config, pas donnée terrain) — prix commercial fixé |
| « envoi sous 3 à 5 jours » | `courrier_delai_jours` « 3 à 5 » (config.py l.214) | Sourcé (config) |
| « Plafond du jour : N/100 restants » | `plafond_jour`/`reste_jour` = `courrier_max_jour` − envois du jour (api l.66) | Sourcé (config + compte DB) |
| Destinataire (« À l'occupant » / raison sociale) | `resoudre_destinataire` (adressage l.58-115) | Sourcé (cadastre PM / règle fixe) |
| Adresse d'envoi | `owner_enrichment` (siège SIRENE) ou `parcel_adresse` (BAN) | Sourcé |
| Référence cadastrale (ex. « BZ 1065 ») | dérivée de l'IDU (adressage l.78) | Sourcé (dérivé) |
| Surface cadastrale (verso) | `surface_terrain(surface_m2, contenance_m2)` (compose l.94) | Sourcé |
| Zone d'urbanisme (verso) | `zone_dominante` (compose l.110) | Sourcé |
| « N mutations publiées sur AAAA-AAAA » (verso) | count `dvf_mutations_parcelle` 500 m / 3 ans (compose l.130-141) | Sourcé (DVF) |
| « Contraintes connues : … » (verso) | `dryrun_cascade_results` HARD_EXCLUDE risques (compose l.153-159) | Sourcé (run cascade) |
| Référence de demande « C-DDMM-XX » | hachage md5 de l'id (courrier.py `_reference` l.323-332) | Estimé (identifiant interne, non devinable) |

## 6. Les limites
- **Aucun envoi réel aujourd'hui** : `provider = "stub"` (config.py l.206 ; `provider_actif` l.559). `/courrier/statut` renvoie `disponible:false`. Le client peut DEMANDER (la demande est enregistrée, Vic notifié), mais rien ne part automatiquement ; le chemin Merci Facteur (`_envoyer_mercifacteur` l.634) est un squelette « à valider en sandbox ».
- **Composition refusée** si le compte n'a pas de raison sociale/signataire (`ExpediteurSansNom`, compose l.219 ; message « Renseignez le nom de votre société dans Compte ») — vérifié par curl anonyme (voir §9).
- **Particuliers jamais nommés** : une parcelle de personne physique → « À l'occupant » sur bâti seulement ; terrain nu PP → bloqué (`MOTIF_NU`, adressage l.21). Donc l'outil ne permet PAS de cibler nominativement un propriétaire privé (c'est volontaire).
- **Oppositions = source interne manuelle** : seule une opposition saisie par Vic (`courrier_opposition`) bloque. Aucun registre externe (Bloctel, listes publiques) n'est consulté.
- **Fraîcheur des données** : la zone, les ventes DVF (arrêt 2026-S1) et l'adresse BAN peuvent dater ; le courrier affiche la période RÉELLE des ventes, mais une parcelle re-zonée récemment peut porter une zone obsolète si `parcel_zone_plu` n'a pas basculé.
- **Le prix/coût/marge sont incohérents entre eux** (voir §10) : le coût×marge (4,035 €) n'est plus servi, le prix affiché 2,50 € est inférieur au coût prestataire 2,69 € — l'écran ne montre jamais cette tension.

## 7. Les tests
- Front `frontend/src/components/outils/CourrierService.test.tsx` : prefill Assemblage amorce une chip (l.68), parcours complet jusqu'à « Demande transmise » avec n° (l.74, vérifie l'absence de n° PK global l.90, et des statuts admin « Imprimé/Posté » l.93-94), aperçu PDF disponible (l.97), prefill mono-parcelle fiche→Courrier (l.106), et surtout qu'un champ vide ne s'imprime jamais (l.49, pas de tiret/parenthèse orpheline).
- Front `frontend/src/components/outils/CourrierRecette4.test.tsx` : PM sans adresse, PP complète, et commune+surface absentes → segments retirés proprement.
- Backend `tests/test_courrier.py` : statut stub sans compte (l.23), responsabilité obligatoire (l.39), plafond/jour (l.46), PDF recto/verso sans placeholder (l.72), idempotence demande séquentielle+concurrente (l.100/120), opposition bloque tous comptes (l.158/194), adressage occupant/nu/siège/opposition (l.273), garde placeholder (l.322), sélection ouverture A→E (l.341), vocabulaire statut unique (l.370), prix non servi / coût admin / prix saisi (l.387). Aussi `tests/test_courrier_boucle.py`, `tests/test_ops3_courrier_zone.py` (zone servie = zone écran).
- **Non vérifié par aucun test** : l'ENVOI RÉEL via Merci Facteur (tout en stub) ; la cohérence prix 2,50 € vs coût 2,69 € × marge 1,5 ; que le délai « 3 à 5 jours » corresponde à un vrai délai postal.

## 8. Les documents liés (PDF, exports)
Le PDF (`POST /courrier/pdf`, `api/courrier.py` l.511-635) et l'aperçu écran (`POST /courrier/composer`) lisent **le même module** `courrier_compose.composer` (commentaires l.414-418 et l.513-516 : « le front et l'admin appellent CE endpoint → le même PDF »). Donc PDF = aperçu = même source, mêmes valeurs (recto A→E + verso synthèse). Le PDF ajoute un en-tête destinataire résolu (même `resoudre_destinataire`), le pied avec la mention STOP et la mention LABUSE/outil. Aucun placeholder `{…}` ne subsiste (garde `corps_a_placeholders`, courrier.py l.151). Vérifié : le PDF anonyme pèse 8983 octets, 1 page = la page de REFUS « Courrier non généré / Renseignez le nom de votre société » (pas de nom de compte en curl).

## 9. Trois cas rejoués
Sur les 3 parcelles témoins. L'ADRESSAGE a été rejoué réellement via `POST /courrier/adressage` (lecture seule) ; la COMPOSITION via appel direct `courrier_compose.composer` avec la marque du compte #30 (SCCV Horizon Austral) car la composition exige un expéditeur nommé (le curl anonyme est refusé). AUCUN envoi, aucune demande créée.

**97411000BZ1065 (Saint-Denis)** — adressage : type `occupant`, destinataire « À l'occupant », adresse « 3 Chemin de la Citerne, 97417 Saint-Denis », non bloqué. Composition : ouverture **B** (bâtie, zone calibrée), réf « BZ 1065 ». Verso : surface cadastrale **1 567 m²**, zone **Uh**, « **30 mutations publiées** dans le périmètre analysé sur **2024-2025** ».

**97409000AK0804 (Saint-André)** — adressage : type `siege`, destinataire « **COMMUNE DE SAINT ANDRE** » (personne morale), mention « au nom du propriétaire, à l'adresse du bien », adresse « 524 Rue Jean Jacques Rousseau, 97440 Saint-André », non bloqué. Composition : ouverture **B**, réf « AK 0804 ». Verso : surface **27 862 m²**, zone **UB**, « **41 mutations publiées** sur **2023-2025** ». (PM sans siège SIRENE enrichi → adressée à son nom à l'adresse du bien, cf. adressage l.95-99.)

**97415000DH0076 (secteur sud)** — la parcelle est en commune **Saint-Paul** (et non Saint-Pierre/-Joseph comme suggéré : adresse « 104 Avenue de Bourbon, 97434 Saint-Paul »). Adressage : type `occupant`, « À l'occupant », non bloqué. Composition : ouverture **B**, réf « DH 0076 ». Verso : surface **19 513 m²**, zone **U2b**, « **58 mutations publiées** sur **2023-2025** ».

Aucun des 3 témoins n'est bloqué (tous bâtis, adressés). Témoin adapté : aucun — les 3 ont du sens pour l'outil.

## 10. Tes doutes (du plus grave au moindre)
1. **Incohérence prix / coût / marge, invisible.** Le coût prestataire servi (`/courrier/admin/config`) est **2,69 €** et la marge **1,5** (→ 4,035 € « hérité »), mais le prix CLIENT servi est **2,50 €** PLAT (config.py l.213), soit UNDER le coût prestataire. Le commentaire « prix = coût × marge si prix client non fixé » (l.210) est donc mort : `tarif()` sert toujours 2,50 € quoi qu'il arrive. Un gérant qui change le coût via l'admin ne change RIEN au prix facturé — risque de vendre à perte sans le voir.
2. **Service « indisponible » mais la demande part quand même.** `provider=stub` → `disponible:false`, aucun envoi réel ; pourtant « Demander l'envoi » enregistre la demande et notifie Vic. La chaîne repose ENTIÈREMENT sur un geste manuel de Vic (rappeler, confirmer le tarif, poster). Si Vic ne traite pas, le courrier ne part jamais — et le client a vu « demande transmise ».
3. **Zone PLU potentiellement obsolète.** La zone est lue via `zone_dominante` + `parcel_zone_plu` (compose l.108-116) ; sur une parcelle re-zonée récemment, si `parcel_zone_plu` n'a pas basculé, le courrier affirme une zone périmée au propriétaire (le code note explicitement l'historique « courrier-zone-bizone », l.102-107).
4. **Le délai « 3 à 5 jours » n'est pas sourcé d'un vrai suivi postal.** C'est une constante de config (l.214), affichée comme un engagement ; aucun test ni donnée ne garantit ce délai réel (surtout depuis La Réunion vers la métropole/DOM).
5. **Oppositions purement internes.** Seules les oppositions saisies à la main par Vic bloquent ; un propriétaire opposé par un autre canal (téléphone, courrier papier non saisi) n'est pas protégé. Et la normalisation d'adresse (`normaliser_adresse`, courrier.py l.157) doit matcher exactement l'adresse BAN servie, sinon un « 12, Rue du Port » opposé ne bloque pas un « 12 RUE DU PORT ».

---
### Synthèse INDEX
- Fiche écrite : `docs/audit-2026-11/outils-fiches-1/courriers.md` (outil M09 « Courrier propriétaire », clé `courriers`).
- Outil = SERVICE d'envoi en 3 étapes (Destinataires → Relecture → Envoi) : le client prépare, LABUSE poste à la main. Provider `stub` → aucun envoi auto aujourd'hui.
- Données lues : `parcels`, `parcel_filtre_bati`, `parcelle_personne_morale`, `owner_enrichment` (SIRENE siège), `parcel_adresse` (BAN), `zone_servie`/`parcel_zone_plu` (PLU), `dvf_mutations_parcelle` (DVF 2026-S1), `dryrun_cascade_results` (risques), `courrier_opposition`.
- Composition déterministe (ouverture A→E selon les faits, `courrier_compose.py`) : PDF et aperçu écran lisent le MÊME module → cohérents.
- Part sourcée vs estimée : ~90 % SOURCÉ (tout le contenu du courrier vient de données en base/API traçables). Les seuls « estimés/config » : prix 2,50 € / coût 2,69 € / marge 1,5 / délai « 3 à 5 » / plafond 100 / seuil DVF 8 — valeurs commerciales ou barèmes internes, aucune invention de potentiel.
- 3 témoins rejoués réellement (adressage via curl, compose via Python compte #30) : BZ1065 Saint-Denis (occupant, Uh, 1 567 m², 30 mut.), AK0804 Saint-André (PM « COMMUNE DE SAINT ANDRE », UB, 27 862 m², 41 mut.), DH0076 **Saint-Paul** (occupant, U2b, 19 513 m², 58 mut.) — tous ouverture B, aucun bloqué.
- Prix/délai RÉELS servis par `/courrier/statut` : **2,50 € par courrier**, **délai « 3 à 5 » jours**, plafond 100/jour. Config : `src/labuse/config.py` l.209-215.
- Coût total = prix unitaire × N destinataires (`courrier.py` l.690) — mais l'écran M09 n'affiche que le prix unitaire, pas de total.
- Doute le plus grave : **incohérence prix/coût/marge invisible** — le prix client servi (2,50 €) est figé en config, inférieur au coût prestataire (2,69 €), et le calcul « coût × marge 1,5 » documenté n'est plus jamais appliqué ; changer le coût admin ne change pas le prix facturé.
