# Lending Integration Test Guide

## Overview

This document describes how to verify the UCP lending extension end-to-end, covering:

1. Unit tests for PII providers (MockPIIProvider / VGSPIIProvider) and lending models
2. PII collection flow (new user with no stored PII)
3. Multi-lender offer aggregation via lender API
4. Incremental PII collection across loan types
5. A2A integration test via curl
5. Capability negotiation verification

## Prerequisites

```bash
# From the a2a/business_agent directory
cd a2a/business_agent
pip install -e .       # or: uv sync

# Ensure .env has GOOGLE_API_KEY
cp env.example .env    # Add your key
```

## 1. Unit Tests

Run all lending tests (34 tests across 5 test classes):

```bash
cd a2a/business_agent
python -m pytest tests/test_lending.py -v
```

### Test Classes

| Class | Tests | What It Covers |
|-------|-------|----------------|
| `TestMockPIIProvider` | 16 | store_pii, get_missing_fields, token issuance/validation, field requirements |
| `TestLenderSearch` | 5 | Lender filtering by loan type, fuzzy search |
| `TestMultiLenderOffers` | 6 | Multi-lender aggregation via mock HTTP transport, rate sorting, offer validation |
| `TestPIICollectionFlow` | 3 | Full new-user flow, incremental collection, cross-loan-type delta |
| `TestCapabilityNegotiation` | 5 | type_generator includes/excludes lending, model validation |
| `TestLoanProviderRegistry` | 7 | Registry creates providers, single provider offers, field requirements |
| `TestPIIVaultEndpoints` | 6 | HTTP endpoints for store, stored-fields, consent |

**Note**: Tests use `PII_PROVIDER=mock` and a mock HTTP transport (`httpx.MockTransport`) so they don't need VGS credentials or a running server. The `loan_registry` fixture patches `httpx.post` to route lender API calls in-process.

Run all tests to verify no regressions:

```bash
PII_PROVIDER=mock python -m pytest tests/ -v
```

Expected: 91 tests pass.

### Provider Architecture

Both `MockPIIProvider` and `VGSPIIProvider` extend `BasePIIProvider`, which implements shared token/consent logic. Tests exercise the mock provider; the VGS provider uses the same base class methods and is tested via integration tests with real VGS credentials.

See [VGS PII Integration](11-vgs-pii-integration.md) for the full VGS architecture.

## 2. PII Collection Flow Test

The `TestPIICollectionFlow::test_full_pii_collection_flow` test verifies:

1. New user has all required PII fields missing
2. Store PII fields via `store_pii(email, pii_data)`
3. After storage, `get_missing_fields()` returns `[]`
4. Token can be issued via `issue_token(email)`
5. Token validates successfully via `process_pii(instrument)`

To verify manually in Python:

```python
from business_agent.pii_provider import MockPIIProvider
from business_agent.models.lending_types import PIIInstrument, PIICredential

provider = MockPIIProvider()

# New user has all fields missing
missing = provider.get_missing_fields("new@example.com", "personal")
assert len(missing) == 8  # All required fields

# Store PII
provider.store_pii("new@example.com", {
    "first_name": "New", "last_name": "User",
    "email": "new@example.com", "phone": "555-0001",
    "address": "100 Test Blvd", "date_of_birth": "1992-03-10",
    "annual_income": "72000", "living_situation": "rent",
})

# Now no fields missing
assert provider.get_missing_fields("new@example.com", "personal") == []

# Issue and validate token
token = provider.issue_token("new@example.com")
instrument = PIIInstrument(
    id="test", handler_id="h1", handler_name="test",
    fields_stored=["first_name"], loan_type="personal",
    credential=PIICredential(type="token", token=token),
)
task = provider.process_pii(instrument)
assert task.status.state.value == "completed"
```

## 3. Multi-Lender Offer Test

Verify offers come from multiple lenders, sorted by rate:

```python
from business_agent.pii_provider import MockPIIProvider

provider = MockPIIProvider()
offers = provider.apply_for_all_lenders("personal", {"loan_amount_requested": 15000})

# Multiple lenders
lender_names = {o.lender_name for o in offers}
assert len(lender_names) >= 2

# Sorted by rate ascending
rates = [o.rate for o in offers]
assert rates == sorted(rates)

# All offers valid
for offer in offers:
    assert offer.rate > 0
    assert offer.monthly_payment > 0
    assert offer.continue_url.startswith("https://")
```

