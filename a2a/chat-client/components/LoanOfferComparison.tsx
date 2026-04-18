/*
 * Copyright 2026 UCP Authors
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 */
import {useState} from 'react';
import type {LoanOffer} from '../types';

interface LoanOfferComparisonProps {
  offers: LoanOffer[];
}

type SortField = 'rate' | 'term_months' | 'monthly_payment';

const SORT_LABELS: Record<SortField, string> = {
  rate: 'APR',
  term_months: 'Term',
  monthly_payment: 'Monthly',
};

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
    <section className="w-full my-4 reveal" aria-label="Loan offers">
      <div className="flex items-end justify-between mb-4 gap-4 flex-wrap">
        <div>
          <div className="caps text-copper mb-1">Offers delivered</div>
          <h3 className="display text-[1.55rem] md:text-[1.85rem] text-ink leading-none">
            {offers.length} {offers.length === 1 ? 'offer' : 'offers'} from your lenders
          </h3>
        </div>
        <div className="flex items-center gap-1" role="tablist" aria-label="Sort offers">
          <span className="caps text-ink-muted mr-2">Sort</span>
          {(['rate', 'term_months', 'monthly_payment'] as SortField[]).map((field) => {
            const active = sortBy === field;
            return (
              <button
                key={field}
                type="button"
                onClick={() => setSortBy(field)}
                role="tab"
                aria-selected={active}
                className={`caps px-2.5 py-1.5 rounded-md transition-colors ${
                  active
                    ? 'bg-ink text-paper'
                    : 'text-ink-muted hover:text-ink hover:bg-paper-deep'
                }`}>
                {SORT_LABELS[field]}
                {active && (
                  <span className="ml-1 opacity-90" aria-hidden>
                    ↑
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      <div className="space-y-3">
        {sortedOffers.map((offer, index) => {
          const isBest = offer.rate === bestRate;
          const totalCost = offer.monthly_payment * offer.term_months;
          const totalInterest = totalCost - offer.amount;

          return (
            <article
              key={`${offer.lender_name}-${offer.rate}-${offer.term_months}-${index}`}
              className={`surface p-4 md:p-5 relative ${
                isBest ? 'border-l-4 border-l-[var(--copper)] pl-[calc(1rem-3px)] md:pl-[calc(1.25rem-3px)]' : ''
              }`}>
              {isBest && (
                <span className="absolute -top-2.5 left-4 caps bg-moss text-paper px-2 py-0.5 rounded-sm">
                  Best rate
                </span>
              )}

              <div className="flex items-start justify-between gap-4 mb-4 flex-wrap">
                <div className="min-w-0">
                  <div className="caps text-ink-muted mb-0.5">Lender</div>
                  <div className="display-tight text-[1.3rem] text-ink truncate">
                    {offer.lender_name}
                  </div>
                </div>
                <div className="text-right">
                  <div className="caps text-ink-muted mb-0.5">APR</div>
                  <div className="display text-[2.15rem] md:text-[2.5rem] leading-none text-ink tnum">
                    {offer.rate.toFixed(2)}
                    <span className="text-[1rem] align-top text-ink-muted ml-0.5">%</span>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 md:gap-6 mb-4">
                <Stat label="Monthly" value={formatPayment(offer.monthly_payment)} />
                <Stat label="Term" value={`${offer.term_months} mo`} />
                <Stat label="Principal" value={formatCurrency(offer.amount)} />
                <Stat label="Total interest" value={formatCurrency(totalInterest)} muted />
              </div>

              <a
                href={offer.continue_url}
                target="_blank"
                rel="noopener noreferrer"
                className={`btn w-full ${isBest ? 'btn-copper' : 'btn-primary'}`}>
                Continue at {offer.lender_name}
                <svg viewBox="0 0 16 16" className="w-3.5 h-3.5" fill="none" aria-hidden>
                  <path
                    d="M5 11l6-6m0 0H6m5 0v5"
                    stroke="currentColor"
                    strokeWidth="1.6"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </a>
            </article>
          );
        })}
      </div>

      <p className="caps text-ink-soft mt-4">
        Rates shown are from each lender's live pricing engine · Continuing
        opens the lender's site
      </p>
    </section>
  );
}

function Stat({
  label,
  value,
  muted,
}: {
  label: string;
  value: string;
  muted?: boolean;
}) {
  return (
    <div>
      <div className="caps text-ink-muted mb-1">{label}</div>
      <div
        className={`mono tnum text-[1.02rem] ${muted ? 'text-ink-muted' : 'text-ink'}`}>
        {value}
      </div>
    </div>
  );
}
