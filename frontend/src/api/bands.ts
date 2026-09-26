import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { paths } from './schema'
import { api, unwrap, type Schemas } from './client'
import { keys } from './keys'

export type BandQuery = NonNullable<paths['/api/v1/bands']['get']['parameters']['query']>

export function useBands(query: BandQuery) {
  return useQuery({
    queryKey: [...keys.bands, 'list', query],
    queryFn: () => unwrap(api.GET('/api/v1/bands', { params: { query } })),
    placeholderData: keepPreviousData,
  })
}

/** Band policy feeds compliance, compa-ratio and every employee's pay assessment. */
function useInvalidatePolicy() {
  const client = useQueryClient()
  return () =>
    Promise.all([
      client.invalidateQueries({ queryKey: keys.bands }),
      client.invalidateQueries({ queryKey: keys.analytics }),
      client.invalidateQueries({ queryKey: keys.employees }),
    ])
}

export function useCreateBand() {
  const invalidate = useInvalidatePolicy()
  return useMutation({
    mutationFn: (body: Schemas['BandCreate']) => unwrap(api.POST('/api/v1/bands', { body })),
    onSuccess: invalidate,
  })
}

export function useUpdateBand() {
  const invalidate = useInvalidatePolicy()
  return useMutation({
    mutationFn: ({ bandId, body }: { bandId: number; body: Schemas['BandUpdate'] }) =>
      unwrap(api.PATCH('/api/v1/bands/{band_id}', { params: { path: { band_id: bandId } }, body })),
    onSuccess: invalidate,
  })
}

export function useDeleteBand() {
  const invalidate = useInvalidatePolicy()
  return useMutation({
    mutationFn: (bandId: number) =>
      unwrap(api.DELETE('/api/v1/bands/{band_id}', { params: { path: { band_id: bandId } } })),
    onSuccess: invalidate,
  })
}
