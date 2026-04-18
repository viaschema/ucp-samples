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
import type {PIIMethod} from '../types';

interface PIIConsentSelectorProps {
  piiMethods: PIIMethod[];
  lenderNames: string[];
  requiredFields: string[];
  loanType: string;
  onSelect: (piiMethodId: string) => void;
}

export default function PIIConsentSelector({
  piiMethods,
  lenderNames,
  requiredFields,
  loanType,
  onSelect,
}: PIIConsentSelectorProps) {
  const [expanded, setExpanded] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const formatFieldName = (field: string) =>
    field
      .split('_')
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(' ');

  const displayFields = requiredFields.length > 0 ? requiredFields : undefined;

  const handleAuthorize = (id: string) => {
    setSelectedId(id);
    onSelect(id);
  };

  return (
    <div className="w-full my-3 surface p-5 md:p-6 reveal">
      <div className="flex items-start justify-between gap-4 mb-3">
        <div>
          <div className="caps text-copper mb-1.5">Authorize lender access</div>
          <h3 className="display text-[1.45rem] md:text-[1.7rem] leading-[1.1] text-ink mb-2">
            Mint per-lender access tokens.
          </h3>
          <p className="text-[0.92rem] text-ink-muted leading-snug max-w-[52ch]">
            Each lender below receives only the fields you consent to — and
            only for this one application. The AI still never sees the raw
            values, only confirmation that the hand-off happened.
          </p>
        </div>
        <div
          aria-label="Secured"
          className="flex-shrink-0 text-moss">
          <svg viewBox="0 0 24 24" fill="none" className="w-6 h-6">
            <rect x="4" y="9" width="16" height="11" rx="1.5" stroke="currentColor" strokeWidth="1.5" />
            <path
              d="M8 9V7a4 4 0 118 0v2"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
            />
          </svg>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
        <div className="surface-quiet p-3">
          <div className="caps text-ink-muted mb-1">Loan type</div>
          <div className="display-tight text-[1.05rem] text-ink capitalize">
            {loanType}
          </div>
        </div>
        <div className="surface-quiet p-3">
          <div className="caps text-ink-muted mb-1">Lenders</div>
          <div className="display-tight text-[1.05rem] text-ink">
            {lenderNames.length} {lenderNames.length === 1 ? 'lender' : 'lenders'}
          </div>
          {lenderNames.length > 0 && (
            <div className="text-[0.78rem] text-ink-muted mt-0.5 leading-tight">
              {lenderNames.join(' · ')}
            </div>
          )}
        </div>
        <div className="surface-quiet p-3">
          <div className="caps text-ink-muted mb-1">Fields shared</div>
          <div className="display-tight text-[1.05rem] text-ink">
            {displayFields ? displayFields.length : '—'}
          </div>
          {displayFields && (
            <button
              type="button"
              onClick={() => setExpanded((s) => !s)}
              className="text-[0.76rem] text-copper hover:underline mt-0.5">
              {expanded ? 'Hide fields' : 'Show the list'}
            </button>
          )}
        </div>
      </div>

      {expanded && displayFields && (
        <div className="surface-deep p-4 mb-4 reveal">
          <div className="caps text-ink-muted mb-2">
            Each lender will receive these values from the vault
          </div>
          <div className="flex flex-wrap gap-1.5">
            {displayFields.map((field) => (
              <span
                key={field}
                className="inline-flex items-center px-2.5 py-1 text-[0.78rem] bg-paper border border-[var(--rule)] rounded-md text-ink">
                <svg
                  viewBox="0 0 12 12"
                  className="w-2.5 h-2.5 mr-1.5 text-moss"
                  fill="currentColor"
                  aria-hidden>
                  <path d="M6 1a3 3 0 00-3 3v2H2.5a.5.5 0 00-.5.5v4a.5.5 0 00.5.5h7a.5.5 0 00.5-.5v-4a.5.5 0 00-.5-.5H9V4a3 3 0 00-3-3zm-2 3a2 2 0 114 0v2H4V4z" />
                </svg>
                {formatFieldName(field)}
              </span>
            ))}
          </div>
        </div>
      )}

      <hr className="hairline my-4" />

      <div className="space-y-2">
        {piiMethods.map((method) => (
          <div
            key={method.id}
            className="surface-quiet p-3.5 flex items-center justify-between gap-3 flex-wrap">
            <div>
              <div className="display-tight text-[1.02rem] text-ink">
                Vaulted profile
              </div>
              <div className="text-[0.78rem] text-ink-muted mt-0.5 mono">
                {method.fields_stored.length} fields tokenized · id{' '}
                {method.id.slice(0, 8)}…
              </div>
            </div>
            <button
              type="button"
              onClick={() => handleAuthorize(method.id)}
              disabled={selectedId === method.id}
              className="btn btn-primary">
              {selectedId === method.id ? 'Authorizing…' : 'Authorize & send'}
            </button>
          </div>
        ))}
      </div>

      <p className="text-[0.72rem] text-ink-soft mt-3 leading-snug">
        Authorization mints per-lender tokens scoped to the fields listed above.
        The AI sees only the tokens; raw values are released in-flight to each
        lender's API and nowhere else.
      </p>
    </div>
  );
}
