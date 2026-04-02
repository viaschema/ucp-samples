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
 * VGS Collect JS-based PII collection form.
 *
 * All fields render inside VGS Collect iframes — including dropdowns,
 * date pickers, and zip-code fields — so PII never touches browser JS.
 */

import type React from 'react';
import {useEffect, useRef, useState} from 'react';

declare global {
  interface Window {
    // biome-ignore lint/suspicious/noExplicitAny: VGS Collect JS global
    VGSCollect: any;
  }
}

interface VGSPIICollectionFormProps {
  missingFields: string[];
  vaultId: string;
  environment: string;
  userEmail: string;
  onSubmit: (result: {fields_stored: string[]; email?: string}) => void;
}

// ---------------------------------------------------------------------------
// Styling
// ---------------------------------------------------------------------------

const VGS_FIELD_CSS = {
  'font-family': 'system-ui, -apple-system, sans-serif',
  'font-size': '0.875rem',
  'line-height': '1.25rem',
  color: '#111827',
  padding: '0.5rem 0.75rem',
  width: '100%',
  height: '100%',
  'box-sizing': 'border-box',
  border: '1px solid #d1d5db',
  'border-radius': '0.375rem',
  '&:focus': {
    outline: 'none',
    'border-color': '#3b82f6',
    'box-shadow': '0 0 0 1px #3b82f6',
  },
};

// ---------------------------------------------------------------------------
// Reference data for dropdowns
// ---------------------------------------------------------------------------

const US_STATES = [
  {value: 'AL', text: 'Alabama'}, {value: 'AK', text: 'Alaska'},
  {value: 'AZ', text: 'Arizona'}, {value: 'AR', text: 'Arkansas'},
  {value: 'CA', text: 'California'}, {value: 'CO', text: 'Colorado'},
  {value: 'CT', text: 'Connecticut'}, {value: 'DE', text: 'Delaware'},
  {value: 'DC', text: 'District of Columbia'}, {value: 'FL', text: 'Florida'},
  {value: 'GA', text: 'Georgia'}, {value: 'HI', text: 'Hawaii'},
  {value: 'ID', text: 'Idaho'}, {value: 'IL', text: 'Illinois'},
  {value: 'IN', text: 'Indiana'}, {value: 'IA', text: 'Iowa'},
  {value: 'KS', text: 'Kansas'}, {value: 'KY', text: 'Kentucky'},
  {value: 'LA', text: 'Louisiana'}, {value: 'ME', text: 'Maine'},
  {value: 'MD', text: 'Maryland'}, {value: 'MA', text: 'Massachusetts'},
  {value: 'MI', text: 'Michigan'}, {value: 'MN', text: 'Minnesota'},
  {value: 'MS', text: 'Mississippi'}, {value: 'MO', text: 'Missouri'},
  {value: 'MT', text: 'Montana'}, {value: 'NE', text: 'Nebraska'},
  {value: 'NV', text: 'Nevada'}, {value: 'NH', text: 'New Hampshire'},
  {value: 'NJ', text: 'New Jersey'}, {value: 'NM', text: 'New Mexico'},
  {value: 'NY', text: 'New York'}, {value: 'NC', text: 'North Carolina'},
  {value: 'ND', text: 'North Dakota'}, {value: 'OH', text: 'Ohio'},
  {value: 'OK', text: 'Oklahoma'}, {value: 'OR', text: 'Oregon'},
  {value: 'PA', text: 'Pennsylvania'}, {value: 'RI', text: 'Rhode Island'},
  {value: 'SC', text: 'South Carolina'}, {value: 'SD', text: 'South Dakota'},
  {value: 'TN', text: 'Tennessee'}, {value: 'TX', text: 'Texas'},
  {value: 'UT', text: 'Utah'}, {value: 'VT', text: 'Vermont'},
  {value: 'VA', text: 'Virginia'}, {value: 'WA', text: 'Washington'},
  {value: 'WV', text: 'West Virginia'}, {value: 'WI', text: 'Wisconsin'},
  {value: 'WY', text: 'Wyoming'},
];

const COUNTRIES = [
  {value: 'US', text: 'United States'}, {value: 'CA', text: 'Canada'},
  {value: 'GB', text: 'United Kingdom'}, {value: 'AU', text: 'Australia'},
  {value: 'DE', text: 'Germany'}, {value: 'FR', text: 'France'},
  {value: 'JP', text: 'Japan'}, {value: 'IN', text: 'India'},
  {value: 'BR', text: 'Brazil'}, {value: 'MX', text: 'Mexico'},
  {value: 'IT', text: 'Italy'}, {value: 'ES', text: 'Spain'},
  {value: 'KR', text: 'South Korea'}, {value: 'NL', text: 'Netherlands'},
  {value: 'CH', text: 'Switzerland'}, {value: 'SE', text: 'Sweden'},
  {value: 'SG', text: 'Singapore'}, {value: 'NZ', text: 'New Zealand'},
  {value: 'IE', text: 'Ireland'}, {value: 'IL', text: 'Israel'},
];

