# Payments API — Error Codes

## Error Response Format

```json
{
  "error": {
    "code": "insufficient_funds",
    "message": "The card has insufficient funds to complete the purchase.",
    "param": "amount"
  }
}
```

## HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request — invalid parameters |
| 401 | Unauthorized — invalid or missing API key |
| 403 | Forbidden — insufficient permissions |
| 404 | Not Found — resource does not exist |
| 409 | Conflict — idempotency key reuse with different params |
| 422 | Validation Error |
| 429 | Rate Limit Exceeded |
| 500 | Internal Error |

## Application Error Codes

### Payment Errors

| Code | Message | Resolution |
|------|---------|------------|
| insufficient_funds | Card has insufficient funds | Ask customer for alternate payment |
| card_declined | Card was declined | Ask customer to contact their bank |
| expired_card | Card has expired | Ask customer for updated card details |
| invalid_amount | Amount must be positive integer | Verify amount is > 0 |
| currency_not_supported | Currency is not supported | Use a supported ISO 4217 code |
| duplicate_payment | Idempotency key already used | Use a new idempotency key |

### Refund Errors

| Code | Message | Resolution |
|------|---------|------------|
| refund_exceeded | Refund exceeds original amount | Reduce refund amount |
| already_refunded | Payment already fully refunded | No action needed |
| refund_window_closed | 90-day refund window has passed | Process manually |

### Authentication Errors

| Code | Message | Resolution |
|------|---------|------------|
| invalid_api_key | API key is invalid | Check key format and validity |
| key_expired | API key has expired | Generate a new key in dashboard |
| wrong_environment | Using test key in production | Switch to live key (sk_live_*) |
