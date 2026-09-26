import { Badge } from '@mantine/core'
import type { Schemas } from '../api/client'
import { humanize } from '../lib/format'
import { positionColor } from '../theme'

type Position = Schemas['PayAssessment']['position']
type Status = Schemas['EmployeeDetail']['status']

const POSITION_LABEL: Record<Position, string> = {
  below: 'Below band',
  within: 'Within band',
  above: 'Above band',
  no_band: 'No band',
}

export function PositionBadge({ position }: { position: Position }) {
  return (
    <Badge color={positionColor[position]} variant="light">
      {POSITION_LABEL[position]}
    </Badge>
  )
}

const STATUS_COLOR: Record<Status, string> = {
  active: 'teal',
  on_leave: 'yellow',
  terminated: 'gray',
}

export function StatusBadge({ status }: { status: Status }) {
  return (
    <Badge color={STATUS_COLOR[status]} variant="dot">
      {humanize(status)}
    </Badge>
  )
}
