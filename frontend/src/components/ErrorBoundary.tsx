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
        <div className="floating max-w-md p-6 text-center">
          <span className="mx-auto mb-3 block h-1.5 w-8 rounded-full bg-st-ecartee/60" aria-hidden />
          <p className="font-display text-lg font-bold text-txt-hi">Une erreur est survenue</p>
          <p className="mt-2 break-all font-mono text-[11px] text-txt-mut">{this.state.error.message}</p>
          {/* Item 3 (UX V1) : wording client — le jargon « labuse api » disparaît de l'écran */}
          <p className="mt-3 text-xs text-txt-dim">
            Si le problème persiste après rechargement, vérifiez votre connexion réseau
            ou réessayez dans quelques instants.
          </p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 rounded-lg bg-mint px-4 py-1.5 text-xs font-medium text-mint-ink transition-[filter] duration-quick hover:brightness-110"
          >
            Recharger
          </button>
        </div>
      </div>
    )
  }
}
