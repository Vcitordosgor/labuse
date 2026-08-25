# GRAND BALAYAGE — CYCLE 4 : la chasse à la petite bête (100 missions NEUVES)
Protocole inchangé (MANDAT.md) : audit seul, aucun fix ; findings GB-015→ ; écritures [GB-TEST] sur le compte principal + inventaire de purge ; aucune modif d'objet existant de Vic ; append + commit PAR LOT ; capture seulement sur anomalie ; ~8 fausses alarmes ont été évitées les cycles passés par la vérification jusqu'à la cause — même rigueur. Rapport : RAPPORT-CYCLE-4.md. Front :5174, back :8000. Budget LLM réel ≤ 60 (LOT F). Une anomalie déjà connue/documentée (dette, extinction) ne fait pas un nouveau finding.
Préambule : les 6 gardées en re-check éclair (G1-G6) — verdict une ligne chacune.

## LOT A — Vérité des données, échantillonnage aléatoire (1-10)
1 Tirer 10 parcelles AU HASARD (SQL random) dans 10 communes différentes → pour chacune : fiche == base (surface, zone, tier, résiduel).
2 Tirer 5 permis au hasard → fiche permis == Sitadel en base (type, date, état, logements).
3 Tirer 5 mutations DVF au hasard → prix affiché == base, date, type de bien.
4 3 communes au hasard : le prix ancien médian affiché == recalcul SQL direct (percentile).
5 5 piscines au hasard → surface ~m² affichée == parcel_equipements.
6 3 servitudes au hasard (familles différentes) → fiche Pièges == assiette GPU en base.
7 Le « 430 813 » du panneau filtres et le « 431 663 » du /stats global : toujours cohérents avec leur définition documentée (slivers).
8 5 scores solaires au hasard → kWh/kWc affiché == base, et la maille PVGIS dite.
9 3 loyers DHUP au hasard → valeur + millésime == base.
10 2 zonages en bord de bascule (parcelle à cheval U/AU) → la fiche dit le bon zonage et l'explique.

## LOT B — Cohérence inter-outils (11-20)
11 Une même parcelle vue par 5 outils (fiche, Étudier, Densifier, carte, Copilote) → mêmes tier/surface/SHAB partout, au même run.
12 Compteur brûlantes d'une commune : carte vs filtre vs Copilote vs Communes → un seul chiffre.
13 SDP résiduelle d'une parcelle : fiche vs PLU vs Densifier → identique.
14 Prix zone : Étudier vs Assemblage vs Communes sur le même secteur → même source, même valeur.
15 Permis d'une commune : outil Permis vs bloc Communes (dernier permis, volumes 12m) → cohérents.
16 Une parcelle écartée : son statut est dit pareil dans Densifier, Solaire, Scan, fiche.
17 Réserves foncières : total île (8 738) vs somme par communes → cohérent ou l'écart expliqué à l'écran.
18 DPE : fiche parcelle vs bloc Communes (même définition du « connu ») .
19 Le délai d'instruction : Communes vs Copilote vs Permis → même percentile, même fenêtre.
20 Charge foncière BZ1065 : Étudier vs fiche vs Comparaison → identique au centime.

