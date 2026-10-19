import { lazy, Suspense, useEffect, useRef, useState } from 'react'
import { api } from '../../shared/api'
import type { VoiceStatus } from '../../shared/api'
import { VoiceDictation } from './VoiceDictation'
import type { DictationProps } from './VoiceDictation'

const VoiceServerDictation = lazy(() => import('./VoiceServerDictation')
  .catch(() => ({ default: VoiceDictation })))

/** An older or disabled backend keeps the existing browser transport. Status
 * discovery never opens the microphone or interrupts capture in progress. */
export function VoiceInput({ sessionId, ...props }: DictationProps & { sessionId?: string }) {
  const [status, setStatus] = useState<VoiceStatus | null>(null)
  const pending = useRef<VoiceStatus | null>(null)
  const active = useRef(false)
  useEffect(() => {
    let disposed = false
    setStatus(null)
    pending.current = null
    if (sessionId) void api.voiceStatus().then((next) => {
      if (disposed || !next?.enabled || !next.available) return
      if (active.current) pending.current = next
      else setStatus(next)
    }).catch(() => { /* Browser speech remains available when discovery fails. */ })
    return () => { disposed = true }
  }, [sessionId])
  const onActiveChange = (value: boolean) => {
    active.current = value
    props.onActiveChange?.(value)
    if (!value && pending.current) {
      setStatus(pending.current)
      pending.current = null
    }
  }
  return status && sessionId
    ? <Suspense fallback={<VoiceDictation {...props} disabled />}><VoiceServerDictation key={`${sessionId}:${props.language}`}
      {...props} sessionId={sessionId} status={status} onActiveChange={onActiveChange} /></Suspense>
    : <VoiceDictation {...props} onActiveChange={onActiveChange} />
}
