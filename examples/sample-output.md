# Sample output

Illustrative output from `t3chats.py` (project names, ids and content are made up).

## `projects`

```
* my-api                                   6 threads  last 2026-01-15T16:42  /home/dev/repos/my-api
  web-dashboard                           12 threads  last 2026-01-14T10:05  /home/dev/repos/web-dashboard
  infra                                    3 threads  last 2026-01-09T08:31  /home/dev/repos/infra

* = project for the current directory
```

## `threads`

```
# Threads in my-api (newest first)

- 2026-01-15T16:42  Refactor auth  (38 msgs, branch feat/auth-refactor)
  id 3f1c2a9e-7b4d-4e21-9c55-0a8f6d2b1e47
- 2026-01-12T11:20  Fix flaky integration tests  (14 msgs, branch main)
  id a07d5e33-1c9b-4f0e-8d72-5b6e4c3a2f10
```

## `read "refactor auth" --last 3`

```
# Refactor auth
project: my-api · id: 3f1c2a9e-7b4d-4e21-9c55-0a8f6d2b1e47 · branch: feat/auth-refactor · model: … · created 2026-01-13T09:02 · updated 2026-01-15T16:42

(showing last 3 of 38 messages)

### USER · 2026-01-15 16:30:12
ok go ahead and move token refresh into the middleware

### ASSISTANT · 2026-01-15 16:30:20
I'll move refresh handling into `auth/middleware.ts`, keep the old helper as a thin wrapper for now, and run the auth tests.

### ASSISTANT · 2026-01-15 16:42:03
Done. Refresh now happens in the middleware; `refreshToken()` delegates to it. 41/41 auth tests pass. Not committed.
```

## `read "refactor auth" --last 1 --activity`

```
### USER · 2026-01-15 16:30:12
ok go ahead and move token refresh into the middleware

### ASSISTANT · 2026-01-15 16:30:20
I'll move refresh handling into `auth/middleware.ts`, ...
- `$ git status --short --branch` → exit 0
- file change: /home/dev/repos/my-api/src/auth/middleware.ts
- file change: /home/dev/repos/my-api/src/auth/refresh.ts
- `$ npm test -- auth` → exit 0
  ```
  Tests: 41 passed, 41 total
  ```

### ASSISTANT · 2026-01-15 16:42:03
Done. Refresh now happens in the middleware; ...
```

## `search "retry" --all`

```
- 2026-01-14T10:01 [web-dashboard] Polling cleanup (assistant)
  id 9b2e…
  …switched to exponential backoff with a max of 5 retry attempts, matching the API client…
```
