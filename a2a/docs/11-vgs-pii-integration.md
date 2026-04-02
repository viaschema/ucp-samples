# VGS PII Integration

## TL;DR

- **VGS (Very Good Security)** provides secure PII tokenization — raw data is stored in VGS vault, the backend works with opaque aliases
- **Two handler types**: PII handlers (VGS) manage secure storage/delivery; lending handlers manage lenders and loan applications
- **Three data paths**: VGS Collect JS (frontend), inbound routes (tokenize in transit), outbound routes (enrich for lenders)
- **Backend never sees raw PII** in VGS mode — aliases flow through Python code, VGS reveals them only in transit to lenders

## Architecture

```
┌─────────────┐     VGS Collect JS      ┌─────────────┐
│   Browser    │ ──── (iframes) ────────>│ VGS Inbound │
│  (React App) │                         │   Route      │
└─────────────┘                         └──────┬──────┘
                                               │ tokenizes PII
                                               │ forwards aliases
                                        ┌──────▼──────┐
                                        │   Backend    │
                                        │ (aliases     │
                                        │  only)       │
                                        └──────┬──────┘
                                               │ forward_pii()
                                        ┌──────▼──────┐
                                        │ VGS Outbound │
                                        │   Route      │──── enriches ────> Lender API
                                        └─────────────┘    (real PII)
```

## Handler Pattern

The system uses the same handler pattern as payments, with two independent handler types declared in `ucp.json`:

```json
{
  "pii": {
    "handlers": [{
      "id": "vgs_pii_provider",
      "name": "vgs.pii.provider",
      "version": "2026-01-11"
    }]
  },
  "lending": {
    "handlers": [{
      "id": "marketplace_lending",
      "name": "marketplace.lending.provider",
      "version": "2026-01-11",
      "supported_loan_types": ["personal", "car"]
    }]
  }
}
```

The lending handler is PII-agnostic — it doesn't reference which PII handler is used. PII delivery to lenders is handled entirely by the PII provider's `forward_pii()` method, which routes through VGS outbound proxy.

## Provider Architecture

### BasePIIProvider (shared logic)

`BasePIIProvider` ABC in `pii_provider.py` implements token/consent machinery shared by all providers:

- `process_pii()` — validate a PII token (TTL, platform scope)
- `issue_token()` — mint a field-scoped, platform-scoped token
- `issue_consent()` — process consent, record it, mint per-lender tokens

### MockPIIProvider (in-memory)

Extends `BasePIIProvider`. Stores raw PII in a Python dict. Used for testing (`PII_PROVIDER=mock`).

### VGSPIIProvider (VGS vault)

Extends `BasePIIProvider`. Stores VGS alias IDs (not raw PII). Key differences:

- `store_pii()` — detects whether values are VGS aliases (from inbound route) or raw values (fallback), tokenizes via `aliases.redact()` if needed
- `resolve_token()` — calls `aliases.reveal()` to get real values (used for debugging/fallback)
- `forward_pii()` — sends aliases through VGS outbound proxy which enriches them in transit

## VGS Collect JS (Frontend)

The `VGSPIICollectionForm` component renders all PII fields as VGS Collect iframes:

| Field | VGS Type | Notes |
|-------|----------|-------|
| first_name, last_name, email, phone | `text` | Standard text input |
| date_of_birth | `date` | Date picker with min validation |
| annual_income, monthly_payment | `text` | Numeric text |
| living_situation, employment_status | `dropdown` | VGS dropdown with options |
| address_region (state) | `dropdown` | US states |
| address_country | `dropdown` | Country list |
| postal_code | `zip-code` | VGS zip validation |
| street_address, city | `text` | Standard text |

The form submits through the VGS reverse proxy, which tokenizes PII fields via the inbound route before forwarding to the backend.

## VGS Routes

### Inbound Route (`routes/inbound_pii_store.yaml`)

Matches `POST /pii/store`. REDACTs (tokenizes) all PII fields in the request body. The backend receives VGS alias IDs instead of raw values.

### Outbound Route (`routes/outbound_lender.yaml`)

Matches `POST /lender-api/*`. ENRICHes (detokenizes) VGS aliases before forwarding to lender API endpoints. The backend sends aliases; the lender receives real PII.

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `VGS_VAULT_ID` | VGS vault identifier |
| `VGS_USERNAME` | Runtime access credential key |
| `VGS_PASSWORD` | Runtime access credential secret |
| `VGS_ENVIRONMENT` | `sandbox` or `live` |
| `PII_PROVIDER` | `mock` for in-memory, omit for VGS |
| `LENDER_API_BASE` | Base URL for lender API (ngrok URL in dev) |

## Dependency Injection

Provider construction happens in `dependencies.py:create_lending_dependencies()`, called from `main.py` after `load_dotenv()`. No import-time side effects in `lending_tools.py` — dependencies are injected via `init_lending()`.

## Local Development Setup

1. Set VGS credentials in `.env`
2. Run ngrok: `ngrok http 10999`
3. Update `LENDER_API_BASE` in `.env` with ngrok URL
4. Apply VGS routes: `vgs apply routes --vault $VGS_VAULT_ID -f routes/inbound_pii_store.yaml`
5. Start server: `uv run business_agent`

## Security

- VGS Collect JS loaded with SRI integrity hash (`index.html`)
- SSL verification disabled only in sandbox mode (`dependencies.py`)
- Raw PII never at rest in the backend (only VGS aliases)
- Per-lender token scoping via `TokenEntry(platform_id, allowed_fields)`
- Outbound routes ensure PII is only revealed to authorized lender endpoints
