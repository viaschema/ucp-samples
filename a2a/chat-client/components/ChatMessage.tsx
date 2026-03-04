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
  onPIICollected?: (piiData: Record<string, string | Record<string, string>>) => void;
  onSubmitNonPII?: (data: Record<string, string>) => void;
}

function TypingIndicator() {
  return (
    <div className="w-full my-1 justify-start">
      <div className="flex items-center gap-2 mb-1">
        <div className="flex-shrink-0">
          <img alt="logo" src={appConfig.logoUrl} className="w-8 h-8" />
        </div>
        <span className="font-semibold text-gray-700">{appConfig.name}</span>
      </div>
      <div className="ml-10 px-4 py-3 rounded-2xl shadow-sm bg-gray-200 text-gray-800 self-start inline-block">
        <div className="flex items-center space-x-2 h-5">
          <span className="h-2 w-2 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
          <span className="h-2 w-2 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
          <span className="h-2 w-2 bg-gray-400 rounded-full animate-bounce"></span>
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
}: ChatMessageProps) {
  const isUser = message.sender === Sender.USER;

  if (message.isLoading) {
    return <TypingIndicator />;
  }

  // User messages are handled separately
  if (isUser) {
    return (
      <div className="flex w-full my-1 items-start gap-2 justify-end">
        <div className="max-w-xs md:max-w-md lg:max-w-2xl px-4 py-2 rounded-2xl shadow-sm bg-blue-500 text-white self-end">
          <div className="whitespace-pre-wrap break-words">{message.text}</div>
        </div>
        <div className="flex-shrink-0 pt-1">
          <UserLogo className="w-8 h-8 text-gray-400" />
        </div>
      </div>
    );
  }

  return (
    <div className="w-full my-1 justify-start">
      <div className="flex items-center gap-2 mb-1">
        <div className="flex-shrink-0">
          <img
            src={appConfig.logoUrl}
            alt={appConfig.name}
            className="w-8 h-8"
          />
        </div>
        <span className="font-semibold text-gray-700">{appConfig.name}</span>
      </div>
      <div className="ml-10 flex-grow min-w-0">
        {message.text && (
          <div className="max-w-xs md:max-w-md lg:max-w-2xl px-4 py-2 rounded-2xl shadow-sm bg-gray-200 text-gray-800 self-start inline-block">
            <div className="break-words whitespace-pre-wrap">
              {message.text}
            </div>
          </div>
        )}

        {/* Domain renderers — each domain handles its own content */}
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
          onSelectPIIMethod={onSelectPIIMethod}
          onPIICollected={onPIICollected}
          onSubmitNonPII={onSubmitNonPII}
        />
      </div>
    </div>
  );
}

export default ChatMessageComponent;
