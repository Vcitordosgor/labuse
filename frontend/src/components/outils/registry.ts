// Registre des modules outils — « filtres savants ». Couleur module : VIOLET (doctrine).
export const VIOLET = '#B497F0'
export const VIOLET_DIM = '#8b76c0'

export interface ModuleDef {
  key: string
  num: string
  label: string
  desc: string
}

export const MODULES: ModuleDef[] = [
  { key: 'division', num: 'M01', label: 'Division parcellaire', desc: 'Maisons sur grand terrain : lot détachable dessiné' },
  { key: 'patrimoine', num: 'M02', label: 'Scan patrimoine', desc: 'Un propriétaire → tout son foncier scoré' },
  { key: 'permis', num: 'M03', label: 'Radar permis', desc: 'Sitadel par commune et période' },
  { key: 'promesses', num: 'M04', label: 'Promesses mortes', desc: 'PC anciens jamais réalisés' },
  { key: 'velocite', num: 'M05', label: 'Vélocité admin', desc: 'Rythmes d’instruction par commune (île)' },
  { key: 'bailleur', num: 'M06', label: 'Mode bailleur', desc: 'Gisement LLS : QPV, TVA réduite' },
  { key: 'fantome', num: 'M07', label: 'Foncier fantôme', desc: 'Constructible mais verrouillé (PM introuvable…)' },
  { key: 'temps', num: 'M08', label: 'Remonter le temps', desc: 'Comparateur 1950 ↔ aujourd’hui' },
  { key: 'courriers', num: 'M09', label: 'Courrier propriétaire', desc: 'Courriers types par lot (pipeline/sélection)' },
  { key: 'duediligence', num: 'M10', label: 'Due diligence', desc: 'Liste de références → rapport multi-parcelles' },
  { key: 'simulplu', num: 'M15', label: 'Simulateur PLU', desc: '« Et si cette zone AU passait en U ? » (à blanc)' },
  { key: 'assemblage', num: 'M16', label: 'Assemblage', desc: 'Sélection contiguë → assiette fusionnée' },
  { key: 'zan', num: 'M17', label: 'Simulateur ZAN', desc: 'Artificialisation par commune, parcelles compatibles' },
  { key: 'barometre', num: 'M18', label: 'Baromètre foncier', desc: 'Rapport trimestriel île entière + PDF' },
  { key: 'matching', num: 'M19', label: 'Matching promoteurs', desc: 'Critères enregistrés → alertes quand ça matche (démo)' },
  { key: 'programme', num: 'M22', label: 'Faisabilité programme', desc: 'Un programme → les parcelles qui peuvent l’accueillir' },
]
