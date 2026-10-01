import React, { useState, useRef, useEffect } from 'react';
import type { ChatMessage, LegalResponse } from './types';
import { sendLegalQuery } from './services/api';
import { Header } from './components/Header';
import { HeroLanding } from './components/HeroLanding';
import { MessageBubble } from './components/MessageBubble';
import { LoadingIndicator } from './components/LoadingIndicator';
import { ChatInput } from './components/ChatInput';
import { DisclaimerBanner } from './components/DisclaimerBanner';
import { generateMessageId, getCurrentTimestamp } from './utils/id';

export const App: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [inputQuery, setInputQuery] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Automatically scroll to the latest message whenever messages or loading state changes
  useEffect(() => {
    if (messages.length > 0 || isLoading) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isLoading]);

  const handleStartNewConversation = () => {
    setMessages([]);
    setConversationId(null);
    setInputQuery('');
    setIsLoading(false);
  };

  const handleSendQuery = async (queryText?: string) => {
    const rawQuery = queryText || inputQuery;
    const cleanQuery = rawQuery.trim();
    if (!cleanQuery || isLoading) return;

    // 1. Append user query
    const userMessageId = generateMessageId('user');
    const newUserMessage: ChatMessage = {
      id: userMessageId,
      role: 'user',
      content: cleanQuery,
      timestamp: getCurrentTimestamp(),
    };

    setMessages((prev) => [...prev, newUserMessage]);
    setInputQuery('');
    setIsLoading(true);

    // 2. Dispatch query to API
    try {
      const legalResponse: LegalResponse = await sendLegalQuery(cleanQuery, conversationId);

      // Store/update conversational session ID
      const resolvedSessionId = legalResponse.conversation_id || legalResponse.session_id;
      if (resolvedSessionId) {
        setConversationId(resolvedSessionId);
      }

      // 3. Append assistant response
      const assistantMessageId = generateMessageId('assistant');
      const newAssistantMessage: ChatMessage = {
        id: assistantMessageId,
        role: 'assistant',
        content: legalResponse.answer,
        response: legalResponse,
        timestamp: getCurrentTimestamp(),
      };

      setMessages((prev) => [...prev, newAssistantMessage]);
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error
          ? err.message
          : 'Unable to reach the LawLens legal service. Please ensure the backend is running.';

      const errorMsgId = generateMessageId('error');
      const errorAssistantMessage: ChatMessage = {
        id: errorMsgId,
        role: 'assistant',
        content: errorMessage,
        timestamp: getCurrentTimestamp(),
        isError: true,
      };

      setMessages((prev) => [...prev, errorAssistantMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRetry = (failedQuery: string) => {
    handleSendQuery(failedQuery);
  };

  return (
    <div className="lawlens-app">
      <Header
        onNewConversation={handleStartNewConversation}
        hasMessages={messages.length > 0}
        conversationId={conversationId}
      />

      <main className="main-content" role="main">
        {messages.length === 0 ? (
          <HeroLanding onSelectQuery={(selected) => handleSendQuery(selected)} />
        ) : (
          <div className="chat-messages-container" role="log" aria-live="polite">
            <div className="chat-messages-inner">
              {messages.map((msg) => (
                <MessageBubble
                  key={msg.id}
                  message={msg}
                  onRetry={msg.isError ? () => handleRetry(msg.content) : undefined}
                />
              ))}

              {isLoading && <LoadingIndicator />}
              <div ref={messagesEndRef} aria-hidden="true" />
            </div>
          </div>
        )}
      </main>

      <ChatInput
        query={inputQuery}
        onChange={setInputQuery}
        onSubmit={() => handleSendQuery()}
        isLoading={isLoading}
      />

      <DisclaimerBanner />
    </div>
  );
};

export default App;
