import { Anchor, Table, Text } from '@mantine/core'
import { Link } from 'react-router-dom'
import type { Schemas } from '../../api/client'
import { formatMoney, formatUsd } from '../../lib/format'
import { StatusBadge } from '../Badges'
import { SortableTh, type SortOrder } from '../SortableTh'

export type EmployeeSort = Schemas['EmployeeSort']

interface Props {
  rows: Schemas['EmployeeListItem'][]
  sort: EmployeeSort
  order: SortOrder
  onSort: (sort: EmployeeSort, order: SortOrder) => void
}

export function EmployeeTable({ rows, sort, order, onSort }: Props) {
  const th = { sort, order, onSort }
  return (
    <Table.ScrollContainer minWidth={960}>
      <Table striped highlightOnHover verticalSpacing="xs">
        <Table.Thead>
          <Table.Tr>
            <SortableTh field="name" {...th}>
              Name
            </SortableTh>
            <SortableTh field="employee_code" {...th}>
              Code
            </SortableTh>
            <SortableTh field="department" {...th}>
              Department
            </SortableTh>
            <Table.Th>Role</Table.Th>
            <SortableTh field="level" {...th}>
              Level
            </SortableTh>
            <SortableTh field="country" {...th}>
              Country
            </SortableTh>
            <Table.Th>Status</Table.Th>
            <Table.Th style={{ textAlign: 'right' }}>Base (local)</Table.Th>
            <SortableTh field="base_salary_usd" align="right" {...th}>
              Base (USD)
            </SortableTh>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {rows.map((e) => (
            <Table.Tr key={e.id}>
              <Table.Td>
                <Anchor component={Link} to={`/employees/${e.id}`} fw={500}>
                  {e.first_name} {e.last_name}
                </Anchor>
                <Text size="xs" c="dimmed">
                  {e.email}
                </Text>
              </Table.Td>
              <Table.Td>{e.employee_code}</Table.Td>
              <Table.Td>{e.department}</Table.Td>
              <Table.Td>{e.role}</Table.Td>
              <Table.Td>{e.level}</Table.Td>
              <Table.Td>{e.country_code}</Table.Td>
              <Table.Td>
                <StatusBadge status={e.status} />
              </Table.Td>
              <Table.Td style={{ textAlign: 'right' }}>
                {formatMoney(e.base_amount, e.currency_code)}
              </Table.Td>
              <Table.Td style={{ textAlign: 'right' }}>{formatUsd(e.base_amount_usd)}</Table.Td>
            </Table.Tr>
          ))}
          {rows.length === 0 && (
            <Table.Tr>
              <Table.Td colSpan={9}>
                <Text c="dimmed" ta="center" py="md">
                  No employees match these filters.
                </Text>
              </Table.Td>
            </Table.Tr>
          )}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  )
}
