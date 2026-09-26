import { Badge, Group, Paper, Text, Timeline } from '@mantine/core'
import type { Schemas } from '../../api/client'
import { formatDate, formatMoney, formatUsd, humanize } from '../../lib/format'

interface Props {
  history: Schemas['SalaryRecordOut'][]
}

/** Salary records newest first; each covers [effective_from, effective_to). */
export function SalaryHistory({ history }: Props) {
  return (
    <Paper withBorder p="md">
      <Text fw={600} mb="md">
        Salary history
      </Text>
      <Timeline active={0} bulletSize={14} lineWidth={2}>
        {history.map((record) => (
          <Timeline.Item
            key={record.id}
            title={
              <Group gap="xs">
                <Text fw={500}>{formatMoney(record.base_amount, record.currency_code)}</Text>
                <Badge size="sm" variant="light" color={record.is_current ? 'teal' : 'gray'}>
                  {humanize(record.reason)}
                </Badge>
                {record.is_current && (
                  <Badge size="sm" variant="outline" color="teal">
                    Current
                  </Badge>
                )}
              </Group>
            }
          >
            <Text size="sm" c="dimmed">
              {formatDate(record.effective_from)} –{' '}
              {record.effective_to ? formatDate(record.effective_to) : 'now'}
            </Text>
            <Text size="sm">
              Bonus {formatMoney(record.bonus_amount, record.currency_code)} · Base{' '}
              {formatUsd(record.base_amount_usd)} at {record.fx_rate_to_usd} USD/
              {record.currency_code}
            </Text>
            {record.note && (
              <Text size="sm" fs="italic">
                {record.note}
              </Text>
            )}
          </Timeline.Item>
        ))}
      </Timeline>
    </Paper>
  )
}
