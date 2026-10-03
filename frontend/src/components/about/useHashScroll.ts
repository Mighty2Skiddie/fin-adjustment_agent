import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'

/**
 * Scrolls to the element named by the URL hash. React Router does not do this on client-side
 * navigation, and the target may sit below content that loads later, so it re-runs when
 * `ready` flips. Returns the active anchor id so the page can highlight it.
 */
export function useHashScroll(ready: boolean): string | undefined {
  const { hash } = useLocation()
  const anchor = hash ? decodeURIComponent(hash.slice(1)) : undefined
  useEffect(() => {
    if (!anchor) return
    const el = document.getElementById(anchor)
    if (!el) return
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    el.scrollIntoView({ block: 'start', behavior: reduce ? 'auto' : 'smooth' })
  }, [anchor, ready])
  return anchor
}
