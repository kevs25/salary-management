import { useQuery } from '@tanstack/react-query'
import { api, unwrap } from './client'
import { keys } from './keys'

/** Departments, roles, levels, countries, statuses and the salary range: rarely changes. */
export function useReferenceData() {
  return useQuery({
    queryKey: keys.reference,
    queryFn: () => unwrap(api.GET('/api/v1/employees/filters')),
    staleTime: 5 * 60_000,
  })
}
