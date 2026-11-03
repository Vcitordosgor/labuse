"""JOHN-TAYLOR-1 — le second de bord de LABUSE (agent d'exploitation).

John Taylor, nommé d'après le second du pirate La Buse, est l'agent qui VOIT l'exploitation (jobs,
incidents, sources, runs, contrôles, sauvegardes, Radar, journaux, carnet de bord, rapports), RÉPOND
à Vic dans l'onglet « John Taylor » de la page Données (admin seul), AGIT sur ordre de Vic dans une
LISTE FERMÉE d'actions (jamais de sa propre initiative), écrit le RÉSUMÉ DU MATIN, mène la VEILLE de
nuit et ENQUÊTE sur un incident.

Règle d'or (identique au Copilote) : John ne fabrique rien. Une affirmation sans donnée est refusée.
Pas de shell, pas de SQL libre, aucune écriture hors de la liste fermée d'actions, aucun secret ni
donnée de client envoyé à l'API.

Modules :
  · budget   — le plafond mensuel de coût (défaut 50 €) ; au plafond, John est en pause.
  · journal  — chaque action journalisée (heure + compte).
  · carnet   — le carnet de bord en base (décisions de Vic, incidents passés, doctrines).
  · contexte — les lectures (jobs, incidents, sources, runs, contrôles, sauvegardes, Radar, journaux).
  · outils   — les outils de lecture exposés au modèle (schémas + aiguillage).
  · actions  — la LISTE FERMÉE des actions ; deux demandent « tu confirmes ? ».
  · chat      — l'orchestration du chat (boucle outils, anti-invention, budget).
  · resume    — le résumé du matin (07h30), écrit par John ; repli sur le résumé actuel.
  · veille    — la veille de nuit (réglementaire, sources, concurrence) — informe, n'injecte rien.
  · enquete   — l'enquête sur un incident (cause probable + correction, ou mandat Claude Code).
"""
