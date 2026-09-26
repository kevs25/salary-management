import { Group, Paper, SegmentedControl, Stack, Table, Text, Title } from '@mantine/core'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { Schemas } from '../../api/client'
import { AXIS_INK, GRID, SERIES } from '../../lib/chartColors'
import { formatCount, formatPct, formatUsd, formatUsdCompact } from '../../lib/format'
import { DIMENSIONS } from '../../lib/labels'

type Dimension = Schemas['Dimension']

interface Props {
  breakdown: Schemas['Breakdown']
  onDimensionChange: (by: Dimension) => void
  stale: boolean
}

const ROW_HEIGHT = 34 // bar (<= 24px) + air

export function BreakdownSection({ breakdown, onDimensionChange, stale }: Props) {
  const rows = breakdown.rows
  // Numbers for bar geometry only; labels and the table use the API's decimal strings.
  const chart = rows.map((r) => ({
    name: r.group.name,
    median: Number(r.base_salary_usd.median ?? 0),
    medianLabel: formatUsd(r.base_salary_usd.median),
    headcount: r.headcount,
  }))

  return (
    <Paper withBorder p="md" style={{ opacity: stale ? 0.6 : 1 }}>
      <Stack>
        <Group justify="space-between">
          <div>
            <Title order={4}>Pay by {breakdown.by}</Title>
            <Text size="sm" c="dimmed">
              Median annual base pay, USD
            </Text>
          </div>
          <SegmentedControl
            aria-label="Group by"
            data={DIMENSIONS}
            value={breakdown.by}
            onChange={(value) => onDimensionChange(value as Dimension)}
          />
        </Group>

        <ResponsiveContainer width="100%" height={Math.max(160, rows.length * ROW_HEIGHT + 40)}>
          <BarChart
            data={chart}
            layout="vertical"
            margin={{ left: 8, right: 24 }}
            barCategoryGap={6}
          >
            <CartesianGrid horizontal={false} stroke={GRID} />
            <XAxis
              type="number"
              tickFormatter={(v: number) => formatUsdCompact(String(v))}
              stroke={AXIS_INK}
              tick={{ fontSize: 12 }}
            />
            <YAxis
              type="category"
              dataKey="name"
              width={breakdown.by === 'role' ? 220 : 120}
              stroke={AXIS_INK}
              tick={{ fontSize: 12 }}
            />
            <Tooltip
              cursor={{ fill: 'rgba(11,11,11,0.04)' }}
              formatter={(_, __, item) => [item.payload.medianLabel, 'Median base']}
              labelFormatter={(label, payload) =>
                `${label} · ${formatCount(payload?.[0]?.payload.headcount ?? 0)} people`
              }
            />
            <Bar dataKey="median" fill={SERIES} maxBarSize={24} radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>

        <Table.ScrollContainer minWidth={900}>
          <Table striped verticalSpacing={4} fz="sm" style={{ fontVariantNumeric: 'tabular-nums' }}>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>{DIMENSIONS.find((d) => d.value === breakdown.by)?.label}</Table.Th>
                <Table.Th ta="right">Headcount</Table.Th>
                <Table.Th ta="right">Payroll (USD)</Table.Th>
                <Table.Th ta="right">Share</Table.Th>
                <Table.Th ta="right">Median</Table.Th>
                <Table.Th ta="right">Average</Table.Th>
                <Table.Th ta="right">Min</Table.Th>
                <Table.Th ta="right">Max</Table.Th>
                <Table.Th ta="right">Below band</Table.Th>
                <Table.Th ta="right">Above band</Table.Th>
                <Table.Th ta="right">Within</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {rows.map((r) => (
                <Table.Tr key={r.group.id ?? 'all'}>
                  <Table.Td>{r.group.name}</Table.Td>
                  <Table.Td ta="right">{formatCount(r.headcount)}</Table.Td>
                  <Table.Td ta="right">{formatUsdCompact(r.payroll_cost_usd)}</Table.Td>
                  <Table.Td ta="right">{formatPct(r.payroll_share_pct)}</Table.Td>
                  <Table.Td ta="right">{formatUsd(r.base_salary_usd.median)}</Table.Td>
                  <Table.Td ta="right">{formatUsd(r.base_salary_usd.avg)}</Table.Td>
                  <Table.Td ta="right">{formatUsd(r.base_salary_usd.min)}</Table.Td>
                  <Table.Td ta="right">{formatUsd(r.base_salary_usd.max)}</Table.Td>
                  <Table.Td ta="right">{formatCount(r.band_compliance.below)}</Table.Td>
                  <Table.Td ta="right">{formatCount(r.band_compliance.above)}</Table.Td>
                  <Table.Td ta="right">{formatPct(r.band_compliance.compliance_pct)}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      </Stack>
    </Paper>
  )
}
