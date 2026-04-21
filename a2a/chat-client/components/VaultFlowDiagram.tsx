/*
 * Copyright 2026 UCP Authors
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 */

/**
 * Three-step visual showing the path sensitive data takes:
 *   Browser  →  VGS vault  →  Authorized lender
 *
 * The AI/agent is shown *outside* this path, receiving only a token.
 */
export default function VaultFlowDiagram() {
  const steps = [
    {
      title: 'Your browser',
      body: 'Typed directly into a VGS-controlled iframe. Our JavaScript cannot read these values.',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" className="w-5 h-5">
          <path
            d="M4 6h16v12H4z"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinejoin="round"
          />
          <path d="M8 10h8M8 13h5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      ),
    },
    {
      title: 'VGS vault',
      body: 'Tokenized at the edge. Our backend stores only the token — no raw SSN, income, or address ever lands on our servers.',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" className="w-5 h-5">
          <rect x="4" y="9" width="16" height="11" rx="1.5" stroke="currentColor" strokeWidth="1.5" />
          <path
            d="M8 9V7a4 4 0 118 0v2"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
          <circle cx="12" cy="14.5" r="1.3" fill="currentColor" />
          <path d="M12 15.8v1.7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      ),
    },
    {
      title: 'Authorized lender',
      body: 'Raw values are decrypted in-flight, only for the lender you explicitly consent to. Never broadcast.',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" className="w-5 h-5">
          <path
            d="M3 20h18M5 20V10l7-5 7 5v10M9 20v-5h6v5"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinejoin="round"
            strokeLinecap="round"
          />
        </svg>
      ),
    },
  ];

  return (
    <div className="surface-deep p-4 md:p-5 my-4">
      <div className="flex items-center justify-between mb-3">
        <span className="caps text-ink-muted">The path your data takes</span>
        <span className="caps text-moss">AI never in this path</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-[1fr_auto_1fr_auto_1fr] gap-3 md:gap-2 items-stretch">
        {steps.map((step, i) => (
          // biome-ignore lint/suspicious/noArrayIndexKey: static ordered list
          <div key={i} className="contents">
            <div className="surface p-3 md:p-4 flex flex-col gap-1.5">
              <div className="flex items-center gap-2 text-moss">
                {step.icon}
                <span className="display-tight text-[1.02rem] text-ink">{step.title}</span>
              </div>
              <p className="text-[0.82rem] leading-snug text-ink-muted">{step.body}</p>
            </div>
            {i < steps.length - 1 && (
              <div className="hidden md:flex items-center justify-center px-1">
                <svg viewBox="0 0 40 12" className="w-10 h-3 text-ink-muted" aria-hidden>
                  <path
                    d="M0 6h32m0 0l-4-4m4 4l-4 4"
                    stroke="currentColor"
                    strokeWidth="1.2"
                    fill="none"
                  />
                </svg>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
