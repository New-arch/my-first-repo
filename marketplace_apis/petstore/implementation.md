# Petstore API — Implementation Guide

## Authentication

The Petstore API supports two authentication methods:

### 1. API Key Authentication

Include your API key in the `api_key` header:

```
GET /v2/pet/findByStatus?status=available
Host: api.petstore.example.com
api_key: YOUR_API_KEY_HERE
```

API keys are issued per partner account. Contact the marketplace team to obtain your key.

### 2. OAuth2 (Implicit Flow)

For user-facing applications, use the OAuth2 implicit flow:

1. Redirect user to: `https://api.petstore.example.com/oauth/authorize?response_type=token&client_id=YOUR_CLIENT_ID`
2. User authenticates and grants access
3. Redirect back to your `redirect_uri` with the access token in the URL fragment
4. Include the token in the `Authorization` header: `Bearer YOUR_ACCESS_TOKEN`

**Token expiry:** 1 hour. Refresh by repeating the flow.

## Environment Setup

### Required Environment Variables

```bash
PETSTORE_API_URL=https://api.petstore.example.com/v2
PETSTORE_API_KEY=YOUR_API_KEY_HERE
# Only for OAuth2 flow:
PETSTORE_CLIENT_ID=YOUR_CLIENT_ID
PETSTORE_REDIRECT_URI=https://yourapp.com/callback
```

### Network Requirements

- HTTPS only (port 443)
- Minimum TLS 1.2
- Outbound access to `api.petstore.example.com`
- No IP allowlisting required

## Rate Limits

| Tier | Requests/hour | Burst limit |
|------|--------------|-------------|
| Free | 100 | 10/min |
| Standard | 1,000 | 100/min |
| Enterprise | 10,000 | 1,000/min |

Rate limit headers are included in every response:
- `X-RateLimit-Limit`: Your hourly limit
- `X-RateLimit-Remaining`: Remaining requests this hour
- `X-RateLimit-Reset`: Unix timestamp when the limit resets

## Retry Strategy

Recommended exponential backoff:

1. On 429 (Too Many Requests): wait `Retry-After` header value
2. On 5xx: retry up to 3 times with backoff (1s, 2s, 4s)
3. On network timeout (>30s): retry once after 5s

## Pagination

List endpoints support cursor-based pagination:

```
GET /v2/pet/findByStatus?status=available&limit=20&cursor=eyJpZCI6MTAwfQ==
```

Response includes `X-Next-Cursor` header for the next page. An empty cursor means no more results.

## Webhooks (Optional)

Register a webhook URL to receive real-time notifications:

```
POST /v2/webhooks
{
  "url": "https://yourapp.com/webhook",
  "events": ["order.placed", "order.delivered", "pet.status_changed"]
}
```

Webhook payloads are signed with HMAC-SHA256 using your webhook secret.
