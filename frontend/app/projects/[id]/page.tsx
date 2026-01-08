'use client';

import { useState, useCallback, useMemo, useRef, useEffect } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  Network,
  MessageSquare,
  Compass,
  Send,
  X,
  ChevronRight,
  Loader2,
  Menu,
  ChevronLeft,
} from 'lucide-react';
import { api } from '@/lib/api';
import { KnowledgeGraph } from '@/components/graph/KnowledgeGraph';
import { NodeDetails } from '@/components/graph/NodeDetails';
import { FilterPanel } from '@/components/graph/FilterPanel';
import { SearchBar } from '@/components/graph/SearchBar';
import { useGraphStore } from '@/hooks/useGraphStore';
import { Header } from '@/components/layout';
import {
  ThemeToggle,
  ErrorDisplay,
  ErrorBoundary,
  ChatMessageSkeleton,
  GraphSkeleton,
} from '@/components/ui';
import type { GraphEntity, EntityType, SearchResult, Citation } from '@/types';

type ViewMode = 'chat' | 'explore' | 'split';

const ALL_ENTITY_TYPES: EntityType[] = ['Paper', 'Author', 'Concept', 'Method', 'Finding'];

export default function ProjectDetailPage() {
  const params = useParams();
  const projectId = params.id as string;

  const [viewMode, setViewMode] = useState<ViewMode>('split');
  const [mobileView, setMobileView] = useState<'chat' | 'graph'>('chat');
  const [chatInput, setChatInput] = useState('');
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Array<{
    role: 'user' | 'assistant';
    content: string;
    citations?: Citation[];
    isNodeExplanation?: boolean;
    nodeId?: string;
  }>>([]);

  // Auto-scroll refs
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);

  const {
    graphData,
    highlightedNodes,
    highlightedEdges,
    selectedNode,
    filters,
    setHighlightedNodes,
    setHighlightedEdges,
    setSelectedNode,
    setFilters,
    resetFilters,
    clearHighlights,
    expandNode,
  } = useGraphStore();

  // Fetch project details
  const { data: project, isLoading: projectLoading, error: projectError, refetch } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => api.getProject(projectId),
  });

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  // Chat mutation
  const chatMutation = useMutation({
    mutationFn: (message: string) =>
      api.sendChatMessage(projectId, message, conversationId || undefined),
    onSuccess: (data) => {
      setConversationId(data.conversation_id);
      setMessages((prev) => [
        ...prev,
        { role: 'user', content: chatInput },
        {
          role: 'assistant',
          content: data.answer,
          citations: data.citations,
        },
      ]);
      setChatInput('');

      if (data.highlighted_nodes?.length > 0) {
        setHighlightedNodes(data.highlighted_nodes);
      }
      if (data.highlighted_edges?.length > 0) {
        setHighlightedEdges(data.highlighted_edges);
      }
    },
  });

  // Calculate node counts by type
  const nodeCountsByType = useMemo(() => {
    if (!graphData) return {} as Record<EntityType, number>;

    const counts: Record<EntityType, number> = {
      Paper: 0,
      Author: 0,
      Concept: 0,
      Method: 0,
      Finding: 0,
    };

    for (const node of graphData.nodes) {
      if (counts[node.entity_type] !== undefined) {
        counts[node.entity_type]++;
      }
    }

    return counts;
  }, [graphData]);

  // Handle node click in graph
  const handleNodeClick = useCallback(
    (nodeId: string, nodeData: GraphEntity) => {
      setSelectedNode(nodeData);
      setHighlightedNodes([nodeId]);
    },
    [setSelectedNode, setHighlightedNodes]
  );

  // Handle search
  const handleSearch = useCallback(
    async (query: string): Promise<SearchResult[]> => {
      try {
        return await api.searchNodes(query, filters.entityTypes);
      } catch (error) {
        console.error('Search failed:', error);
        return [];
      }
    },
    [filters.entityTypes]
  );

  // Handle search result selection
  const handleSelectSearchResult = useCallback(
    (result: SearchResult) => {
      setHighlightedNodes([result.id]);
      const entity = graphData?.nodes.find((n) => n.id === result.id);
      if (entity) {
        setSelectedNode(entity);
      }
    },
    [graphData, setHighlightedNodes, setSelectedNode]
  );

  // Handle asking about a node in chat
  const handleAskAboutNode = useCallback(
    (nodeId: string, nodeName: string) => {
      const question = `Tell me more about "${nodeName}" and its connections in the literature.`;
      setChatInput(question);
      setViewMode('split');
      setMobileView('chat');
    },
    []
  );

  // Handle showing node connections
  const handleShowConnections = useCallback(
    (nodeId: string) => {
      expandNode(nodeId);
      setHighlightedNodes([nodeId]);
    },
    [expandNode, setHighlightedNodes]
  );

  // Handle chat submit
  const handleChatSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim() || chatMutation.isPending) return;
    clearHighlights();
    chatMutation.mutate(chatInput);
  };

  // Handle citation click
  const handleCitationClick = (citation: Citation) => {
    setHighlightedNodes([citation.paper_id]);
    const entity = graphData?.nodes.find((n) => n.id === citation.paper_id);
    if (entity) {
      setSelectedNode(entity);
    }
    setMobileView('graph');
  };

  if (projectLoading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-blue-600 animate-spin mx-auto" />
          <p className="mt-4 text-gray-600 dark:text-gray-300">프로젝트 로딩 중...</p>
        </div>
      </div>
    );
  }

  if (projectError) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center p-4">
        <ErrorDisplay
          error={projectError as Error}
          title="프로젝트를 불러올 수 없습니다"
          onRetry={() => refetch()}
        />
      </div>
    );
  }

  return (
    <ErrorBoundary>
      <div className="h-screen flex flex-col bg-gray-50 dark:bg-gray-900">
        {/* Custom Header for Project Detail */}
        <header className="bg-white dark:bg-gray-800 shadow-sm border-b dark:border-gray-700 flex-shrink-0">
          <div className="px-3 sm:px-4 py-3 flex items-center justify-between gap-2">
            {/* Left: Back + Project Info */}
            <div className="flex items-center gap-2 sm:gap-4 min-w-0 flex-1">
              <Link
                href="/projects"
                className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors touch-target"
                aria-label="프로젝트 목록으로 돌아가기"
              >
                <ChevronLeft className="w-5 h-5" />
              </Link>
              <div className="flex items-center gap-2 sm:gap-3 min-w-0">
                <Network className="w-5 sm:w-6 h-5 sm:h-6 text-blue-600 flex-shrink-0" />
                <div className="min-w-0">
                  <h1 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white truncate">
                    {project?.name || 'Project'}
                  </h1>
                  {project?.research_question && (
                    <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400 truncate hidden sm:block">
                      {project.research_question}
                    </p>
                  )}
                </div>
              </div>
            </div>

            {/* Center: Search Bar (hidden on mobile) */}
            <div className="hidden lg:block flex-1 max-w-md mx-4">
              <SearchBar
                onSearch={handleSearch}
                onSelectResult={handleSelectSearchResult}
                placeholder="Search papers, concepts..."
              />
            </div>

            {/* Right: View Mode Toggle + Theme */}
            <div className="flex items-center gap-2">
              {/* Desktop View Mode */}
              <div className="hidden md:flex items-center gap-1 bg-gray-100 dark:bg-gray-700 p-1 rounded-lg">
                <button
                  onClick={() => setViewMode('chat')}
                  className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-sm transition-colors ${
                    viewMode === 'chat'
                      ? 'bg-white dark:bg-gray-600 shadow-sm text-blue-600 dark:text-blue-400'
                      : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white'
                  }`}
                  aria-pressed={viewMode === 'chat'}
                >
                  <MessageSquare className="w-4 h-4" />
                  <span className="hidden lg:inline">Chat</span>
                </button>
                <button
                  onClick={() => setViewMode('split')}
                  className={`px-2.5 py-1.5 rounded-md text-sm transition-colors ${
                    viewMode === 'split'
                      ? 'bg-white dark:bg-gray-600 shadow-sm text-blue-600 dark:text-blue-400'
                      : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white'
                  }`}
                  aria-pressed={viewMode === 'split'}
                >
                  Split
                </button>
                <button
                  onClick={() => setViewMode('explore')}
                  className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-sm transition-colors ${
                    viewMode === 'explore'
                      ? 'bg-white dark:bg-gray-600 shadow-sm text-blue-600 dark:text-blue-400'
                      : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white'
                  }`}
                  aria-pressed={viewMode === 'explore'}
                >
                  <Compass className="w-4 h-4" />
                  <span className="hidden lg:inline">Explore</span>
                </button>
              </div>

              {/* Mobile View Toggle */}
              <div className="flex md:hidden items-center gap-1 bg-gray-100 dark:bg-gray-700 p-1 rounded-lg">
                <button
                  onClick={() => setMobileView('chat')}
                  className={`p-2 rounded-md transition-colors ${
                    mobileView === 'chat'
                      ? 'bg-white dark:bg-gray-600 shadow-sm text-blue-600'
                      : 'text-gray-600 dark:text-gray-300'
                  }`}
                  aria-pressed={mobileView === 'chat'}
                  aria-label="채팅 보기"
                >
                  <MessageSquare className="w-5 h-5" />
                </button>
                <button
                  onClick={() => setMobileView('graph')}
                  className={`p-2 rounded-md transition-colors ${
                    mobileView === 'graph'
                      ? 'bg-white dark:bg-gray-600 shadow-sm text-blue-600'
                      : 'text-gray-600 dark:text-gray-300'
                  }`}
                  aria-pressed={mobileView === 'graph'}
                  aria-label="그래프 보기"
                >
                  <Network className="w-5 h-5" />
                </button>
              </div>

              <ThemeToggle />
            </div>
          </div>

          {/* Mobile Search Bar */}
          <div className="lg:hidden px-3 pb-3">
            <SearchBar
              onSearch={handleSearch}
              onSelectResult={handleSelectSearchResult}
              placeholder="Search..."
            />
          </div>
        </header>

        {/* Main Content */}
        <div className="flex-1 flex overflow-hidden">
          {/* Chat Panel */}
          <div
            className={`flex flex-col bg-white dark:bg-gray-800 border-r dark:border-gray-700 transition-all ${
              // Desktop visibility
              viewMode === 'chat' ? 'w-full' :
              viewMode === 'split' ? 'w-1/2' :
              'hidden'
            } ${
              // Mobile visibility override
              'max-md:hidden'
            } ${
              mobileView === 'chat' ? 'max-md:flex max-md:w-full' : ''
            }`}
          >
            {/* Messages */}
            <div
              ref={chatContainerRef}
              className="flex-1 overflow-y-auto p-3 sm:p-4 space-y-3 sm:space-y-4"
            >
              {messages.length === 0 && (
                <div className="text-center py-8 sm:py-12 text-gray-500 dark:text-gray-400">
                  <MessageSquare className="w-10 sm:w-12 h-10 sm:h-12 mx-auto mb-4 text-gray-300 dark:text-gray-600" />
                  <p className="text-sm sm:text-base">연구 문헌에 대해 질문해보세요</p>
                  <p className="text-xs sm:text-sm mt-2">
                    예: "주요 발견은 무엇인가요?" 또는 "방법론을 비교해주세요"
                  </p>
                  <div className="mt-4 sm:mt-6 flex flex-wrap justify-center gap-2">
                    {[
                      '핵심 발견 요약',
                      '방법론 비교',
                      '연구 갭 분석',
                    ].map((suggestion) => (
                      <button
                        key={suggestion}
                        onClick={() => setChatInput(suggestion)}
                        className="px-3 py-1.5 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-full text-xs sm:text-sm text-gray-600 dark:text-gray-300 transition-colors touch-target"
                      >
                        {suggestion}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {messages.map((msg, i) => (
                <div
                  key={i}
                  className={`p-3 sm:p-4 rounded-lg ${
                    msg.role === 'user'
                      ? 'bg-blue-50 dark:bg-blue-900/20 ml-4 sm:ml-12 border border-blue-100 dark:border-blue-800'
                      : 'bg-gray-50 dark:bg-gray-700 mr-4 sm:mr-12 border border-gray-100 dark:border-gray-600'
                  }`}
                >
                  <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">
                    {msg.role === 'user' ? 'You' : 'AI Assistant'}
                  </p>
                  <p className="text-sm sm:text-base text-gray-800 dark:text-gray-200 whitespace-pre-wrap">
                    {msg.content}
                  </p>

                  {/* Citations */}
                  {msg.citations && msg.citations.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-600">
                      <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">
                        References:
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {msg.citations.map((citation) => (
                          <button
                            key={citation.id}
                            onClick={() => handleCitationClick(citation)}
                            className="inline-flex items-center gap-1.5 px-2 py-1 bg-white dark:bg-gray-600 border dark:border-gray-500 rounded text-xs text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-500 hover:border-blue-300 dark:hover:border-blue-400 transition-colors touch-target"
                          >
                            <span className="truncate max-w-[120px] sm:max-w-[150px]">
                              {citation.title}
                            </span>
                            {citation.year && (
                              <span className="text-gray-400">({citation.year})</span>
                            )}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}

              {chatMutation.isPending && (
                <ChatMessageSkeleton isUser={false} />
              )}

              {/* Auto-scroll anchor */}
              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <form
              onSubmit={handleChatSubmit}
              className="p-3 sm:p-4 border-t dark:border-gray-700 bg-gray-50 dark:bg-gray-800 safe-area-inset-bottom"
            >
              <div className="flex gap-2">
                <input
                  type="text"
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  placeholder="연구에 대해 질문하세요..."
                  className="flex-1 px-3 sm:px-4 py-2.5 border dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 text-sm sm:text-base"
                  aria-label="질문 입력"
                />
                <button
                  type="submit"
                  disabled={!chatInput.trim() || chatMutation.isPending}
                  className="px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors touch-target"
                  aria-label="질문 보내기"
                >
                  <Send className="w-5 h-5" />
                </button>
              </div>
            </form>
          </div>

          {/* Graph Panel */}
          <div
            className={`relative transition-all ${
              // Desktop visibility
              viewMode === 'explore' ? 'w-full' :
              viewMode === 'split' ? 'w-1/2' :
              'hidden'
            } ${
              // Mobile visibility override
              'max-md:hidden'
            } ${
              mobileView === 'graph' ? 'max-md:flex max-md:w-full' : ''
            }`}
          >
            <KnowledgeGraph
              projectId={projectId}
              onNodeClick={handleNodeClick}
              highlightedNodes={highlightedNodes}
              highlightedEdges={highlightedEdges}
            />

            {/* Filter Panel */}
            <FilterPanel
              entityTypes={ALL_ENTITY_TYPES}
              selectedTypes={filters.entityTypes}
              onTypeChange={(types) => setFilters({ entityTypes: types })}
              onReset={resetFilters}
              nodeCountsByType={nodeCountsByType}
            />

            {/* Node Details Panel */}
            {selectedNode && (
              <NodeDetails
                node={selectedNode}
                projectId={projectId}
                onClose={() => setSelectedNode(null)}
                onAskAbout={handleAskAboutNode}
                onShowConnections={handleShowConnections}
              />
            )}

            {/* Clear highlights button */}
            {(highlightedNodes.length > 0 || highlightedEdges.length > 0) && !selectedNode && (
              <button
                onClick={clearHighlights}
                className="absolute bottom-4 right-4 flex items-center gap-2 px-3 py-2 bg-white dark:bg-gray-800 rounded-lg shadow-md text-sm text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white z-10 touch-target"
              >
                <X className="w-4 h-4" />
                <span className="hidden sm:inline">Clear highlights</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </ErrorBoundary>
  );
}
