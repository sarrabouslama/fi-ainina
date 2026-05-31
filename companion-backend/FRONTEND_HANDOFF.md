# Frontend Handoff: Companion Backend

This file is the implementation guide for the React team. It summarizes what the backend already provides, what the frontend must send, and what it should listen for.

## What The Backend Does

The backend is the API gateway for the system. It does not talk directly to fall detection or emotion detection. Those services publish to Redis, the alerts service consumes them, and the backend receives processed alert updates from the alerts service over WebSocket.

It also handles:

- Authentication and session management
- Role-based dashboard data
- User CRUD and GDPR consent / erasure flows
- Review threads between caregivers and admins
- Real-time push updates via WebSocket
- Health status polling for downstream services

## Roles And Scope

There are three roles:

- `admin`: global access, sees all users and all reviews
- `caregiver`: sees assigned elderly users and their own review threads
- `elderly`: sees self-only data

The dashboard payload already returns a `role` and a `scope` object so the frontend can render the correct level of visibility without re-deriving permissions.

## Auth Flow

### Login

- `POST /auth/login`
- Body: `{ "email": "...", "password": "..." }`
- Response: `{ "access_token": "...", "token_type": "bearer" }`
- Refresh token is set as an `httpOnly` cookie.

### Refresh

- `POST /auth/refresh`
- Uses the refresh cookie.
- Returns a rotated access token and refresh cookie.

### Logout

- `POST /auth/logout`
- Invalidates the token in Redis.

### Current User

- `GET /auth/me`
- Used to bootstrap the logged-in user on the frontend.
- Returns `consent_given` and `consent_date` so the frontend can decide whether to render the dashboard or the consent gate.

### Consent Gate Flow

If `GET /auth/me` returns `consent_given: false`, the React app should replace the entire dashboard with a full-screen consent gate.

The backend already exposes the consent update endpoint:

- `POST /users/{id}/consent`
- Body: `{ "consent_given": true }`

When the user agrees, the frontend should call that endpoint, then reload the normal dashboard state.

When the user declines, the frontend should log them out and fall back to a minimal read-only view that only shows system status, an emergency contact action, and a way to reopen the consent flow later.

Consent is not stored in localStorage. The frontend should treat `/auth/me` as the source of truth on every page load or route change.

### Login Lockout

- After 5 failed attempts, the account is locked for 15 minutes.
- The frontend should show a lockout message if login returns `429`.

## Dashboard APIs

### Overview

- `GET /dashboard/overview`
- Returns role-aware aggregated state.

Response shape includes:

- `role`
- `scope`
- `services_health`
- `active_alerts`
- `today_stats`
- `user_stats` for admins
- `review_stats`
- `users`

The frontend should use this endpoint to populate the main dashboard cards and per-user summary panels.

### Alerts List

- `GET /dashboard/alerts?status=&type=&from=&to=&page=&limit=`
- Returns alert history.

### Conversations List

- `GET /dashboard/conversations?from=&to=`
- Returns conversation sessions.

## Real-Time WebSocket Feed

### Dashboard Push Channel

- `ws://backend/ws/events?token=<access_token>`

The frontend must connect with a valid access token in the query string.

### WebSocket Event Types

The backend broadcasts these event types:

- `alert_escalated`
- `service_health_change`
- `review_message_created`

### Event Payloads

#### Alert Escalation

```json
{
  "type": "alert_escalated",
  "payload": {
    "alert_id": 123,
    "user_id": "user-1",
    "alert_type": "fall",
    "severity": "high"
  }
}
```

#### Service Health Change

```json
{
  "type": "service_health_change",
  "payload": {
    "service": "llm",
    "status": "unhealthy"
  }
}
```

#### Review Message Created

```json
{
  "type": "review_message_created",
  "payload": {
    "review_id": 12,
    "alert_id": 99,
    "review_type": "false_positive",
    "subject": "Fall alert was false positive",
    "status": "replied",
    "sender_role": "admin",
    "message_type": "reply",
    "content_preview": "We will get back to you.",
    "timestamp": "2026-05-30T12:00:00+00:00"
  }
}
```

## Alerts Service WebSocket Bridge

The backend already receives processed alert events from the alerts service and persists them to the database. The frontend does not connect to the alerts service directly.

When the backend receives an alert event, it stores the alert and forwards a dashboard WebSocket event so the UI can update immediately.

## Reviews Workflow

This is the new caregiver-to-admin review flow.

### Create Review

- `POST /reviews`
- Allowed for `caregiver` and `admin`.
- Use this when something is wrong with the system, or when an alert was a false positive / false negative.

Request body:

```json
{
  "review_type": "false_positive",
  "subject": "Fall alert was false positive",
  "content": "The alert was triggered by a chair moving.",
  "alert_id": 99
}
```

### Admin Reply

- `POST /reviews/{review_id}/reply`
- Allowed for `admin` only.
- If the admin sends an empty string or omits content, the backend automatically uses:

```text
We will get back to you.
```

### List Reviews

- `GET /reviews`
- Admin sees all reviews.
- Caregiver sees their own reviews.

### Review Detail

- `GET /reviews/{review_id}`
- Returns the review plus the full message thread.

### Push Notification Requirement

Whenever a new review message is created, the backend broadcasts a WebSocket event of type `review_message_created`. The frontend should treat this as the push notification trigger and update:

- Review inbox / thread list
- Toast or badge count
- Review detail thread if open

## Users And GDPR

### User CRUD

- `POST /users` for admin-only creation
- `GET /users` for admin-only listing
- `GET /users/{id}` for self or admin
- `PATCH /users/{id}` for self or admin
- `DELETE /users/{id}` for admin

### Consent

- `POST /users/{id}/consent`
- Used to record explicit GDPR consent from the elderly user.

### Erasure

- `DELETE /users/{id}/data`
- This anonymizes the user record and scrubs personal content from conversations and alert metadata.

The frontend should expose this carefully and make the irreversible nature of erasure obvious.

## Health And Status

- `GET /health`
- Returns overall status plus per-service state and latency.

The backend also polls `llm` and `voice_assistant` every 30 seconds and broadcasts health changes through the dashboard WebSocket.

## UI Expectations

### Admin UI

Should show:

- Global dashboard stats
- All monitored users
- Review inbox across all caregivers and users
- Alert history and system health

### Caregiver UI

Should show:

- Assigned elderly users only
- Their alert history and active alerts
- Review inbox for their own submitted reviews
- Ability to create a new review when something looks wrong

### Elderly UI

Should show:

- Self-only overview
- Own conversations and alerts, if exposed

### When Consent Is Missing

If the authenticated user has not given GDPR consent:

- No dashboard content should be visible behind the gate
- The consent screen should not be dismissible by clicking outside or pressing Escape
- The gate should explain what data is collected, why it is collected, who can access it, and that consent can be withdrawn later from settings
- If the user declines, show only a minimal read-only surface with system status and emergency contact access

## Frontend Integration Notes

- Always send `Authorization: Bearer <access_token>` for protected HTTP requests.
- Keep the WebSocket open after login and reconnect on disconnect.
- Update the UI from WebSocket events rather than polling whenever possible.
- Use the overview endpoint as the initial page load source.
- Treat `review_message_created` as both an inbox update and a push notification source.

## Suggested Screens

- Login
- Admin dashboard
- Caregiver dashboard
- User detail panel
- Alert history page
- Review inbox / review thread page
- Health status panel
