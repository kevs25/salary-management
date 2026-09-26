import { AppShell, Center, Group, Loader, NavLink, Text, Title } from '@mantine/core'
import { lazy, Suspense } from 'react'
import { Navigate, NavLink as RouterLink, Route, Routes, useLocation } from 'react-router-dom'

// One chunk per screen, loaded when first visited.
const DashboardPage = lazy(() =>
  import('./pages/DashboardPage').then((m) => ({ default: m.DashboardPage })),
)
const EmployeesPage = lazy(() =>
  import('./pages/EmployeesPage').then((m) => ({ default: m.EmployeesPage })),
)
const EmployeeDetailPage = lazy(() =>
  import('./pages/EmployeeDetailPage').then((m) => ({ default: m.EmployeeDetailPage })),
)

const NAV = [
  { to: '/dashboard', label: 'Dashboard', hint: 'How the org pays people' },
  { to: '/employees', label: 'Employees', hint: 'Find, add, revise pay' },
]

export function App() {
  const { pathname } = useLocation()
  return (
    <AppShell header={{ height: 56 }} navbar={{ width: 230, breakpoint: 'sm' }} padding="lg">
      <AppShell.Header>
        <Group h="100%" px="lg">
          <Title order={4}>ACME</Title>
          <Text c="dimmed" size="sm">
            Salary management
          </Text>
        </Group>
      </AppShell.Header>
      <AppShell.Navbar p="sm">
        {NAV.map((item) => (
          <NavLink
            key={item.to}
            component={RouterLink}
            to={item.to}
            label={item.label}
            description={item.hint}
            active={pathname.startsWith(item.to)}
          />
        ))}
      </AppShell.Navbar>
      <AppShell.Main>
        <Suspense
          fallback={
            <Center py="xl">
              <Loader />
            </Center>
          }
        >
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/employees" element={<EmployeesPage />} />
            <Route path="/employees/:employeeId" element={<EmployeeDetailPage />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </Suspense>
      </AppShell.Main>
    </AppShell>
  )
}
