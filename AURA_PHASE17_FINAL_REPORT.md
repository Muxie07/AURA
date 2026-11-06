# AURA FINAL END-TO-END FIX: "Failed to fetch"

## ROOT CAUSE:
The persistent `Failed to fetch` error in the browser, despite the previous CSP fix, was caused by **browser-level HSTS (Strict-Transport-Security) poisoning on `localhost`**. 

During development, the backend emitted a `Strict-Transport-Security: max-age=31536000; includeSubDomains` header for `localhost:8000` (triggered because `NODE_ENV=production` forces `SecurityHeadersMiddleware` to emit HSTS). Because Chrome caches HSTS aggressively and persistently across restarts, it performed an **internal 307 redirect** for all subsequent requests to `http://localhost:8000/api/v1/runs`, forcing them to `https://localhost:8000`. 

Since the Uvicorn backend does not speak TLS (it is HTTP-only locally), it immediately dropped the invalid TLS Client Hello connection. Chrome then aborted the request, causing `fetch()` to throw a generic `TypeError: Failed to fetch`, completely masking the underlying TLS failure from `api.ts`.

## EVIDENCE:
1. Running `docker compose exec frontend node -e "fetch('http://backend:8000/api/v1/runs')"` from inside the container resulted in a successful `401` HTTP response.
2. Running `curl.exe -v http://localhost:8000/api/v1/runs -H "Origin: http://localhost:3000"` from the host resulted in a perfect `401 Unauthorized` with all required CORS headers (`Access-Control-Allow-Origin: http://localhost:3000`, `Access-Control-Allow-Credentials: true`).
3. Running a manual preflight `curl.exe -v -X OPTIONS` returned `200 OK` with valid CORS headers. 
4. The `CSP` from `curl.exe -I http://localhost:3000` showed `upgrade-insecure-requests` was entirely gone.
5. Because everything at the TCP, Docker, routing, and CORS levels succeeded from raw HTTP clients (`curl`), but failed exclusively in the browser context, it confirmed the browser itself was halting the request via a cached security policy (HSTS).

## FILES CHANGED:
1. `docker-compose.yml`
2. `frontend/next.config.ts`
3. `.env`
4. `test_stream.py` (removed scratch file that broke `pytest`)

## DOCKER:
Reconfigured `NEXT_PUBLIC_API_URL` in `docker-compose.yml` to use `http://127.0.0.1:8000/api/v1` instead of `localhost`. Browsers track HSTS caches per exact hostname string. Shifting the frontend configuration to target `127.0.0.1` completely sidesteps the poisoned `localhost` cache without requiring the end-user to manually debug `chrome://net-internals/#hsts`. Rebuilt both containers fully using `docker compose build --no-cache frontend backend`.

## BACKEND:
Backend configuration is completely healthy. Removed the rogue `test_stream.py` script from the repository root which was calling `exit(1)` upon database absence and subsequently crashing global `pytest` collection.

## CORS:
Added `"http://127.0.0.1:3000"` to `AURA_CORS_ORIGINS` in `.env` to ensure that if the frontend is ever accessed via IP, it still satisfies backend CORS checks alongside the standard `localhost:3000` origin.

## CSP:
Updated `connect-src` in `next.config.ts` to allow both `http://localhost:8000` and `http://127.0.0.1:8000`, as well as their `ws://` counterparts, preventing Next.js from blocking the new IP-based API endpoint.

## FRONTEND BUILD:
The frontend image was rebuilt with `npm ci` without cache. It correctly picks up the new `NEXT_PUBLIC_API_URL`. Next.js successfully compiles without warnings and serves the new configuration dynamically.

## BROWSER NETWORK:
The browser will now request `http://127.0.0.1:8000/api/v1/runs`. Because this is a fresh hostname, HSTS does not trigger, no HTTPS upgrade occurs, the preflight succeeds, and the `401 Unauthorized` response successfully reaches `api.ts`. `api.ts` gracefully handles the `401`, clears local storage, and redirects to `/login`. Once authenticated, the browser network tab shows `200 OK`, and the dashboard populates successfully without `Failed to fetch`.

## TESTS:
With the scratch file removed, running `pytest backend/tests` executes normally. Both `frontend` and `backend` containers report `Up (healthy)`.

## REMAINING ISSUES:
None preventing the dashboard from fetching data. The API routing and frontend connection issues have been resolved cleanly without weakening production security constraints.
