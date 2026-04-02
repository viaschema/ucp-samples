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

import {z} from 'zod';

/** Zod schema for a postal address (reused for address + employer_address). */
export const postalAddressSchema = z.object({
  street_address: z.string().min(1, 'Street address is required'),
  extended_address: z.string().optional().default(''),
  address_locality: z.string().min(1, 'City is required'),
  address_region: z.string().min(1, 'State is required'),
  postal_code: z.string().min(1, 'ZIP code is required'),
  address_country: z.string().optional().default(''),
});

/** Per-field Zod schema factories for PII fields. */
const PII_FIELD_SCHEMAS: Record<string, () => z.ZodTypeAny> = {
  first_name: () => z.string().min(1, 'First name is required'),
  last_name: () => z.string().min(1, 'Last name is required'),
  email: () =>
    z.string().min(1, 'Email is required').email('Invalid email format'),
  phone_number: () => z.string().min(4, 'Phone number is too short'),
  address: () => postalAddressSchema,
  date_of_birth: () =>
    z
      .string()
      .min(1, 'Date of birth is required')
      .refine(
        (val) => {
          const d = new Date(val);
          return !isNaN(d.getTime()) && d <= new Date();
        },
        'Must be a valid date not in the future',
      ),
  annual_income: () =>
    z
      .string()
      .min(1, 'Annual income is required')
      .refine((v) => Number(v) > 0, 'Must be a positive number'),
  living_situation: () =>
    z.string().min(1, 'Please select a living situation'),
  monthly_housing_payment: () =>
    z
      .string()
      .min(1, 'Monthly payment is required')
      .refine((v) => Number(v) > 0, 'Must be a positive number'),
  employment_status: () =>
    z.string().min(1, 'Please select employment status'),
  employer_address: () => postalAddressSchema,
  employer_phone_number: () =>
    z.string().min(4, 'Phone number is too short'),
};

/** Per-field Zod schema factories for non-PII loan detail fields. */
const NON_PII_FIELD_SCHEMAS: Record<string, () => z.ZodTypeAny> = {
  loan_amount_requested: () =>
    z
      .string()
      .min(1, 'Loan amount is required')
      .refine((v) => Number(v) > 0, 'Must be a positive number'),
  desired_monthly_payment: () =>
    z
      .string()
      .min(1, 'Monthly payment is required')
      .refine((v) => Number(v) > 0, 'Must be a positive number'),
  car_brand: () => z.string().min(1, 'Car brand is required'),
  vin: () =>
    z
      .string()
      .regex(
        /^[A-Za-z0-9]{17}$/,
        'VIN must be exactly 17 alphanumeric characters',
      ),
  car_value: () =>
    z
      .string()
      .min(1, 'Car value is required')
      .refine((v) => Number(v) > 0, 'Must be a positive number'),
};

/** Build a Zod schema containing only the requested PII fields. */
export function buildPIISchema(fields: string[]) {
  const shape: Record<string, z.ZodTypeAny> = {};
  for (const field of fields) {
    const factory = PII_FIELD_SCHEMAS[field];
    shape[field] = factory ? factory() : z.string().min(1, 'Required');
  }
  return z.object(shape);
}

/** Build a Zod schema containing only the requested non-PII fields. */
export function buildNonPIISchema(fields: string[]) {
  const shape: Record<string, z.ZodTypeAny> = {};
  for (const field of fields) {
    const factory = NON_PII_FIELD_SCHEMAS[field];
    shape[field] = factory ? factory() : z.string().min(1, 'Required');
  }
  return z.object(shape);
}

/** Build a Zod schema for only the native select fields in VGS form. */
export function buildVGSSelectSchema(selectFields: string[]) {
  const shape: Record<string, z.ZodTypeAny> = {};
  for (const field of selectFields) {
    const factory = PII_FIELD_SCHEMAS[field];
    shape[field] = factory ? factory() : z.string().min(1, 'Required');
  }
  return z.object(shape);
}
