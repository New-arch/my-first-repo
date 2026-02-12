# Petstore API — Product Brief

## Overview

The Petstore API is a sample marketplace API that manages an online pet store inventory. It allows partners to browse available pets, place orders, and manage their user accounts.

## Business Value

- **Inventory Management**: Real-time visibility into available pets across categories
- **Order Processing**: Streamlined order placement and tracking
- **Partner Onboarding**: Self-service account creation and management
- **Marketplace Integration**: Standard REST API for embedding pet listings in partner applications

## Key Capabilities

1. **Pet Catalog** — Browse, search, and filter pets by status (available, pending, sold)
2. **Order Management** — Place orders, check order status, and manage fulfillment
3. **User Accounts** — Create, update, and manage user profiles
4. **Inventory Tracking** — Real-time stock counts by status

## Target Users

- Marketplace partners integrating pet listings
- E-commerce platforms adding pet categories
- Mobile applications displaying pet inventories

## Use Cases

### UC-1: Partner Storefront
A partner website displays available pets from the Petstore API, allowing customers to browse and place orders directly.

### UC-2: Inventory Sync
A warehouse management system syncs pet inventory status in real-time to keep stock levels accurate across channels.

### UC-3: Order Fulfillment
An order management system places orders via the API and tracks delivery status through to completion.

## Limitations

- Maximum 100 pets per listing request
- Orders must be placed within 24 hours of inventory check
- Rate limit: 1,000 requests per hour per API key
- No bulk order endpoint (orders are placed one at a time)
