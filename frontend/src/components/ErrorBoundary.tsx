import { Component, type ReactNode } from 'react'

interface State {
  error: Error | null
}

/** Filet global : jamais d'écran noir. Affiche l'erreur + un bouton de rechargement. */
export class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  render() {
    if (!this.state.error) return this.props.children
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-bg p-8">
        <div className="max-w-md rounded-xl border border-line-2 bg-surface-2 p-6 text-center">
          <p className="font-display text-lg font-bold text-st-ecartee">Une erreur est survenue</p>
          <p className="mt-2 break-all font-mono text-[11px] text-txt-mut">{this.state.error.message}</p>
          <p className="mt-3 text-xs text-txt-dim">
            Si le problème persiste après rechargement, relancer le serveur (`labuse api`) — un
            serveur périmé est la cause la plus fréquente.
          </p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 rounded-lg bg-mint px-4 py-1.5 text-xs font-medium text-mint-ink"
          >
            Recharger
          </button>
        </div>
      </div>
    )
  }
}
