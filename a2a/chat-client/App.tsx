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
import {useEffect, useRef, useState} from 'react';
import ChatInput from './components/ChatInput';
import ChatMessageComponent from './components/ChatMessage';
import Header from './components/Header';
import {appConfig} from './config';
import {CredentialProviderProxy} from './mocks/credentialProviderProxy';
import {PIIProviderProxy} from './mocks/piiProviderProxy';

import {registry} from './domains';

import {
  type AvailabilitySlot,
  type ChatMessage,
  type Checkout,
  type PIIConsent,
  type PIIHandler,
  type PIIInstrument,
  type PaymentHandler,
  type PaymentInstrument,
  type Product,
  Sender,
  type ServiceVariation,
} from './types';

type RequestPart =
  | {type: 'text'; text: string}
  | {type: 'data'; data: Record<string, unknown>};

function createChatMessage(
  sender: Sender,
  text: string,
  props: Partial<ChatMessage> = {},
): ChatMessage {
  return {
    id: crypto.randomUUID(),
    sender,
    text,
    ...props,
  };
}

const initialMessage: ChatMessage = createChatMessage(
  Sender.MODEL,
  appConfig.defaultMessage,
  {id: 'initial'},
);

/**
 * An example A2A chat client that demonstrates consuming a business's A2A Agent with UCP Extension.
 * Only for demo purposes, not intended for production use.
 */
