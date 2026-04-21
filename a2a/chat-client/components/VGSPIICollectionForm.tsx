/*
 * Copyright 2026 UCP Authors
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 */

/**
 * VGS Collect JS-based PII collection form.
 *
 * Every field renders inside a VGS-controlled cross-origin iframe.
 * Values are tokenized at VGS before reaching our backend — the agent/LLM
 * only ever receives an opaque token reference.
 */

import type React from 'react';
import {useEffect, useMemo, useRef, useState} from 'react';
import VaultFlowDiagram from './VaultFlowDiagram';

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
// Styling — VGS iframe fields
// ---------------------------------------------------------------------------

const VGS_FIELD_CSS = {
  'font-family':
    "'Instrument Sans', system-ui, -apple-system, sans-serif",
  'font-size': '0.95rem',
  'line-height': '1.25rem',
  color: '#1A1C20',
  padding: '0.65rem 0.9rem',
  width: '100%',
  height: '100%',
  'box-sizing': 'border-box',
  background: '#FFFFFF',
  border: '1px solid rgba(26,28,32,0.11)',
  'border-radius': '10px',
  '&:focus': {
    outline: 'none',
    'border-color': '#A44626',
    'box-shadow': '0 0 0 3px rgba(164,70,38,0.22)',
  },
  '&::placeholder': {
    color: '#9CA0A8',
  },
};

// ---------------------------------------------------------------------------
// Reference data
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
  {value: 'fully_own', text: 'Fully own'},
  {value: 'mortgage', text: 'Mortgage'},
];

const EMPLOYMENT_STATUS_OPTIONS = [
  {value: 'employed', text: 'Employed'},
  {value: 'self_employed', text: 'Self-employed'},
  {value: 'unemployed', text: 'Unemployed'},
  {value: 'retired', text: 'Retired'},
];

// ---------------------------------------------------------------------------
// Field configuration
// ---------------------------------------------------------------------------

interface VGSFieldConfig {
  label: string;
  vgsType: string;
  placeholder?: string;
  options?: {value: string; text: string}[];
  defaultValue?: string;
  min?: string;
  sensitive?: boolean; // shows a lock glyph indicating particularly sensitive
  hint?: string;
}

