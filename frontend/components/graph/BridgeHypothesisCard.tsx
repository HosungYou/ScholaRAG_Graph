'use client';

import { useState } from 'react';
import {
  Lightbulb,
  Beaker,
  BookOpen,
  Link2,
  ChevronDown,
  ChevronUp,
  Copy,
  Check,
  Sparkles,
} from 'lucide-react';
import type { BridgeHypothesis } from '@/types';

/* ============================================================
   BridgeHypothesisCard - AI-Generated Bridge Hypothesis Display
   Phase 3: InfraNodus Integration

   Displays a single AI-generated bridge hypothesis with:
   - Title and description
   - Methodology suggestion
   - Connecting concepts
   - Confidence score

   Design: VS Design Diverge Style (Direction B - Editorial Research)
   ============================================================ */

interface BridgeHypothesisCardProps {
  hypothesis: BridgeHypothesis;
  index: number;
  onAccept?: (hypothesis: BridgeHypothesis) => void;
}

// Confidence level styling
function getConfidenceStyle(confidence: number): {
  bg: string;
  text: string;
  label: string;
} {
  if (confidence >= 0.7) {
    return {
      bg: 'bg-accent-emerald/10',
      text: 'text-accent-emerald',
      label: 'High',
    };
  } else if (confidence >= 0.4) {
    return {
      bg: 'bg-accent-amber/10',
      text: 'text-accent-amber',
      label: 'Medium',
    };
  } else {
    return {
      bg: 'bg-accent-red/10',
      text: 'text-accent-red',
      label: 'Low',
    };
  }
}

