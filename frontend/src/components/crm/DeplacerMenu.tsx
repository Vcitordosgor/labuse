// DA-FIX-5c — LE menu « Déplacer vers… » PARTAGÉ entre la carte du kanban CRM et le bloc CRM de la
// fiche parcelle. Même source de colonnes (meta.columns), même rendu, même composant : l'alternative
// au glisser-déposer. Dernière entrée « Retirer du CRM » (ton danger). Il REMPLACE l'ancien sélecteur
// d'étiquette de contact (doublon des colonnes) dans les deux endroits.
export const RETIRER = '__retirer__'

export function DeplacerMenu({ columns, currentStatus, onMove, onRetirer, className = '' }: {
  columns: { key: string; label: string }[]
  currentStatus?: string
  onMove: (status: string) => void
  onRetirer: () => void
  className?: string
}) {
  return (
    <select
      data-crm-move
      value=""
      onChange={(ev) => { const v = ev.target.value; if (v === RETIRER) onRetirer(); else if (v) onMove(v) }}
      aria-label="Déplacer la parcelle vers une autre colonne du CRM"
      className={`w-full cursor-pointer rounded-md border border-line-2 bg-surface-2 px-1.5 py-1 text-[10.5px] text-txt-dim focus:outline-none focus:ring-1 focus:ring-mint/50 ${className}`.trim()}
    >
      <option value="">Déplacer vers…</option>
      {columns.map((c) => (
        <option key={c.key} value={c.key} disabled={c.key === currentStatus}>{c.label}</option>
      ))}
      <option value={RETIRER} style={{ color: '#E8695A' }}>Retirer du CRM</option>
    </select>
  )
}

export default DeplacerMenu
