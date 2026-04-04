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
 * Lending domain — response handlers and renderers for lender search,
 * PII collection/consent, and loan offer comparison.
 */

import type React from 'react';
import LenderCard from '../components/LenderCard';
import LoanOfferComparison from '../components/LoanOfferComparison';
import NonPIIForm from '../components/NonPIIForm';
import VGSPIICollectionForm from '../components/VGSPIICollectionForm';
import PIIConsentSelector from '../components/PIIConsentSelector';
import type {ChatMessage, Lender, LoanOffer} from '../types';
import type {ResponseHandler} from './registry';

// ---------------------------------------------------------------------------
// Response handlers
// ---------------------------------------------------------------------------

export const lendingResponseHandlers: ResponseHandler[] = [
  {
    dataKey: 'a2a.ucp.lending.lenders',
    parse: (data: unknown) => ({lenders: data as Lender[]}),
  },
  {
    dataKey: 'a2a.ucp.lending.loan_offers',
    parse: (data: unknown) => ({loanOffers: data as LoanOffer[]}),
  },
];

export function lendingHasContent(msg: ChatMessage): boolean {
  return !!(
    msg.lenders ||
    msg.loanOffers ||
    msg.piiMethods ||
    msg.piiCollectionFields ||
    msg.nonPIIForm
  );
}

// ---------------------------------------------------------------------------
// Renderer
// ---------------------------------------------------------------------------

export interface LendingRendererProps {
  message: ChatMessage;
  userEmail: string;
  onSelectPIIMethod?: (method: string) => void;
  onPIICollected?: (result: {fields_stored: string[]}) => void;
  onSubmitNonPII?: (data: Record<string, string>) => void;
}

export const LendingRenderer: React.FC<LendingRendererProps> = ({
  message,
  userEmail,
  onSelectPIIMethod,
  onPIICollected,
  onSubmitNonPII,
}) => {
  return (
    <>
      {message.lenders && message.lenders.length > 0 && (
        <div className="w-full my-1 overflow-x-auto">
          <div className="flex space-x-4 p-2">
            {message.lenders.map((lender) => (
              <LenderCard
                key={lender.platform_id}
                lender={lender}
              />
            ))}
          </div>
        </div>
      )}

      {message.loanOffers && message.loanOffers.length > 0 && (
        <LoanOfferComparison offers={message.loanOffers} />
      )}

      {message.piiMethods && message.piiMethods.length > 0 && onSelectPIIMethod && (
        <PIIConsentSelector
          piiMethods={message.piiMethods}
          lenderNames={message.piiLenderNames || []}
          requiredFields={message.piiRequiredFields || []}
          loanType={message.piiLoanType || 'personal'}
          onSelect={onSelectPIIMethod}
        />
      )}

      {message.piiCollectionFields && message.piiCollectionFields.length > 0 && onPIICollected && message.vgsConfig && (
        <VGSPIICollectionForm
          missingFields={message.piiCollectionFields}
          vaultId={message.vgsConfig.vgs_vault_id}
          environment={message.vgsConfig.vgs_environment}
          userEmail={userEmail}
          onSubmit={onPIICollected}
        />
      )}

      {message.nonPIIForm && onSubmitNonPII && (
        <NonPIIForm
          loanType={message.nonPIIForm.loan_type}
          fields={message.nonPIIForm.fields}
          onSubmit={onSubmitNonPII}
        />
      )}
    </>
  );
};
