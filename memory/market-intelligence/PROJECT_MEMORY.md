# Yundor Market Intelligence Project Memory

## Current Phase
Sales Intelligence: Product → Buyer linkage (Sprint 15.69)

## Architecture
- Next.js app with D1 database
- CRM module with leads, contacts, follow-ups
- Hot products ranking from shipment data
- Website verification pipeline
- ImportYeti integration (gateway layer)

## Key Constraints
- No paid API without explicit approval
- Preserve raw data, never NULL existing values
- Incremental changes, no rewrites
- Mac environment, use .wrangler for local D1

## Last Commit
472f12c Sprint 15.68: Link hot products to buyers and sources
