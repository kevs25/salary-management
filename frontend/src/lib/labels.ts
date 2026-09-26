import type { Schemas } from '../api/client'

type Scope = Schemas['BandOut']['scope']
type Dimension = Schemas['Dimension']

export const SCOPE_LABEL: Record<Scope, string> = {
  'department+role+level+country': 'Role + country',
  'department+level+country': 'All roles, one country',
  'department+level': 'Department-wide (USD)',
}

export const DIMENSIONS: { value: Dimension; label: string }[] = [
  { value: 'department', label: 'Department' },
  { value: 'country', label: 'Country' },
  { value: 'level', label: 'Level' },
  { value: 'role', label: 'Role' },
]

export const isDimension = (value: string | undefined): value is Dimension =>
  DIMENSIONS.some((d) => d.value === value)
