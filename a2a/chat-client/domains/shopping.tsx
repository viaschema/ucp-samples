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

/**
 * Shopping domain — response handlers and renderers for catalog,
 * checkout, payment method selection, and payment confirmation.
 */

import type React from 'react';
import CheckoutComponent from '../components/Checkout';
import PaymentConfirmationComponent from '../components/PaymentConfirmation';
import PaymentMethodSelector from '../components/PaymentMethodSelector';
import ProductCard from '../components/ProductCard';
import type {
  AvailabilitySlot,
  ChatMessage,
  Checkout,
  PaymentInstrument,
  Product,
  ServiceVariation,
} from '../types';
import type {ResponseHandler} from './registry';

// ---------------------------------------------------------------------------
// Response handlers
// ---------------------------------------------------------------------------

export const shoppingResponseHandlers: ResponseHandler[] = [
  {
    dataKey: 'a2a.product_results',
    parse: (data: unknown) => {
      const d = data as {content?: string; results?: Product[]};
      return {
        text: d.content || '',
        products: d.results,
      };
    },
  },
  {
    dataKey: 'a2a.ucp.checkout',
    parse: (data: unknown) => ({checkout: data as Checkout}),
  },
];

export function shoppingHasContent(msg: ChatMessage): boolean {
  return !!(msg.products || msg.checkout || msg.paymentMethods || msg.paymentInstrument);
}

// ---------------------------------------------------------------------------
// Renderer
// ---------------------------------------------------------------------------

export interface ShoppingRendererProps {
  message: ChatMessage;
  onAddToCart?: (product: Product) => void;
  onCheckout?: () => void;
  onCompletePayment?: (checkout: Checkout) => void;
  onSelectPaymentMethod?: (method: string) => void;
  onConfirmPayment?: (instrument: PaymentInstrument) => void;
  isLastCheckout?: boolean;
}

export const ShoppingRenderer: React.FC<ShoppingRendererProps> = ({
  message,
  onAddToCart,
  onCheckout,
  onCompletePayment,
  onSelectPaymentMethod,
  onConfirmPayment,
  isLastCheckout,
}) => {
  return (
    <>
      {message.paymentMethods && onSelectPaymentMethod && (
        <PaymentMethodSelector
          paymentMethods={message.paymentMethods}
          onSelect={onSelectPaymentMethod}
        />
      )}

      {message.paymentInstrument && onConfirmPayment && (
        <PaymentConfirmationComponent
          paymentInstrument={message.paymentInstrument}
          onConfirm={() => onConfirmPayment(message.paymentInstrument!)}
        />
      )}

      {message.products && message.products.length > 0 && (
        <div className="w-full my-1 overflow-x-auto">
          <div className="flex space-x-4 p-2">
            {message.products.map((product) => (
              <ProductCard
                key={product.productID}
                product={product}
                onAddToCart={onAddToCart}
              />
            ))}
          </div>
        </div>
      )}

      {message.checkout && (
        <CheckoutComponent
          checkout={message.checkout}
          onCheckout={isLastCheckout ? onCheckout : undefined}
          onCompletePayment={isLastCheckout ? onCompletePayment : undefined}
        />
      )}
    </>
  );
};
