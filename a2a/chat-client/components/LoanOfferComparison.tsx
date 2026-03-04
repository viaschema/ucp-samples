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
import {useState} from 'react';
import type {LoanOffer} from '../types';

interface LoanOfferComparisonProps {
  offers: LoanOffer[];
}

type SortField = 'rate' | 'term_months' | 'monthly_payment';

export default function LoanOfferComparison({
  offers,
}: LoanOfferComparisonProps) {
  const [sortBy, setSortBy] = useState<SortField>('rate');

  const sortedOffers = [...offers].sort((a, b) => a[sortBy] - b[sortBy]);
  const bestRate = sortedOffers.length > 0 ? sortedOffers[0].rate : null;

  const formatCurrency = (amount: number) =>
    new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);

  const formatPayment = (amount: number) =>
    new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);

  return (
    <div className="w-full my-2">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-lg text-gray-900">
          Loan Offers ({offers.length})
        </h3>
        <div className="flex items-center gap-2 text-sm">
          <span className="text-gray-500">Sort by:</span>
          {(['rate', 'term_months', 'monthly_payment'] as SortField[]).map(
            (field) => (
              <button
                key={field}
                type="button"
                onClick={() => setSortBy(field)}
                className={`px-2 py-1 rounded ${sortBy === field ? 'bg-blue-100 text-blue-700' : 'text-gray-600 hover:bg-gray-100'}`}>
                {field === 'rate'
                  ? 'Rate'
                  : field === 'term_months'
                    ? 'Term'
                    : 'Payment'}
              </button>
            ),
          )}
        </div>
      </div>

      <div className="space-y-3">
        {sortedOffers.map((offer, index) => {
          const isBest = offer.rate === bestRate;
          const totalCost = offer.monthly_payment * offer.term_months;
          const totalInterest = totalCost - offer.amount;

          return (
            <div
              key={`${offer.lender_name}-${offer.rate}-${offer.term_months}-${index}`}
              className={`rounded-lg border p-4 ${
                isBest
                  ? 'border-green-300 bg-green-50'
                  : 'border-gray-200 bg-white hover:border-gray-300'
              }`}>
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-gray-900 text-base">
                    {offer.lender_name}
                  </span>
                  {isBest && (
                    <span className="px-2 py-0.5 text-xs font-medium bg-green-100 text-green-700 rounded-full">
                      Best Rate
                    </span>
                  )}
                </div>
                <span className="text-2xl font-bold text-gray-900">
                  {offer.rate}%
                  <span className="text-xs font-normal text-gray-500 ml-1">
                    APR
                  </span>
                </span>
              </div>

              <div className="grid grid-cols-4 gap-3 mb-3 text-sm">
                <div>
                  <span className="text-gray-500 block">Monthly</span>
                  <span className="font-semibold text-gray-900">
                    {formatPayment(offer.monthly_payment)}
                  </span>
                </div>
                <div>
                  <span className="text-gray-500 block">Term</span>
                  <span className="font-semibold text-gray-900">
                    {offer.term_months} months
                  </span>
                </div>
                <div>
                  <span className="text-gray-500 block">Amount</span>
                  <span className="font-semibold text-gray-900">
                    {formatCurrency(offer.amount)}
                  </span>
                </div>
                <div>
                  <span className="text-gray-500 block">Total Interest</span>
                  <span className="font-semibold text-gray-900">
                    {formatCurrency(totalInterest)}
                  </span>
                </div>
              </div>

              <a
                href={offer.continue_url}
                target="_blank"
                rel="noopener noreferrer"
                className={`block w-full text-center py-2 px-4 rounded-md text-sm font-semibold transition-colors ${
                  isBest
                    ? 'bg-green-600 hover:bg-green-700 text-white'
                    : 'bg-blue-600 hover:bg-blue-700 text-white'
                }`}>
                Apply at {offer.lender_name}
              </a>
            </div>
          );
        })}
      </div>
    </div>
  );
}
