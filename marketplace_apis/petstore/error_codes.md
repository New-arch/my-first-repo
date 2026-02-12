# Petstore API — Error Codes

## Error Response Format

All errors follow a consistent JSON structure:

```json
{
  "code": 404,
  "type": "error",
  "message": "Pet not found"
}
```

## HTTP Status Codes

| Code | Meaning | When |
|------|---------|------|
| 200 | Success | Request completed successfully |
| 400 | Bad Request | Invalid input, missing required fields |
| 401 | Unauthorized | Missing or invalid API key / token |
| 403 | Forbidden | Valid credentials but insufficient permissions |
| 404 | Not Found | Resource does not exist |
| 405 | Method Not Allowed | HTTP method not supported for this endpoint |
| 409 | Conflict | Resource already exists (e.g., duplicate username) |
| 422 | Validation Error | Input fails validation rules |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Unexpected server-side failure |

## Application Error Codes

### Pet Errors (1xxx)

| Code | Message | Resolution |
|------|---------|------------|
| 1001 | Pet not found | Verify the pet ID exists using GET /pet/{id} |
| 1002 | Invalid pet status | Use one of: `available`, `pending`, `sold` |
| 1003 | Pet name required | Include `name` field in request body |
| 1004 | Invalid photo URL | Ensure URLs are valid HTTPS URLs |
| 1005 | Pet already sold | Cannot modify a pet with status `sold` |

### Order Errors (2xxx)

| Code | Message | Resolution |
|------|---------|------------|
| 2001 | Order not found | Verify the order ID |
| 2002 | Pet not available | Pet status must be `available` to place an order |
| 2003 | Invalid quantity | Quantity must be between 1 and 10 |
| 2004 | Order expired | Orders expire after 24 hours if not approved |
| 2005 | Duplicate order | An active order already exists for this pet |

### User Errors (3xxx)

| Code | Message | Resolution |
|------|---------|------------|
| 3001 | User not found | Verify the username |
| 3002 | Username taken | Choose a different username |
| 3003 | Invalid email format | Provide a valid email address |
| 3004 | Password too weak | Minimum 8 characters, 1 uppercase, 1 number |
| 3005 | Session expired | Re-authenticate using /user/login |

### Authentication Errors (4xxx)

| Code | Message | Resolution |
|------|---------|------------|
| 4001 | Invalid API key | Check your API key is correct and active |
| 4002 | API key revoked | Contact support to reactivate |
| 4003 | Token expired | Re-authenticate to get a new token |
| 4004 | Insufficient scope | Request additional OAuth2 scopes |
| 4005 | Account suspended | Contact support |

### Rate Limit Errors (5xxx)

| Code | Message | Resolution |
|------|---------|------------|
| 5001 | Hourly limit exceeded | Wait until `X-RateLimit-Reset` timestamp |
| 5002 | Burst limit exceeded | Slow down request frequency |
| 5003 | Daily quota reached | Upgrade your plan or wait until midnight UTC |
