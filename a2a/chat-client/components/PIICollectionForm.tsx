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
  first_name: {label: 'First Name', type: 'text', placeholder: 'John'},
  last_name: {label: 'Last Name', type: 'text', placeholder: 'Doe'},
  email: {label: 'Email', type: 'email', placeholder: 'john@example.com'},
  phone_number: {label: 'Phone Number', type: 'phone', placeholder: ''},
  address: {label: 'Address', type: 'address', placeholder: ''},
  date_of_birth: {label: 'Date of Birth', type: 'date', placeholder: ''},
  annual_income: {
    label: 'Annual Income ($)',
    type: 'number',
    placeholder: '75000',
  },
  living_situation: {
    label: 'Living Situation',
    type: 'select',
    placeholder: '',
    options: ['rent', 'fully_own', 'mortgage'],
  },
  monthly_housing_payment: {
    label: 'Monthly Housing Payment ($)',
    type: 'number',
    placeholder: '2000',
  },
  employment_status: {
    label: 'Employment Status',
    type: 'select',
    placeholder: '',
    options: ['employed', 'self_employed', 'unemployed', 'retired'],
  },
  employer_address: {
    label: 'Employer Address',
    type: 'address',
    placeholder: '',
  },
  employer_phone_number: {
    label: 'Employer Phone Number',
    type: 'phone',
    placeholder: '',
  },
};

/**
 * Dynamic form for collecting missing PII fields.
 * Renders PhoneInput for phone fields, AddressInput for address fields,
 * selects for enum fields, and standard inputs for the rest.
 */
export default function PIICollectionForm({
  missingFields,
  onSubmit,
}: PIICollectionFormProps) {
  const [formData, setFormData] = useState<Record<string, PIIFieldValue>>({});

  const handleChange = (field: string, value: PIIFieldValue) => {
    setFormData((prev) => ({...prev, [field]: value}));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
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
      // Phone values include the dial code prefix (e.g. "+1") even when
      // empty. Require at least 4 chars for a meaningful phone entry.
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
    <div className="w-full my-2 border border-amber-200 rounded-lg p-4 bg-amber-50">
      <h3 className="font-semibold text-lg text-gray-900 mb-1">
        Additional Information Required
      </h3>
      <p className="text-sm text-gray-600 mb-3">
        We need some additional information to process your loan application.
        This data will be securely stored by your PII provider.
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
                  className="block text-sm font-medium text-gray-700 mb-1">
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
                  className="block text-sm font-medium text-gray-700 mb-1">
                  {config.label}
                </label>
                <select
                  id={`pii-${field}`}
                  value={(formData[field] as string) || ''}
                  onChange={(e) => handleChange(field, e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-blue-500 focus:border-blue-500">
                  <option value="">Select...</option>
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
              <label
                htmlFor={`pii-${field}`}
                className="block text-sm font-medium text-gray-700 mb-1">
                {config.label}
              </label>
              <input
                id={`pii-${field}`}
                type={config.type}
                placeholder={config.placeholder}
                value={(formData[field] as string) || ''}
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
          Submit Information
        </button>
      </form>
    </div>
  );
}
