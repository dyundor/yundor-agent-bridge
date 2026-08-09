# Market Intelligence — Knowledge Base

## Architecture

### Stack
- **Framework**: Next.js (App Router) on Cloudflare Workers (vinext)
- **Database**: D1 (SQLite) via `.wrangler/state/v3/d1/miniflare-D1DatabaseObject/*.sqlite`
- **Language**: TypeScript
- **Testing**: Node.js native test runner (`node:test` + `node:assert`)

### Key Modules
| Module | Path | Purpose |
|--------|------|---------|
| Hot Products | `lib/products/hot-products.ts` | Product classification + ranking from shipment data |
| Qualification | `lib/qualification/` | Buyer scoring, classification, supplier intel |
| Leads/CRM | `lib/leads/` | Pipeline, outreach, contacts, feedback |
| Company | `lib/company/` | Website verification, identity resolution |
| Repositories | `lib/repositories/` | D1 data access layer |
| API Routes | `app/api/` | Next.js route handlers |

### Database Tables (key ones)
- `importyeti_web_entities` — company profiles with identity status
- `importyeti_web_shipments` — shipment/BOL records  
- `importyeti_web_relationships` — buyer-supplier relationships
- `buyer_watchlist` — lead pipeline with scores
- `lead_contacts` — verified contact routes
- `lead_actions` — outreach activity log

## Development Patterns

### Commit format
`Sprint XX.XX: Short description`

### API patterns
- All routes use Cloudflare Workers `env.DB` binding
- Query params over dynamic segments
- Import paths use `.ts` extension

### Data rules
- COALESCE(existing, incoming) — never NULL existing values
- Keep raw external data for rebuildable rankings
- Mark unverified instead of NULL-ing out

## Known Limitations
- OpenCode v1.18.15 ignores session `directory` parameter
- Must start `opencode serve` from project directory
- 195 shipment records currently stored (small sample)

## Sprint History
- 15.67: Add hot-selling product intelligence
- 15.68: Link hot products to buyers and sources
- 15.69: Enrich hot product buyers with qualification (157 tests pass)
