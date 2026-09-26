import { Table, UnstyledButton } from '@mantine/core'
import type { ReactNode } from 'react'

export type SortOrder = 'asc' | 'desc'

interface Props<F extends string> {
  field: F
  sort: F
  order: SortOrder
  onSort: (field: F, order: SortOrder) => void
  children: ReactNode
  align?: 'left' | 'right'
}

/** Header cell that sorts by its field; clicking the active one flips the direction. */
export function SortableTh<F extends string>({
  field,
  sort,
  order,
  onSort,
  children,
  align,
}: Props<F>) {
  const active = sort === field
  return (
    <Table.Th
      style={{ textAlign: align }}
      aria-sort={active ? (order === 'asc' ? 'ascending' : 'descending') : 'none'}
    >
      <UnstyledButton
        fw={600}
        fz="sm"
        onClick={() => onSort(field, active && order === 'asc' ? 'desc' : 'asc')}
      >
        {children}
        {active ? (order === 'asc' ? ' ▲' : ' ▼') : ''}
      </UnstyledButton>
    </Table.Th>
  )
}
