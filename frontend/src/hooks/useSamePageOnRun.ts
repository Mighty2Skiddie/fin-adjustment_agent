import { useLocation } from 'react-router-dom'

/** Same page on another run: /runs/abc/queue -> /runs/<target>/queue. */
export function useSamePageOnRun(target: string): string {
  const { pathname } = useLocation()
  const m = /^\/runs\/[^/]+(\/.*)?$/.exec(pathname)
  return `/runs/${target}${m?.[1] ?? '/health'}`
}
