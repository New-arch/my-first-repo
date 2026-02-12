# Payments API — Product Brief

## Overview

The Payments API enables marketplace partners to process payments, manage refunds, and track transaction history. It supports credit cards, bank transfers, and digital wallets.

## Business Value

- **Payment Processing**: Accept payments from multiple sources in a single integration
- **Refund Management**: Automated full and partial refund handling
- **Transaction Reporting**: Real-time and historical transaction data for reconciliation
- **Multi-currency**: Support for 30+ currencies with automatic conversion

## Key Capabilities

1. **Payment Intents** — Create and confirm payment intents with idempotency keys
2. **Refunds** — Full or partial refunds with reason tracking
3. **Transaction History** — Query transactions by date range, status, and currency
4. **Webhooks** — Real-time notifications for payment events

## Limitations

- Maximum transaction amount: $50,000 per payment
- Refunds must be requested within 90 days of the original transaction
- Rate limit: 500 requests per minute per API key
- Settlement takes 2-3 business days for bank transfers
