/** Retry only the same creation request. Persist a digest and a random key,
 * never CSV, questions, assumptions or tokens. The scope is the active session.
 * Without Web Crypto/storage the live form still keeps its attempt in memory.
 */
export class CreationAttempt {
  private signature = ''
  private key = ''

  async forRequest(scope: string, payload: string): Promise<string> {
    const signature = JSON.stringify([scope, payload])
    if (this.signature === signature && this.key) return this.key
    const storageKey = `aos-draft:${scope}:analysis-attempt`
    let fingerprint: string | null = null
    try {
      const bytes = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(payload))
      fingerprint = Array.from(new Uint8Array(bytes), (byte) => byte.toString(16).padStart(2, '0')).join('')
    } catch { /* A non-secure development origin can use memory-only recovery. */ }
    let key: string = crypto.randomUUID()
    if (fingerprint) {
      try {
        const saved: unknown = JSON.parse(sessionStorage.getItem(storageKey) ?? 'null')
        if (saved && typeof saved === 'object' && 'fingerprint' in saved && 'key' in saved
          && saved.fingerprint === fingerprint && typeof saved.key === 'string'
          && /^[a-f0-9-]{36}$/.test(saved.key)) key = saved.key
        sessionStorage.setItem(storageKey, JSON.stringify({ fingerprint, key }))
      } catch { /* Storage refusal must not lose the current form's attempt. */ }
    }
    this.signature = signature
    this.key = key
    return key
  }

  complete(scope: string) {
    this.signature = ''; this.key = ''
    try { sessionStorage.removeItem(`aos-draft:${scope}:analysis-attempt`) } catch { /* memory cleared */ }
  }
}
