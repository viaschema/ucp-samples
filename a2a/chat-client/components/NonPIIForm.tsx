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
import type React from 'react';
import {useState} from 'react';

interface NonPIIFormProps {
  loanType: string;
  fields: string[];
  onSubmit: (data: Record<string, string>) => void;
}

const FIELD_CONFIG: Record<
  string,
  {label: string; type: string; placeholder: string}
> = {
  loan_amount_requested: {
    label: 'Loan Amount ($)',
    type: 'number',
    placeholder: '15000',
  },
  desired_monthly_payment: {
    label: 'Desired Monthly Payment ($)',
    type: 'number',
    placeholder: '400',
  },
  car_brand: {label: 'Car Brand', type: 'text', placeholder: 'Toyota'},
  vin: {label: 'VIN', type: 'text', placeholder: '1HGBH41JXMN109186'},
  car_value: {label: 'Car Value ($)', type: 'number', placeholder: '25000'},
};

/**
 * Form for collecting non-PII loan application details.
 * Renders fields dynamically based on the loan type requirements.
 */
export default function NonPIIForm({
  loanType,
  fields,
  onSubmit,
}: NonPIIFormProps) {
  const [formData, setFormData] = useState<Record<string, string>>({});

  const handleChange = (field: string, value: string) => {
    setFormData((prev) => ({...prev, [field]: value}));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
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
    <div className="w-full my-2 border border-gray-200 rounded-lg p-4 bg-white">
      <h3 className="font-semibold text-lg text-gray-900 mb-1">
        Loan Details ({loanType} loan)
      </h3>
      <p className="text-sm text-gray-600 mb-3">
        Please provide the following details for your loan application.
      </p>
      <form onSubmit={handleSubmit} className="space-y-3">
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
                className="block text-sm font-medium text-gray-700 mb-1">
                {config.label}
              </label>
              <input
                id={`nonpii-${field}`}
                type={config.type}
                placeholder={config.placeholder}
                value={formData[field] || ''}
                onChange={(e) => handleChange(field, e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          );
        })}
        <button
          type="submit"
          disabled={!allFilled}
          className={`w-full px-4 py-2 rounded-lg font-medium transition-colors ${
            allFilled
              ? 'bg-blue-600 text-white hover:bg-blue-700'
              : 'bg-gray-300 text-gray-500 cursor-not-allowed'
          }`}>
          Submit Loan Details
        </button>
      </form>
    </div>
  );
}
