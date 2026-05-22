<<<<<<< HEAD
# ai-content
=======
# Core Product Architecture Skeleton

This repository contains the Week 1-4 architecture baseline for a creator-led growth product.

## What is included

- Architecture decision record with service boundaries and tradeoffs
- Minimal API with persistence for users, content, and metrics
- CI pipeline with lint/test workflow
- Staging deployment path definition

## Stack

- Node.js 20
- Express
- Prisma + SQLite (swap to Postgres for staging/prod)

## Quickstart

```bash
npm install
npm run prisma:generate
npm run prisma:migrate
npm run dev
```

API runs on `http://localhost:3000`.

## Endpoints

- `GET /health`
- `POST /users`
- `GET /users`
- `POST /content`
- `GET /content`
- `POST /metrics`
- `GET /metrics`

## CI

GitHub Actions workflow at `.github/workflows/ci.yml` runs install, lint, and tests.

## Staging deployment path

See `docs/deployment/staging.md`.
>>>>>>> ee6801f (Initial project commit)
