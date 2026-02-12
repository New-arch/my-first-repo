# Petstore API — Swagger / OpenAPI Spec

## Base URL

```
https://api.petstore.example.com/v2
```

## Authentication

All endpoints require an `api_key` header or OAuth2 bearer token.

---

## Endpoints

### Pet

#### GET /pet/findByStatus

Find pets by status.

**Parameters:**
| Name | In | Type | Required | Description |
|------|-----|------|----------|-------------|
| status | query | string | Yes | Status filter: `available`, `pending`, `sold` |

**Response 200:**
```json
[
  {
    "id": 1,
    "name": "Rex",
    "category": { "id": 1, "name": "Dogs" },
    "photoUrls": ["https://example.com/rex.jpg"],
    "tags": [{ "id": 1, "name": "friendly" }],
    "status": "available"
  }
]
```

#### GET /pet/{petId}

Find pet by ID.

**Parameters:**
| Name | In | Type | Required | Description |
|------|-----|------|----------|-------------|
| petId | path | integer | Yes | ID of pet to return |

**Response 200:**
```json
{
  "id": 1,
  "name": "Rex",
  "category": { "id": 1, "name": "Dogs" },
  "photoUrls": ["https://example.com/rex.jpg"],
  "tags": [{ "id": 1, "name": "friendly" }],
  "status": "available"
}
```

**Response 404:** Pet not found

#### POST /pet

Add a new pet to the store.

**Request Body:**
```json
{
  "name": "Rex",
  "category": { "id": 1, "name": "Dogs" },
  "photoUrls": ["https://example.com/rex.jpg"],
  "tags": [{ "id": 1, "name": "friendly" }],
  "status": "available"
}
```

**Response 200:** Pet object created

#### PUT /pet

Update an existing pet.

**Request Body:** Same as POST /pet but with `id` field included.

**Response 200:** Updated pet object
**Response 404:** Pet not found

#### DELETE /pet/{petId}

Delete a pet.

**Parameters:**
| Name | In | Type | Required | Description |
|------|-----|------|----------|-------------|
| petId | path | integer | Yes | ID of pet to delete |

**Response 200:** Pet deleted
**Response 404:** Pet not found

---

### Store

#### POST /store/order

Place an order for a pet.

**Request Body:**
```json
{
  "petId": 1,
  "quantity": 1,
  "shipDate": "2025-01-15T10:00:00Z",
  "status": "placed",
  "complete": false
}
```

**Response 200:**
```json
{
  "id": 10,
  "petId": 1,
  "quantity": 1,
  "shipDate": "2025-01-15T10:00:00Z",
  "status": "placed",
  "complete": false
}
```

#### GET /store/order/{orderId}

Find purchase order by ID.

**Response 200:** Order object
**Response 404:** Order not found

#### DELETE /store/order/{orderId}

Delete purchase order by ID.

#### GET /store/inventory

Returns pet inventories by status.

**Response 200:**
```json
{
  "available": 42,
  "pending": 5,
  "sold": 120
}
```

---

### User

#### POST /user

Create user.

**Request Body:**
```json
{
  "username": "partner1",
  "firstName": "Jane",
  "lastName": "Doe",
  "email": "jane@example.com",
  "password": "securepassword",
  "phone": "+1234567890",
  "userStatus": 1
}
```

#### GET /user/{username}

Get user by username.

#### PUT /user/{username}

Update user.

#### DELETE /user/{username}

Delete user.

#### GET /user/login

Log in and receive session token.

**Parameters:**
| Name | In | Type | Required | Description |
|------|-----|------|----------|-------------|
| username | query | string | Yes | Username |
| password | query | string | Yes | Password |

**Response 200:** Session token in `X-Session-Token` header

#### GET /user/logout

Log out current session.

---

## Models

### Pet
| Field | Type | Description |
|-------|------|-------------|
| id | integer | Unique identifier |
| name | string | Pet name (required) |
| category | Category | Pet category |
| photoUrls | string[] | Photo URLs (required) |
| tags | Tag[] | Tags for filtering |
| status | string | `available`, `pending`, `sold` |

### Category
| Field | Type | Description |
|-------|------|-------------|
| id | integer | Category ID |
| name | string | Category name |

### Tag
| Field | Type | Description |
|-------|------|-------------|
| id | integer | Tag ID |
| name | string | Tag name |

### Order
| Field | Type | Description |
|-------|------|-------------|
| id | integer | Order ID |
| petId | integer | ID of ordered pet |
| quantity | integer | Number of pets |
| shipDate | datetime | Scheduled ship date |
| status | string | `placed`, `approved`, `delivered` |
| complete | boolean | Whether order is complete |
