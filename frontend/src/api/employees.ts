import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { paths } from './schema'
import { api, unwrap, type Schemas } from './client'
import { keys } from './keys'

export type EmployeeQuery = NonNullable<paths['/api/v1/employees']['get']['parameters']['query']>

export function useEmployees(query: EmployeeQuery) {
  return useQuery({
    queryKey: [...keys.employees, 'list', query],
    queryFn: () => unwrap(api.GET('/api/v1/employees', { params: { query } })),
    placeholderData: keepPreviousData, // keep the table on screen while the next page loads
  })
}

export function useEmployee(employeeId: number) {
  return useQuery({
    queryKey: [...keys.employees, 'detail', employeeId],
    queryFn: () =>
      unwrap(
        api.GET('/api/v1/employees/{employee_id}', {
          params: { path: { employee_id: employeeId } },
        }),
      ),
  })
}

function useInvalidateWorkforce() {
  const client = useQueryClient()
  return () =>
    Promise.all([
      client.invalidateQueries({ queryKey: keys.employees }),
      client.invalidateQueries({ queryKey: keys.analytics }),
    ])
}

export function useCreateEmployee() {
  const invalidate = useInvalidateWorkforce()
  return useMutation({
    mutationFn: (body: Schemas['EmployeeCreate']) =>
      unwrap(api.POST('/api/v1/employees', { body })),
    onSuccess: invalidate,
  })
}

export function useUpdateEmployee(employeeId: number) {
  const invalidate = useInvalidateWorkforce()
  return useMutation({
    mutationFn: (body: Schemas['EmployeeUpdate']) =>
      unwrap(
        api.PATCH('/api/v1/employees/{employee_id}', {
          params: { path: { employee_id: employeeId } },
          body,
        }),
      ),
    onSuccess: invalidate,
  })
}

export function useReviseSalary(employeeId: number) {
  const invalidate = useInvalidateWorkforce()
  return useMutation({
    mutationFn: (body: Schemas['SalaryRevisionCreate']) =>
      unwrap(
        api.POST('/api/v1/employees/{employee_id}/salary-revisions', {
          params: { path: { employee_id: employeeId } },
          body,
        }),
      ),
    onSuccess: invalidate,
  })
}
