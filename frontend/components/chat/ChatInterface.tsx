'use client';

import { useState, useRef, useEffect } from 'react';
import { Send, Loader2, Sparkles, Copy, Check } from 'lucide-react';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: string[];
  highlighted_nodes?: string[];
  highlighted_edges?: string[];
  timestamp: Date;
}

interface ChatInterfaceProps {
  projectId: string;
  onSendMessage: (message: string) => Promise<{
    content: string;
    citations?: string[];
    highlighted_nodes?: string[];
    highlighted_edges?: string[];
  }>;
  onCitationClick?: (citation: string) => void;
  initialMessages?: Message[];
}

export function ChatInterface({
  projectId,
  onSendMessage,
  onCitationClick,
  initialMessages = [],
}: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Handle send message
  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await onSendMessage(input.trim());

      const assistantMessage: Message = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: response.content,
        citations: response.citations,
        highlighted_nodes: response.highlighted_nodes,
        highlighted_edges: response.highlighted_edges,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage: Message = {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your request. Please try again.',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle copy message
  const handleCopy = async (messageId: string, content: string) => {
    await navigator.clipboard.writeText(content);
    setCopiedId(messageId);
    setTimeout(() => setCopiedId(null), 2000);
  };

  // Handle keyboard submit
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Suggested questions
  const suggestedQuestions = [
    'What are the main research methods used?',
    'Which concepts appear most frequently?',
    'What are the key findings?',
    'Identify research gaps in this collection',
  ];

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center py-12">
            <Sparkles className="w-12 h-12 text-blue-500 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Ask about your research
            </h3>
            <p className="text-gray-600 mb-6 max-w-md mx-auto">
              I can help you explore your knowledge graph, find connections between papers,
              and identify research trends and gaps.
            </p>

            {/* Suggested Questions */}
            <div className="flex flex-wrap justify-center gap-2">
              {suggestedQuestions.map((question, i) => (
                <button
                  key={i}
                  onClick={() => {
                    setInput(question);
                    inputRef.current?.focus();
                  }}
                  className="px-3 py-1.5 text-sm bg-gray-100 text-gray-700 rounded-full hover:bg-gray-200 transition-colors"
                >
                  {question}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-lg p-4 ${
                message.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-900'
              }`}
            >
              {/* Message Content */}
              <div className="whitespace-pre-wrap">{message.content}</div>

              {/* Citations */}
              {message.citations && message.citations.length > 0 && (
                <div className="mt-3 pt-3 border-t border-gray-200">
                  <p className="text-xs font-medium mb-2 opacity-70">References:</p>
                  <div className="flex flex-wrap gap-1">
                    {message.citations.map((citation, i) => (
                      <button
                        key={i}
                        onClick={() => onCitationClick?.(citation)}
                        className="px-2 py-0.5 text-xs bg-white/20 hover:bg-white/30 rounded transition-colors"
                      >
                        [{i + 1}]
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Actions */}
              {message.role === 'assistant' && (
                <div className="mt-2 flex justify-end">
                  <button
                    onClick={() => handleCopy(message.id, message.content)}
                    className="p-1 hover:bg-gray-200 rounded transition-colors"
                    title="Copy to clipboard"
                  >
                    {copiedId === message.id ? (
                      <Check className="w-4 h-4 text-green-600" />
                    ) : (
                      <Copy className="w-4 h-4 text-gray-500" />
                    )}
                  </button>
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Loading indicator */}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-lg p-4 flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin text-gray-500" />
              <span className="text-gray-500">Thinking...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t p-4">
        <div className="flex gap-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about your research..."
            rows={1}
            className="flex-1 px-4 py-2 border rounded-lg resize-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            style={{ minHeight: '42px', maxHeight: '120px' }}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
        <p className="text-xs text-gray-500 mt-2 text-center">
          Press Enter to send, Shift+Enter for new line
        </p>
      </div>
    </div>
  );
}