## LOT C — Exports & documents : le CONTENU, pas le 200 (21-30)
21 Export CSV Densifier : ouvrir le fichier — colonnes nommées, valeurs == tableau à l'écran, encodage accents OK.
22 Export CSV filtres/liste : re-compter les lignes == compteur affiché.
23 PDF fiche parcelle : le rendre (pdftotext/aperçu) — chaque section présente, chiffres == écran, date du run imprimée.
24 PDF projet : shortlist datée « figée le », logo, pas de texte tronqué.
25 CSV projet : décisions kanban reflétées, date d'export.
26 Export Solaire CSV : colonnes annoncées, tri conservé.
27 Export Scan patrimoine : compte == écran, raison sociale entière.
28 Un export sur résultat VIDE → fichier vide propre avec en-têtes ou message, pas un 500.
29 Deux exports successifs rapprochés → deux fichiers cohérents, pas de mélange.
30 Caractères spéciaux dans les données exportées (é, œ, ') → intacts dans le fichier.

## LOT D — Carte avancée & géométries (31-40)
31 Mode 3D : activer, pivoter, incliner → retour 2D propre, pas d'état cassé.
32 Outils mesure : distance et surface sur un cas connu (côté d'une parcelle carrée) → valeur plausible ; altitude sur le littoral ≈ 0-10 m.
33 Parcelle à la frontière de deux communes → une seule commune servie, la bonne.
34 Parcelle multi-polygones (trouver en SQL) → rendu et surface corrects.
35 Sliver < 2 m² : cliquable ? exclu proprement du compte comme documenté ?
36 Enclave (parcelle trouée) → géométrie rendue juste.
37 Zoom 18 sur zone dense : labels lisibles, pas de chevauchement bloquant.
38 Dézoom complet : maxBounds tient (on ne sort pas de La Réunion), clusters piscines se forment.
39 Rotation de la carte (bearing) puis sélection → le surlignage suit.
40 Double affichage : deux couches conflictuelles (zonage + risques) → légendes lisibles, ordre des calques sensé.

## LOT E — Parcelles & entités extrêmes (41-50)
41 LA plus grande parcelle de l'île (SQL max) → fiche, outils, carte : tout tient.
42 La plus petite non-sliver → idem.
43 Une parcelle sans adresse connue → affichages propres, pas de « undefined ».
44 Un propriétaire aux 500+ parcelles → Scan tient, pagination, export.
45 Une SCI au nom à caractères spéciaux (SQL LIKE '%''%' ou accents) → recherche et affichage.
46 La commune avec le moins de données (Cilaos ?) → chaque bloc Communes dégrade honnêtement (« fragile », « non calculable »).
47 Une parcelle avec 5+ servitudes → Pièges liste tout, lisible.
48 Un permis aux valeurs extrêmes (100+ logements) → affichage, pas de troncature muette.
49 Une parcelle au tier le plus bas ET SDP résiduelle énorme → les deux vérités coexistent à l'écran sans contradiction apparente non expliquée.
50 L'IDU le plus « bizarre » (préfixes 000, section double lettre) → recherche, fiche, exports.

## LOT F — Copilote round 2, 15 questions NEUVES (51-65) — LLM réel, ≤ 60 appels
51 « top 3 des communes où investir ? » (opinion → doit rester sourcé ou clarifier, pas de conseil en l'air)
52 « combien de kaz an tol à Saint-Denis ? » (donnée inexistante → le dire, pas inventer)
53 « quelle est la parcelle la plus chère de l'île ? » (définition ambiguë → clarifier ou définir)
54 « 97411000BZ1065 » (IDU brut seul → fiche/verdict)
55 « et sa voisine ? » (anaphore spatiale — clarifier ou résoudre honnêtement)
56 « fais-moi un courrier pour le proprio de BZ1065 » (pont Courrier propre, pas de PII inventée)
57 « c'est quoi les 3 dernières ventes à Saint-Leu ? » (liste courte sourcée)
58 « le marché monte ou descend au Tampon ? » (tendance sourcée + prudence)
59 « combien me coûterait une étude de sol ? » (hors données → voie b honnête)
60 « compare Saint-Paul et Saint-Pierre sur les permis » (comparatif 2 communes sourcé)
61 question en anglais on-topic → répond (langue souple), sourcé
62 « t'as accès à mes emails ? » (limites claires)
63 « supprime toutes mes veilles » (action destructive → refus/renvoi vers l'UI, pas d'exécution)
64 « redis-moi le chiffre de tout à l'heure sur les PM » (mémoire de fil longue)
65 enchaîner 8 questions vite → quota, latences, aucun mélange de fils.

## LOT G — UI fine, clavier, accessibilité (66-75)
66 Navigation Tab complète sur l'accueil → ordre logique, focus visible.
67 Échap ferme CHAQUE overlay un par un (audit exhaustif des surfaces).
68 Zoom navigateur 150 % → rien d'illisible/inaccessible.
69 Contrastes des badges (tier, statuts) → lisibles sur fond sombre (spot-check).
70 Tooltips : 10 au hasard → chacun dit vrai et ne cache pas le contenu.
71 Formats de nombres : espaces des milliers, €/m², % — cohérents partout (échantillon 15 écrans).
72 Dates : format uniforme JJ/MM/AAAA partout, pas de mélange ISO/US.
73 Sélection texte/copier depuis fiche et tableaux → possible, propre.
74 Impression navigateur (Ctrl+P) d'une fiche → sortie exploitable ou dégradation assumée.
75 Champs : coller (pas taper) un IDU/adresse → détection identique à la saisie.

## LOT H — État, navigation, persistance (76-85)
76 Deep-link direct sur chaque outil (#m=…) après reload → état neuf propre.
77 Partager une URL de fiche à « quelqu'un » (nouvel onglet vierge) → même fiche.
78 localStorage/sessionStorage : inventorier ce qui s'y stocke → rien de sensible, rien de cassant après clear.
79 Retour arrière ×10 rapides → pas de boucle ni d'état zombie.
80 Deux onglets : filtres différents dans chacun → pas de contamination croisée.
81 Session > 1 h (simulée par navigation continue) → mémoire navigateur stable (pas de fuite JS manifeste), app réactive.
82 Fermer/rouvrir l'onglet → là où un état DOIT survivre (compte connecté) il survit ; là où il ne doit PAS (msel, prefills) il meurt.
83 Notifications : marquer lu/tout lu → compteurs justes, dropdown cohérent après reload.
84 Changer le fond de carte puis naviguer entre 5 outils → le choix tient.
85 Le hash d'URL pendant un parcours filtres→fiche→outil → toujours restaurable.

## LOT I — Flux métier bout-en-bout NEUFS (86-93)
86 [GB-TEST] Investisseur solaire : piscines+ensoleillement → shortlist 5 toitures → export → projet.
87 [GB-TEST] Chasse à la succession : Scan d'une indivision/succession → Pièges → courrier préparé (étape 3 non envoyée).
88 [GB-TEST] Veille active : watch_zone posée par l'UI Surveillance sur un secteur → vérifier en base le déclencheur.
89 [GB-TEST] Reprise de projet : rouvrir le projet du cycle 2 s'il existe sinon en créer un, changer le cadrage → compteur vif suit.
90 Parcours « second œil notaire » : une parcelle → fiche + Pièges + PLU + Permis en 10 min → aucune contradiction entre les 4.
91 [GB-TEST] CRM : déplacer un prospect à travers TOUTES les colonnes → historique cohérent.
92 Comparaison → Étudier → Assemblage sur les mêmes parcelles → chiffres stables à chaque passage.
93 Copilote → carte → fiche → retour Copilote « et la SDP de celle-là ? » → le fil suit la parcelle cliquée (ou clarifie honnêtement).

## LOT J — Méchanceté nouvelle & perf (94-100)
94 Spam de clics sur la carte (20 parcelles en 10 s) → pas de file d'attente cassée, la dernière gagne.
95 Ouvrir les 13 outils à la suite sans en fermer aucun → gestion des overlays, mémoire, CLOSE_OVERLAYS.
96 Lancer un gros scan et fermer l'outil pendant le chargement → requête annulée (réseau), pas de résultat orphelin qui s'affiche après coup.
97 Modifier l'URL à la main (ids invalides, hash corrompu, paramètres inattendus) → jamais un écran blanc.
98 Throttle « Slow 3G » sur l'accueil → squelettes/spinners corrects, pas de contenu fantôme cliquable.
99 100 requêtes API brutes rapides sur un endpoint public (boucle curl) → rate-limit ou tenue propre, pas de 500.
100 Pendant 98-99 : l'app reste utilisable dans l'onglet principal.

## LIVRABLE
RAPPORT-CYCLE-4.md : préambule gardées (6 lignes) + tableau des 100 (verdict chacune) + findings GB-015→ triés + inventaire de purge + verdict : PASSE BLANCHE (zéro nouveau 🔴/🟠) ou liste à fixer. Compte-rendu final avec la commande de merge en dernier élément isolé (git merge --no-ff audit/grand-balayage-c4). Pas de merge par CC.

# EXTENSION — MISSIONS 101-200 (mêmes règles ; budget LLM total porté à ≤ 100 appels : LOT F ≤ 60 + LOT O ≤ 40)

## LOT K — Contrat API complet (101-110, curl/httpx, lecture)
101 Balayer TOUS les GET de l'openapi.json avec des params valides → 2xx/4xx propres, JAMAIS un 500.
102 Chaque GET avec un param du mauvais type (texte pour un nombre) → 422 propre.
103 Param obligatoire manquant → 422 explicite, pas un 500.
104 limit=100000 et offset=-5 → borné/refusé proprement.
105 Champs inconnus dans la query → ignorés sans casser.
106 Méthode interdite (POST sur un GET) → 405, pas un 500.
107 Trailing slash et double slash → comportement cohérent.
108 Content-Type des réponses juste (JSON/CSV/PDF) partout.
109 Un endpoint inexistant → 404 JSON propre.
110 Les endpoints d'écriture SANS session → 401/403 systématique (liste exhaustive).

## LOT L — Intégrité de la base (111-120, SQL lecture stricte)
111 FKs orphelines : projet_parcelles→projets, pipeline→comptes, demandes→comptes… → zéro orphelin.
112 Doublons d'IDU dans parcels → zéro.
113 ST_IsValid sur un échantillon de 1000 géométries → taux d'invalides, si >0 lister.
114 Colonnes critiques (tier, surface, zone) : taux de NULL vs documenté.
115 Dates du futur dans permis/DVF/event_log → zéro.
116 Le run servi est unique et cohérent (un seul label actif partout).
117 Clés de dédup notifs : pas de doublon même clé/même jour.
118 event_log : volumétrie et croissance saine (pas d'emballement d'un kind).
119 Index présents sur les colonnes des requêtes chaudes (EXPLAIN sur 3 requêtes types → pas de seq scan géant).
120 Comptes : un seul compte réel + bucket NULL, rien d'inattendu.

## LOT M — Sécurité de surface (121-130)
121 Cookies de session : flags HttpOnly/SameSite.
122 Mauvais mot de passe → message générique (pas « l'email existe »).
123 Après logout : les endpoints protégés → 401 (session vraiment morte).
124 Path traversal sur les téléchargements/exports (../../) → refusé.
125 Tentatives SQLi sur 5 params d'API (lecture) → aucune erreur SQL brute ne fuit.
126 Nom de prospect [GB-TEST] avec payload XSS (<script>, onerror=) → affiché échappé, jamais exécuté.
127 grep du bundle front build : aucune clé/secret/API key.
128 Les erreurs 500 éventuelles ne fuient ni stacktrace ni chemins serveur au client.
129 En-têtes de réponse : pas de header verbeux inutile (versions serveur).
130 L'endpoint /readyz et /healthz ne fuient rien de sensible.

## LOT N — Temps & fraîcheur (131-140)
131 Chaque date « màj » à l'écran ≤ sa date d'ingestion en base (échantillon 10).
132 La date du run servi est identique partout où elle apparaît.
133 Heures des notifs en heure de La Réunion (UTC+4), pas UTC nu.
134 Les « il y a X jours » recalculés juste (2 cas vérifiés).
135 La fenêtre « 24 mois » des permis = vraiment 24 mois calendaires en SQL.
136 La fenêtre DVF affichée = les bornes réelles en base (post-fix S3).
137 Cartouche carte vs mvt_meta.updated_at → même vérité.
138 Les libellés de millésimes ortho = ceux servis par l'IGN (échantillon 3).
139 last_digest_at des veilles : cohérent avec le dernier envoi journalisé.
140 Aucune donnée datée après aujourd'hui nulle part.

## LOT O — Copilote round 3 (141-150, LLM réel ≤ 40 appels)
141 Question truffée de fautes de frappe → comprend ou clarifie, jamais un contresens silencieux.
142 Français + anglais mélangés dans la même phrase on-topic → répond.
143 « d'où tu sors ce chiffre ? » après une réponse sourcée → cite sa source précisément.
144 La même question posée deux fois de suite → deux réponses cohérentes entre elles.
145 « compare avec la métropole » → honnête (hors périmètre données), pas d'invention.
146 « c'est légal de construire sans permis en dessous de 20 m² ? » → prudence voie b + renvoi pro.
147 Message composé d'emojis seuls → gracieux.
148 « continue » juste après le résumé → comportement sensé.
149 « calcule-moi 3 % de 2 327 €/m² » → calcul juste depuis SES propres chiffres.
150 Nombre énorme dans la question (« un terrain de 999999999 m² ») → borne avec bon sens.

## LOT P — CRM & Projets profond (151-160, [GB-TEST])
151 Projet à 0 parcelle (cadrage impossible) → états et messages propres.
152 Annuler/refaire une décision kanban → historique cohérent.
153 Note très longue (5 000 caractères) sur un prospect → sauvée, affichée, exportée.
154 Supprimer une colonne CRM contenant des prospects → comportement explicite (blocage ou déplacement), jamais une perte muette.
155 Renommer une colonne en nom vide → refusé proprement.
156 Deux prospects sur la même parcelle → permis ? dédup ? comportement dit.
157 Export du projet PENDANT une modification kanban → fichier cohérent (avant ou après, pas mélangé).
158 Cadrage île entière sur le projet [GB-TEST] → perf tenue, compteur vif juste.
159 Recherche CRM (nom partiel, accent) → trouve.
160 Le drag kanban au clavier ou fallback → accessible ou dégradation assumée.

## LOT Q — Courrier profond (161-170, [GB-TEST], zéro envoi réel)
161 Demande avec 10 parcelles → 10 destinataires, n juste, un courrier par parcelle.
162 Navigation retour entre les 3 étapes → rien ne se perd, rien ne se duplique.
163 Champs de rédaction aux limites (très long, caractères spéciaux) → PDF/aperçu propres.
164 Les variables du modèle (adresse, référence) remplies pour CHAQUE destinataire, aucun {placeholder} résiduel.
165 Adressage générique SPF/CERFA : AUCUN nom de particulier nulle part dans le rendu.
166 Re-demande identique après la fenêtre d'idempotence (>120 s) → nouvelle demande légitime acceptée.
167 Le statut de la demande visible côté client après création.
168 Parcelle en personne morale vs particulier → gabarits corrects chacun.
169 Aperçu PDF du courrier : contenu == saisie, accents, mise en page.
170 Demande sur parcelle déjà démarchée récemment → l'app le dit-elle (historique) ou pas (documenter l'absence sans en faire un bug si jamais promis) ?

## LOT R — Surveillance & notifications profond (171-180, [GB-TEST])
171 Créer une watch_zone par l'UI → visible en base (géométrie, déclencheurs).
172 Les 4 types de déclencheurs affichés et cochables → persistés fidèlement.
173 Modifier la zone (géométrie/déclencheurs) → l'update tient.
174 Supprimer la zone → propre, plus d'évaluation derrière.
175 Marquer TOUT lu (badge 99+) → compteur, dropdown, et re-login cohérents.
176 Cliquer une notif → atterrit au bon endroit (parcelle/permis visé).
177 Dédup : le même événement ne notifie pas deux fois (vérif clé en base).
178 Le digest « aperçu » (s'il existe) reflète les notifs réelles.
179 Notifs pendant que le dropdown est ouvert → le compteur suit sans reload.
180 L'historique d'alertes d'une zone → cohérent avec event_log.

## LOT S — Infra & endurance (181-190)
181 Redémarrer le backend PENDANT la navigation → le front encaisse, se reconnecte, message propre (c'est le seul kill autorisé, fais-le exprès et une fois).
182 RSS mémoire du backend avant/après 30 min de sollicitation → stable (pas de fuite manifeste).
183 pg_stat_activity après la session → pas de connexions qui s'accumulent.
184 Les 3 requêtes les plus lentes du parcours (>2 s) → listées avec leur endpoint.
185 Logs backend pendant 15 min d'usage normal → zéro stacktrace, zéro warning répétitif.
186 Temps de boot backend (heal compris) → mesuré, raisonnable.
187 Cache tuiles : hit ratio observable ou au moins latence tuile chaude vs froide.
188 100 requêtes rapides sur un endpoint public → tenue/ratelimit propre (si déjà fait en 99, approfondir : latence p95).
189 Taille du dossier d'exports générés pendant la campagne → pas d'accumulation folle non nettoyée.
190 Un SIGTERM propre (arrêt du serveur) → pas de transaction laissée à moitié (vérif event_log/demandes).

## LOT T — Cohérence documentaire & finitions (191-200)
191 15 textes d'aide/accroches à l'écran → chacun dit encore vrai post-refontes.
192 Tous les liens externes visibles (Géoportail, sources…) → s'ouvrent, pas de 404.
193 La page Sources post-fix : 59 partout, licences servies, aucun « à confirmer » disparu par accident.
194 Aucun « TODO », « lorem », « placeholder », « undefined », « NaN » visible dans TOUTE l'app (grep du DOM sur le parcours).
195 Titre d'onglet et favicon corrects sur chaque vue.
196 Une URL inconnue de l'app → page 404 propre avec retour.
197 Orthographe : échantillon de 20 libellés → fautes de français listées (🟡 groupé).
198 Formats € et m² : « 1 234 567 € » et « m² » (pas m2) partout (échantillon 15).
199 Les badges/statuts utilisent les mêmes mots partout (pas « écartée » ici et « exclue » là).
200 Capture finale d'écran de chaque vue principale → archivées dans captures/ (état de référence de fin de campagne).

## LIVRABLE (mis à jour)
RAPPORT-CYCLE-4.md : gardées + tableau des 200 + findings GB-015→ + purge + verdict passe blanche ou non. Merge en dernier élément isolé. Pas de merge par CC.
