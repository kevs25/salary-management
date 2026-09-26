import type { Schemas } from '../../api/client'

type Employee = Schemas['EmployeeDetail']

/** Form state: selects hold ids as strings, money holds decimal strings. */
export interface EmployeeFormValues {
  employee_code: string
  first_name: string
  last_name: string
  email: string
  department_id: string | null
  role_id: string | null
  level_id: string | null
  country_id: string | null
  manager_id: string | null
  hire_date: string
  status: Employee['status']
  base_amount: string
  bonus_amount: string
}

export const blankEmployee: EmployeeFormValues = {
  employee_code: '',
  first_name: '',
  last_name: '',
  email: '',
  department_id: null,
  role_id: null,
  level_id: null,
  country_id: null,
  manager_id: null,
  hire_date: '',
  status: 'active',
  base_amount: '',
  bonus_amount: '0',
}

export function fromEmployee(e: Employee): EmployeeFormValues {
  return {
    ...blankEmployee,
    employee_code: e.employee_code,
    first_name: e.first_name,
    last_name: e.last_name,
    email: e.email,
    department_id: String(e.department.id),
    role_id: String(e.role.id),
    level_id: String(e.level.id),
    country_id: String(e.country.id),
    manager_id: e.manager ? String(e.manager.id) : null,
    hire_date: e.hire_date,
    status: e.status,
  }
}

const toId = (value: string | null) => (value == null ? null : Number(value))

export function toCreateBody(values: EmployeeFormValues): Schemas['EmployeeCreate'] {
  return {
    employee_code: values.employee_code,
    first_name: values.first_name,
    last_name: values.last_name,
    email: values.email,
    department_id: Number(values.department_id),
    role_id: Number(values.role_id),
    level_id: Number(values.level_id),
    country_id: Number(values.country_id),
    manager_id: toId(values.manager_id),
    hire_date: values.hire_date,
    status: values.status,
    base_amount: values.base_amount, // decimal string, never a float
    bonus_amount: values.bonus_amount || '0',
  }
}

/** Only what changed, so a PATCH never re-sends (or re-validates) untouched fields. */
export function changedFields(
  employee: Employee,
  values: EmployeeFormValues,
): Schemas['EmployeeUpdate'] {
  const before = fromEmployee(employee)
  const patch: Schemas['EmployeeUpdate'] = {}
  if (values.first_name !== before.first_name) patch.first_name = values.first_name
  if (values.last_name !== before.last_name) patch.last_name = values.last_name
  if (values.email !== before.email) patch.email = values.email
  if (values.department_id !== before.department_id)
    patch.department_id = toId(values.department_id)
  if (values.role_id !== before.role_id) patch.role_id = toId(values.role_id)
  if (values.level_id !== before.level_id) patch.level_id = toId(values.level_id)
  if (values.manager_id !== before.manager_id) patch.manager_id = toId(values.manager_id)
  if (values.status !== before.status) patch.status = values.status
  return patch
}
