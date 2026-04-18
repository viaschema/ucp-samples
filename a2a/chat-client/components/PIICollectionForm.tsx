/*
 * Copyright 2026 UCP Authors
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 */
import type React from 'react';
import {useState} from 'react';
import {PhoneInput} from 'react-international-phone';
import 'react-international-phone/style.css';
import AddressInput, {
  isAddressComplete,
  type PostalAddressData,
} from './AddressInput';

export type PIIFieldValue = string | PostalAddressData;

interface PIICollectionFormProps {
  missingFields: string[];
  onSubmit: (piiData: Record<string, PIIFieldValue>) => void;
}

const FIELD_CONFIG: Record<
  string,
  {label: string; type: string; placeholder: string; options?: string[]}
> = {
  first_name: {label: 'First name', type: 'text', placeholder: 'Jamie'},
  last_name: {label: 'Last name', type: 'text', placeholder: 'Rivera'},
  email: {label: 'Email', type: 'email', placeholder: 'jamie@example.com'},
  phone_number: {label: 'Phone number', type: 'phone', placeholder: ''},
  address: {label: 'Address', type: 'address', placeholder: ''},
  date_of_birth: {label: 'Date of birth', type: 'date', placeholder: ''},
  annual_income: {
    label: 'Annual income ($)',
    type: 'number',
    placeholder: '75000',
  },
  living_situation: {
    label: 'Living situation',
    type: 'select',
    placeholder: '',
    options: ['rent', 'fully_own', 'mortgage'],
  },
  monthly_housing_payment: {
    label: 'Monthly housing payment ($)',
    type: 'number',
    placeholder: '2000',
  },
  employment_status: {
    label: 'Employment status',
    type: 'select',
    placeholder: '',
    options: ['employed', 'self_employed', 'unemployed', 'retired'],
  },
  employer_address: {
    label: 'Employer address',
    type: 'address',
    placeholder: '',
  },
  employer_phone_number: {
    label: 'Employer phone number',
    type: 'phone',
    placeholder: '',
  },
};

/**
 * Non-VGS fallback PII form. Used only when VGS tokenization is unavailable
 * (e.g. local dev without VGS credentials). Values flow through the backend
 * as plaintext — clearly labeled as a fallback.
 */
export default function PIICollectionForm({
  missingFields,
  onSubmit,
}: PIICollectionFormProps) {
  const [formData, setFormData] = useState<Record<string, PIIFieldValue>>({});
  const [submitting, setSubmitting] = useState(false);

  const handleChange = (field: string, value: PIIFieldValue) => {
    setFormData((prev) => ({...prev, [field]: value}));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    onSubmit(formData);
  };

  const isFieldFilled = (field: string): boolean => {
    const val = formData[field];
    if (!val) return false;
    const config = FIELD_CONFIG[field];
    if (config?.type === 'address') {
      return isAddressComplete(val as PostalAddressData);
    }
    if (typeof val === 'string') {
      if (config?.type === 'phone') return val.length > 3;
      return val.trim() !== '';
    }
    return false;
  };

  const allFilled = missingFields.every(isFieldFilled);

  const formatFieldName = (field: string) =>
    field
      .split('_')
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(' ');

  return (
    <div className="w-full my-3 surface p-5 md:p-6 reveal">
      <div
        role="alert"
        className="mb-4 px-3 py-2.5 rounded-md border border-[var(--oxblood)] bg-[color-mix(in_srgb,var(--oxblood)_8%,var(--paper))]">
        <div className="flex items-start gap-2">
          <svg
            viewBox="0 0 20 20"
            className="w-4 h-4 text-[var(--oxblood)] mt-0.5 flex-shrink-0"
            fill="currentColor"
            aria-hidden>
            <path d="M10 2a8 8 0 100 16 8 8 0 000-16zm0 5a.9.9 0 01.9.9v4a.9.9 0 01-1.8 0v-4A.9.9 0 0110 7zm0 9.2a1.1 1.1 0 110-2.2 1.1 1.1 0 010 2.2z" />
          </svg>
          <div>
            <div className="caps text-[var(--oxblood)] mb-0.5">Fallback mode</div>
            <p className="text-[0.85rem] text-ink leading-snug">
              VGS tokenization is unavailable in this environment. Values below
              will be sent to the backend directly — not as vault tokens.
              Prefer the secure flow when available.
            </p>
          </div>
        </div>
      </div>

      <h3 className="display text-[1.45rem] text-ink leading-[1.1] mb-2">
        Application details
      </h3>
      <p className="text-[0.9rem] text-ink-muted mb-4 max-w-[52ch]">
        We need some additional information to process your loan application.
        This data will be stored by your PII provider.
      </p>
      <form onSubmit={handleSubmit} className="space-y-3">
        {missingFields.map((field) => {
          const config = FIELD_CONFIG[field] || {
            label: formatFieldName(field),
            type: 'text',
            placeholder: '',
          };

          if (config.type === 'phone') {
            return (
              <div key={field}>
                <label
                  htmlFor={`pii-${field}`}
                  className="field-label">
                  {config.label}
                </label>
                <PhoneInput
                  defaultCountry="us"
                  value={(formData[field] as string) || ''}
                  onChange={(phone) => handleChange(field, phone)}
                />
              </div>
            );
          }

          if (config.type === 'address') {
            return (
              <div key={field}>
                <AddressInput
                  id={`pii-${field}`}
                  label={config.label}
                  value={(formData[field] as PostalAddressData) || {}}
                  onChange={(addr) => handleChange(field, addr)}
                />
              </div>
            );
          }

          if (config.type === 'select' && config.options) {
            return (
              <div key={field}>
                <label
                  htmlFor={`pii-${field}`}
                  className="field-label">
                  {config.label}
                </label>
                <select
                  id={`pii-${field}`}
                  value={(formData[field] as string) || ''}
                  onChange={(e) => handleChange(field, e.target.value)}
                  className="field">
                  <option value="">Select…</option>
                  {config.options.map((opt) => (
                    <option key={opt} value={opt}>
                      {formatFieldName(opt)}
                    </option>
                  ))}
                </select>
              </div>
            );
          }

          return (
            <div key={field}>
              <label htmlFor={`pii-${field}`} className="field-label">
                {config.label}
              </label>
              <input
                id={`pii-${field}`}
                type={config.type}
                placeholder={config.placeholder}
                value={(formData[field] as string) || ''}
                onChange={(e) => handleChange(field, e.target.value)}
                disabled={submitting}
                className="field"
              />
            </div>
          );
        })}
        <button
          type="submit"
          disabled={!allFilled || submitting}
          className="btn btn-primary w-full">
          {submitting ? 'Submitting…' : 'Submit information'}
        </button>
      </form>
    </div>
  );
}
