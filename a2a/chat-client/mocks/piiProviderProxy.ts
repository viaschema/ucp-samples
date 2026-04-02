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
import type {Lender, PIIConsent, PIIInstrument, PIIMethod} from '../types';

/**
 * PII Provider Proxy that communicates with the backend PII provider
 * via HTTP endpoints. The backend is the single source of truth for PII
 * storage and token issuance.
 *
 * PII collection is handled by VGS Collect JS (which submits through
 * the VGS inbound route). This proxy only handles stored-fields queries
 * and consent submission.
 */
export class PIIProviderProxy {
  handler_id = 'vgs_pii_provider';
  handler_name = 'vgs.pii.provider';

  /**
   * Get the PII fields stored for a user from the backend vault.
   *
   * @param user_email The user's email address.
   * @param config The PII handler config from the merchant.
   * @returns Available PII profiles with stored field lists.
   */
  async getStoredPIIFields(
    user_email: string,
    // biome-ignore lint/suspicious/noExplicitAny: no specific type for config
    config: any,
  ): Promise<{pii_methods: PIIMethod[]}> {
    console.log(
      `PIIProviderProxy: Checking stored PII for ${user_email} with config:`,
      config,
    );

    const response = await fetch('/api/pii/stored-fields', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({email: user_email}),
    });

    if (!response.ok) {
      throw new Error(`Failed to get stored PII fields: ${response.status}`);
    }

    return response.json();
  }

  /**
   * Submit a formal PIIConsent to the backend vault. The vault validates
   * the consent, records it, and returns platform-scoped tokens.
   *
   * @param user_email The user's email address.
   * @param consent The formal consent object authorizing PII sharing.
   * @returns The consent ID and an array of PIIInstruments (one per platform).
   */
  async submitConsent(
    user_email: string,
    consent: PIIConsent,
  ): Promise<{consent_id: string; instruments: PIIInstrument[]}> {
    console.log(
      `PIIProviderProxy: Submitting PII consent for ${user_email}, ` +
        `platforms: ${consent.platform_ids.join(', ')}, ` +
        `fields: ${consent.fields_consented.join(', ')}`,
    );

    const response = await fetch('/api/pii/consent', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({email: user_email, consent}),
    });

    if (!response.ok) {
      throw new Error(`Failed to submit PII consent: ${response.status}`);
    }

    return response.json();
  }

  /**
   * Get available lenders, optionally filtered by loan type.
   * Mirrors getSupportedPaymentMethods from the payment handler.
   */
  async getLenders(
    loan_type?: string,
  ): Promise<{lenders: Lender[]}> {
    const params = loan_type ? `?loan_type=${loan_type}` : '';
    const response = await fetch(`/api/lending/lenders${params}`);

    if (!response.ok) {
      throw new Error(`Failed to get lenders: ${response.status}`);
    }

    return response.json();
  }

  /**
   * Get VGS Collect JS configuration from the backend.
   * The vault ID and environment are server-side secrets, not in ucp.json.
   */
  async getCollectConfig(): Promise<{vgs_vault_id: string; vgs_environment: string}> {
    const response = await fetch('/api/lending/collect-config');

    if (!response.ok) {
      throw new Error(`Failed to get collect config: ${response.status}`);
    }

    return response.json();
  }
}
