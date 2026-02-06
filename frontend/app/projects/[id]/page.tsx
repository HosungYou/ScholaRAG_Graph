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
  ChevronLeft,
  Loader2,
  Hexagon,
  PanelLeftClose,
  PanelLeft,
} from 'lucide-react';
import { api } from '@/lib/api';
import { KnowledgeGraph3D } from '@/components/graph/KnowledgeGraph3D';
import { NodeDetails } from '@/components/graph/NodeDetails';
import { FilterPanel } from '@/components/graph/FilterPanel';
import { SearchBar } from '@/components/graph/SearchBar';
import { useGraphStore } from '@/hooks/useGraphStore';
import {
  ThemeToggle,
  ErrorDisplay,
  ErrorBoundary,
  ChatMessageSkeleton,
  ResizeHandle,
} from '@/components/ui';
import type { GraphEntity, EntityType, SearchResult, Citation } from '@/types';

/* ============================================================
   ScholaRAG Graph - Project Detail Page
   VS Design Diverge: Direction B (T-Score 0.4) "Editorial Research"

   Design Principles:
   - Line-based view mode toggles
   - Left accent bar for chat messages
   - Monospace status indicators
   - Minimal border radius
   - No blue colors (use accent-teal)
   ============================================================ */

type ViewMode = 'chat' | 'explore' | 'split';

const ALL_ENTITY_TYPES: EntityType[] = ['Paper', 'Author', 'Concept', 'Method', 'Finding'];

