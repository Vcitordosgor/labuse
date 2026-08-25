# GRAND BALAYAGE — CYCLE 2 (missions renouvelées ~50%)
Même protocole que le cycle 1 (voir MANDAT.md : audit seul, aucun fix, Playwright MCP, findings GB-xxx, commit par lot, [GB-TEST] + inventaire de purge, front :5174 back :8000). Numérotation GB-xxx CONTINUE (le cycle 1 s'est arrêté à GB-012 ; on démarre à GB-013). Rapport : RAPPORT-CYCLE-2.md.
Décision Vic : pas de compte de test — écritures sur le compte principal, préfixe [GB-TEST], inventaire de purge, aucune modif d'objet existant. M45 reste en scoping code (cloison compte_id vérifiée en base ; IDOR à deux comptes = dette au 2e client).

## GARDÉES — anti-régression (les missions qui ont trouvé un bug au cycle 1, doivent rester vertes)
G1. Courrier bout-en-bout [GB-TEST] : demande 3 étapes → 200, GET /courrier/demandes → 200, notif admin en event_log. (ex-GB-011, le 🔴 — la preuve que le heal tient.)
G2. /readyz dit vrai : schema.ok=true honnête ; provoque mentalement un module en échec et confirme qu'il basculerait 503 (lecture du code, pas de casse réelle).
G3. Scan patrimoine par sigle : « SHLMR », « SAFER » → raison sociale + compte == autocomplétion == scan (ex-GB-006/007).
G4. Filtre Communes : chips « Nom (code postal) » (ex-GB-008). Omnibox : réf. cadastrale en cours n'affiche plus « Aucune adresse » (ex-GB-009).
G5. msel purgé à la fermeture d'Assemblage ET de tout outil qui sélectionne (ex-GB-010, généralisé).
G6. Accueil : porte « 13 outils » == tiroir ; badge cloche « 99+ » (ex-GB-001/002).

## COMBLÉES — dettes du cycle 1
C1 (ex-M33). Copilote EN CONDITIONS RÉELLES (LLM branché cette fois) : 12 questions métier NEUVES, dont 3 enchaînées à anaphores, 1 hors-domaine, 1 « t'es sûr ? », 1 vocabulaire maison. Le LLM était offline au cycle 1 — c'est le vrai test. Budget appels réels ≤ 30.
C2 (ex-M45). IDOR : contrôle de scoping code sur CHAQUE ressource (projets, CRM, courrier, veilles, exports) — confirme que chaque requête porte compte_id. Note « à rejouer à deux comptes avant le 2e client ».

## NEUVES — ~50% renouvelées (autres communes / entreprises / enchaînements / adversités)
N1. 50 parcelles d'entreprises en liquidation à LE TAMPON + SAINT-BENOÎT (pas Saint-Paul/Denis) → liste exploitable.
N2. Patrimoine d'une grosse SCI et d'une SARL du BTP local (autres que SHLMR) → assiette d'assemblage sur 2 contiguës.
N3. Densifier SAINTE-MARIE : top 20, écartées incluses, 3 fiches ouvertes depuis le tableau.
N4. PLU : bascules AUs→U (pas AUc) d'une commune → agrégats stables en paginant.
N5. Faisabilité par critères : « 12 maisons individuelles sur 4 000 m² » (programme different du R+3) — cohérence SDP/logements.
N6. Étudier une parcelle de SAINT-LEU : bouger marge + VRD + prix terrain → le verdict suit dans le bon sens.
N7. Solaire ensoleillement sur 5 toitures d'une rue de SAINT-PIERRE : maille PVGIS dite partout, pas de fausse précision.
N8. Comparaison de 3 parcelles (pas 2) : stepper complet, double-Échap, retour propre.
N9. Projet complet [GB-TEST] à partir d'un cadrage SAINTE-SUZANNE : créer, décider 15 parcelles au kanban, rejouer le cadrage, exports PDF+CSV datés, compteur vif == ouverture (ex-P1 projets).
N10. CRM [GB-TEST] : prospect avec un nom en Unicode exotique (accents, apostrophe typographique, emoji) → création/affichage/renommage colonne [GB-TEST] propres.
N11. Permis : « au point mort » sur SAINT-ANDRÉ 48 mois → libellé honnête, ouverture de permis.
N12. Communes : comparer LE TAMPON / SAINT-BENOÎT / CILAOS (dont une petite commune) — chaque chiffre daté+sourcé, « fragile » quand n faible.

## ADVERSITÉ NOUVELLE (robustesse cycle 2)
A1. Concurrence : deux onglets ouverts sur le même projet [GB-TEST], écrire dans les deux → dernier gagne proprement, pas de corruption ni de doublon.
A2. Réseau lent simulé (throttle) : lancer un scan lourd puis naviguer ailleurs → pas d'état figé, annulation propre (AbortController).
A3. Dates/bornes : filtres de permis sur une fenêtre vide (commune × période sans permis) → « 0 » propre, jamais un écran cassé.
A4. Double-submit sur la demande Courrier [GB-TEST] (le heal est réparé — vérifier qu'un double-clic ne crée pas 2 demandes).
A5. F5 en plein cadrage projet + en pleine demande Courrier étape 2 → reprise propre.

## LIVRABLE
RAPPORT-CYCLE-2.md : registre GB-013→ trié par gravité + section « GARDÉES : régressions ? » (chaque G vert/rouge) + TOP des nouveaux findings + inventaire de purge. 
PASSE BLANCHE si : zéro nouveau 🔴 et zéro nouveau 🟠 sur tout le cycle (gardées comprises). Sinon → mandats de fix puis cycle 3.
Compte-rendu final avec la commande de merge en dernier élément isolé. Pas de merge par CC.
