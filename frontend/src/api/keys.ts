/** Query-key roots; mutations invalidate by root so every dependent view refreshes. */
export const keys = {
  reference: ['reference'] as const,
  employees: ['employees'] as const,
  bands: ['bands'] as const,
  analytics: ['analytics'] as const,
}
