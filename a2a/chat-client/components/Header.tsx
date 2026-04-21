/*
 * Copyright 2026 UCP Authors
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 */
import {useEffect, useState} from 'react';
import {appConfig} from '@/config';

function BrandMark() {
  return (
    <div
      className="w-10 h-10 rounded-md surface-deep flex items-center justify-center overflow-hidden"
      aria-hidden>
      <img
        src={appConfig.logoUrl}
        alt=""
        className="w-7 h-7 object-contain"
      />
    </div>
  );
}

function PrivacyExplainerModal({onClose}: {onClose: () => void}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="privacy-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[rgba(21,20,26,0.38)]"
      onClick={onClose}>
      <div
        className="surface max-w-xl w-full p-6 md:p-8 reveal"
        onClick={(e) => e.stopPropagation()}>
        <div className="caps text-copper mb-2">How this agent handles your data</div>
        <h2
          id="privacy-modal-title"
          className="display text-[1.7rem] md:text-[2rem] text-ink leading-[1.1] mb-4">
          Three separate systems. One conversation.
        </h2>

        <ol className="space-y-4 text-[0.94rem] text-ink leading-snug">
          <li>
            <span className="caps text-moss block mb-0.5">1 · Vault</span>
            Your PII is typed into VGS-controlled iframes. Values are tokenized at
            the VGS edge before they ever reach our backend. We store tokens; we
            never store the underlying SSN, date of birth, income, or address.
          </li>
          <li>
            <span className="caps text-moss block mb-0.5">2 · Assistant</span>
            The AI model (Gemini) only sees opaque references like{' '}
            <code className="mono text-[0.88em]">pii_token_7f3a…</code>. Not your
            name. Not your income. Not in the prompt, not in logs, not in
            training.
          </li>
          <li>
            <span className="caps text-moss block mb-0.5">3 · Lender</span>
            When you authorize a specific lender, VGS decrypts in-flight on that
            one outbound request. Other lenders and other parts of our system
            never see the raw values.
          </li>
        </ol>

        <hr className="hairline my-5" />

        <p className="text-[0.82rem] text-ink-muted">
          This is a demo of the UCP lending protocol with VGS as the PII
          provider. Source: <span className="mono">samples/a2a/docs/12-pii-collection-overview.md</span>.
        </p>

        <div className="mt-6 flex justify-end">
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Got it
          </button>
        </div>
      </div>
    </div>
  );
}

function Header() {
  const [showPrivacy, setShowPrivacy] = useState(false);

  return (
    <>
      <header className="bg-paper border-b border-[var(--rule)] flex-shrink-0">
        <div className="max-w-offers mx-auto px-4 md:px-6 py-4 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <BrandMark />
            <div className="flex flex-col leading-none min-w-0">
              <span className="display text-[1.3rem] md:text-[1.55rem] text-ink leading-tight">
                {appConfig.titleText}
              </span>
              <span className="caps text-ink-muted mt-1">
                {appConfig.tagline}
              </span>
            </div>
          </div>

          <button
            type="button"
            onClick={() => setShowPrivacy(true)}
            className="btn btn-ghost min-h-[40px] py-0 text-sm"
            aria-haspopup="dialog">
            <svg viewBox="0 0 20 20" className="w-4 h-4" fill="currentColor" aria-hidden>
              <path d="M10 2a8 8 0 100 16 8 8 0 000-16zm.75 11.5a.75.75 0 11-1.5 0V9a.75.75 0 011.5 0v4.5zM10 7.25a.9.9 0 110-1.8.9.9 0 010 1.8z" />
            </svg>
            How your data is handled
          </button>
        </div>
      </header>
      {showPrivacy && <PrivacyExplainerModal onClose={() => setShowPrivacy(false)} />}
    </>
  );
}

export default Header;
