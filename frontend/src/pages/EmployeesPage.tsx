import { Button, Group, Pagination, Paper, Select, Stack, Text, Title } from '@mantine/core'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { type EmployeeQuery, useEmployees } from '../api/employees'
import { useReferenceData } from '../api/reference'
import { DebouncedInput } from '../components/DebouncedInput'
import { DimensionFilters } from '../components/DimensionFilters'
import { EmployeeFormModal } from '../components/employees/EmployeeFormModal'
import { type EmployeeSort, EmployeeTable } from '../components/employees/EmployeeTable'
import { QueryStatus } from '../components/QueryStatus'
import { intParam, useUrlParams } from '../hooks/useUrlParams'
import { formatCount, humanize, MONEY_PATTERN } from '../lib/format'

const PAGE_SIZE = 25
const SORTS: readonly EmployeeSort[] = [
  'name',
  'employee_code',
  'hire_date',
  'department',
  'country',
  'level',
  'base_salary_usd',
]
type Status = NonNullable<EmployeeQuery['status']>

const moneyParam = (value: string | undefined) =>
  value && MONEY_PATTERN.test(value) ? value : undefined

export function EmployeesPage() {
  const [params, update] = useUrlParams()
  const navigate = useNavigate()
  const { data: reference } = useReferenceData()
  const [creating, setCreating] = useState(false)

  const sort = SORTS.includes(params.sort as EmployeeSort) ? (params.sort as EmployeeSort) : 'name'
  const order = params.order === 'desc' ? 'desc' : 'asc'
  const query: EmployeeQuery = {
    q: params.q || undefined,
    department_id: intParam(params.department_id),
    role_id: intParam(params.role_id),
    level_id: intParam(params.level_id),
    country_id: intParam(params.country_id),
    status: (params.status as Status) || undefined,
    min_salary_usd: moneyParam(params.min_salary_usd),
    max_salary_usd: moneyParam(params.max_salary_usd),
    sort,
    order,
    page: intParam(params.page) ?? 1,
    page_size: PAGE_SIZE,
  }
  const { data, isPending, error, isFetching } = useEmployees(query)
  const pages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1

  return (
    <Stack>
      <Group justify="space-between">
        <div>
          <Title order={2}>Employees</Title>
          <Text c="dimmed" size="sm">
            {data ? `${formatCount(data.total)} matching` : ' '}
          </Text>
        </div>
        <Button onClick={() => setCreating(true)}>New employee</Button>
      </Group>

      <Paper withBorder p="md">
        <Stack gap="sm">
          <Group gap="sm" wrap="wrap" align="flex-end">
            <DebouncedInput
              aria-label="Search"
              placeholder="Search name, code or email"
              value={params.q ?? ''}
              onCommit={(q) => update({ q })}
              w={280}
            />
            <Select
              aria-label="Status"
              placeholder="Any status"
              clearable
              data={(reference?.statuses ?? []).map((s) => ({ value: s, label: humanize(s) }))}
              value={params.status ?? null}
              onChange={(status) => update({ status })}
              w={150}
            />
            <DebouncedInput
              aria-label="Minimum base salary (USD)"
              placeholder="Min base USD"
              value={params.min_salary_usd ?? ''}
              onCommit={(v) => update({ min_salary_usd: moneyParam(v) ?? null })}
              w={140}
            />
            <DebouncedInput
              aria-label="Maximum base salary (USD)"
              placeholder="Max base USD"
              value={params.max_salary_usd ?? ''}
              onCommit={(v) => update({ max_salary_usd: moneyParam(v) ?? null })}
              w={140}
            />
          </Group>
          <DimensionFilters values={query} onChange={update} />
        </Stack>
      </Paper>

      <QueryStatus isPending={isPending} error={error}>
        <Paper withBorder style={{ opacity: isFetching ? 0.6 : 1 }}>
          <EmployeeTable
            rows={data?.items ?? []}
            sort={sort}
            order={order}
            onSort={(s, o) => update({ sort: s, order: o })}
          />
        </Paper>
        <Group justify="center">
          <Pagination total={pages} value={query.page ?? 1} onChange={(page) => update({ page })} />
        </Group>
      </QueryStatus>

      <EmployeeFormModal
        opened={creating}
        onClose={() => setCreating(false)}
        onSaved={(employee) => navigate(`/employees/${employee.id}`)}
      />
    </Stack>
  )
}