const FIELD_CONFIG: Record<string, VGSFieldConfig> = {
  first_name: {label: 'First name', vgsType: 'text', placeholder: 'Jamie'},
  last_name: {label: 'Last name', vgsType: 'text', placeholder: 'Rivera'},
  email: {label: 'Email', vgsType: 'text', placeholder: 'jamie@example.com'},
  phone_number: {label: 'Phone', vgsType: 'text', placeholder: '+1 555 123 4567'},
  date_of_birth: {
    label: 'Date of birth',
    vgsType: 'date',
    min: '1920-01-01',
    sensitive: true,
  },
  annual_income: {
    label: 'Annual income',
    vgsType: 'text',
    placeholder: '75000',
    sensitive: true,
    hint: 'Pre-tax, USD',
  },
  living_situation: {
    label: 'Living situation',
    vgsType: 'dropdown',
    options: LIVING_SITUATION_OPTIONS,
  },
  monthly_housing_payment: {
    label: 'Monthly housing payment',
    vgsType: 'text',
    placeholder: '2000',
    hint: 'Rent or mortgage',
  },
  employment_status: {
    label: 'Employment status',
    vgsType: 'dropdown',
    options: EMPLOYMENT_STATUS_OPTIONS,
  },
  employer_phone_number: {
    label: 'Employer phone',
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
  {key: 'street_address', label: 'Street address', vgsType: 'text', placeholder: '123 Main St'},
  {key: 'address_locality', label: 'City', vgsType: 'text', placeholder: 'San Francisco'},
  {key: 'address_region', label: 'State', vgsType: 'dropdown', options: US_STATES},
  {key: 'postal_code', label: 'ZIP', vgsType: 'zip-code', placeholder: '94102'},
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

  if (cfg.vgsType === 'date' && cfg.min) {
    opts.min = cfg.min;
    opts.validations = [
      'required',
      {
        type: 'compareDate',
        params: {field: new Date(cfg.min), function: 'more'},
      },
    ];
  }

  return opts;
}

// Fake, UI-only illustrative token — regenerated per mount so it feels alive.
function makeIllustrativeToken() {
  const chars = 'abcdef0123456789';
  let body = '';
  for (let i = 0; i < 18; i++) {
    body += chars[Math.floor(Math.random() * chars.length)];
    if (i === 3 || i === 9) body += '-';
  }
  return `pii_token_${body}…`;
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

  const addressFields = missingFields.filter(
    (f) => f === 'address' || f === 'employer_address',
  );
  const standardFields = missingFields.filter(
    (f) => FIELD_CONFIG[f] && f !== 'address' && f !== 'employer_address',
  );

  const vgsFieldNames = getVGSFieldNames(missingFields);
  const illustrativeToken = useMemo(makeIllustrativeToken, []);

  useEffect(() => {
    if (formRef.current) {
      setIsReady(true);
      return;
    }

    if (!window.VGSCollect) {
      setError('VGS Collect JS could not load. Check your connection, then retry.');
      return;
    }

    const form = window.VGSCollect.create(
      vaultId,
      environment,
      () => {
        setIsReady(true);
      },
    );
    formRef.current = form;

    for (const field of standardFields) {
      const config = FIELD_CONFIG[field];
      if (!config) continue;
      form.field(
        `#vgs-${field}`,
        buildVGSFieldConfig({...config, name: field}),
      );
    }

    for (const addrField of addressFields) {
      for (const sub of ADDRESS_SUBFIELDS) {
        form.field(
          `#vgs-${addrField}-${sub.key}`,
          buildVGSFieldConfig({...sub, name: addrFlatKey(addrField, sub.key)}),
        );
      }
    }
    // biome-ignore lint/correctness/useExhaustiveDependencies: initialize once per vault
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
          const emailMarker =
            formValues['email'] ?? {__type: 'vgs-key', key: 'email'};
          return {email: emailMarker, pii_data: piiData};
        },
      },
      // biome-ignore lint/suspicious/noExplicitAny: VGS callback types
      (status: number, response: any) => {
        setIsSubmitting(false);
        if (status >= 200 && status < 300) {
          const result =
            typeof response === 'string' ? JSON.parse(response) : response;
          onSubmit({
            fields_stored: result.fields_stored || missingFields,
            email: result.email,
          });
        } else {
          setError(
            `We couldn't seal the submission (status ${status}). Please try again.`,
          );
        }
      },
      // biome-ignore lint/suspicious/noExplicitAny: VGS callback types
      (errors: any) => {
        setIsSubmitting(false);
        console.error('VGS Collect submission error:', errors);
        setError(
          'Some fields need attention before we can seal them. Check the highlighted entries.',
        );
      },
    );
  };

  const renderVGSField = (field: string) => {
    const config = FIELD_CONFIG[field];
    const label = config?.label || formatFieldName(field);

    return (
      <div key={field}>
        <label
          htmlFor={`vgs-${field}`}
          className="field-label flex items-center justify-between gap-2">
          <span className="flex items-center gap-1.5">
            {label}
            {config?.sensitive && (
              <span
                aria-label="Sensitive field"
                title="Especially sensitive — encrypted end-to-end"
                className="text-moss">
                <svg viewBox="0 0 12 12" className="w-3 h-3" fill="currentColor">
                  <path d="M6 1a3 3 0 00-3 3v2H2.5a.5.5 0 00-.5.5v4a.5.5 0 00.5.5h7a.5.5 0 00.5-.5v-4a.5.5 0 00-.5-.5H9V4a3 3 0 00-3-3zm-2 3a2 2 0 114 0v2H4V4z" />
                </svg>
              </span>
            )}
          </span>
          {config?.hint && (
            <span className="text-[0.72rem] text-ink-soft font-normal">
              {config.hint}
            </span>
          )}
        </label>
        <div
          id={`vgs-${field}`}
          className="w-full"
          style={{height: '44px'}}
        />
      </div>
    );
  };

  const renderAddressFields = (addrField: string) => {
    const label = addrField === 'employer_address' ? 'Employer address' : 'Address';

    return (
      <fieldset key={addrField} className="space-y-2">
        <legend className="field-label mb-1">{label}</legend>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {ADDRESS_SUBFIELDS.map((sub) => (
            <div
              key={`${addrField}-${sub.key}`}
              className={sub.key === 'street_address' ? 'sm:col-span-2' : ''}>
              <label
                htmlFor={`vgs-${addrField}-${sub.key}`}
                className="block text-[0.72rem] text-ink-soft mb-0.5">
                {sub.label}
              </label>
              <div
                id={`vgs-${addrField}-${sub.key}`}
                className="w-full"
                style={{height: '44px'}}
              />
            </div>
          ))}
        </div>
      </fieldset>
    );
  };

  return (
    <div className="w-full my-3 surface p-5 md:p-6 reveal">
      <style>{`
        [id^="vgs-"] iframe {
          width: 100% !important;
          height: 100% !important;
          border: none;
        }
      `}</style>

      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="caps text-copper mb-1.5">Secure application details</div>
          <h3 className="display text-[1.55rem] md:text-[1.85rem] leading-[1.1] text-ink mb-2">
            The AI never sees what you type below.
          </h3>
          <p className="text-[0.94rem] text-ink-muted leading-snug max-w-[52ch]">
            Each field is a sealed VGS iframe. Values are tokenized before they
            reach our servers and only decrypted when routed to a lender you
            explicitly authorize. The assistant — and the model behind it —
            only ever receives an opaque token.
          </p>
        </div>
        <div
          className="flex-shrink-0 flex flex-col items-center gap-1 text-moss"
          aria-label="Encrypted">
          <svg viewBox="0 0 24 24" fill="none" className="w-7 h-7">
            <rect x="4" y="9" width="16" height="11" rx="1.5" stroke="currentColor" strokeWidth="1.5" />
            <path
              d="M8 9V7a4 4 0 118 0v2"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
            />
          </svg>
          <span className="caps text-[0.62rem]">Sealed</span>
        </div>
      </div>

      {/* Vault flow diagram */}
      <VaultFlowDiagram />

      {/* What the AI receives */}
      <div className="surface-quiet px-4 py-3 mb-5 flex items-center gap-3 flex-wrap">
        <div className="caps text-ink-muted flex-shrink-0">What the AI receives</div>
        <code className="mono text-[0.82rem] text-ink bg-paper-deep border border-[var(--rule)] rounded px-2 py-1 tnum">
          {illustrativeToken}
        </code>
        <span className="text-[0.78rem] text-ink-soft">
          An opaque reference — not your data.
        </span>
      </div>

      {/* Error */}
      {error && (
        <div
          role="alert"
          aria-live="polite"
          className="mb-4 px-3 py-2.5 rounded-md border border-[var(--oxblood)] bg-[color-mix(in_srgb,var(--oxblood)_8%,var(--paper))] text-[0.88rem] text-[var(--oxblood)]">
          {error}
        </div>
      )}

      {/* Fields */}
      <form onSubmit={handleSubmit} className="space-y-3.5">
        {standardFields.map(renderVGSField)}
        {addressFields.map(renderAddressFields)}

        <hr className="hairline my-4" />

        <p className="text-[0.78rem] text-ink-muted leading-snug">
          This assistant uses <span className="mono">VGS</span> for tokenization. Your
          SSN, birthdate, income, and address stay encrypted end-to-end. The AI
          model never receives them — not during this conversation, not in
          logs, not in training data.
          {userEmail ? (
            <>
              {' '}You'll be recognized as{' '}
              <span className="mono text-ink">{userEmail}</span>.
            </>
          ) : null}
        </p>

        <div className="flex items-center gap-3 pt-1">
          <button
            type="submit"
            disabled={!isReady || isSubmitting}
            className={`btn btn-seal flex-1 ${isSubmitting ? 'sealing' : ''}`}
            aria-describedby="vgs-submit-note">
            {isSubmitting ? (
              <>
                <svg viewBox="0 0 20 20" className="w-4 h-4" fill="none" aria-hidden>
                  <circle cx="10" cy="10" r="7" stroke="currentColor" strokeOpacity="0.35" strokeWidth="2" />
                  <path d="M10 3a7 7 0 017 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                </svg>
                Sealing…
              </>
            ) : (
              <>
                <svg viewBox="0 0 20 20" className="w-4 h-4" fill="none" aria-hidden>
                  <rect x="4" y="8" width="12" height="9" rx="1.25" stroke="currentColor" strokeWidth="1.6" />
                  <path d="M7 8V6a3 3 0 116 0v2" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
                </svg>
                Store securely
              </>
            )}
          </button>
        </div>
        <p id="vgs-submit-note" className="text-[0.72rem] text-ink-soft">
          Submitting stores tokens only. You'll pick which lenders receive which
          fields on the next step.
        </p>
      </form>
    </div>
  );
}
