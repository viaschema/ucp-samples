/*
 * Copyright 2026 UCP Authors
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 */

interface LandingSuggestionsProps {
  onSuggest: (prompt: string) => void;
}

const SUGGESTIONS = [
  {
    kind: 'Personal',
    prompt:
      'I want a $15k personal loan to consolidate credit card debt. Show me options.',
    detail: 'Consolidate ~$15k of revolving debt at a fixed rate.',
  },
  {
    kind: 'Auto',
    prompt:
      'Show me 60-month auto loan offers for a used 2022 Toyota around $28k.',
    detail: 'Compare rates across lenders for a used-car purchase.',
  },
  {
    kind: 'How it works',
    prompt:
      'Walk me through how applying works and what data you share with lenders.',
    detail: 'Understand the privacy model before you share anything.',
  },
];

export default function LandingSuggestions({onSuggest}: LandingSuggestionsProps) {
  return (
    <section className="w-full max-w-chat mx-auto reveal" aria-label="Suggested ways to start">
      <div className="mb-4 flex items-baseline justify-between">
        <span className="caps text-ink-muted">Try starting with</span>
        <span className="caps text-ink-soft hidden sm:inline">Optional — you can also just type</span>
      </div>
      <div className="grid gap-3 grid-cols-1 md:grid-cols-3">
        {SUGGESTIONS.map((s, i) => (
          <button
            key={s.kind}
            type="button"
            onClick={() => onSuggest(s.prompt)}
            className="surface text-left p-4 md:p-5 hover:border-[var(--copper)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--copper)] transition-colors reveal"
            style={{animationDelay: `${100 + i * 80}ms`}}>
            <div className="caps text-copper mb-2">{s.kind}</div>
            <div className="display-tight text-[1.08rem] leading-snug text-ink mb-2">
              {s.prompt.replace(/^"|"$/g, '')}
            </div>
            <div className="text-[0.82rem] text-ink-muted leading-snug">{s.detail}</div>
          </button>
        ))}
      </div>
    </section>
  );
}
