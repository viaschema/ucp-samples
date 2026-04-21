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
export class AppProperties {
  name: string;
  description: string;
  logoUrl: string;
  defaultMessage: string;
  titleText: string;
  tagline: string;

  constructor(
    name: string,
    description: string,
    logoUrl: string,
    defaultMessage: string,
    titleText: string,
    tagline: string,
  ) {
    this.name = name;
    this.description = description;
    this.logoUrl = logoUrl;
    this.defaultMessage = defaultMessage;
    this.titleText = titleText;
    this.tagline = tagline;
  }
}

export const appConfig = new AppProperties(
  'Personal Finance Agent',
  'A privacy-first personal finance assistant.',
  '/images/bank-icon.webp',
  "Hi — I'm your Personal Finance Agent. I'll help you shop lenders, compare real offers, and keep your personal details out of the AI's hands. What are you thinking about borrowing for?",
  'Personal Finance Agent',
  'Privacy-first lending',
);
