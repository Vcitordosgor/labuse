type Acte = Record<string, any>

export function actesParParcelle(data?: Record<string, unknown>) {
  const directs = (data?.rattaches ?? []) as Acte[]
  const cle = (a: Acte) => `${a.nature}-${a.permit_id}`
  const dejaCites = new Set(directs.map(cle))
  const voisins = ((data?.items ?? []) as Acte[]).filter(a => !dejaCites.has(cle(a)))
  return { directs, voisins, tous: [...directs, ...voisins] }
}

const dateReunion = new Intl.DateTimeFormat('sv-SE', { timeZone: 'Indian/Reunion' })

export function agePermis(date?: string, maintenant = new Date()) {
  if (!date || !/^\d{4}-\d{2}-\d{2}/.test(date)) return null
  const jour = dateReunion.format(maintenant)
  return Number(jour.slice(0, 4)) - Number(date.slice(0, 4)) -
    Number(jour.slice(5) < date.slice(5, 10))
}

export function surfacesPermis(fiche: Acte): { label: string; valeur: string }[] {
  return (fiche.surfaces_plancher_creees ?? []).map((s: { destination: string; m2: number }) => ({
    label: s.destination.startsWith('dont ') ? s.destination : `Plancher créé · ${s.destination}`,
    valeur: `${s.m2.toLocaleString('fr-FR', { maximumFractionDigits: 3 })} m²`,
  }))
}

export function adressePermis(adresse?: string) {
  if (!adresse) return ''
  // Certains libellés du CSV contiennent des caractères de contrôle irrécupérables.
  if (/[\u0080-\u009f\uFFFD]/u.test(adresse)) return 'Libellé illisible dans Sitadel'
  return adresse
}
