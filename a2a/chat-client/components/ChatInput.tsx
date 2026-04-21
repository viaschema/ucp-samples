/*
 * Copyright 2026 UCP Authors
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 */
import type React from 'react';
import {useEffect, useRef, useState} from 'react';

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  isLoading: boolean;
  prefill?: string;
}

function SendIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      aria-label="Send"
      role="img"
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="w-5 h-5">
      <path d="M4 20l16-8L4 4l3 8-3 8z" />
      <path d="M7 12h13" />
    </svg>
  );
}

function ChatInput({onSendMessage, isLoading, prefill}: ChatInputProps) {
  const [inputValue, setInputValue] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (prefill !== undefined) {
      setInputValue(prefill);
      inputRef.current?.focus();
    }
  }, [prefill]);

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (inputValue.trim() && !isLoading) {
      onSendMessage(inputValue.trim());
      setInputValue('');
    }
  };

  return (
    <div className="bg-paper border-t border-[var(--rule)] flex-shrink-0">
      <form
        onSubmit={handleSubmit}
        className="flex items-center gap-3 max-w-chat mx-auto px-4 md:px-6 py-4">
        <div className="relative flex-grow">
          <input
            ref={inputRef}
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Ask about loan options, rates, or applying…"
            className="field w-full pr-3"
            disabled={isLoading}
            autoComplete="off"
            aria-label="Message input"
          />
        </div>
        <button
          type="submit"
          disabled={isLoading || !inputValue.trim()}
          className="btn btn-copper min-w-[44px] px-3"
          aria-label="Send message">
          <SendIcon />
        </button>
      </form>
      <div className="max-w-chat mx-auto px-4 md:px-6 pb-3 -mt-2">
        <p className="text-[0.7rem] text-ink-soft tracking-wide">
          Your SSN, income, or address is never sent to the AI. Those go
          directly into a VGS vault — only an opaque token reaches this
          conversation.
        </p>
      </div>
    </div>
  );
}

export default ChatInput;
