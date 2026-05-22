# Staging Deployment Path

Date: 2026-05-22

## Goal

Deploy from `main` automatically to staging with repeatable runtime setup.

## Path

1. CI workflow runs on push to `main`.
2. Build Docker image and run tests/lint.
3. Push image to container registry.
4. Deploy to staging environment via platform CLI/API.

## Required environment variables

- `DATABASE_URL`
- `PORT`
- `NODE_ENV=staging`

## Initial platform target

- Any OCI-compatible platform (Fly.io, Render, Railway, ECS) using the included Dockerfile.

## Promotion policy

- Only green CI builds on `main` are deployable.
- Staging deploy should be idempotent and immutable-image based.

## Verification checklist

- `GET /health` returns `200`
- users/content/metrics endpoints return valid JSON
- migration command succeeds against staging DB
