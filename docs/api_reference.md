# API Reference

Base URL: configured via `VITE_API_URL` (frontend) — default
`http://localhost:8000`. Interactive SwaggerUI at `/docs`.

## REST endpoints

| Method | Path | Body / Query | Response |
|--------|------|--------------|----------|
| GET | `/api/health` | — | `{status, version, environment}` |
| GET | `/api/health/ready` | — | `{status, components}` |
| POST | `/api/verify` | `{signature, session_id, channel_snapshot?}` | `VerificationResponse` |
| GET | `/api/verify/history` | `?limit=50` | `[VerificationResponse]` |
| POST | `/api/attack/{attack_type}` | `?intensity=0.5&session_id=` | `AttackResponse` |
| GET | `/api/attack/types` | — | `[attack descriptor]` |
| GET | `/api/dashboard/state` | — | `DashboardSnapshot` |
| GET | `/api/dashboard/metrics` | `?metric=trust_score&limit=50` | `{metric, points[], count}` |
| GET | `/api/dashboard/nh-spectrum` | `?tampering=0.0` | `{spectrum, baseline, exceptional_points}` |
| GET | `/api/logs` | `?limit=100&severity=` | `[SecurityEvent]` |
| GET | `/api/logs/export` | — | full log export payload |
| WS | `/ws/live` | — | streamed frames (below) |

`attack_type` ∈ `forgery | impersonation | replay | channel_tampering | coherent`.

## Core schemas

**VerificationResponse**

```json
{
  "verdict": "authentic | suspicious | rejected",
  "decision": "ACCEPT | QUARANTINE | REJECT",
  "trust_score": 0.9989,
  "hom_visibility": 0.98,
  "channel_fidelity": 0.95,
  "layer_results": [
    {"layer_id": 0, "layer_name": "QGM", "verdict": "authentic",
     "confidence": 0.9956, "metrics": {"hamming_distance": 0.0044, "...": 0}}
  ]
}
```

**AttackResponse**

```json
{
  "attack_type": "forgery",
  "detected": true,
  "trust_score_after": 0.7035,
  "details": {"attack_intensity": 0.6, "decision": "REJECT",
              "deviations": {"QGM": 0.004, "HIS": 0.982}, "chernoff_bound": 0.83}
}
```

**SecurityEvent**

```json
{"timestamp": "2026-09-12T17:19:31+00:00", "severity": "warning",
 "source": "attack.replay", "message": "Attack replay DETECTED | ...",
 "session_id": "smoke-1"}
```

## WebSocket protocol (`/ws/live`)

Three frame types, one JSON object per message:

**`dashboard_update`** — pushed every 500 ms:

```json
{"type": "dashboard_update",
 "data": {"layer_statuses": [{"layer_id": 0, "layer_name": "QGM",
                              "status": "PASS", "deviation_score": 0.004}, "..."],
          "trust_score": 0.984,
          "recent_events": ["... up to 20 SecurityEvent objects"],
          "metrics": {"hom_visibility": 0.98, "channel_fidelity": 0.99}}}
```

**`new_event`** — pushed the moment a security event is recorded:

```json
{"type": "new_event", "data": {"timestamp": "...", "severity": "info",
                               "source": "verification", "message": "...",
                               "decision": "accept", "trust_score": 0.998}}
```

**`attack_detected`** — pushed as soon as an attack simulation completes:

```json
{"type": "attack_detected",
 "data": {"attack_type": "forgery", "detected": true, "trust_score_after": 0.703,
          "decision": "REJECT", "details": {"deviations": {}, "chernoff_bound": 0.83}}}
```

## Error model

- `422` — payload validation failure (pydantic detail array in the body).
- `404` — unknown route.
- WS frames with `"type": "error"` carry an internal snapshot failure detail.
