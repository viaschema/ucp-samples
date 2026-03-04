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
import type {PIIMethod} from '../types';

interface PIIConsentSelectorProps {
  piiMethods: PIIMethod[];
  lenderNames: string[];
  requiredFields: string[];
  loanType: string;
  onSelect: (piiMethodId: string) => void;
}

/**
 * Displays available PII profiles for the user to authorize sharing.
 * Shows which lenders will receive the data and which fields will be shared.
 */
export default function PIIConsentSelector({
  piiMethods,
  lenderNames,
  requiredFields,
  loanType,
  onSelect,
}: PIIConsentSelectorProps) {
  const formatFieldName = (field: string) =>
    field
      .split('_')
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(' ');

  const displayFields = requiredFields.length > 0 ? requiredFields : undefined;

  return (
    <div className="w-full my-2 border border-blue-200 rounded-lg p-4 bg-blue-50">
      <h3 className="font-semibold text-lg text-gray-900 mb-2">
        Authorize PII Sharing
      </h3>
      <p className="text-sm text-gray-600 mb-3">
        Your data is shared securely via token with the lenders below. Raw data
        never passes through the agent.
      </p>
      <div className="mb-3">
        <p className="text-sm font-medium text-gray-700 mb-1">Loan type:</p>
        <span className="inline-block px-2 py-0.5 text-xs bg-green-100 text-green-700 rounded-full font-medium capitalize">
          {loanType}
        </span>
      </div>
      {lenderNames.length > 0 && (
        <div className="mb-3">
          <p className="text-sm font-medium text-gray-700 mb-1">
            Sharing with:
          </p>
          <div className="flex flex-wrap gap-1">
            {lenderNames.map((name) => (
              <span
                key={name}
                className="inline-block px-2 py-0.5 text-xs bg-blue-100 text-blue-700 rounded-full font-medium">
                {name}
              </span>
            ))}
          </div>
        </div>
      )}
      {displayFields && (
        <div className="mb-3">
          <p className="text-sm font-medium text-gray-700 mb-1">
            Fields to be shared:
          </p>
          <div className="flex flex-wrap gap-1">
            {displayFields.map((field) => (
              <span
                key={field}
                className="inline-block px-2 py-0.5 text-xs bg-white text-gray-700 rounded border border-gray-200">
                {formatFieldName(field)}
              </span>
            ))}
          </div>
        </div>
      )}
      <div className="space-y-2">
        {piiMethods.map((method) => (
          <div
            key={method.id}
            className="border border-gray-200 rounded-lg p-3 bg-white">
            <div className="flex items-center justify-between">
              <span className="font-medium text-gray-900">
                PII Profile ({method.fields_stored.length} fields stored)
              </span>
              <button
                type="button"
                onClick={() => onSelect(method.id)}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium">
                Authorize
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
