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
 * Structured address form matching UCP PostalAddress fields.
 */

export interface PostalAddressData {
  street_address?: string;
  extended_address?: string;
  address_locality?: string;
  address_region?: string;
  postal_code?: string;
  address_country?: string;
}

/** Returns true when the required address sub-fields are filled. */
export function isAddressComplete(addr: PostalAddressData | undefined): boolean {
  if (!addr) return false;
  return Boolean(
    addr.street_address?.trim() &&
      addr.address_locality?.trim() &&
      addr.address_region?.trim() &&
      addr.postal_code?.trim(),
  );
}

interface AddressInputProps {
  value: PostalAddressData;
  onChange: (addr: PostalAddressData) => void;
  id?: string;
  label?: string;
}

const inputClass =
  'w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-blue-500 focus:border-blue-500';

export default function AddressInput({
  value,
  onChange,
  id = 'address',
  label = 'Address',
}: AddressInputProps) {
  const update = (field: keyof PostalAddressData, v: string) => {
    onChange({...value, [field]: v});
  };

  return (
    <fieldset className="space-y-2">
      <legend className="block text-sm font-medium text-gray-700 mb-1">
        {label}
      </legend>

      <input
        id={`${id}-street`}
        type="text"
        placeholder="Street address"
        value={value.street_address || ''}
        onChange={(e) => update('street_address', e.target.value)}
        className={inputClass}
      />

      <input
        id={`${id}-extended`}
        type="text"
        placeholder="Apt, suite, unit (optional)"
        value={value.extended_address || ''}
        onChange={(e) => update('extended_address', e.target.value)}
        className={inputClass}
      />

      <div className="grid grid-cols-6 gap-2">
        <input
          id={`${id}-city`}
          type="text"
          placeholder="City"
          value={value.address_locality || ''}
          onChange={(e) => update('address_locality', e.target.value)}
          className={`col-span-3 ${inputClass}`}
        />
        <input
          id={`${id}-state`}
          type="text"
          placeholder="State"
          value={value.address_region || ''}
          onChange={(e) => update('address_region', e.target.value)}
          className={`col-span-1 ${inputClass}`}
        />
        <input
          id={`${id}-zip`}
          type="text"
          placeholder="ZIP"
          value={value.postal_code || ''}
          onChange={(e) => update('postal_code', e.target.value)}
          className={`col-span-2 ${inputClass}`}
        />
      </div>

      <input
        id={`${id}-country`}
        type="text"
        placeholder="Country"
        value={value.address_country || 'US'}
        onChange={(e) => update('address_country', e.target.value)}
        className={inputClass}
      />
    </fieldset>
  );
}