## 4. A2A Integration Test

### Start Servers

**Terminal 1 (Backend):**
```bash
cd a2a/business_agent
source .env && export GOOGLE_API_KEY
uv run business_agent
# Starts on :10999
```

**Terminal 2 (Frontend):**
```bash
cd a2a/chat-client
npm run dev
# Starts on :3000
```

### Verify Endpoints

```bash
# Agent card - should include com.viaschema.lending capability and "lending" skill
curl -s http://localhost:10999/.well-known/agent-card.json | python -m json.tool | grep -A4 "lending"

# Client profile - should include com.viaschema.lending
curl -s http://localhost:3000/profile/agent_profile.json | python -m json.tool | grep "lending"
```

### Send Lending Request via A2A

```bash
curl -s -X POST http://localhost:10999/ \
  -H 'Content-Type: application/json' \
  -H 'X-A2A-Extensions: https://ucp.dev/specification/reference?v=2026-01-11' \
  -H 'UCP-Agent: profile="http://localhost:3000/profile/agent_profile.json"' \
  -d '{
    "jsonrpc": "2.0",
    "id": "test-lending-1",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"type": "text", "text": "I want to apply for a personal loan"}],
        "messageId": "msg-lending-1",
        "kind": "message"
      },
      "configuration": {"historyLength": 0}
    }
  }' | python -m json.tool
```

### Expected Response Structure

The response should contain parts with:

1. **Text part**: Agent message about loan application
2. **Data part** with `a2a.ucp.checkout` containing:
   - `lending.loan_type`: `"personal"`
   - `lending.status`: `"consent_needed"` or `"pii_missing"`
   - `lending.handlers`: Array with `example_pii_provider`
   - `lending.lenders`: Array of 5 personal loan lenders (SoFi, LendingClub, Upstart, LightStream, MoneyTree)
   - `lending.required_pii_fields`: 8 fields
   - `lending.required_non_pii_fields`: `["loan_amount_requested", "desired_monthly_payment"]`

### Verify Response

```bash
# Pipe the curl response to check specific fields:
curl -s -X POST http://localhost:10999/ \
  -H 'Content-Type: application/json' \
  -H 'X-A2A-Extensions: https://ucp.dev/specification/reference?v=2026-01-11' \
  -H 'UCP-Agent: profile="http://localhost:3000/profile/agent_profile.json"' \
  -d '{ ... }' | python -c "
import json, sys
data = json.load(sys.stdin)
parts = data.get('result', {}).get('parts', [])
for part in parts:
    if 'a2a.ucp.checkout' in part.get('data', {}):
        checkout = part['data']['a2a.ucp.checkout']
        lending = checkout.get('lending', {})
        print(f'Loan type: {lending.get(\"loan_type\")}')
        print(f'Status: {lending.get(\"status\")}')
        print(f'Lenders: {[l[\"lender_name\"] for l in lending.get(\"lenders\", [])]}')
        print(f'PII handlers: {[h[\"id\"] for h in lending.get(\"handlers\", [])]}')
        print(f'Required PII fields: {lending.get(\"required_pii_fields\")}')
        print(f'Required non-PII fields: {lending.get(\"required_non_pii_fields\")}')
"
```

## 5. Capability Negotiation Test

### Test: Lending Present When Declared

When the client profile includes `com.viaschema.lending`, the response checkout should include it in active capabilities:

```bash
# Use the standard client profile (has com.viaschema.lending)
curl -s http://localhost:3000/profile/agent_profile.json | python -c "
import json, sys
caps = [c['name'] for c in json.load(sys.stdin)['ucp']['capabilities']]
assert 'com.viaschema.lending' in caps, f'Missing lending in {caps}'
print('PASS: com.viaschema.lending in client capabilities')
"
```

### Test: Lending Absent When Not Declared

Create a profile without lending and verify the response excludes it:

