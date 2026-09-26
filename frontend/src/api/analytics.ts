import { keepPreviousData, useQuery } from '@tanstack/react-query'
import type { paths } from './schema'
import { api, unwrap } from './client'
import { keys } from './keys'

type QueryOf<P extends keyof paths> = paths[P] extends {
  get: { parameters: { query?: infer Q } }
}
  ? NonNullable<Q>
  : never

export type AnalyticsFilter = QueryOf<'/api/v1/analytics/summary'>
export type BreakdownQuery = QueryOf<'/api/v1/analytics/breakdown'>
export type CompaRatioQuery = QueryOf<'/api/v1/analytics/compa-ratio'>

export function usePaySummary(query: AnalyticsFilter) {
  return useQuery({
    queryKey: [...keys.analytics, 'summary', query],
    queryFn: () => unwrap(api.GET('/api/v1/analytics/summary', { params: { query } })),
    placeholderData: keepPreviousData,
  })
}

export function useBreakdown(query: BreakdownQuery) {
  return useQuery({
    queryKey: [...keys.analytics, 'breakdown', query],
    queryFn: () => unwrap(api.GET('/api/v1/analytics/breakdown', { params: { query } })),
    placeholderData: keepPreviousData,
  })
}

export function useCompaRatio(query: CompaRatioQuery) {
  return useQuery({
    queryKey: [...keys.analytics, 'compa-ratio', query],
    queryFn: () => unwrap(api.GET('/api/v1/analytics/compa-ratio', { params: { query } })),
    placeholderData: keepPreviousData,
  })
}
