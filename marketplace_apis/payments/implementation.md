# Payments API — Implementation Guide

## Authentication

The Payments API uses Bearer token authentication:

```
POST /v1/payment-intents
Host: api.payments.example.com
Authorization: Bearer YOUR_SECRET_KEY
Content-Type: application/json
```

API keys are scoped: use `sk_test_*` for sandbox and `sk_live_*` for production.

## Environment Setup

### Required Environment Variables

```bash
PAYMENTS_API_URL=https://api.payments.example.com/v1
PAYMENTS_SECRET_KEY=sk_test_YOUR_KEY_HERE
PAYMENTS_WEBHOOK_SECRET=whsec_YOUR_SECRET_HERE
```

### Network Requirements

- HTTPS only (port 443)
- Minimum TLS 1.2
- IP allowlisting available for enterprise plans

## Idempotency

All POST endpoints support idempotency via the `Idempotency-Key` header:

```
POST /v1/payment-intents
Idempotency-Key: unique-request-id-123
```

Keys are valid for 24 hours. Duplicate requests return the original response.

## Retry Strategy

- On 429: wait for `Retry-After` header value
- On 5xx: retry up to 3 times with exponential backoff (1s, 2s, 4s)
- Always use idempotency keys for POST requests to avoid duplicate charges

## Webhook Verification

Verify webhook signatures using HMAC-SHA256:

1. Extract the `Payments-Signature` header
2. Compute HMAC-SHA256 of the raw request body using your webhook secret
3. Compare the computed signature with the header value