function App() {
  const [user_email, setUserEmail] = useState<string | null>('foo@example.com');
  const [messages, setMessages] = useState<ChatMessage[]>([initialMessage]);
  const [isLoading, setIsLoading] = useState(false);
  const [contextId, setContextId] = useState<string | null>(null);
  const [taskId, setTaskId] = useState<string | null>(null);
  const credentialProvider = useRef(new CredentialProviderProxy());
  const piiProvider = useRef(new PIIProviderProxy());
  const pendingPIIInstruments = useRef<PIIInstrument[] | null>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);

  // Scroll to the bottom when new messages are added
  // biome-ignore lint/correctness/useExhaustiveDependencies: Scroll when messages change
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop =
        chatContainerRef.current.scrollHeight;
    }
  }, [messages]);

  // Auto-trigger PII flow when a lending checkout arrives
  // biome-ignore lint/correctness/useExhaustiveDependencies: Trigger PII flow on new messages
  useEffect(() => {
    const lastMsg = messages[messages.length - 1];
    const lendingStatus = lastMsg?.checkout?.lending?.status;
    if (
      (lendingStatus === 'consent_needed' || lendingStatus === 'pii_missing') &&
      !isLoading
    ) {
      handlePIIMethodSelection(lastMsg.checkout);
    }
  }, [messages]);

  const handleAddToCheckout = (productToAdd: Product) => {
    const actionPayload = JSON.stringify({
      action: 'add_to_checkout',
      product_id: productToAdd.productID,
      quantity: 1,
    });
    handleSendMessage(actionPayload, {isUserAction: true});
  };

  const handleAddServiceToCheckout = (service: ServiceVariation) => {
    const actionPayload = JSON.stringify({
      action: 'add_to_checkout',
      service_id: service.id,
    });
    handleSendMessage(actionPayload, {isUserAction: true});
  };

  const handleSelectLocation = (locationId: string) => {
    const actionPayload = JSON.stringify({
      action: 'select_location',
      location_id: locationId,
    });
    handleSendMessage(actionPayload, {isUserAction: true});
  };

  const handleSelectTimeSlot = (slot: AvailabilitySlot) => {
    const actionPayload = JSON.stringify({
      action: 'select_time_slot',
      start_time: slot.start_time || slot.start_at,
      location_id: slot.location?.id || slot.location_id,
      staff_id: slot.staff?.id || slot.appointment_segments?.[0]?.team_member_id,
    });
    handleSendMessage(actionPayload, {isUserAction: true});
  };

  const handleStartPayment = () => {
    const actionPayload = JSON.stringify({action: 'start_payment'});
    handleSendMessage(actionPayload, {
      isUserAction: true,
    });
  };

  const handlePaymentMethodSelection = async (checkout: Checkout) => {
    if (!checkout || !checkout.payment || !checkout.payment.handlers) {
      const errorMessage = createChatMessage(
        Sender.MODEL,
        "Sorry, I couldn't retrieve payment methods.",
      );
      setMessages((prev) => [...prev, errorMessage]);
      return;
    }

    //find the handler with id "example_payment_provider"
    const handler = checkout.payment.handlers.find(
      (handler: PaymentHandler) => handler.id === 'example_payment_provider',
    );
    if (!handler) {
      const errorMessage = createChatMessage(
        Sender.MODEL,
        "Sorry, I couldn't find the supported payment handler.",
      );
      setMessages((prev) => [...prev, errorMessage]);
      return;
    }

    try {
      const paymentResponse =
        await credentialProvider.current.getSupportedPaymentMethods(
          user_email,
          handler.config,
        );
      const paymentMethods = paymentResponse.payment_method_aliases;

      const paymentSelectorMessage = createChatMessage(Sender.MODEL, '', {
        paymentMethods,
      });
      setMessages((prev) => [...prev, paymentSelectorMessage]);
    } catch (error) {
      console.error('Failed to resolve mandate:', error);
      const errorMessage = createChatMessage(
        Sender.MODEL,
        "Sorry, I couldn't retrieve payment methods.",
      );
      setMessages((prev) => [...prev, errorMessage]);
    }
  };

  const handlePaymentMethodSelected = async (selectedMethod: string) => {
    // Hide the payment selector by removing it from the messages
    setMessages((prev) => prev.filter((msg) => !msg.paymentMethods));

    // Add a temporary user message
    const userActionMessage = createChatMessage(
      Sender.USER,
      `User selected payment method: ${selectedMethod}`,
      {isUserAction: true},
    );
    setMessages((prev) => [...prev, userActionMessage]);

    try {
      if (!user_email) {
        throw new Error('User email is not set.');
      }

      const paymentInstrument =
        await credentialProvider.current.getPaymentToken(
          user_email,
          selectedMethod,
        );

      if (!paymentInstrument || !paymentInstrument.credential) {
        throw new Error('Failed to retrieve payment credential');
      }

      const paymentInstrumentMessage = createChatMessage(Sender.MODEL, '', {
        paymentInstrument,
      });
      setMessages((prev) => [...prev, paymentInstrumentMessage]);
    } catch (error) {
      console.error('Failed to process payment mandate:', error);
      const errorMessage = createChatMessage(
        Sender.MODEL,
        "Sorry, I couldn't process the payment. Please try again.",
      );
      setMessages((prev) => [...prev, errorMessage]);
    }
  };

  const handleConfirmPayment = async (paymentInstrument: PaymentInstrument) => {
    // Hide the payment confirmation component
    const userActionMessage = createChatMessage(
      Sender.USER,
      `User confirmed payment.`,
      {isUserAction: true},
    );
    // Let handleSendMessage manage the loading indicator
    setMessages((prev) => [
      ...prev.filter((msg) => !msg.paymentInstrument),
      userActionMessage,
    ]);

    try {
      const parts: RequestPart[] = [
        {type: 'data', data: {'action': 'complete_checkout'}},
        {
          type: 'data',
          data: {
            'a2a.ucp.checkout.payment_data': paymentInstrument,
            'a2a.ucp.checkout.risk_signals': {'data': 'some risk data'},
          },
        },
      ];

      await handleSendMessage(parts, {
        isUserAction: true,
      });
    } catch (error) {
      console.error('Error confirming payment:', error);
      const errorMessage = createChatMessage(
        Sender.MODEL,
        'Sorry, there was an issue confirming your payment.',
      );
      // If handleSendMessage wasn't called, we might need to manually update state
      // In this case, we remove the loading indicator that handleSendMessage would have added
      setMessages((prev) => [...prev.slice(0, -1), errorMessage]); // This assumes handleSendMessage added a loader
      setIsLoading(false); // Ensure loading is stopped on authorization error
    }
  };

  const handlePIIMethodSelection = async (checkout: Checkout) => {
    if (!checkout?.lending?.handlers) {
      const errorMessage = createChatMessage(
        Sender.MODEL,
        "Sorry, I couldn't retrieve PII handlers.",
      );
      setMessages((prev) => [...prev, errorMessage]);
      return;
    }

    // PII handlers are declared independently in pii.handlers.
    // The lending provider is PII-agnostic — it doesn't reference
    // which PII handler to use. The frontend discovers it directly.
    const handler = checkout.lending.handlers?.[0];
    if (!handler) {
      const errorMessage = createChatMessage(
        Sender.MODEL,
        "Sorry, I couldn't find the supported PII handler.",
      );
      setMessages((prev) => [...prev, errorMessage]);
      return;
    }

    try {
      // Use the backend's missing_pii_fields as the source of truth.
      const backendMissing = checkout.lending.missing_pii_fields || [];

      if (backendMissing.length > 0) {
        // Path B: Backend says fields are missing - fetch VGS config and show form
        const vgsConfig = await piiProvider.current.getCollectConfig();
        const collectionMessage = createChatMessage(
          Sender.MODEL,
          'Some personal information is missing. Please fill in the required fields below.',
          {
            piiCollectionFields: backendMissing,
            vgsConfig: vgsConfig.vgs_vault_id
              ? vgsConfig
              : undefined,
          },
        );
        setMessages((prev) => [...prev, collectionMessage]);
      } else {
        // Path A: Backend has all PII, get consent from the frontend vault
        const response = await piiProvider.current.getStoredPIIFields(
          user_email,
          handler.config || {},
        );
        const piiMethods = response.pii_methods;
        const lenders = checkout.lending.lenders || [];
        const piiSelectorMessage = createChatMessage(Sender.MODEL, '', {
          piiMethods,
          piiLenderNames: lenders.map((l) => l.lender_name),
          piiRequiredFields: checkout.lending.required_pii_fields || [],
          piiLoanType: checkout.lending.loan_type || 'personal',
        });
        setMessages((prev) => [...prev, piiSelectorMessage]);
      }
    } catch (error) {
      console.error('Failed to get PII methods:', error);
      const errorMessage = createChatMessage(
        Sender.MODEL,
        "Sorry, I couldn't retrieve PII information.",
      );
      setMessages((prev) => [...prev, errorMessage]);
    }
  };

  const handlePIICollected = async (result: {fields_stored: string[]; email?: string}) => {
    // VGS Collect already stored the data via the inbound route.
    // Update user_email if the form provided one.
    if (result.email) {
      setUserEmail(result.email);
    }
    const effectiveEmail = result.email || user_email;

    // Hide the collection form and proceed to consent.
    setMessages((prev) => prev.filter((msg) => !msg.piiCollectionFields));

    const userActionMessage = createChatMessage(
      Sender.USER,
      'User submitted personal information.',
      {isUserAction: true},
    );
    setMessages((prev) => [...prev, userActionMessage]);

    try {
      if (!effectiveEmail) throw new Error('User email is not set.');

      // Now get PII methods (should have all fields stored)
      const piiResponse = await piiProvider.current.getStoredPIIFields(
        effectiveEmail,
        {},
      );

      const lastCheckoutMsg = [...messages].reverse().find((m) => m.checkout?.lending);
      const lenders = lastCheckoutMsg?.checkout?.lending?.lenders || [];

      const piiSelectorMessage = createChatMessage(Sender.MODEL, '', {
        piiMethods: piiResponse.pii_methods,
        piiLenderNames: lenders.map((l) => l.lender_name),
        piiRequiredFields: lastCheckoutMsg?.checkout?.lending?.required_pii_fields || [],
        piiLoanType: lastCheckoutMsg?.checkout?.lending?.loan_type || 'personal',
      });
      setMessages((prev) => [...prev, piiSelectorMessage]);
    } catch (error) {
      console.error('Failed to process PII submission:', error);
      const errorMessage = createChatMessage(
        Sender.MODEL,
        "Sorry, I couldn't process your information. Please try again.",
      );
      setMessages((prev) => [...prev, errorMessage]);
    }
  };

  const handlePIIMethodSelected = async (selectedMethodId: string) => {
    // Hide the PII selector
    setMessages((prev) => prev.filter((msg) => !msg.piiMethods));

    const userActionMessage = createChatMessage(
      Sender.USER,
      'User authorized PII sharing.',
      {isUserAction: true},
    );
    setMessages((prev) => [...prev, userActionMessage]);

    try {
      if (!user_email) throw new Error('User email is not set.');

      // Build a formal PIIConsent from the checkout context.
      // Discover PII handler dynamically from the lending handler reference.
      const lastCheckoutMsg = [...messages].reverse().find((m) => m.checkout?.lending);
      const lending = lastCheckoutMsg?.checkout?.lending;
      const lenders = lending?.lenders || [];
      const piiHandler = lending?.handlers?.[0];
      if (!piiHandler) {
        throw new Error(
          'No PII handler configured. Check pii.handlers in ucp.json.',
        );
      }

      const consent: PIIConsent = {
        pii_method_id: selectedMethodId,
        handler_id: piiHandler.id,
        fields_consented: lending?.required_pii_fields || [],
        loan_type: lending?.loan_type || 'personal',
        platform_ids: lenders.map((l) => l.platform_id),
        consented_at: new Date().toISOString(),
      };

      // Submit formal consent to the PII vault — it validates, records, and mints tokens
      const {instruments} = await piiProvider.current.submitConsent(
        user_email,
        consent,
      );

      if (!instruments.length || !instruments[0]?.credential) {
        throw new Error('Failed to retrieve PII credentials');
      }

      // Proceed to non-PII form or submit
      const nonPIIFields = lending?.required_non_pii_fields || [];
      const loanType = lending?.loan_type || 'personal';

      if (nonPIIFields.length > 0) {
        pendingPIIInstruments.current = instruments;
        const nonPIIFormMessage = createChatMessage(Sender.MODEL,
          'Please provide the following loan details.',
          {nonPIIForm: {loan_type: loanType, fields: nonPIIFields}},
        );
        setMessages((prev) => [...prev, nonPIIFormMessage]);
      } else {
        await submitLoanApplication(instruments, {});
      }
    } catch (error) {
      console.error('Failed to submit PII consent:', error);
      const errorMessage = createChatMessage(
        Sender.MODEL,
        "Sorry, I couldn't process PII authorization. Please try again.",
      );
      setMessages((prev) => [...prev, errorMessage]);
    }
  };

  const handleSubmitNonPII = async (nonPIIData: Record<string, string>) => {
    const instruments = pendingPIIInstruments.current;

    if (!instruments || instruments.length === 0) {
      const errorMessage = createChatMessage(
        Sender.MODEL,
        'Sorry, PII authorization was not found. Please restart the process.',
      );
      setMessages((prev) => [...prev, errorMessage]);
      return;
    }

    // Hide the non-PII form
    setMessages((prev) => prev.filter((msg) => !msg.nonPIIForm));

    const userActionMessage = createChatMessage(
      Sender.USER,
      'User submitted loan details.',
      {isUserAction: true},
    );
    setMessages((prev) => [...prev, userActionMessage]);

    await submitLoanApplication(instruments, nonPIIData);
  };

  const submitLoanApplication = async (
    piiInstruments: PIIInstrument[],
    nonPIIData: Record<string, string>,
  ) => {
    try {
      const parts: RequestPart[] = [
        {type: 'data', data: {'action': 'submit_loan_application'}},
        {
          type: 'data',
          data: {
            'a2a.ucp.checkout.pii_data': piiInstruments,
            'a2a.ucp.checkout.loan_application': nonPIIData,
          },
        },
      ];

      await handleSendMessage(parts, {isUserAction: true});
    } catch (error) {
      console.error('Error submitting loan application:', error);
      const errorMessage = createChatMessage(
        Sender.MODEL,
        'Sorry, there was an issue submitting your loan application.',
      );
      setMessages((prev) => [...prev, errorMessage]);
      setIsLoading(false);
    }
  };

  const handleSendMessage = async (
    messageContent: string | RequestPart[],
    options?: {isUserAction?: boolean; headers?: Record<string, string>},
  ) => {
    if (isLoading) return;

    const userMessage = createChatMessage(
      Sender.USER,
      options?.isUserAction
        ? '<User Action>'
        : typeof messageContent === 'string'
          ? messageContent
          : 'Sent complex data',
    );
    if (userMessage.text) {
      // Only add if there's text
      setMessages((prev) => [...prev, userMessage]);
    }
    setMessages((prev) => [
      ...prev,
      createChatMessage(Sender.MODEL, '', {isLoading: true}),
    ]);
    setIsLoading(true);

    try {
      const requestParts =
        typeof messageContent === 'string'
          ? [{type: 'text' as const, text: messageContent}]
          : messageContent;

      const requestParams: {
        message: {
          role: string;
          parts: RequestPart[];
          messageId: string;
          kind: string;
          contextId?: string;
          taskId?: string;
        };
        configuration: {
          historyLength: number;
        };
      } = {
        message: {
          role: 'user',
          parts: requestParts,
          messageId: crypto.randomUUID(),
          kind: 'message',
        },
        configuration: {
          historyLength: 0,
        },
      };

      if (contextId) {
        requestParams.message.contextId = contextId;
      }
      if (taskId) {
        requestParams.message.taskId = taskId;
      }

      const defaultHeaders = {
        'Content-Type': 'application/json',
        'X-A2A-Extensions':
          'https://ucp.dev/specification/reference?v=2026-01-11',
        'UCP-Agent':
          'profile="http://localhost:3000/profile/agent_profile.json"',
      };

      const response = await fetch('/api', {
        method: 'POST',
        headers: {...defaultHeaders, ...options?.headers},
        body: JSON.stringify({
          jsonrpc: '2.0',
          id: crypto.randomUUID(),
          method: 'message/send',
          params: requestParams,
        }),
      });

      if (!response.ok || !response.body) {
        throw new Error(`API request failed with status ${response.status}`);
      }

      const data = await response.json();

      // Update context and task IDs from the response for subsequent requests
      if (data.result?.contextId) {
        setContextId(data.result.contextId);
      }
      //if there is a task and it's in one of the active states
      if (
        data.result?.id &&
        data.result?.status?.state in ['working', 'submitted', 'input-required']
      ) {
        setTaskId(data.result.id);
      } else {
        //if not reset taskId
        setTaskId(undefined);
      }

      const combinedBotMessage = createChatMessage(Sender.MODEL, '');

      const responseParts =
        data.result?.parts || data.result?.status?.message?.parts || [];

      for (const part of responseParts) {
        if (part.text) {
          combinedBotMessage.text +=
            (combinedBotMessage.text ? '\n' : '') + part.text;
        } else if (part.data) {
          // Use the domain registry to parse data parts
          const parsed = registry.parseDataPart(part.data);
          // Merge parsed text (product_results may include text content)
          if (parsed.text) {
            combinedBotMessage.text +=
              (combinedBotMessage.text ? '\n' : '') + parsed.text;
            // biome-ignore lint/performance/noDelete: removing before spread
            delete parsed.text;
          }
          Object.assign(combinedBotMessage, parsed);
        }
      }

      const newMessages: ChatMessage[] = [];
      const hasContent =
        combinedBotMessage.text || registry.hasContent(combinedBotMessage);
      if (hasContent) {
        newMessages.push(combinedBotMessage);
      }

      if (newMessages.length > 0) {
        setMessages((prev) => [...prev.slice(0, -1), ...newMessages]);
      } else {
        const fallbackResponse =
          "Sorry, I received a response I couldn't understand.";
        setMessages((prev) => [
          ...prev.slice(0, -1),
          createChatMessage(Sender.MODEL, fallbackResponse),
        ]);
      }
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage = createChatMessage(
        Sender.MODEL,
        'Sorry, something went wrong. Please try again.',
      );
      // Replace the placeholder with the error message
      setMessages((prev) => [...prev.slice(0, -1), errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const lastCheckoutIndex = messages.map((m) => !!m.checkout).lastIndexOf(true);

  return (
    <div className="flex flex-col h-screen max-h-screen bg-white font-sans">
      <Header />
      <main
        ref={chatContainerRef}
        className="flex-grow overflow-y-auto p-4 md:p-6 space-y-2">
        {messages.map((msg, index) => (
          <ChatMessageComponent
            key={msg.id}
            message={msg}
            onAddToCart={handleAddToCheckout}
            onAddServiceToCheckout={handleAddServiceToCheckout}
            onSelectLocation={handleSelectLocation}
            onSelectTimeSlot={handleSelectTimeSlot}
            onCheckout={
              msg.checkout?.status !== 'ready_for_complete' && !msg.checkout?.lending?.loan_type
                ? handleStartPayment
                : undefined
            }
            onSelectPaymentMethod={handlePaymentMethodSelected}
            onConfirmPayment={handleConfirmPayment}
            onCompletePayment={
              msg.checkout?.status === 'ready_for_complete' && !msg.checkout?.lending?.loan_type
                ? handlePaymentMethodSelection
                : undefined
            }
            isLastCheckout={index === lastCheckoutIndex}
            onSelectPIIMethod={handlePIIMethodSelected}
            onPIICollected={handlePIICollected}
            onSubmitNonPII={handleSubmitNonPII}
            userEmail={user_email || undefined}></ChatMessageComponent>
        ))}
      </main>
      <ChatInput onSendMessage={handleSendMessage} isLoading={isLoading} />
    </div>
  );
}

export default App;
