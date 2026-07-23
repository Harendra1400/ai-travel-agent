# Frontend

Next.js 16 App Router application with React 19, TypeScript, Tailwind CSS,
shadcn-compatible primitives, theme switching, Auth.js OIDC, and a functional
planning/approval/itinerary flow.

## Why the App Router

The App Router provides nested layouts, React Server Components, Route Handlers,
server actions, streaming boundaries, and colocated loading/error UI. Here it
keeps OIDC/session work on the server while the planning workspace remains a
small client component for polling and approval interaction.

## TypeScript

`tsconfig.json` enables strict checking, uses the Next.js plugin and bundler module
resolution, preserves JSX for Next.js, and maps `@/*` to `src/*`. API response
contracts are explicit TypeScript types in `src/lib/api.ts`; the optimized build
performs a full type check.

## Commands

```powershell
pnpm install --frozen-lockfile
Copy-Item .env.example .env.local
pnpm dev
pnpm lint
pnpm build
pnpm start
```

The browser calls `/api/backend/*`. That Route Handler reads the encrypted Auth.js
JWT server-side and forwards the OIDC access token to FastAPI, so application code
does not store tokens in local storage. `AUTH_DISABLED=true` is honored only
outside production.

The production Docker image uses Next.js standalone output and runs as a non-root
user.
