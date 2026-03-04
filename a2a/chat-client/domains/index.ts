/*
 * Copyright 2026 UCP Authors
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/**
 * Domain registry assembly — import and register all UCP domains.
 *
 * To add a new domain:
 *   1. Create `domains/myDomain.tsx` with handlers, hasContent, and renderer
 *   2. Import and register below
 *   3. Add the renderer to the `domainRenderers` export
 */

import {DomainResponseRegistry} from './registry';
import {
  appointmentHasContent,
  appointmentResponseHandlers,
} from './appointments';
import {
  lendingHasContent,
  lendingResponseHandlers,
} from './lending';
import {
  shoppingHasContent,
  shoppingResponseHandlers,
} from './shopping';

// Build the singleton registry
const registry = new DomainResponseRegistry();

// Register shopping domain
registry.registerHandlers(shoppingResponseHandlers);
registry.registerContentChecker(shoppingHasContent);

// Register appointment domain
registry.registerHandlers(appointmentResponseHandlers);
registry.registerContentChecker(appointmentHasContent);

// Register lending domain
registry.registerHandlers(lendingResponseHandlers);
registry.registerContentChecker(lendingHasContent);

export {registry};

// Re-export renderers for ChatMessage.tsx
export {ShoppingRenderer} from './shopping';
export type {ShoppingRendererProps} from './shopping';
export {AppointmentRenderer} from './appointments';
export type {AppointmentRendererProps} from './appointments';
export {LendingRenderer} from './lending';
export type {LendingRendererProps} from './lending';
