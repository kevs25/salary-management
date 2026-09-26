import { Group, Select } from '@mantine/core'
import { useReferenceData } from '../api/reference'
import type { ParamPatch } from '../hooks/useUrlParams'

export interface DimensionValues {
  department_id?: number | null
  role_id?: number | null
  level_id?: number | null
  country_id?: number | null
}

interface Props {
  values: DimensionValues
  onChange: (patch: ParamPatch) => void
}

/** Department / role / level / country selects. Roles narrow to the chosen department. */
export function DimensionFilters({ values, onChange }: Props) {
  const { data } = useReferenceData()
  const roles = (data?.roles ?? []).filter(
    (r) => values.department_id == null || r.department_id === values.department_id,
  )
  const select = (key: keyof DimensionValues, value: string | null) =>
    onChange({ [key]: value == null ? null : Number(value) })

  return (
    <Group gap="sm" wrap="wrap">
      <Select
        aria-label="Department"
        placeholder="All departments"
        clearable
        data={(data?.departments ?? []).map((d) => ({ value: String(d.id), label: d.name }))}
        value={values.department_id?.toString() ?? null}
        onChange={(value) => {
          // Keep the role only if it belongs to the newly chosen department.
          const role = data?.roles.find((r) => r.id === values.role_id)
          const keepRole = value != null && role?.department_id === Number(value)
          onChange({ department_id: value, role_id: keepRole ? values.role_id : null })
        }}
        w={180}
      />
      <Select
        aria-label="Role"
        placeholder="All roles"
        clearable
        searchable
        data={roles.map((r) => ({ value: String(r.id), label: r.name }))}
        value={values.role_id?.toString() ?? null}
        onChange={(value) => select('role_id', value)}
        w={230}
      />
      <Select
        aria-label="Level"
        placeholder="All levels"
        clearable
        data={(data?.levels ?? []).map((l) => ({
          value: String(l.id),
          label: `${l.code} · ${l.name}`,
        }))}
        value={values.level_id?.toString() ?? null}
        onChange={(value) => select('level_id', value)}
        w={170}
      />
      <Select
        aria-label="Country"
        placeholder="All countries"
        clearable
        data={(data?.countries ?? []).map((c) => ({ value: String(c.id), label: c.name }))}
        value={values.country_id?.toString() ?? null}
        onChange={(value) => select('country_id', value)}
        w={170}
      />
    </Group>
  )
}
