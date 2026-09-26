import { Box, Group, Paper, Stack, Text, Tooltip } from '@mantine/core'
import type { Schemas } from '../../api/client'
import { formatMoney, formatPct, formatRatio } from '../../lib/format'
import { positionColor } from '../../theme'
import { SCOPE_LABEL } from '../../lib/labels'
import { markerPosition } from '../../lib/pay'
import { PositionBadge } from '../Badges'

interface Props {
  assessment: Schemas['PayAssessment'] | null | undefined
}

export function PayAssessmentCard({ assessment }: Props) {
  if (!assessment) {
    return (
      <Paper withBorder p="md">
        <Text fw={600}>Band position</Text>
        <Text c="dimmed" size="sm" mt="xs">
          No salary band covers this employee's department, level and country yet.
        </Text>
      </Paper>
    )
  }
  const { band } = assessment
  // Numbers here only place the marker on screen; amounts are displayed from the strings.
  const salary = Number(assessment.salary_in_band_currency)
  const min = Number(band.min_amount)
  const max = Number(band.max_amount)
  const left = markerPosition(min, min, max)
  const right = markerPosition(max, min, max)

  return (
    <Paper withBorder p="md">
      <Stack gap="sm">
        <Group justify="space-between">
          <Text fw={600}>Band position</Text>
          <PositionBadge position={assessment.position} />
        </Group>
        <Box pos="relative" h={28} aria-hidden>
          <Box
            pos="absolute"
            top={12}
            left={0}
            right={0}
            h={4}
            bg="gray.2"
            style={{ borderRadius: 2 }}
          />
          <Box
            pos="absolute"
            top={10}
            h={8}
            bg="teal.3"
            style={{ left: `${left}%`, width: `${right - left}%`, borderRadius: 4 }}
          />
          <Tooltip label={formatMoney(assessment.salary_in_band_currency, band.currency_code)}>
            <Box
              pos="absolute"
              top={4}
              w={4}
              h={20}
              bg={`${positionColor[assessment.position]}.7`}
              style={{ left: `calc(${markerPosition(salary, min, max)}% - 2px)`, borderRadius: 2 }}
            />
          </Tooltip>
        </Box>
        <Group justify="space-between" gap="xs">
          <Text size="xs" c="dimmed">
            Min {formatMoney(band.min_amount, band.currency_code)}
          </Text>
          <Text size="xs" c="dimmed">
            Mid {formatMoney(band.mid_amount, band.currency_code)}
          </Text>
          <Text size="xs" c="dimmed">
            Max {formatMoney(band.max_amount, band.currency_code)}
          </Text>
        </Group>
        <Group gap="xl">
          <div>
            <Text size="xs" c="dimmed">
              Compa-ratio
            </Text>
            <Text fw={600}>{formatRatio(assessment.compa_ratio)}</Text>
          </div>
          <div>
            <Text size="xs" c="dimmed">
              Outside band by
            </Text>
            <Text fw={600}>
              {assessment.position === 'within'
                ? '—'
                : `${formatMoney(assessment.gap_amount, band.currency_code)} (${formatPct(assessment.gap_pct)})`}
            </Text>
          </div>
          <div>
            <Text size="xs" c="dimmed">
              Band
            </Text>
            <Text size="sm">{SCOPE_LABEL[band.scope]}</Text>
          </div>
        </Group>
      </Stack>
    </Paper>
  )
}
