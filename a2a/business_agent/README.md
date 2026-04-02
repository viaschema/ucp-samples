<!--
   Copyright 2026 UCP Authors

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
-->

# Cymbal Retail Agent

Example agent implementing A2A Extension for UCP

### Pre-requisites:

1. Python 3.13
2. UV
3. Gemini API Key (The agent uses Gemini model to generate responses)

## Quick Start

1. Run `uv sync`
2. Copy env.example to .env and update it with relevant Gemini API key.
3. Run `uv run business_agent`
4. This starts the Cymbal Retail Agent on port 10999. You can verify by accessing
the agent card at http://localhost:10999/.well-known/agent-card.json

## VGS PII Integration (Optional)

For real PII tokenization via VGS instead of the mock provider:

1. Create a VGS vault at https://dashboard.verygoodsecurity.com
2. Generate runtime access credentials: `vgs generate access-credentials --vault $VAULT_ID`
3. Add to `.env`:
   ```
   VGS_VAULT_ID=<your vault id>
   VGS_USERNAME=<runtime key>
   VGS_PASSWORD=<runtime secret>
   VGS_ENVIRONMENT=sandbox
   LENDER_API_BASE=https://<your-ngrok-id>.ngrok-free.app/lender-api
   ```
4. Start ngrok: `ngrok http 10999`
5. Apply VGS routes:
   ```bash
   vgs login
   vgs apply routes --vault $VGS_VAULT_ID -f routes/inbound_pii_store.yaml
   vgs apply routes --vault $VGS_VAULT_ID -f routes/outbound_lender.yaml
   ```
6. Run: `uv run business_agent`

To use the mock provider instead (no VGS needed): set `PII_PROVIDER=mock` in `.env`.

See [docs/11-vgs-pii-integration.md](../docs/11-vgs-pii-integration.md) for the full architecture.
