# 10 — Domain Module Pattern

This document describes the **domain module pattern** used to organize UCP extensions in the Cymbal Retail Agent. The pattern makes it straightforward to add new UCP capabilities (e.g., medical insurance payments, store negotiation) without modifying the core agent assembly, executor, or frontend routing.

## Overview

Each UCP extension is encapsulated as a **domain module** — a self-contained unit that defines:

| Concern | Backend (`DomainModule`) | Frontend (`domains/*.tsx`) |
|---------|--------------------------|----------------------------|
| Capability URI | `capability_uri` property | N/A (server-side) |
| Agent tools | `tools` property | N/A |
| Agent instructions | `agent_instructions` property | N/A |
| Checkout schema mixin | `checkout_mixin` property | N/A |
| Response data keys | `response_data_keys` property | `ResponseHandler[]` |
| Checkout initialization | `initialize_checkout_fields()` | N/A |
| Content detection | N/A | `hasContent()` function |
| UI rendering | N/A | `<DomainRenderer>` component |

## Backend Architecture

### Directory Structure

```
business_agent/
├── domains/
│   ├── __init__.py          # DomainRegistry
│   ├── base.py              # DomainModule ABC
│   ├── shopping.py          # ShoppingDomain + shopping tools
│   ├── appointments.py      # AppointmentDomain + appointment tools
│   └── lending.py           # LendingDomain (wraps lending_tools.py)
├── appointment_manager.py   # Appointment slot CRUD (extracted from store)
├── agent.py                 # Registry assembly + root agent
├── store.py                 # Core checkout store (delegates to domains)
└── constants.py             # Namespaced key classes + flat aliases
```

### DomainModule Base Class

Every domain implements `domains/base.py:DomainModule`:

```python
from business_agent.domains.base import DomainModule

class InsuranceDomain(DomainModule):

    @property
    def capability_uri(self) -> str:
        return "com.example.insurance"

    @property
    def tools(self) -> list:
        return [search_providers, submit_claim, ...]

    @property
    def agent_instructions(self) -> str:
        return "Insurance workflow:\n1. Search providers ..."

    @property
    def checkout_mixin(self) -> type | None:
        return InsuranceCheckout  # Pydantic model

    @property
    def response_data_keys(self) -> list[str]:
        return ["a2a.ucp.insurance.providers", "a2a.ucp.insurance.claims"]

    def initialize_checkout_fields(self, checkout, ucp_metadata):
        if hasattr(checkout, "insurance"):
            checkout.insurance = InsuranceResponse()
```

### DomainRegistry

The registry in `domains/__init__.py` aggregates all domain modules:

```python
registry = DomainRegistry()
registry.register(ShoppingDomain())
registry.register(InsuranceDomain())

# Used by agent.py:
root_agent = Agent(
    tools=registry.all_tools,
    instruction=registry.combined_instructions,
)

# Used by type_generator.py:
mixins = registry.get_checkout_mixins(active_capabilities)

# Used by store.py:
registry.initialize_checkout(checkout, ucp_metadata, active_caps)
```

### Namespaced State Keys

Constants are organized into per-domain classes in `constants.py`:

```python
class CoreKeys:
    CHECKOUT_ID = "user:checkout_id"
    UCP_METADATA = "__ucp_metadata__"

class ShoppingKeys:
    PAYMENT_STATE = "__payment_data__"
    CHECKOUT = "a2a.ucp.checkout"

class LendingKeys:
    PII_STATE = "__pii_data__"
    PII_DATA = "a2a.ucp.checkout.pii_data"
```

Flat aliases (e.g., `ADK_USER_CHECKOUT_ID = CoreKeys.CHECKOUT_ID`) are maintained for backward compatibility.

### AppointmentManager

Appointment-specific checkout logic is extracted into `appointment_manager.py`. The `ServiceStore` delegates to it:

```python
# store.py
self.appointments = AppointmentManager(
    square_client=self.square,
    service_resolver=self.get_service_variation,
)

# Checkout operations delegate:
self.appointments.add_or_update_slot(checkout, ...)
self.appointments.remove_slots_for_line_item(checkout, ...)
self.appointments.apply_appointment_request(checkout, ...)
self.appointments.validate_appointments(checkout)
```