export default function ProjectDetailPage() {
  const params = useParams();
  const projectId = params.id as string;

  const [viewMode, setViewMode] = useState<ViewMode>('split');
  const [mobileView, setMobileView] = useState<'chat' | 'graph'>('chat');
  const [chatInput, setChatInput] = useState('');
  const [conversationId, setConversationId] = useState<string | null>(null);

  // Chat panel resize and collapse state
  const [chatPanelWidth, setChatPanelWidth] = useState(480);
  const [isChatCollapsed, setIsChatCollapsed] = useState(false);
  const mainContainerRef = useRef<HTMLDivElement>(null);

  // Load saved panel width from localStorage
  useEffect(() => {
    const savedWidth = localStorage.getItem('scholarag-chat-panel-width');
    const savedCollapsed = localStorage.getItem('scholarag-chat-panel-collapsed');
    if (savedWidth) {
      setChatPanelWidth(parseInt(savedWidth, 10));
    }
    if (savedCollapsed) {
      setIsChatCollapsed(savedCollapsed === 'true');
    }
  }, []);

  // Save panel width to localStorage
  const handlePanelResize = useCallback((width: number) => {
    setChatPanelWidth(width);
    localStorage.setItem('scholarag-chat-panel-width', String(width));
  }, []);

  // Toggle chat panel collapse
  const toggleChatPanel = useCallback(() => {
    setIsChatCollapsed(prev => {
      const newValue = !prev;
      localStorage.setItem('scholarag-chat-panel-collapsed', String(newValue));
      return newValue;
    });
  }, []);

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
    pinnedNodes,
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
      api.sendChatMessage(
        projectId,
        message,
        conversationId || undefined,
        {
          selectedNodeIds: selectedNode ? [selectedNode.id] : [],
          pinnedNodeIds: pinnedNodes,
        }
      ),
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
      Problem: 0,
      Dataset: 0,
      Metric: 0,
      Innovation: 0,
      Limitation: 0,
    };

    for (const node of graphData.nodes) {
      if (counts[node.entity_type] !== undefined) {
        counts[node.entity_type]++;
      }
    }

    return counts;
  }, [graphData]);

  // Dynamic entity types: only show types that have at least 1 node in the graph
  // This prevents showing Paper/Author (or other types) when they don't exist
  // Per ADR-001: Paper/Author are metadata-only, not visualized in concept-centric mode
  const actualEntityTypes = useMemo(() => {
    // Define the preferred order for entity types
    const orderedTypes: EntityType[] = ['Concept', 'Method', 'Finding', 'Problem', 'Dataset', 'Metric', 'Innovation', 'Limitation', 'Paper', 'Author'];
    // Filter to only types that have at least 1 node
    return orderedTypes.filter(type => (nodeCountsByType[type] || 0) > 0);
  }, [nodeCountsByType]);

  // UI-003 FIX: Sync entity types ONLY on initial graph load
  // Track whether initial sync has been done to allow user freedom after
  const [hasInitializedFilters, setHasInitializedFilters] = useState(false);

  useEffect(() => {
    // Only run on initial graph load, not on every filter change
    if (actualEntityTypes.length > 0 && !hasInitializedFilters) {
      // Only select types that actually exist in the graph
      const validSelectedTypes = filters.entityTypes.filter(
        type => actualEntityTypes.includes(type)
      );
      // If no valid types match, select all available types
      if (validSelectedTypes.length === 0) {
        setFilters({ entityTypes: [...actualEntityTypes] });
      } else if (validSelectedTypes.length !== filters.entityTypes.length) {
        // Update to only include valid types
        setFilters({ entityTypes: validSelectedTypes });
      }
      // Mark as initialized - user can now freely toggle without auto-reset
      setHasInitializedFilters(true);
    }
  }, [actualEntityTypes, hasInitializedFilters, filters.entityTypes, setFilters]);

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
    const nodeId = citation.paper_id || citation.id;
    setHighlightedNodes([nodeId]);
    const entity = graphData?.nodes.find((n) => n.id === nodeId);
    if (entity) {
      setSelectedNode(entity);
    }
    setMobileView('graph');
  };

  if (projectLoading) {
    return (
      <div className="min-h-screen bg-paper dark:bg-ink flex items-center justify-center">
        <div className="text-center">
          <div className="relative inline-block mb-6">
            <Hexagon className="w-16 h-16 text-accent-teal/30 animate-pulse-slow" strokeWidth={1} />
            <Loader2 className="w-6 h-6 text-accent-teal absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 animate-spin" />
          </div>
          <p className="font-mono text-sm text-muted">Loading project...</p>
        </div>
      </div>
    );
  }

  if (projectError) {
    return (
      <div className="min-h-screen bg-paper dark:bg-ink flex items-center justify-center p-4">
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
      <div className="h-screen flex flex-col bg-paper dark:bg-ink">
        {/* Custom Header - Editorial Research Style */}
        <header className="bg-paper dark:bg-ink border-b border-ink/10 dark:border-paper/10 flex-shrink-0">
          <div className="px-4 py-3 flex items-center justify-between gap-4">
            {/* Left: Back + Project Info */}
            <div className="flex items-center gap-4 min-w-0 flex-1">
              <Link
                href="/projects"
                className="p-2 text-muted hover:text-ink dark:hover:text-paper transition-colors"
                aria-label="프로젝트 목록으로 돌아가기"
              >
                <ChevronLeft className="w-5 h-5" />
              </Link>

              <div className="flex items-center gap-3 min-w-0">
                <Hexagon className="w-6 h-6 text-accent-teal flex-shrink-0" strokeWidth={1.5} />
                <div className="min-w-0">
                  <h1 className="font-display text-lg text-ink dark:text-paper truncate">
                    {project?.name || 'Project'}
                  </h1>
                  {project?.research_question && (
                    <p className="text-xs text-muted truncate hidden sm:block">
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
            <div className="flex items-center gap-3">
              {/* Desktop View Mode - Line-based */}
              <div className="hidden md:flex items-center border border-ink/10 dark:border-paper/10">
                <button
                  onClick={() => setViewMode('chat')}
                  className={`flex items-center gap-2 px-3 py-2 text-sm transition-colors border-r border-ink/10 dark:border-paper/10 ${
                    viewMode === 'chat'
                      ? 'bg-accent-teal/10 text-accent-teal'
                      : 'text-muted hover:text-ink dark:hover:text-paper hover:bg-surface/5'
                  }`}
                  aria-pressed={viewMode === 'chat'}
                >
                  <MessageSquare className="w-4 h-4" />
                  <span className="hidden lg:inline font-mono text-xs uppercase tracking-wider">Chat</span>
                </button>
                <button
                  onClick={() => setViewMode('split')}
                  className={`px-3 py-2 text-sm transition-colors border-r border-ink/10 dark:border-paper/10 ${
                    viewMode === 'split'
                      ? 'bg-accent-teal/10 text-accent-teal'
                      : 'text-muted hover:text-ink dark:hover:text-paper hover:bg-surface/5'
                  }`}
                  aria-pressed={viewMode === 'split'}
                >
                  <span className="font-mono text-xs uppercase tracking-wider">Split</span>
                </button>
                <button
                  onClick={() => setViewMode('explore')}
                  className={`flex items-center gap-2 px-3 py-2 text-sm transition-colors ${
                    viewMode === 'explore'
                      ? 'bg-accent-teal/10 text-accent-teal'
                      : 'text-muted hover:text-ink dark:hover:text-paper hover:bg-surface/5'
                  }`}
                  aria-pressed={viewMode === 'explore'}
                >
                  <Compass className="w-4 h-4" />
                  <span className="hidden lg:inline font-mono text-xs uppercase tracking-wider">Explore</span>
                </button>
              </div>

              {/* Mobile View Toggle */}
              <div className="flex md:hidden items-center border border-ink/10 dark:border-paper/10">
                <button
                  onClick={() => setMobileView('chat')}
                  className={`p-2 transition-colors border-r border-ink/10 dark:border-paper/10 ${
                    mobileView === 'chat'
                      ? 'bg-accent-teal/10 text-accent-teal'
                      : 'text-muted'
                  }`}
                  aria-pressed={mobileView === 'chat'}
                  aria-label="채팅 보기"
                >
                  <MessageSquare className="w-5 h-5" />
                </button>
                <button
                  onClick={() => setMobileView('graph')}
                  className={`p-2 transition-colors ${
                    mobileView === 'graph'
                      ? 'bg-accent-teal/10 text-accent-teal'
                      : 'text-muted'
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
          <div className="lg:hidden px-4 pb-3">
            <SearchBar
              onSearch={handleSearch}
              onSelectResult={handleSelectSearchResult}
              placeholder="Search..."
            />
          </div>
        </header>

        {/* Main Content */}
        <div ref={mainContainerRef} className="flex-1 flex overflow-hidden">
          {/* Chat Panel Toggle Button (when collapsed) */}
          {isChatCollapsed && viewMode === 'split' && (
            <button
              onClick={toggleChatPanel}
              className="flex-shrink-0 w-10 flex flex-col items-center justify-center gap-2 bg-paper dark:bg-ink border-r border-ink/10 dark:border-paper/10 hover:bg-accent-teal/10 transition-colors"
              aria-label="Open chat panel"
            >
              <PanelLeft className="w-5 h-5 text-muted" />
              <span className="text-[10px] font-mono text-muted uppercase tracking-wider [writing-mode:vertical-lr] rotate-180">
                Chat
              </span>
            </button>
          )}

          {/* Chat Panel - Editorial Research Style */}
          <div
            style={viewMode === 'split' && !isChatCollapsed ? { width: `${chatPanelWidth}px` } : undefined}
            className={`flex flex-col bg-paper dark:bg-ink border-r border-ink/10 dark:border-paper/10 transition-all flex-shrink-0 ${
              // Desktop visibility
              viewMode === 'chat' ? 'w-full' :
              viewMode === 'split' ? (isChatCollapsed ? 'hidden' : '') :
              'hidden'
            } ${
              // Mobile visibility override
              'max-md:hidden'
            } ${
              mobileView === 'chat' ? 'max-md:flex max-md:w-full' : ''
            }`}
          >
            {/* Panel Header with Collapse Button */}
            {viewMode === 'split' && (
              <div className="flex items-center justify-between px-4 py-2 border-b border-ink/10 dark:border-paper/10 flex-shrink-0">
                <span className="font-mono text-xs uppercase tracking-wider text-muted">
                  Research Chat
                </span>
                <button
                  onClick={toggleChatPanel}
                  className="p-1.5 text-muted hover:text-accent-teal hover:bg-accent-teal/10 transition-colors rounded"
                  aria-label="Collapse chat panel"
                >
                  <PanelLeftClose className="w-4 h-4" />
                </button>
              </div>
            )}
            {/* Messages */}
            <div
              ref={chatContainerRef}
              className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6"
            >
              {messages.length === 0 && (
                <div className="text-center py-12 md:py-20">
                  <div className="relative inline-block mb-6">
                    <Hexagon className="w-16 h-16 text-accent-teal/20" strokeWidth={1} />
                    <MessageSquare className="w-6 h-6 text-accent-teal absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
                  </div>
                  <h3 className="font-display text-xl text-ink dark:text-paper mb-2">
                    Research Dialogue
                  </h3>
                  <p className="text-muted text-sm max-w-md mx-auto">
                    Ask questions about your literature collection. The AI will reference specific papers and concepts.
                  </p>

                  {/* Suggestion Tags */}
                  <div className="mt-8 flex flex-wrap justify-center gap-2">
                    {[
                      'Summarize key findings',
                      'Compare methodologies',
                      'Identify research gaps',
                    ].map((suggestion) => (
                      <button
                        key={suggestion}
                        onClick={() => setChatInput(suggestion)}
                        className="px-3 py-1.5 border border-ink/10 dark:border-paper/10 text-xs text-muted hover:text-accent-teal hover:border-accent-teal transition-colors"
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
                  className={`relative pl-4 ${
                    msg.role === 'user' ? 'ml-8 md:ml-16' : 'mr-4 md:mr-8'
                  }`}
                >
                  {/* Left Accent Bar */}
                  <div
                    className={`absolute left-0 top-0 bottom-0 w-0.5 ${
                      msg.role === 'user' ? 'bg-accent-amber' : 'bg-accent-teal'
                    }`}
                  />

                  {/* Message Header */}
                  <div className="flex items-center gap-2 mb-2">
                    <span className="font-mono text-xs uppercase tracking-wider text-muted">
                      {msg.role === 'user' ? 'You' : 'AI'}
                    </span>
                    <span className="text-ink/10 dark:text-paper/10">·</span>
                    <span className="font-mono text-xs text-muted">
                      {String(i + 1).padStart(2, '0')}
                    </span>
                  </div>

                  {/* Message Content */}
                  <p className="text-sm md:text-base text-ink dark:text-paper leading-relaxed whitespace-pre-wrap">
                    {msg.content}
                  </p>

                  {/* Citations */}
                  {msg.citations && msg.citations.length > 0 && (
                    <div className="mt-4 pt-4 border-t border-ink/10 dark:border-paper/10">
                      <span className="font-mono text-xs uppercase tracking-wider text-muted">
                        References
                      </span>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {msg.citations.map((citation, citIndex) => (
                          <button
                            key={citation.id}
                            onClick={() => handleCitationClick(citation)}
                            className="group inline-flex items-center gap-2 px-2 py-1 border border-ink/10 dark:border-paper/10 hover:border-accent-teal transition-colors"
                          >
                            <span className="font-mono text-xs text-accent-teal">
                              [{citIndex + 1}]
                            </span>
                            <span className="text-xs text-muted group-hover:text-ink dark:group-hover:text-paper truncate max-w-[150px]">
                              {citation.title}
                            </span>
                            {citation.year && (
                              <span className="font-mono text-xs text-muted">
                                {citation.year}
                              </span>
                            )}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}

              {chatMutation.isPending && (
                <div className="relative pl-4 mr-4 md:mr-8">
                  <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-accent-teal animate-pulse" />
                  <div className="flex items-center gap-2 mb-2">
                    <span className="font-mono text-xs uppercase tracking-wider text-muted">AI</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Loader2 className="w-4 h-4 text-accent-teal animate-spin" />
                    <span className="text-sm text-muted">Analyzing literature...</span>
                  </div>
                </div>
              )}

              {/* Auto-scroll anchor */}
              <div ref={messagesEndRef} />
            </div>

            {/* Input - Line-based Style */}
            <form
              onSubmit={handleChatSubmit}
              className="p-4 border-t border-ink/10 dark:border-paper/10"
            >
              <div className="flex gap-3">
                <input
                  type="text"
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  placeholder="Ask about your research..."
                  className="flex-1 px-4 py-3 bg-transparent border-b-2 border-ink/20 dark:border-paper/20 focus:border-accent-teal focus:outline-none text-ink dark:text-paper placeholder-muted text-sm transition-colors"
                  aria-label="질문 입력"
                />
                <button
                  type="submit"
                  disabled={!chatInput.trim() || chatMutation.isPending}
                  className="px-4 py-3 bg-accent-teal text-ink hover:bg-accent-teal/90 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  aria-label="질문 보내기"
                >
                  <Send className="w-5 h-5" />
                </button>
              </div>
            </form>
          </div>

          {/* Resize Handle (only in split mode, when chat is visible) */}
          {viewMode === 'split' && !isChatCollapsed && (
            <ResizeHandle
              onResize={handlePanelResize}
              currentWidth={chatPanelWidth}
              minWidth={320}
              maxWidth={800}
              containerRef={mainContainerRef}
            />
          )}

          {/* Graph Panel */}
          <div
            className={`relative transition-all flex-1 ${
              // Desktop visibility
              viewMode === 'explore' ? 'w-full' :
              viewMode === 'split' ? '' :
              'hidden'
            } ${
              // Mobile visibility override
              'max-md:hidden'
            } ${
              mobileView === 'graph' ? 'max-md:flex max-md:w-full' : ''
            }`}
          >
            <KnowledgeGraph3D
              projectId={projectId}
              onNodeClick={handleNodeClick}
            />

            {/* Filter Panel */}
            <FilterPanel
              entityTypes={actualEntityTypes}
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

            {/* Clear highlights button - Editorial Style */}
            {(highlightedNodes.length > 0 || highlightedEdges.length > 0) && !selectedNode && (
              <button
                onClick={clearHighlights}
                className="absolute bottom-4 right-4 flex items-center gap-2 px-3 py-2 bg-paper dark:bg-ink border border-ink/10 dark:border-paper/10 text-sm text-muted hover:text-accent-red hover:border-accent-red transition-colors z-10"
              >
                <X className="w-4 h-4" />
                <span className="hidden sm:inline font-mono text-xs uppercase tracking-wider">Clear</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </ErrorBoundary>
  );
}
