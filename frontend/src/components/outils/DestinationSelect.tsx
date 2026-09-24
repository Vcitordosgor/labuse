// DESTINATIONS-1 (X4) — sélecteur « Activité (destination) » PARTAGÉ (Étude de zone · Faisabilité
// par critères) + badge d'état de verdict. Alimenté par le référentiel R151-27/28 SERVI (libellés
// officiels groupés par destination) — rien en dur au front. Optionnel : '' = aucune destination.
import { useQuery } from '@tanstack/react-query'
import { etudeZoneDestinationsRef } from '../../lib/api'
import { Badge, type BadgeTon } from '../ui/Badge'

export function useDestinationsRef() {
  return useQuery({ queryKey: ['destinations-referentiel'], queryFn: etudeZoneDestinationsRef, staleTime: Infinity })
}

export function DestinationSelect({ value, onChange, dataAttr }: {
  value: string | null; onChange: (slug: string | null) => void; dataAttr?: string
}) {
  const ref = useDestinationsRef()
  const d = ref.data
  return (
    <label className="block text-[11px] tracking-wide text-txt-dim">Activité (destination)
      <select data-destination-select={dataAttr ?? true} value={value ?? ''}
        onChange={(e) => onChange(e.target.value || null)}
        className="mt-0.5 h-8 w-full rounded-md border border-line-2 bg-surface-1 px-2 text-[11.5px] text-txt focus:border-mint focus:outline-none">
        <option value="">— toutes (facultatif) —</option>
        {(d?.destinations ?? []).map((g) => (
          <optgroup key={g.slug} label={g.libelle}>
            {(d?.sous_destinations ?? []).filter((s) => s.destination === g.slug).map((s) => (
              <option key={s.slug} value={s.slug}>{s.libelle}</option>
            ))}
          </optgroup>
        ))}
      </select>
    </label>
  )
}

// Badge d'état — DA-034 : trois tons du Badge partagé. autorisé = vert, sous condition = ambre,
// en cours de calibration = neutre. Le corail « interdit » PASSE EN AMBRE (pas de 4ᵉ ton). Accepte
// les états effectifs backend (autorise/sous_condition/interdit/en_cours_de_calibration/non_lu —
// non_lu ≡ calibration en cours).
const ETATS: Record<string, { label: string; ton: BadgeTon }> = {
  autorise: { label: 'autorisé', ton: 'vert' },
  sous_condition: { label: 'sous condition', ton: 'ambre' },
  interdit: { label: 'interdit', ton: 'ambre' },
  en_cours_de_calibration: { label: 'calibration en cours', ton: 'neutre' },
  non_lu: { label: 'calibration en cours', ton: 'neutre' },
}
export function DestinationBadge({ etat }: { etat: string | null | undefined }) {
  const e = ETATS[etat ?? ''] ?? ETATS.en_cours_de_calibration
  return (
    <Badge data-destination-etat={etat ?? 'inconnu'} ton={e.ton}>{e.label}</Badge>
  )
}