const LIVING_SITUATION_OPTIONS = [
  {value: 'rent', text: 'Rent'},
  {value: 'fully_own', text: 'Fully Own'},
  {value: 'mortgage', text: 'Mortgage'},
];

const EMPLOYMENT_STATUS_OPTIONS = [
  {value: 'employed', text: 'Employed'},
  {value: 'self_employed', text: 'Self Employed'},
  {value: 'unemployed', text: 'Unemployed'},
  {value: 'retired', text: 'Retired'},
];

// ---------------------------------------------------------------------------
// Field configuration — all fields are VGS Collect iframes
// ---------------------------------------------------------------------------

interface VGSFieldConfig {
  label: string;
  vgsType: string;
  placeholder?: string;
  options?: {value: string; text: string}[];
  defaultValue?: string;
  min?: string;
}

const FIELD_CONFIG: Record<string, VGSFieldConfig> = {
  first_name: {label: 'First Name', vgsType: 'text', placeholder: 'John'},
  last_name: {label: 'Last Name', vgsType: 'text', placeholder: 'Doe'},
  email: {label: 'Email', vgsType: 'text', placeholder: 'john@example.com'},
  phone_number: {label: 'Phone Number', vgsType: 'text', placeholder: '+1 555 123 4567'},
  date_of_birth: {label: 'Date of Birth', vgsType: 'date', min: '1920-01-01'},
  annual_income: {label: 'Annual Income ($)', vgsType: 'text', placeholder: '75000'},
  living_situation: {
    label: 'Living Situation',
    vgsType: 'dropdown',
    options: LIVING_SITUATION_OPTIONS,
  },
  monthly_housing_payment: {
    label: 'Monthly Housing Payment ($)',
    vgsType: 'text',
    placeholder: '2000',
  },
  employment_status: {
    label: 'Employment Status',
    vgsType: 'dropdown',
    options: EMPLOYMENT_STATUS_OPTIONS,
  },
  employer_phone_number: {
    label: 'Employer Phone Number',
    vgsType: 'text',
    placeholder: '+1 555 567 8901',
  },
};

interface AddressSubfield {
  key: string;
  label: string;
  vgsType: string;
  placeholder?: string;
  options?: {value: string; text: string}[];
  defaultValue?: string;
}

