import { useCallback, useState } from 'react'

function read(key: string, fallback: string): string {
  try {
    return window.localStorage.getItem(key) ?? fallback
  } catch {
    return fallback
  }
}

/** A string remembered per browser (e.g. the reviewer's name). Storage failures are ignored. */
export function useLocalStorage(key: string, fallback = ''): [string, (value: string) => void] {
  const [value, setValue] = useState(() => read(key, fallback))
  const set = useCallback(
    (next: string) => {
      setValue(next)
      try {
        window.localStorage.setItem(key, next)
      } catch {
        /* private mode or blocked storage: keep the in-memory value */
      }
    },
    [key],
  )
  return [value, set]
}
