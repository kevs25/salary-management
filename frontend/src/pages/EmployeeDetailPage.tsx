import { Anchor, Button, Grid, Group, Paper, SimpleGrid, Stack, Text, Title } from '@mantine/core'
import { type ReactNode, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useEmployee } from '../api/employees'
import { StatusBadge } from '../components/Badges'
import { EmployeeFormModal } from '../components/employees/EmployeeFormModal'
import { PayAssessmentCard } from '../components/employees/PayAssessmentCard'
import { ReviseSalaryModal } from '../components/employees/ReviseSalaryModal'
import { SalaryHistory } from '../components/employees/SalaryHistory'
import { QueryStatus } from '../components/QueryStatus'
import { formatDate, formatMoney, formatUsd } from '../lib/format'

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <Text size="xs" c="dimmed">
        {label}
      </Text>
      <Text size="sm">{children}</Text>
    </div>
  )
}

export function EmployeeDetailPage() {
  const employeeId = Number(useParams().employeeId)
  const { data: employee, isPending, error } = useEmployee(employeeId)
  const [editing, setEditing] = useState(false)
  const [revising, setRevising] = useState(false)
  const current = employee?.current_salary

  return (
    <QueryStatus isPending={isPending} error={error}>
      {employee && (
        <Stack>
          <Anchor component={Link} to="/employees" size="sm">
            ← Employees
          </Anchor>
          <Group justify="space-between" align="flex-start">
            <div>
              <Group gap="sm">
                <Title order={2}>
                  {employee.first_name} {employee.last_name}
                </Title>
                <StatusBadge status={employee.status} />
              </Group>
              <Text c="dimmed">
                {employee.employee_code} · {employee.role.name}, {employee.level.code} ·{' '}
                {employee.country.name}
              </Text>
            </div>
            <Group>
              <Button variant="default" onClick={() => setEditing(true)}>
                Edit
              </Button>
              <Button
                onClick={() => setRevising(true)}
                disabled={!current || employee.status === 'terminated'}
              >
                Revise salary
              </Button>
            </Group>
          </Group>

          <Grid>
            <Grid.Col span={{ base: 12, md: 5 }}>
              <Stack>
                <Paper withBorder p="md">
                  <Text fw={600} mb="sm">
                    Current pay
                  </Text>
                  {current ? (
                    <SimpleGrid cols={2}>
                      <Field label="Annual base">
                        {formatMoney(current.base_amount, current.currency_code)}
                      </Field>
                      <Field label="Annual bonus">
                        {formatMoney(current.bonus_amount, current.currency_code)}
                      </Field>
                      <Field label="Base in USD">{formatUsd(current.base_amount_usd)}</Field>
                      <Field label="Since">{formatDate(current.effective_from)}</Field>
                    </SimpleGrid>
                  ) : (
                    <Text c="dimmed">No current salary record.</Text>
                  )}
                </Paper>
                <PayAssessmentCard assessment={employee.pay_assessment} />
                <Paper withBorder p="md">
                  <Text fw={600} mb="sm">
                    Profile
                  </Text>
                  <SimpleGrid cols={2}>
                    <Field label="Department">{employee.department.name}</Field>
                    <Field label="Role">{employee.role.name}</Field>
                    <Field label="Level">
                      {employee.level.code} · {employee.level.name}
                    </Field>
                    <Field label="Country">
                      {employee.country.name} ({employee.country.currency_code})
                    </Field>
                    <Field label="Email">{employee.email}</Field>
                    <Field label="Hired">{formatDate(employee.hire_date)}</Field>
                    <Field label="Manager">
                      {employee.manager ? (
                        <Anchor component={Link} to={`/employees/${employee.manager.id}`}>
                          {employee.manager.full_name}
                        </Anchor>
                      ) : (
                        '—'
                      )}
                    </Field>
                  </SimpleGrid>
                </Paper>
              </Stack>
            </Grid.Col>
            <Grid.Col span={{ base: 12, md: 7 }}>
              <SalaryHistory history={employee.salary_history} />
            </Grid.Col>
          </Grid>

          <EmployeeFormModal
            opened={editing}
            onClose={() => setEditing(false)}
            employee={employee}
          />
          {current && (
            <ReviseSalaryModal
              opened={revising}
              onClose={() => setRevising(false)}
              employeeId={employee.id}
              current={current}
            />
          )}
        </Stack>
      )}
    </QueryStatus>
  )
}