const ADDRESS_SUBFIELDS: AddressSubfield[] = [
  {key: 'street_address', label: 'Street Address', vgsType: 'text', placeholder: '123 Main St'},
  {key: 'address_locality', label: 'City', vgsType: 'text', placeholder: 'San Francisco'},
  {key: 'address_region', label: 'State', vgsType: 'dropdown', options: US_STATES},
  {key: 'postal_code', label: 'ZIP Code', vgsType: 'zip-code', placeholder: '94102'},
  {key: 'address_country', label: 'Country', vgsType: 'dropdown', options: COUNTRIES, defaultValue: 'US'},
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const formatFieldName = (field: string) =>
  field
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');

const addrFlatKey = (addrField: string, subKey: string) => `${addrField}_${subKey}`;

function getVGSFieldNames(missingFields: string[]): string[] {
  const names: string[] = [];
  for (const f of missingFields) {
    if (f === 'address' || f === 'employer_address') {
      for (const sub of ADDRESS_SUBFIELDS) {
        names.push(addrFlatKey(f, sub.key));
      }
    } else if (FIELD_CONFIG[f]) {
      names.push(f);
    }
  }
  return names;
}

/** Build VGS field options from a VGSFieldConfig or AddressSubfield. */
// biome-ignore lint/suspicious/noExplicitAny: VGS field config object
function buildVGSFieldConfig(cfg: {
  vgsType: string;
  placeholder?: string;
  options?: {value: string; text: string}[];
  defaultValue?: string;
  min?: string;
  name: string;
// biome-ignore lint/suspicious/noExplicitAny: VGS field config
}): Record<string, any> {
  // biome-ignore lint/suspicious/noExplicitAny: VGS field config
  const opts: Record<string, any> = {
    type: cfg.vgsType,
    name: cfg.name,
    css: VGS_FIELD_CSS,
    validations: ['required'],
  };

  if (cfg.placeholder) opts.placeholder = cfg.placeholder;
  if (cfg.options) opts.options = cfg.options;
  if (cfg.defaultValue) opts.defaultValue = cfg.defaultValue;

  // Date fields
  if (cfg.vgsType === 'date' && cfg.min) {
    opts.min = cfg.min;
    opts.validations = [
      'required',
      {
        type: 'compareDate',
        params: {
          field: new Date(cfg.min),
          function: 'more',
        },
      },
    ];
  }

  return opts;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function VGSPIICollectionForm({
  missingFields,
  vaultId,
  environment,
  userEmail,
  onSubmit,
}: VGSPIICollectionFormProps) {
  // biome-ignore lint/suspicious/noExplicitAny: VGS Collect form instance
  const formRef = useRef<any>(null);
  const [isReady, setIsReady] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // All fields are now VGS-managed — separate by type for rendering.
  const addressFields = missingFields.filter(
    (f) => f === 'address' || f === 'employer_address',
  );
  const standardFields = missingFields.filter(
    (f) => FIELD_CONFIG[f] && f !== 'address' && f !== 'employer_address',
  );

  const vgsFieldNames = getVGSFieldNames(missingFields);

  useEffect(() => {
    if (formRef.current) {
      setIsReady(true);
      return;
    }

    if (!window.VGSCollect) {
      setError('VGS Collect JS not loaded. Check index.html.');
      return;
    }

    const form = window.VGSCollect.create(
      vaultId,
      environment,
      () => { setIsReady(true); },
    );
    formRef.current = form;

    // Create VGS Collect fields for standard PII fields.
    for (const field of standardFields) {
      const config = FIELD_CONFIG[field];
      if (!config) continue;

      form.field(`#vgs-${field}`, buildVGSFieldConfig({
        ...config,
        name: field,
      }));
    }

    // Create VGS Collect fields for address sub-fields.
    for (const addrField of addressFields) {
      for (const sub of ADDRESS_SUBFIELDS) {
        form.field(`#vgs-${addrField}-${sub.key}`, buildVGSFieldConfig({
          ...sub,
          name: addrFlatKey(addrField, sub.key),
        }));
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [vaultId, environment]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formRef.current || isSubmitting) return;

    setIsSubmitting(true);
    setError(null);

    formRef.current.submit(
      '/pii/store',
      {
        headers: {'Content-Type': 'application/json'},
        // biome-ignore lint/suspicious/noExplicitAny: VGS formValues type
        data: (formValues: Record<string, any>) => {
          const piiData: Record<string, unknown> = {};

          for (const name of vgsFieldNames) {
            piiData[name] = formValues[name] ?? {__type: 'vgs-key', key: name};
          }

          const emailMarker = formValues['email'] ?? {__type: 'vgs-key', key: 'email'};

          return {
            email: emailMarker,
            pii_data: piiData,
          };
        },
      },
      // biome-ignore lint/suspicious/noExplicitAny: VGS callback types
      (status: number, response: any) => {
        setIsSubmitting(false);
        if (status >= 200 && status < 300) {
          const result = typeof response === 'string' ? JSON.parse(response) : response;
          onSubmit({fields_stored: result.fields_stored || missingFields, email: result.email});
        } else {
          setError(`Submission failed (${status}). Please try again.`);
        }
      },
      // biome-ignore lint/suspicious/noExplicitAny: VGS callback types
      (errors: any) => {
        setIsSubmitting(false);
        console.error('VGS Collect submission error:', errors);
        setError('Failed to submit securely. Please check your inputs.');
      },
    );
  };

  const renderVGSField = (field: string) => {
    const config = FIELD_CONFIG[field];
    const label = config?.label || formatFieldName(field);

    return (
      <div key={field}>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          {label}
        </label>
        <div
          id={`vgs-${field}`}
          className="w-full"
          style={{height: '40px'}}
        />
      </div>
    );
  };

  const renderAddressFields = (addrField: string) => {
    const label = addrField === 'employer_address' ? 'Employer Address' : 'Address';

    return (
      <fieldset key={addrField} className="space-y-2">
        <legend className="block text-sm font-medium text-gray-700 mb-1">
          {label}
        </legend>
        {ADDRESS_SUBFIELDS.map((sub) => (
          <div key={`${addrField}-${sub.key}`}>
            <label className="block text-xs text-gray-500 mb-0.5">
              {sub.label}
            </label>
            <div
              id={`vgs-${addrField}-${sub.key}`}
              className="w-full"
              style={{height: '40px'}}
            />
          </div>
        ))}
      </fieldset>
    );
  };

  return (
    <div className="w-full my-2 border border-amber-200 rounded-lg p-4 bg-amber-50">
      <style>{`
        [id^="vgs-"] iframe {
          width: 100% !important;
          height: 100% !important;
          border: none;
        }
      `}</style>
      <h3 className="font-semibold text-lg text-gray-900 mb-1">
        Additional Information Required
      </h3>
      <p className="text-sm text-gray-600 mb-1">
        We need some additional information to process your loan application.
        Your data is collected securely via VGS and never stored on our servers.
      </p>
      <div className="flex items-center gap-1 mb-3">
        <svg className="w-3 h-3 text-green-600" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"/>
        </svg>
        <span className="text-xs text-green-700">Secured by VGS</span>
      </div>

      {error && (
        <div className="mb-3 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-700">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-3">
        {standardFields.map(renderVGSField)}
        {addressFields.map(renderAddressFields)}

        <button
          type="submit"
          disabled={!isReady || isSubmitting}
          className={`w-full px-4 py-2 rounded-lg font-medium transition-colors ${
            isReady && !isSubmitting
              ? 'bg-blue-600 text-white hover:bg-blue-700'
              : 'bg-gray-300 text-gray-500 cursor-not-allowed'
          }`}>
          {isSubmitting ? 'Submitting securely...' : 'Submit Information'}
        </button>
      </form>
    </div>
  );
}