## Frontend Architecture

### Directory Structure

```
chat-client/
├── domains/
│   ├── index.ts             # Registry assembly + re-exports
│   ├── registry.ts          # DomainResponseRegistry class
│   ├── shopping.tsx         # Response handlers + ShoppingRenderer
│   ├── appointments.tsx     # Response handlers + AppointmentRenderer
│   └── lending.tsx          # Response handlers + LendingRenderer
├── App.tsx                  # Uses registry.parseDataPart()
└── components/
    └── ChatMessage.tsx      # Uses domain renderers
```

### Response Handler Registry

Each domain registers `ResponseHandler` objects that map A2A data keys to `ChatMessage` properties:

```typescript
// domains/registry.ts
export interface ResponseHandler {
  dataKey: string;
  parse: (data: unknown) => Partial<ChatMessage>;
}

// domains/appointments.tsx
export const appointmentResponseHandlers: ResponseHandler[] = [
  {
    dataKey: 'a2a.locations',
    parse: (data) => ({locations: data as Location[]}),
  },
  // ...
];
```

`App.tsx` uses the registry instead of hard-coded if/else chains:

```typescript
// Before (hard-coded):
if (part.data?.['a2a.locations']) {
  combinedBotMessage.locations = part.data['a2a.locations'];
}

// After (registry):
const parsed = registry.parseDataPart(part.data);
Object.assign(combinedBotMessage, parsed);
```

### Domain Renderers

Each domain exports a React component that renders its content:

```typescript
// domains/lending.tsx
export const LendingRenderer: React.FC<LendingRendererProps> = ({
  message, onSelectPIIMethod, onPIICollected, onSubmitNonPII,
}) => (
  <>
    {message.lenders && <LenderCards ... />}
    {message.loanOffers && <LoanOfferComparison ... />}
    {message.piiMethods && <PIIConsentSelector ... />}
  </>
);
```

`ChatMessage.tsx` composes domain renderers instead of inlining all conditionals:

```tsx
<ShoppingRenderer message={message} ... />
<AppointmentRenderer message={message} ... />
<LendingRenderer message={message} ... />
```

## Adding a New Domain

### Backend Steps

1. **Create the domain module** at `domains/my_domain.py`:
   - Subclass `DomainModule`
   - Define tools, instructions, checkout_mixin, response_data_keys
   - Implement `initialize_checkout_fields()` if your domain extends checkout

2. **Create Pydantic models** at `models/my_domain_types.py`:
   - Define a checkout mixin (e.g., `MyDomainCheckout`)
   - Define response models

3. **Add state key class** to `constants.py`:
   ```python
   class MyDomainKeys:
       MY_STATE = "__my_domain_data__"
   ```

4. **Register** in `agent.py:_build_registry()`:
   ```python
   from .domains.my_domain import MyDomainModule
   registry.register(MyDomainModule())
   ```

5. **Add capability** to `data/ucp.json` and `data/agent_card.json`

### Frontend Steps

1. **Create the domain file** at `domains/myDomain.tsx`:
   - Export `ResponseHandler[]` for your data keys
   - Export a `hasContent()` checker
   - Export a `<MyDomainRenderer>` component

2. **Register** in `domains/index.ts`:
   ```typescript
   import {myDomainHandlers, myDomainHasContent} from './myDomain';
   registry.registerHandlers(myDomainHandlers);
   registry.registerContentChecker(myDomainHasContent);
   ```

3. **Add renderer** to `ChatMessage.tsx`:
   ```tsx
   <MyDomainRenderer message={message} ... />
   ```

4. **Add types** to `types.ts` and extend the `ChatMessage` interface

5. **Add capability** to `profile/agent_profile.json`

### Files You DON'T Need to Touch

- `agent_executor.py` — domain-agnostic A2A bridge
- `store.py` — unless your domain extends the checkout (use `initialize_checkout_fields`)
- `App.tsx` — response parsing is handled by the registry
- `helpers/type_generator.py` — checkout mixins are picked up via the registry
