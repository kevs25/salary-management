import { MantineProvider, Table } from '@mantine/core'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { SortableTh } from './SortableTh'

const wrap = (ui: ReactNode) => render(<MantineProvider>{ui}</MantineProvider>)

describe('SortableTh', () => {
  const header = (sort: string, order: 'asc' | 'desc', onSort = vi.fn()) => {
    wrap(
      <Table>
        <Table.Thead>
          <Table.Tr>
            <SortableTh field="name" sort={sort} order={order} onSort={onSort}>
              Name
            </SortableTh>
          </Table.Tr>
        </Table.Thead>
      </Table>,
    )
    return onSort
  }

  it('sorts ascending when a new column is clicked', async () => {
    const onSort = header('level', 'desc')

    await userEvent.click(screen.getByRole('button', { name: 'Name' }))

    expect(onSort).toHaveBeenCalledWith('name', 'asc')
  })

  it('flips the direction of the active column and exposes it to assistive tech', async () => {
    const onSort = header('name', 'asc')

    expect(screen.getByRole('columnheader')).toHaveAttribute('aria-sort', 'ascending')
    await userEvent.click(screen.getByRole('button', { name: 'Name ▲' }))

    expect(onSort).toHaveBeenCalledWith('name', 'desc')
  })
})
