import { Group, Paper, SegmentedControl, Stack, Table, Text, Title } from '@mantine/core'
import type { Schemas } from '../../api/client'
import { formatCount, formatRatio } from '../../lib/format'
import { DIMENSIONS } from '../../lib/labels'

type Dimension = Schemas['Dimension']

interface Props {
  distribution: Schemas['CompaRatioDistribution']
  onDimensionChange: (by: Dimension) => void
  stale: boolean
}

/** Compa-ratio distribution per group: quartiles and how many fall in each range. */
export function CompaRatioSection({ distribution, onDimensionChange, stale }: Props) {
  const rows = distribution.rows
  const labels = rows[0]?.buckets.map((b) => b.label) ?? []

  return (
    <Paper withBorder p="md" style={{ opacity: stale ? 0.6 : 1 }}>
      <Stack>
        <Group justify="space-between">
          <div>
            <Title order={4}>Compa-ratio by {distribution.by}</Title>
            <Text size="sm" c="dimmed">
              Base pay ÷ band midpoint. 1.00 is paid exactly at the midpoint; below 0.80 or from
              1.20 is typically outside the band.
            </Text>
          </div>
          <SegmentedControl
            aria-label="Group compa-ratio by"
            data={DIMENSIONS}
            value={distribution.by}
            onChange={(value) => onDimensionChange(value as Dimension)}
          />
        </Group>

        <Table.ScrollContainer minWidth={900}>
          <Table striped verticalSpacing={4} fz="sm" style={{ fontVariantNumeric: 'tabular-nums' }}>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>{DIMENSIONS.find((d) => d.value === distribution.by)?.label}</Table.Th>
                <Table.Th ta="right">With band</Table.Th>
                <Table.Th ta="right">P25</Table.Th>
                <Table.Th ta="right">Median</Table.Th>
                <Table.Th ta="right">P75</Table.Th>
                {labels.map((label) => (
                  <Table.Th key={label} ta="right">
                    {label}
                  </Table.Th>
                ))}
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {rows.map((r) => (
                <Table.Tr key={r.group.id ?? 'all'}>
                  <Table.Td>{r.group.name}</Table.Td>
                  <Table.Td ta="right">{formatCount(r.employees_with_band)}</Table.Td>
                  <Table.Td ta="right">{formatRatio(r.p25)}</Table.Td>
                  <Table.Td ta="right">{formatRatio(r.median)}</Table.Td>
                  <Table.Td ta="right">{formatRatio(r.p75)}</Table.Td>
                  {r.buckets.map((b) => (
                    <Table.Td key={b.label} ta="right">
                      {formatCount(b.count)}
                    </Table.Td>
                  ))}
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      </Stack>
    </Paper>
  )
}
