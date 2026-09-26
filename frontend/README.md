# Frontend

React + TypeScript + Vite, Mantine components, TanStack Query for server state, Recharts
for the analytics views.

## Run

```sh
docker compose up --build            # from the repo root: app on http://localhost:8080
```

or against a locally running API:

```sh
npm install
npm run dev                          # http://localhost:5173, /api proxied to :8000
```

## Scripts

| Script | What it does |
|---|---|
| `npm test` | Vitest unit and component tests (jsdom, no network) |
| `npm run typecheck` / `lint` / `format:check` | tsc, oxlint, Prettier |
| `npm run api:types` | Regenerate `src/api/schema.d.ts` from the running API's OpenAPI schema |

## How it is put together

- **One typed API client.** `src/api/schema.d.ts` is generated from FastAPI's OpenAPI
  schema; `openapi-fetch` checks every path, parameter and body against it. Query and
  mutation hooks live in `src/api/<domain>.ts`; each mutation invalidates the views it
  affects (a salary revision refreshes the employee, the list and analytics).
- **Filters live in the URL.** Every list and the dashboard read their filters, sort and
  page from search params (`useUrlParams`), so any view can be bookmarked or shared.
- **Containers and presentational components.** Pages own URL state and queries;
  components under `src/components` render props.
- **Money stays decimal.** Amounts arrive as decimal strings, are formatted from the
  string (`Intl.NumberFormat` keeps exact values) and are sent back as strings. Numbers
  are used only for chart geometry.
- **Charts** use a validated palette (`src/lib/chartColors.ts`): one hue for the pay
  breakdown's bars, paired with a table showing the same figures.
