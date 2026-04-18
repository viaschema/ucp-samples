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

interface NonPIIFormProps {
  loanType: string;
  fields: string[];
  onSubmit: (data: Record<string, string>) => void;
}

const FIELD_CONFIG: Record<
  string,
  {label: string; type: string; placeholder: string; prefix?: string; hint?: string}
> = {
  loan_amount_requested: {
    label: 'Loan amount',
    type: 'number',
    placeholder: '15000',
    prefix: '$',
    hint: 'USD, before fees',
  },
  desired_monthly_payment: {
    label: 'Desired monthly payment',
    type: 'number',
    placeholder: '400',
    prefix: '$',
    hint: 'We match lenders whose terms fit',
  },
  car_brand: {label: 'Car brand', type: 'text', placeholder: 'Toyota'},
  vin: {label: 'VIN', type: 'text', placeholder: '1HGBH41JXMN109186'},
  car_value: {
    label: 'Car value',
    type: 'number',
    placeholder: '25000',
    prefix: '$',
  },
};

export default function NonPIIForm({
  loanType,
  fields,
  onSubmit,
}: NonPIIFormProps) {
  const [formData, setFormData] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  const handleChange = (field: string, value: string) => {
    setFormData((prev) => ({...prev, [field]: value}));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    onSubmit(formData);
  };

  const formatFieldName = (field: string) =>
    field
      .split('_')
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(' ');

  const allFilled = fields.every(
    (field) => formData[field] && formData[field].trim() !== '',
  );

  return (
    <div className="w-full my-3 surface p-5 md:p-6 reveal">
      <div className="caps text-copper mb-1.5">Loan terms · {loanType}</div>
      <h3 className="display text-[1.45rem] md:text-[1.65rem] leading-[1.1] text-ink mb-2">
        Non-sensitive details.
      </h3>
      <p className="text-[0.9rem] text-ink-muted leading-snug max-w-[52ch] mb-4">
        These values shape the offers you'll see. Amounts and product specifics
        are not PII — they go through our backend directly, not the vault.
      </p>

      <form onSubmit={handleSubmit} className="space-y-3.5">
        {fields.map((field) => {
          const config = FIELD_CONFIG[field] || {
            label: formatFieldName(field),
            type: 'text',
            placeholder: '',
          };
          return (
            <div key={field}>
              <label
                htmlFor={`nonpii-${field}`}
                className="field-label flex items-center justify-between gap-2">
                <span>{config.label}</span>
                {config.hint && (
                  <span className="text-[0.72rem] text-ink-soft font-normal">
                    {config.hint}
                  </span>
                )}
              </label>
              <div className="relative">
                {config.prefix && (
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-muted mono">
                    {config.prefix}
                  </span>
                )}
                <input
                  id={`nonpii-${field}`}
                  type={config.type}
                  inputMode={config.type === 'number' ? 'decimal' : undefined}
                  placeholder={config.placeholder}
                  value={formData[field] || ''}
                  onChange={(e) => handleChange(field, e.target.value)}
                  disabled={submitting}
                  className={`field ${
                    config.type === 'number' && config.prefix ? 'pl-7 mono tnum' : ''
                  }`}
                />
              </div>
            </div>
          );
        })}
        <button
          type="submit"
          disabled={!allFilled || submitting}
          className={`btn btn-primary w-full ${submitting ? 'sealing' : ''}`}>
          {submitting ? 'Submitting…' : 'Save loan terms & continue'}
        </button>
      </form>
    </div>
  );
}
