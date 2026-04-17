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
/// <reference types="vite/client" />

// Default to the dev-server proxy prefix ('/api' is rewritten to '/' by Vite
// and forwarded to the local backend). In production builds, set
// VITE_API_BASE_URL to the deployed backend origin (e.g. Render URL).
const API_BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) || '/api';

const API_KEY: string | undefined = import.meta.env.VITE_API_KEY as
  | string
  | undefined;

/**
 * fetch wrapper that targets the business-agent backend. Prefixes paths with
 * the configured base URL and attaches `Authorization: Bearer <VITE_API_KEY>`
 * if a key is configured. Caller-supplied headers win over defaults so auth
 * can be overridden in tests.
 */
export function apiFetch(
  path: string,
  init: RequestInit = {},
): Promise<Response> {
  const url = path.startsWith('http')
    ? path
    : `${API_BASE_URL}${path.startsWith('/') ? path : `/${path}`}`;

  const authHeader: Record<string, string> = API_KEY
    ? {Authorization: `Bearer ${API_KEY}`}
    : {};

  return fetch(url, {
    ...init,
    headers: {
      ...authHeader,
      ...(init.headers as Record<string, string> | undefined),
    },
  });
}
