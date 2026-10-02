# Troubleshooting

## Frontend shows "Failed to fetch"
If the Next.js frontend shows a "Failed to fetch" network error on every request, check the following:

1. **API running:** Ensure the backend is up and running by executing `docker compose ps` and verifying the `backend` service is healthy.
2. **Ports:** Ensure the backend port 8000 is published to the host in development. Check `curl -i http://localhost:8000/health`.
3. **CORS:** Ensure `AURA_CORS_ORIGINS` in your environment contains exactly `http://localhost:3000` without wildcards.
4. **HTTPS Upgrades:** Ensure `AURA_ENV=development`. If the backend sends a `Strict-Transport-Security` (HSTS) header or the frontend uses a CSP with `upgrade-insecure-requests`, the browser will force requests to `https://localhost:8000`, causing fetch to fail if the server only speaks HTTP.