```bash
# Create a minimal profile without lending
cat > /tmp/no_lending_profile.json << 'EOF'
{
  "ucp": {
    "version": "2026-01-11",
    "capabilities": [
      {"name": "dev.ucp.shopping.checkout", "version": "2026-01-11"}
    ]
  }
}
EOF

# Serve it
python -m http.server 3099 --directory /tmp &
PID=$!

# Send request with no-lending profile
curl -s -X POST http://localhost:10999/ \
  -H 'Content-Type: application/json' \
  -H 'X-A2A-Extensions: https://ucp.dev/specification/reference?v=2026-01-11' \
  -H 'UCP-Agent: profile="http://localhost:3099/no_lending_profile.json"' \
  -d '{
    "jsonrpc": "2.0",
    "id": "test-no-lending",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"type": "text", "text": "I want a personal loan"}],
        "messageId": "msg-1",
        "kind": "message"
      },
      "configuration": {"historyLength": 0}
    }
  }' | python -c "
import json, sys
data = json.load(sys.stdin)
for part in data.get('result', {}).get('parts', []):
    if 'a2a.ucp.checkout' in part.get('data', {}):
        caps = [c['name'] for c in part['data']['a2a.ucp.checkout'].get('ucp', {}).get('capabilities', [])]
        assert 'com.viaschema.lending' not in caps, f'Lending should not be in negotiated caps: {caps}'
        print(f'PASS: com.viaschema.lending NOT in negotiated capabilities: {caps}')
        break
"

# Cleanup
kill $PID 2>/dev/null
```

### Unit Test for Type Generator

The capability negotiation at the model level is tested in `test_lending.py::TestCapabilityNegotiation`:

```python
# With lending capability -> checkout type has 'lending' field
def test_type_generator_includes_lending(self):
    ucp_metadata = ResponseCheckout(
        version="2026-01-11",
        capabilities=[
            CapResponse(name="dev.ucp.shopping.checkout"),
            CapResponse(name="com.viaschema.lending"),
        ],
    )
    checkout_type = get_checkout_type(ucp_metadata)
    assert "lending" in checkout_type.model_fields

# Without lending capability -> checkout type does NOT have 'lending' field
def test_type_generator_excludes_lending(self):
    ucp_metadata = ResponseCheckout(
        version="2026-01-11",
        capabilities=[
            CapResponse(name="dev.ucp.shopping.checkout"),
        ],
    )
    checkout_type = get_checkout_type(ucp_metadata)
    assert "lending" not in checkout_type.model_fields
```

## Manual UI Test (Path A & Path B)

### Path A: PII Already Stored (foo@example.com)

1. Open http://localhost:3000
2. Type "I want a personal loan"
3. Agent responds with lender list and checkout with lending info
4. Frontend auto-triggers PII flow -> PIIProviderProxy finds all fields stored for `foo@example.com`
5. PIIConsentSelector appears showing stored fields -> Click "Authorize"
6. PIIConfirmation appears -> Click "Authorize PII Sharing"
7. NonPIIForm appears for loan_amount, desired_monthly_payment -> Fill and submit
8. Agent submits to all lenders -> LoanOfferComparison table appears with rate-sorted offers

### Path B: PII Not Stored (new email)

1. Change `user_email` in App.tsx from `foo@example.com` to a new email like `new@example.com`
2. Open http://localhost:3000
3. Type "I want a car loan"
4. Agent responds with lender list, checkout shows `status: "pii_missing"` with `missing_pii_fields`
5. Frontend detects missing fields -> PIICollectionForm renders with input fields for each missing PII field
6. Fill in all fields and submit -> PIIProviderProxy stores PII
7. PIIConsentSelector appears (now all fields stored) -> Continue same as Path A steps 5-8

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| `Connection refused` on A2A call | Frontend not running (profile fetch fails) | Start frontend on :3000 first |
| Checkout has no `lending` field | `com.viaschema.lending` not in client profile | Add to `agent_profile.json` capabilities |
| All PII fields show as missing | Backend MockPIIProvider starts empty | This is correct - frontend proxy has mock data |
| LLM doesn't call lending tools | Agent instruction may not match user query | Check `domains/lending.py` `LendingDomain.agent_instructions` property |
| Offers not sorted | `apply_for_all_lenders` bug | Check `all_offers.sort(key=lambda o: o.rate)` in pii_provider.py |
