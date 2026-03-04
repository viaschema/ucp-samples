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
import type {Lender} from '../types';

interface LenderCardProps {
  lender: Lender;
}

export default function LenderCard({lender}: LenderCardProps) {
  return (
    <div className="flex-shrink-0 w-64 border border-gray-200 rounded-lg p-4 bg-white shadow-sm">
      <h3 className="font-semibold text-lg text-gray-900">
        {lender.lender_name}
      </h3>
      <p className="text-sm text-gray-600 mt-1">{lender.description}</p>
      <div className="mt-2 flex flex-wrap gap-1">
        {lender.loan_types_offered.map((type) => (
          <span
            key={type}
            className="inline-block px-2 py-0.5 text-xs bg-blue-100 text-blue-700 rounded-full">
            {type}
          </span>
        ))}
      </div>
    </div>
  );
}
