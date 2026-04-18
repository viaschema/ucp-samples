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

import type {Checkout, CheckoutItem} from '../types';
import AppointmentDetails from './AppointmentDetails';

interface CheckoutProps {
  checkout: Checkout;
  onCheckout?: () => void;
  onCompletePayment?: (checkout: Checkout) => void;
}

type CheckoutMode = 'lending' | 'appointment' | 'shopping';

function getMode(checkout: Checkout): CheckoutMode {
  if (checkout.lending?.loan_type) return 'lending';
  if (checkout.appointment?.slots && checkout.appointment.slots.length > 0)
    return 'appointment';
  return 'shopping';
}

function LendingMark() {
  return (
    <svg
      viewBox="0 0 24 24"
      className="w-5 h-5 text-ink"
      fill="none"
      aria-hidden>
      <path
        d="M3 20h18M5 20V10l7-4 7 4v10M9 20v-6h6v6"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      <path d="M3 10h18" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

function CartMark() {
  return (
    <svg
      viewBox="0 0 24 24"
      className="w-5 h-5 text-ink"
      fill="none"
      aria-hidden>
      <path
        d="M3 4h2l2.2 11.2a2 2 0 002 1.6h7.4a2 2 0 002-1.5L20 8H6"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      <circle cx="10" cy="20" r="1.3" fill="currentColor" />
      <circle cx="17" cy="20" r="1.3" fill="currentColor" />
    </svg>
  );
}

function CalendarMark() {
  return (
    <svg
      viewBox="0 0 24 24"
      className="w-5 h-5 text-ink"
      fill="none"
      aria-hidden>
      <rect x="3.5" y="5" width="17" height="15" rx="1.5" stroke="currentColor" strokeWidth="1.5" />
      <path d="M3.5 10h17M8 3v4M16 3v4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

function lendingStatusTone(status: string | undefined) {
  switch (status) {
    case 'offers_received':
    case 'completed':
      return {bg: 'bg-[color-mix(in_srgb,var(--moss)_12%,var(--paper))]', text: 'text-moss', label: 'Offers ready'};
    case 'pii_missing':
      return {bg: 'bg-[color-mix(in_srgb,var(--copper)_14%,var(--paper))]', text: 'text-copper', label: 'Collecting details'};
    case 'consent_needed':
      return {bg: 'bg-[color-mix(in_srgb,var(--copper)_14%,var(--paper))]', text: 'text-copper', label: 'Authorization required'};
    case 'applying':
    case 'processing':
      return {bg: 'bg-[color-mix(in_srgb,var(--ink)_8%,var(--paper))]', text: 'text-ink-muted', label: 'Processing'};
    default:
      return {bg: 'bg-[color-mix(in_srgb,var(--ink)_8%,var(--paper))]', text: 'text-ink-muted', label: status ?? 'In progress'};
  }
}

const CheckoutComponent: React.FC<CheckoutProps> = ({
  checkout,
  onCheckout,
  onCompletePayment,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const mode = getMode(checkout);
  const isLending = mode === 'lending';

  const hasLineItems = checkout.line_items && checkout.line_items.length > 0;
  const itemsToShow = isExpanded
    ? checkout.line_items
    : checkout.line_items?.slice(0, 5) ?? [];

  const formatCurrency = (amount: number, currency: string) => {
    const currencySymbol = currency === 'EUR' ? '€' : '$';
    return `${currencySymbol}${(amount / 100).toFixed(2)}`;
  };

  const getTotal = (type: string) => checkout.totals?.find((t) => t.type === type);
  const getItemTotal = (lineItem: CheckoutItem) =>
    lineItem.totals?.find((t) => t.type === 'total');

  const grandTotal = getTotal('total');
  const hasTotals =
    checkout.totals?.some((t) => t.type !== 'total' && t.amount > 0) ?? false;

  const title =
    checkout.status === 'completed'
      ? isLending
        ? 'Application submitted'
        : 'Order confirmed'
      : isLending
        ? 'Loan application'
        : mode === 'appointment'
          ? 'Appointment'
          : 'Checkout summary';

  const eyebrow = isLending
    ? 'In progress · Lending'
    : mode === 'appointment'
      ? 'In progress · Booking'
      : 'In progress · Checkout';

  const Mark = isLending ? LendingMark : mode === 'appointment' ? CalendarMark : CartMark;

  return (
    <div className="w-full my-3 flex justify-start reveal">
      <div className="surface w-full max-w-md p-5 md:p-6">
        {/* Header */}
        <div className="flex items-start gap-3 mb-3">
          <div className="flex-shrink-0 mt-0.5">
            <Mark />
          </div>
          <div className="flex-grow min-w-0">
            <div className="caps text-ink-muted mb-1">{eyebrow}</div>
            <h3 className="display-tight text-[1.35rem] leading-tight text-ink">
              {title}
            </h3>
          </div>
        </div>

        {checkout.order?.id && (
          <>
            <hr className="hairline my-3" />
            <div className="flex items-center justify-between text-[0.84rem]">
              <span className="caps text-ink-muted">Order</span>
              <span className="mono text-ink">{checkout.order.id}</span>
            </div>
          </>
        )}

        {/* Line items (shopping only) */}
        {hasLineItems && (
          <>
            <hr className="hairline my-3" />
            <div className="space-y-3">
              {itemsToShow.map((lineItem: CheckoutItem) => {
                const total = getItemTotal(lineItem);
                return (
                  <div key={lineItem.id} className="flex items-center gap-3 text-sm">
                    {lineItem.item.image_url && (
                      <img
                        src={lineItem.item.image_url}
                        alt={lineItem.item.id}
                        className="w-14 h-14 object-cover rounded-md border border-[var(--rule)]"
                      />
                    )}
                    <div className="flex-grow min-w-0">
                      <p className="font-medium text-ink truncate">
                        {lineItem.item.title}
                      </p>
                      <p className="text-ink-muted text-xs">
                        Qty {lineItem.quantity}
                      </p>
                    </div>
                    {total && (
                      <p className="mono tnum text-ink">
                        {formatCurrency(total.amount, checkout.currency)}
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
            {checkout.line_items.length > 5 && (
              <button
                type="button"
                onClick={() => setIsExpanded((s) => !s)}
                className="mt-3 caps text-copper hover:underline">
                {isExpanded
                  ? 'Show less'
                  : `Show ${checkout.line_items.length - 5} more items`}
              </button>
            )}
          </>
        )}

        {/* Totals (shopping) */}
        {hasTotals && (
          <>
            <hr className="hairline my-3" />
            <div className="space-y-1.5 text-sm">
              {checkout.totals
                .filter((t) => t.type !== 'total' && t.amount > 0)
                .map((total) => (
                  <div key={total.type} className="flex justify-between">
                    <span className="text-ink-muted">{total.display_text}</span>
                    <span className="mono tnum text-ink">
                      {formatCurrency(total.amount, checkout.currency)}
                    </span>
                  </div>
                ))}
            </div>
          </>
        )}

        {grandTotal && !isLending && (
          <>
            <hr className="hairline my-3" />
            <div className="flex justify-between items-baseline">
              <span className="display-tight text-[1.05rem] text-ink">
                {grandTotal.display_text}
              </span>
              <span className="mono tnum text-[1.2rem] text-ink">
                {formatCurrency(grandTotal.amount, checkout.currency)}
              </span>
            </div>
          </>
        )}

        {/* Appointment details — only if slots actually present */}
        {mode === 'appointment' && (
          <>
            <hr className="hairline my-3" />
            <AppointmentDetails appointment={checkout.appointment!} />
          </>
        )}

        {/* Lending summary */}
        {isLending && (
          <>
            <hr className="hairline my-3" />
            <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2.5 text-sm">
              <dt className="caps text-ink-muted self-center">Loan type</dt>
              <dd className="text-right text-ink capitalize">
                {checkout.lending!.loan_type}
              </dd>

              {checkout.lending!.lenders && (
                <>
                  <dt className="caps text-ink-muted self-center">Lenders matched</dt>
                  <dd className="text-right mono tnum text-ink">
                    {checkout.lending!.lenders.length}
                  </dd>
                </>
              )}

              <dt className="caps text-ink-muted self-center">Status</dt>
              <dd className="text-right">
                {(() => {
                  const tone = lendingStatusTone(checkout.lending!.status);
                  return (
                    <span
                      className={`inline-flex items-center px-2 py-0.5 caps rounded-md border border-[var(--rule)] ${tone.bg} ${tone.text}`}>
                      {tone.label}
                    </span>
                  );
                })()}
              </dd>
            </dl>
          </>
        )}

        {/* Footer ID */}
        <hr className="hairline my-3" />
        <p className="caps text-ink-soft text-center">
          {isLending ? 'Application' : 'Checkout'}
          <span className="mono normal-case tracking-normal ml-2 text-[0.7rem]">
            {checkout.id.slice(0, 8)}…
          </span>
        </p>

        {/* Actions */}
        {checkout.status !== 'completed' && !isLending && (
          <div className="mt-4 flex flex-col sm:flex-row gap-2">
            {checkout.continue_url && (
              <a
                href={checkout.continue_url}
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-ghost flex-1">
                Go to checkout
              </a>
            )}
            {onCheckout && (
              <button
                type="button"
                onClick={onCheckout}
                className="btn btn-primary flex-1">
                Start payment
              </button>
            )}
            {onCompletePayment && (
              <button
                type="button"
                onClick={() => onCompletePayment(checkout)}
                className="btn btn-seal flex-1">
                Complete payment
              </button>
            )}
          </div>
        )}

        {checkout.order?.permalink_url && (
          <a
            href={checkout.order.permalink_url}
            className="btn btn-primary w-full mt-4"
            target="_blank"
            rel="noopener noreferrer">
            View order
          </a>
        )}
      </div>
    </div>
  );
};

export default CheckoutComponent;
