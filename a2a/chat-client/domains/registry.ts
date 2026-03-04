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
 * Domain registry for UCP extensions — response parsing and rendering.
 *
 * Each UCP domain registers:
 *   - Response handlers: map A2A data keys to ChatMessage property setters
 *   - A renderer: given a ChatMessage, return JSX for domain-specific content
 *
 * To add a new domain (e.g., insurance):
 *   1. Create `domains/insurance.ts` with handlers and renderer
 *   2. Import and register in `domains/index.ts`
 *   3. No changes needed to App.tsx or ChatMessage.tsx
 */

import type {ChatMessage} from '../types';

/**
 * Maps an A2A response data key to a ChatMessage property setter.
 * The `parse` function receives the raw data and returns a Partial<ChatMessage>
 * that will be merged into the combined bot message.
 */
export interface ResponseHandler {
  dataKey: string;
  parse: (data: unknown) => Partial<ChatMessage>;
}

/**
 * A function that checks a ChatMessage for domain-specific content
 * and returns true if this domain has content to render.
 */
export type DomainContentChecker = (message: ChatMessage) => boolean;

/**
 * Checks whether a ChatMessage has any domain-specific content
 * (used by App.tsx to determine if a response has displayable content).
 */
export type HasContentChecker = (message: ChatMessage) => boolean;

export class DomainResponseRegistry {
  private _handlers: ResponseHandler[] = [];
  private _contentCheckers: HasContentChecker[] = [];

  /**
   * Register response handlers for a domain.
   */
  registerHandlers(handlers: ResponseHandler[]): void {
    this._handlers.push(...handlers);
  }

  /**
   * Register a content checker for a domain.
   * Used to determine if a bot message has displayable content.
   */
  registerContentChecker(checker: HasContentChecker): void {
    this._contentCheckers.push(checker);
  }

  /**
   * Parse a response data part and return ChatMessage properties.
   * Tries each handler's dataKey against the part. For keys that
   * are top-level (like 'a2a.product_results'), checks part.data[key].
   * Returns a merged Partial<ChatMessage>.
   */
  parseDataPart(
    // biome-ignore lint/suspicious/noExplicitAny: A2A parts are untyped
    dataPart: Record<string, any>,
  ): Partial<ChatMessage> {
    let result: Partial<ChatMessage> = {};

    for (const handler of this._handlers) {
      const value = dataPart[handler.dataKey];
      if (value !== undefined) {
        result = {...result, ...handler.parse(value)};
      }
    }

    return result;
  }

  /**
   * Check if a ChatMessage has any domain-specific content to display.
   */
  hasContent(message: ChatMessage): boolean {
    return this._contentCheckers.some((checker) => checker(message));
  }
}
