# Payments API — Swagger / OpenAPI Spec

## Base URL

```
https://api.payments.example.com/v1
```

## Authentication

All endpoints require a Bearer token in the Authorization header.

---

## Endpoints

### Payment Intents

#### POST /payment-intents

Create a new payment intent.

**Request Body:**
```json
{
  "amount": 2500,
  "currency": "usd",
  "payment_method": "card",
  "description": "Order #1234",
  "idempotency_key": "unique-key-123"
}
```

**Response 201:**
```json
{
  "id": "pi_abc123",
  "amount": 2500,
  "currency": "usd",
  "status": "requires_confirmation",
  "created_at": "2025-01-15T10:00:00Z"
}
```

#### POST /payment-intents/{id}/confirm

Confirm a payment intent.

**Response 200:**
```json
{
  "id": "pi_abc123",
  "status": "succeeded",
  "confirmed_at": "2025-01-15T10:01:00Z"
}
```

#### GET /payment-intents/{id}

Retrieve a payment intent by ID.

### Refunds

#### POST /refunds

Create a refund for a payment.

**Request Body:**
```json
{
  "payment_intent_id": "pi_abc123",
  "amount": 1000,
  "reason": "customer_request"
}
```

#### GET /refunds/{id}

Retrieve a refund by ID.

### Transactions

#### GET /transactions

List transactions with filters.

**Parameters:**
| Name | In | Type | Required | Description |
|------|-----|------|----------|-------------|
| start_date | query | datetime | No | Filter from date |
| end_date | query | datetime | No | Filter to date |
| status | query | string | No | Filter by status |
| limit | query | integer | No | Max results (default 20, max 100) |

## Models

### PaymentIntent
| Field | Type | Description |
|-------|------|-------------|
| id | string | Unique identifier (pi_ prefix) |
| amount | integer | Amount in smallest currency unit |
| currency | string | ISO 4217 currency code |
| status | string | `requires_confirmation`, `succeeded`, `failed`, `cancelled` |
| payment_method | string | `card`, `bank_transfer`, `digital_wallet` |

### Refund
| Field | Type | Description |
|-------|------|-------------|
| id | string | Unique identifier (rf_ prefix) |
| payment_intent_id | string | Original payment ID |
| amount | integer | Refund amount |
| reason | string | `customer_request`, `duplicate`, `fraudulent` |
| status | string | `pending`, `succeeded`, `failed` |
