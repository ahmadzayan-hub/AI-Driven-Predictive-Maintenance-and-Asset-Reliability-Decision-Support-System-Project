import { createContext, useContext } from 'react'

// True in the view-only demo (ADR 2026-10-21 view-only demo mode): views
// hide the controls that would write, since the server refuses them.
// Defaults to false, so a view rendered on its own behaves as before.
export const ReadOnlyContext = createContext(false)

export function useReadOnly(): boolean {
  return useContext(ReadOnlyContext)
}
