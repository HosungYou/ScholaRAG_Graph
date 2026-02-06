'use client';

import { useState, useRef, useEffect, useMemo } from 'react';
import { Send, Loader2, Sparkles, Copy, Check, ArrowRight } from 'lucide-react';
import clsx from 'clsx';

/* ============================================================
   ScholaRAG Graph - Research Dialogue Chat Interface
   VS Design Diverge: Direction B (T-Score 0.4)

   Design Principles:
   - No bubble backgrounds - use typography and spacing
   - Left-aligned messages for both roles (conversational)
   - Accent bar for assistant messages (2px teal)
   - Inline superscript citations
   - Bottom-border-only input field
   ============================================================ */

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
  graphStats?: {
    totalNodes?: number;
    totalEdges?: number;
    topConcepts?: string[];
    clusterCount?: number;
    gapCount?: number;
  };
}

export function ChatInterface({
  projectId,
  onSendMessage,
  onCitationClick,
  initialMessages = [],
  graphStats,
}: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [hoveredCitation, setHoveredCitation] = useState<number | null>(null);
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

  // Format timestamp
  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });
  };

  // v0.11.0: Dynamic suggested questions based on graph data
  const suggestedQuestions = useMemo(() => {
    const questions: string[] = [];

    // Base questions that always apply
    questions.push('What are the main research themes in this collection?');
    questions.push('Which methodologies are most commonly used?');

    // Graph-aware questions
    if (graphStats?.topConcepts && graphStats.topConcepts.length >= 2) {
      questions.push(
        `How are "${graphStats.topConcepts[0]}" and "${graphStats.topConcepts[1]}" related?`
      );
    } else {
      questions.push('What are the key findings across all papers?');
    }

    if (graphStats?.gapCount && graphStats.gapCount > 0) {
      questions.push(`What research gaps exist between the ${graphStats.clusterCount || ''} concept clusters?`);
    } else {
      questions.push('Identify potential research gaps in this literature');
    }

    return questions;
  }, [graphStats]);

  return (
    <div className="chat-container flex flex-col h-full bg-paper dark:bg-ink">
      {/* Messages Area */}
      <div className="chat-messages flex-1 overflow-y-auto px-6 py-8 space-y-8">
        {/* Empty State */}
        {messages.length === 0 && (
          <div className="text-center py-16">
            <div
              className="w-16 h-16 mx-auto mb-6 flex items-center justify-center"
              style={{
                backgroundColor: 'rgb(var(--color-accent-teal) / 0.1)',
                borderRadius: '4px',
              }}
            >
              <Sparkles className="w-8 h-8 text-accent-teal" />
            </div>

            <h3 className="font-display text-2xl text-ink dark:text-paper mb-3">
              Explore Your Research
            </h3>
            <p className="text-muted max-w-md mx-auto mb-8 leading-relaxed">
              Ask questions about your knowledge graph. I can help find connections,
              identify trends, and reveal research gaps.
            </p>

            {/* Suggestion Tags */}
            <div className="suggestion-tags flex flex-wrap justify-center gap-2">
              {suggestedQuestions.map((question, i) => (
                <button
                  key={i}
                  onClick={() => {
                    setInput(question);
                    inputRef.current?.focus();
                  }}
                  className="suggestion-tag group flex items-center gap-2"
                >
                  <span>{question}</span>
                  <ArrowRight className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Messages */}
        {messages.map((message) => (
          <div
            key={message.id}
            className={clsx(
              'chat-message animate-fade-in',
              message.role === 'user' ? 'chat-message--user' : 'chat-message--assistant'
            )}
          >
            {/* Message Content */}
            <div className="chat-message__content">
              {/* Parse content to inject citation superscripts */}
              {message.content}
            </div>

            {/* Inline Citations */}
            {message.citations && message.citations.length > 0 && (
              <div className="mt-4 flex flex-wrap gap-1.5">
                {message.citations.map((citation, i) => (
                  <span
                    key={i}
                    className="citation-ref relative"
                    onClick={() => onCitationClick?.(citation)}
                    onMouseEnter={() => setHoveredCitation(i)}
                    onMouseLeave={() => setHoveredCitation(null)}
                  >
                    {i + 1}

                    {/* Citation Popover */}
                    {hoveredCitation === i && (
                      <div className="citation-popover absolute bottom-full left-1/2 -translate-x-1/2 mb-2 whitespace-nowrap">
                        <span className="text-xs font-mono truncate max-w-[200px] block">
                          {citation}
                        </span>
                      </div>
                    )}
                  </span>
                ))}
              </div>
            )}

            {/* Timestamp & Actions */}
            <div className="flex items-center justify-between mt-3">
              <span className="chat-message__time">
                {formatTime(message.timestamp)}
              </span>

              {message.role === 'assistant' && (
                <button
                  onClick={() => handleCopy(message.id, message.content)}
                  className="p-1.5 text-muted hover:text-ink dark:hover:text-paper transition-colors"
                  title="Copy to clipboard"
                >
                  {copiedId === message.id ? (
                    <Check className="w-4 h-4 text-accent-teal" />
                  ) : (
                    <Copy className="w-4 h-4" />
                  )}
                </button>
              )}
            </div>
          </div>
        ))}

        {/* Loading indicator */}
        {isLoading && (
          <div className="chat-message chat-message--assistant animate-fade-in">
            <div className="flex items-center gap-3 text-muted">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span className="font-mono text-sm">Analyzing...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="chat-input-area">
        <div className="flex items-end gap-4">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about your research..."
            rows={1}
            className="chat-input flex-1 font-body"
            style={{
              minHeight: '44px',
              maxHeight: '120px',
            }}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            className={clsx(
              'btn btn--primary flex-shrink-0',
              'disabled:opacity-40 disabled:cursor-not-allowed'
            )}
            style={{ marginBottom: '3px' }}
          >
            <Send className="w-4 h-4" />
          </button>
        </div>

        <p className="text-xs text-muted mt-3 text-center font-mono">
          Enter to send · Shift+Enter for new line
        </p>
      </div>
    </div>
  );
}
