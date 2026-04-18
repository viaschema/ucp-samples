/*
 * Copyright 2026 UCP Authors
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 */
import {appConfig} from '@/config';
import {
  AppointmentRenderer,
  LendingRenderer,
  ShoppingRenderer,
} from '../domains';
import {
  type AvailabilitySlot,
  type ChatMessage,
  type Checkout,
  type PaymentInstrument,
  type Product,
  Sender,
  type ServiceVariation,
} from '../types';
import UserLogo from './UserLogo';

interface ChatMessageProps {
  message: ChatMessage;
  onAddToCart?: (product: Product) => Promise<void> | void;
  onAddServiceToCheckout?: (service: ServiceVariation) => void;
  onSelectLocation?: (locationId: string) => void;
  onSelectTimeSlot?: (slot: AvailabilitySlot) => void;
  onCheckout?: () => void;
  onSelectPaymentMethod?: (selectedMethod: string) => void;
  onConfirmPayment?: (paymentInstrument: PaymentInstrument) => void;
  onCompletePayment?: (checkout: Checkout) => void;
  isLastCheckout?: boolean;
  onSelectPIIMethod?: (selectedMethod: string) => void;
  onPIICollected?: (result: {fields_stored: string[]}) => void;
  onSubmitNonPII?: (data: Record<string, string>) => void;
  userEmail?: string;
}

function BotAvatar() {
  return (
    <div
      className="w-8 h-8 rounded-full surface-deep flex items-center justify-center text-ink"
      aria-hidden>
      <svg viewBox="0 0 20 20" fill="none" className="w-4 h-4">
        <circle cx="10" cy="10" r="8" stroke="currentColor" strokeWidth="1.25" />
        <path
          d="M7 11c.7.9 1.8 1.5 3 1.5s2.3-.6 3-1.5"
          stroke="currentColor"
          strokeWidth="1.25"
          strokeLinecap="round"
          fill="none"
        />
        <circle cx="7.8" cy="8.5" r="0.85" fill="currentColor" />
        <circle cx="12.2" cy="8.5" r="0.85" fill="currentColor" />
      </svg>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="w-full my-2 reveal">
      <div className="flex items-center gap-2 mb-1.5">
        <BotAvatar />
        <span className="caps text-ink-muted">{appConfig.name}</span>
      </div>
      <div
        className="ml-10 surface inline-flex px-4 py-3"
        aria-label="Tenor is composing">
        <div className="dot-pulse flex items-center gap-1.5 h-4">
          <span className="w-1.5 h-1.5 rounded-full bg-ink-muted block" />
          <span className="w-1.5 h-1.5 rounded-full bg-ink-muted block" />
          <span className="w-1.5 h-1.5 rounded-full bg-ink-muted block" />
        </div>
      </div>
    </div>
  );
}

function ChatMessageComponent({
  message,
  onAddToCart,
  onAddServiceToCheckout,
  onSelectLocation,
  onSelectTimeSlot,
  onCheckout,
  onSelectPaymentMethod,
  onConfirmPayment,
  onCompletePayment,
  isLastCheckout,
  onSelectPIIMethod,
  onPIICollected,
  onSubmitNonPII,
  userEmail,
}: ChatMessageProps) {
  const isUser = message.sender === Sender.USER;

  if (message.isLoading) {
    return <TypingIndicator />;
  }

  if (isUser) {
    return (
      <div className="flex w-full my-2 items-start gap-2 justify-end reveal">
        <div className="max-w-[85%] md:max-w-md lg:max-w-xl px-4 py-2.5 surface border-l-2 border-l-[var(--copper)] text-ink">
          <div className="whitespace-pre-wrap break-words text-[0.95rem] leading-snug">
            {message.text}
          </div>
        </div>
        <div className="flex-shrink-0 pt-0.5">
          <UserLogo className="w-8 h-8 text-ink-muted" />
        </div>
      </div>
    );
  }

  return (
    <div className="w-full my-2 justify-start reveal">
      <div className="flex items-center gap-2 mb-1.5">
        <BotAvatar />
        <span className="caps text-ink-muted">{appConfig.name}</span>
      </div>
      <div className="ml-10 flex-grow min-w-0 space-y-2">
        {message.text && (
          <div className="max-w-[92%] md:max-w-md lg:max-w-xl surface inline-block px-4 py-2.5 text-ink">
            <div className="break-words whitespace-pre-wrap text-[0.95rem] leading-snug">
              {message.text}
            </div>
          </div>
        )}

        <ShoppingRenderer
          message={message}
          onAddToCart={onAddToCart}
          onCheckout={isLastCheckout ? onCheckout : undefined}
          onCompletePayment={isLastCheckout ? onCompletePayment : undefined}
          onSelectPaymentMethod={onSelectPaymentMethod}
          onConfirmPayment={onConfirmPayment}
          isLastCheckout={isLastCheckout}
        />

        <AppointmentRenderer
          message={message}
          onAddServiceToCheckout={onAddServiceToCheckout}
          onSelectLocation={onSelectLocation}
          onSelectTimeSlot={onSelectTimeSlot}
        />

        <LendingRenderer
          message={message}
          userEmail={userEmail || ''}
          onSelectPIIMethod={onSelectPIIMethod}
          onPIICollected={onPIICollected}
          onSubmitNonPII={onSubmitNonPII}
        />
      </div>
    </div>
  );
}

export default ChatMessageComponent;
