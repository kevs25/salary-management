import { AppShell, Center, Group, Text, Title } from '@mantine/core'

/** The shell; screens are added one page at a time. */
export function App() {
  return (
    <AppShell header={{ height: 56 }} padding="lg">
      <AppShell.Header>
        <Group h="100%" px="lg">
          <Title order={4}>ACME</Title>
          <Text c="dimmed" size="sm">
            Salary management
          </Text>
        </Group>
      </AppShell.Header>
      <AppShell.Main>
        <Center py="xl">
          <Text c="dimmed">The API is ready; screens are added one page at a time.</Text>
        </Center>
      </AppShell.Main>
    </AppShell>
  )
}