export function BridgeHypothesisCard({
  hypothesis,
  index,
  onAccept,
}: BridgeHypothesisCardProps) {
  const [isExpanded, setIsExpanded] = useState(index === 0); // First one expanded by default
  const [copied, setCopied] = useState(false);

  const confidenceStyle = getConfidenceStyle(hypothesis.confidence);

  const handleCopy = async () => {
    const text = `
${hypothesis.title}

${hypothesis.description}

Methodology: ${hypothesis.methodology}

Connecting Concepts: ${hypothesis.connecting_concepts.join(', ')}

Confidence: ${Math.round(hypothesis.confidence * 100)}%
`.trim();

    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  return (
    <div className="border border-ink/10 dark:border-paper/10 bg-surface/5 relative overflow-hidden">
      {/* Left accent bar */}
      <div className="absolute left-0 top-0 bottom-0 w-1 bg-accent-amber" />

      {/* Hypothesis number badge */}
      <div className="absolute -top-1 -left-1 w-6 h-6 flex items-center justify-center bg-accent-amber text-white font-mono text-xs z-10">
        {index + 1}
      </div>

      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full p-4 pl-8 text-left hover:bg-surface/5 transition-colors"
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2 flex-wrap">
              <Lightbulb className="w-4 h-4 text-accent-amber flex-shrink-0" />
              <span className={`px-2 py-0.5 font-mono text-xs ${confidenceStyle.bg} ${confidenceStyle.text}`}>
                {confidenceStyle.label} ({Math.round(hypothesis.confidence * 100)}%)
              </span>
            </div>

            <h4 className="font-mono text-sm text-ink dark:text-paper mb-1 line-clamp-2">
              {hypothesis.title}
            </h4>

            {!isExpanded && (
              <p className="text-xs text-muted line-clamp-2">
                {hypothesis.description}
              </p>
            )}
          </div>

          <div className="flex items-center gap-2 flex-shrink-0">
            {isExpanded ? (
              <ChevronUp className="w-4 h-4 text-muted" />
            ) : (
              <ChevronDown className="w-4 h-4 text-muted" />
            )}
          </div>
        </div>
      </button>

      {/* Expanded content */}
      {isExpanded && (
        <div className="px-4 pl-8 pb-4 space-y-4 border-t border-ink/5 dark:border-paper/5">
          {/* Description */}
          <div className="pt-4">
            <p className="text-sm text-ink dark:text-paper leading-relaxed">
              {hypothesis.description}
            </p>
          </div>

          {/* Methodology */}
          <div className="p-3 bg-accent-teal/5 border-l-2 border-accent-teal">
            <div className="flex items-center gap-2 mb-2">
              <Beaker className="w-4 h-4 text-accent-teal" />
              <span className="font-mono text-xs uppercase tracking-wider text-accent-teal">
                Suggested Methodology
              </span>
            </div>
            <p className="text-sm text-ink dark:text-paper">
              {hypothesis.methodology}
            </p>
          </div>

          {/* Connecting concepts */}
          {hypothesis.connecting_concepts.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-2">
                <Link2 className="w-4 h-4 text-accent-violet" />
                <span className="font-mono text-xs uppercase tracking-wider text-accent-violet">
                  Connecting Concepts
                </span>
              </div>
              <div className="flex flex-wrap gap-2">
                {hypothesis.connecting_concepts.map((concept, i) => (
                  <span
                    key={i}
                    className="px-2 py-1 bg-accent-violet/10 text-accent-violet font-mono text-xs border border-accent-violet/30"
                  >
                    {concept}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center justify-between pt-2 border-t border-ink/5 dark:border-paper/5">
            <button
              onClick={handleCopy}
              className="flex items-center gap-2 px-3 py-1.5 font-mono text-xs text-muted hover:text-ink dark:hover:text-paper hover:bg-surface/10 transition-colors"
            >
              {copied ? (
                <>
                  <Check className="w-3 h-3 text-accent-teal" />
                  Copied
                </>
              ) : (
                <>
                  <Copy className="w-3 h-3" />
                  Copy
                </>
              )}
            </button>

            {onAccept && (
              <button
                onClick={() => onAccept(hypothesis)}
                className="flex items-center gap-2 px-4 py-2 bg-accent-teal/10 hover:bg-accent-teal/20 text-accent-teal font-mono text-xs uppercase tracking-wider transition-colors"
              >
                <Sparkles className="w-3 h-3" />
                Accept & Create Bridge
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/* ============================================================
   BridgeHypothesisList - List of Bridge Hypotheses
   ============================================================ */

interface BridgeHypothesisListProps {
  hypotheses: BridgeHypothesis[];
  bridgeType: 'theoretical' | 'methodological' | 'empirical';
  keyInsight: string;
  onAccept?: (hypothesis: BridgeHypothesis) => void;
}

// Bridge type styling
function getBridgeTypeStyle(type: string): { icon: JSX.Element; label: string; color: string } {
  switch (type) {
    case 'methodological':
      return {
        icon: <Beaker className="w-4 h-4" />,
        label: 'Methodological',
        color: 'text-accent-teal',
      };
    case 'empirical':
      return {
        icon: <BookOpen className="w-4 h-4" />,
        label: 'Empirical',
        color: 'text-accent-emerald',
      };
    case 'theoretical':
    default:
      return {
        icon: <Lightbulb className="w-4 h-4" />,
        label: 'Theoretical',
        color: 'text-accent-amber',
      };
  }
}

export function BridgeHypothesisList({
  hypotheses,
  bridgeType,
  keyInsight,
  onAccept,
}: BridgeHypothesisListProps) {
  const bridgeStyle = getBridgeTypeStyle(bridgeType);

  return (
    <div className="space-y-4">
      {/* Key insight */}
      <div className="p-4 bg-accent-amber/5 border border-accent-amber/20 relative">
        <div className="absolute left-0 top-0 bottom-0 w-1 bg-accent-amber" />
        <div className="flex items-start gap-3 pl-3">
          <Sparkles className="w-5 h-5 text-accent-amber flex-shrink-0 mt-0.5" />
          <div>
            <span className="font-mono text-xs uppercase tracking-wider text-accent-amber mb-1 block">
              Key Insight
            </span>
            <p className="text-sm text-ink dark:text-paper">{keyInsight}</p>
          </div>
        </div>
      </div>

      {/* Bridge type indicator */}
      <div className="flex items-center gap-2">
        <span className={bridgeStyle.color}>{bridgeStyle.icon}</span>
        <span className="font-mono text-xs uppercase tracking-wider text-muted">
          {bridgeStyle.label} Bridge
        </span>
        <span className="text-xs text-muted">
          ({hypotheses.length} hypothesis{hypotheses.length !== 1 ? 'es' : ''})
        </span>
      </div>

      {/* Hypotheses list */}
      <div className="space-y-3">
        {hypotheses.map((hypothesis, index) => (
          <BridgeHypothesisCard
            key={index}
            hypothesis={hypothesis}
            index={index}
            onAccept={onAccept}
          />
        ))}
      </div>
    </div>
  );
}
