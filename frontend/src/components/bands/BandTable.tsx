import { Button, Group, Table, Text } from '@mantine/core'
import type { Schemas } from '../../api/client'
import { formatDate, formatMoney } from '../../lib/format'
import { ScopeBadge } from '../Badges'

type Band = Schemas['BandOut']

interface Props {
  rows: Band[]
  onEdit: (band: Band) => void
  onDelete: (band: Band) => void
}

export function BandTable({ rows, onEdit, onDelete }: Props) {
  const money = (band: Band, amount: string) => formatMoney(amount, band.currency_code)
  return (
    <Table.ScrollContainer minWidth={1000}>
      <Table striped highlightOnHover verticalSpacing="xs">
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Department</Table.Th>
            <Table.Th>Role</Table.Th>
            <Table.Th>Level</Table.Th>
            <Table.Th>Country</Table.Th>
            <Table.Th>Scope</Table.Th>
            <Table.Th style={{ textAlign: 'right' }}>Min</Table.Th>
            <Table.Th style={{ textAlign: 'right' }}>Mid</Table.Th>
            <Table.Th style={{ textAlign: 'right' }}>Max</Table.Th>
            <Table.Th>Updated</Table.Th>
            <Table.Th />
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {rows.map((band) => (
            <Table.Tr key={band.id}>
              <Table.Td>{band.department.name}</Table.Td>
              <Table.Td>{band.role?.name ?? <Text c="dimmed">All roles</Text>}</Table.Td>
              <Table.Td>{band.level.code}</Table.Td>
              <Table.Td>{band.country?.name ?? <Text c="dimmed">All countries</Text>}</Table.Td>
              <Table.Td>
                <ScopeBadge scope={band.scope} />
              </Table.Td>
              <Table.Td style={{ textAlign: 'right' }}>{money(band, band.min_amount)}</Table.Td>
              <Table.Td style={{ textAlign: 'right' }} fw={600}>
                {money(band, band.mid_amount)}
              </Table.Td>
              <Table.Td style={{ textAlign: 'right' }}>{money(band, band.max_amount)}</Table.Td>
              <Table.Td>{formatDate(band.updated_at)}</Table.Td>
              <Table.Td>
                <Group gap={4} wrap="nowrap">
                  <Button size="compact-xs" variant="subtle" onClick={() => onEdit(band)}>
                    Edit
                  </Button>
                  <Button
                    size="compact-xs"
                    variant="subtle"
                    color="red"
                    onClick={() => onDelete(band)}
                  >
                    Delete
                  </Button>
                </Group>
              </Table.Td>
            </Table.Tr>
          ))}
          {rows.length === 0 && (
            <Table.Tr>
              <Table.Td colSpan={10}>
                <Text c="dimmed" ta="center" py="md">
                  No bands match these filters.
                </Text>
              </Table.Td>
            </Table.Tr>
          )}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  )
}
