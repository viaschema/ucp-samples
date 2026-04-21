/*
 * Copyright 2026 UCP Authors
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 */

import type {ChatMessage} from '../types';

interface MarginaliaProps {
  messages: ChatMessage[];
}

type Phase =
  | 'chatting'
  | 'lenders'
  | 'collecting'
  | 'consent'
  | 'loan-details'
  | 'offers'
  | 'complete';

const PHASES: {id: Phase; label: string; detail: string}[] = [
  {id: 'chatting', label: 'Chat', detail: 'Describing your need'},
  {id: 'lenders', label: 'Lenders', detail: 'Matching networks'},
  {id: 'collecting', label: 'Details', detail: 'Sealed into VGS vault'},
  {id: 'consent', label: 'Authorize', detail: 'Per-lender consent'},
  {id: 'loan-details', label: 'Loan terms', detail: 'Amount & structure'},
  {id: 'offers', label: 'Offers', detail: 'Compare APRs'},
];

function derivePhase(messages: ChatMessage[]): Phase {
  for (let i = messages.length - 1; i >= 0; i--) {
    const m = messages[i];
    if (m.loanOffers?.length) return 'offers';
    if (m.nonPIIForm) return 'loan-details';
    if (m.piiMethods?.length) return 'consent';
    if (m.piiCollectionFields?.length) return 'collecting';
    if (m.lenders?.length) return 'lenders';
  }
  return 'chatting';
}

export default function Marginalia({messages}: MarginaliaProps) {
  const current = derivePhase(messages);
  const currentIndex = PHASES.findIndex((p) => p.id === current);

  return (
    <aside
      aria-label="Application progress"
      className="hidden lg:block w-56 pl-6 pt-2 sticky top-4 self-start">
      <div className="caps text-ink-muted mb-4">Progress</div>
      <ol className="space-y-3">
        {PHASES.map((phase, i) => {
          const state =
            i < currentIndex ? 'done' : i === currentIndex ? 'active' : 'todo';
          return (
            <li key={phase.id} className="flex gap-3">
              <div className="flex flex-col items-center pt-1">
                <span
                  className={`w-2 h-2 rounded-full transition-colors ${
                    state === 'done'
                      ? 'bg-moss'
                      : state === 'active'
                        ? 'bg-copper ring-4 ring-[color-mix(in_srgb,var(--copper)_25%,transparent)]'
                        : 'bg-[var(--rule-strong)]'
                  }`}
                />
                {i < PHASES.length - 1 && (
                  <span
                    className={`w-px flex-1 min-h-[22px] mt-1 ${
                      state === 'done' ? 'bg-moss' : 'bg-[var(--rule)]'
                    }`}
                  />
                )}
              </div>
              <div
                className={`text-sm leading-snug ${
                  state === 'active'
                    ? 'text-ink'
                    : state === 'done'
                      ? 'text-ink-muted'
                      : 'text-ink-soft'
                }`}>
                <div className={state === 'active' ? 'display-tight' : 'font-medium'}>
                  {phase.label}
                </div>
                <div className="text-[0.76rem] text-ink-muted leading-tight">
                  {phase.detail}
                </div>
              </div>
            </li>
          );
        })}
      </ol>
    </aside>
  );
}
