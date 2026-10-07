import { describe, expect, it } from 'vitest'
import type { Schemas } from '../../api/client'
import { changedFields, fromEmployee, toCreateBody } from './employeeForm'

const employee = {
  id: 7,
  employee_code: 'E00007',
  first_name: 'Asha',
  last_name: 'Rao',
  email: 'asha.rao@acme.example',
  hire_date: '2024-04-01',
  status: 'active',
  department: { id: 1, name: 'Engineering' },
  role: { id: 10, name: 'Backend Engineer', department_id: 1 },
  level: { id: 2, code: 'L2', name: 'Intermediate', rank: 2, min_years: 2, max_years: 5 },
  country: { id: 2, code: 'IN', name: 'India', currency_code: 'INR' },
  manager: { id: 3, employee_code: 'E00003', full_name: 'Wei Tan' },
  current_salary: null,
  net_pay: null,
  pay_assessment: null,
  salary_history: [],
} as Schemas['EmployeeDetail']

describe('changedFields', () => {
  it('is empty when nothing changed', () => {
    expect(changedFields(employee, fromEmployee(employee))).toEqual({})
  })

  it('sends only the edited fields, ids as numbers', () => {
    const values = { ...fromEmployee(employee), level_id: '3', email: 'asha@acme.example' }
    expect(changedFields(employee, values)).toEqual({ level_id: 3, email: 'asha@acme.example' })
  })

  it('sends an explicit null to clear the manager', () => {
    const values = { ...fromEmployee(employee), manager_id: null }
    expect(changedFields(employee, values)).toEqual({ manager_id: null })
  })
})

describe('toCreateBody', () => {
  it('keeps money as decimal strings and converts ids', () => {
    const body = toCreateBody({
      ...fromEmployee(employee),
      employee_code: 'N00001',
      manager_id: null,
      base_amount: '1500000.50',
      bonus_amount: '',
    })
    expect(body.base_amount).toBe('1500000.50')
    expect(body.bonus_amount).toBe('0')
    expect(body.department_id).toBe(1)
    expect(body.manager_id).toBeNull()
  })
})
