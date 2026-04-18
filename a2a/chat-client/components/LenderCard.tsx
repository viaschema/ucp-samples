/*
 * Copyright 2026 UCP Authors
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 */
import type {Lender} from '../types';

interface LenderCardProps {
  lender: Lender;
}

export default function LenderCard({lender}: LenderCardProps) {
  return (
    <article className="flex-shrink-0 w-72 surface p-4 reveal">
      <div className="caps text-ink-muted mb-1.5">{lender.platform_id}</div>
      <h3 className="display-tight text-[1.2rem] text-ink mb-1 leading-tight">
        {lender.lender_name}
      </h3>
      <p className="text-[0.86rem] text-ink-muted leading-snug mb-3 line-clamp-3">
        {lender.description}
      </p>
      <div className="flex flex-wrap gap-1.5">
        {lender.loan_types_offered.map((type) => (
          <span
            key={type}
            className="inline-flex items-center px-2 py-0.5 text-[0.72rem] border border-[var(--rule)] rounded-md text-moss capitalize">
            {type.replace(/_/g, ' ')}
          </span>
        ))}
      </div>
    </article>
  );
}
