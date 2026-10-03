import { useEffect, useRef } from 'react'

export type HotkeyMap = Partial<Record<string, (event: KeyboardEvent) => void>>

function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false
  if (target.isContentEditable) return true
  const tag = target.tagName
  if (tag === 'TEXTAREA' || tag === 'SELECT') return true
  if (tag === 'INPUT') {
    const type = (target as HTMLInputElement).type
    return !['button', 'checkbox', 'radio', 'submit', 'reset'].includes(type)
  }
  return false
}

/**
 * Single-key shortcuts (e.g. j / k / Enter / a / r) that never fire while the user is typing
 * in a field or holding a modifier. Keys match `KeyboardEvent.key` ("j", "Enter", "Escape").
 * The handler map may change every render; only `enabled` re-subscribes.
 */
export function useHotkeys(map: HotkeyMap, enabled = true): void {
  const ref = useRef(map)
  useEffect(() => {
    ref.current = map
  })
  useEffect(() => {
    if (!enabled) return
    const onKey = (event: KeyboardEvent) => {
      if (event.defaultPrevented || event.repeat) return
      if (event.metaKey || event.ctrlKey || event.altKey) return
      if (isTypingTarget(event.target)) return
      const handler = ref.current[event.key]
      if (handler) handler(event)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [enabled])
}
