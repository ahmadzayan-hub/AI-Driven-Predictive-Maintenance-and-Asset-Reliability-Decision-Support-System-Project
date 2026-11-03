import { createContext, useContext } from 'react'

/** A question a screen section hands to Jarvis (ADR 2026-11-03-generative-layout).
 *  It only fills Jarvis's draft for the current selection; the reader still asks. */
export const JarvisPromptContext = createContext<((text: string) => void) | null>(null)
export const useJarvisPrompt = () => useContext(JarvisPromptContext)
