import { useCallback, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'

export type ParamValue = string | number | null | undefined
export type ParamPatch = Record<string, ParamValue>

/**
 * Apply a patch to URL search params. Empty values remove the key. Any change
 * other than to `page` itself goes back to page 1, so a new filter never lands
 * on a page that no longer exists.
 */
export function applyPatch(current: URLSearchParams, patch: ParamPatch): URLSearchParams {
  const next = new URLSearchParams(current)
  for (const [key, value] of Object.entries(patch)) {
    if (value == null || value === '') next.delete(key)
    else next.set(key, String(value))
  }
  if (!('page' in patch)) next.delete('page')
  return next
}

/** Read an integer param; anything else (missing, "abc") is undefined. */
export function intParam(value: string | undefined): number | undefined {
  if (value == null || !/^\d+$/.test(value)) return undefined
  return Number(value)
}

/**
 * Filters, sort and page live in the URL, so any view can be bookmarked or shared
 * and the back button behaves. Returns plain string params and an updater.
 */
export function useUrlParams() {
  const [searchParams, setSearchParams] = useSearchParams()
  const params = useMemo(() => Object.fromEntries(searchParams), [searchParams])
  const update = useCallback(
    (patch: ParamPatch) => setSearchParams((prev) => applyPatch(prev, patch), { replace: true }),
    [setSearchParams],
  )
  return [params, update] as const
}
