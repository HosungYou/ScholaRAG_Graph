'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { CheckCircle, Circle, Loader2, XCircle, ArrowRight, Hexagon } from 'lucide-react';
import { api } from '@/lib/api';
import type { ImportJob } from '@/types';

/* ============================================================
   ImportProgress - VS Design Diverge Style
   Direction B (T-Score 0.4) "Editorial Research"

   Design Principles:
   - Line-based hierarchy (left accent bars)
   - No blue/purple gradients
   - Teal accent for active/complete states
   - Monospace numbers
   - Minimal border-radius
   ============================================================ */

interface ImportProgressProps {
  jobId: string;
  onComplete?: (projectId: string) => void;
  onError?: (error: string) => void;
}

interface StepInfo {
  id: string;
  label: string;
  description: string;
}

const IMPORT_STEPS: StepInfo[] = [
  { id: 'validate', label: 'Validation', description: 'Validating project structure' },
  { id: 'parse_config', label: 'Parse Config', description: 'Reading config.yaml' },
  { id: 'import_papers', label: 'Import Papers', description: 'Importing papers from CSV' },
  { id: 'extract_entities', label: 'Extract Entities', description: 'Extracting concepts, methods, findings' },
  { id: 'build_relationships', label: 'Build Graph', description: 'Creating relationships between entities' },
  { id: 'create_embeddings', label: 'Embeddings', description: 'Generating vector embeddings' },
  { id: 'finalize', label: 'Complete', description: 'Finalizing import' },
];

function getStepIndex(stepId: string): number {
  return IMPORT_STEPS.findIndex(s => s.id === stepId);
}

export function ImportProgress({ jobId, onComplete, onError }: ImportProgressProps) {
  const [job, setJob] = useState<ImportJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    if (!jobId) return;

    let intervalId: NodeJS.Timeout;

    const pollStatus = async () => {
      try {
        const status = await api.getImportStatus(jobId);
        setJob(status);

        if (status.status === 'completed' && status.result?.project_id) {
          clearInterval(intervalId);
          onComplete?.(status.result.project_id);
        } else if (status.status === 'failed') {
          clearInterval(intervalId);
          setError(status.error || 'Import failed');
          onError?.(status.error || 'Import failed');
        }
      } catch (err) {
        console.error('Failed to fetch import status:', err);
      }
    };

    // Initial fetch
    pollStatus();

    // Poll every 2 seconds
    intervalId = setInterval(pollStatus, 2000);

    return () => clearInterval(intervalId);
  }, [jobId, onComplete, onError]);

  if (error) {
    return (
      <div className="border-l-2 border-accent-red bg-accent-red/5 p-6">
        <div className="flex items-center gap-3 mb-4">
          <XCircle className="w-6 h-6 text-accent-red" />
          <div>
            <h3 className="font-medium text-ink dark:text-paper">Import Failed</h3>
            <p className="text-sm text-accent-red">{error}</p>
          </div>
        </div>
        <button
          onClick={() => router.back()}
          className="btn btn--secondary"
        >
          Try Again
        </button>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="border border-ink/10 dark:border-paper/10 p-6">
        <div className="flex items-center justify-center gap-3">
          <Loader2 className="w-5 h-5 animate-spin text-accent-teal" />
          <span className="text-muted">Initializing import...</span>
        </div>
      </div>
    );
  }

  const currentStepIndex = job.current_step ? getStepIndex(job.current_step) : 0;
  const isComplete = job.status === 'completed';

  return (
    <div className="relative overflow-hidden bg-paper dark:bg-ink rounded-sm shadow-lg border-2 border-accent-teal/30">
      {/* Decorative corner accent */}
      <div className="absolute top-0 right-0 w-24 h-24 bg-accent-teal/10 transform rotate-45 translate-x-12 -translate-y-12" />

      {/* Header - Rich dark with subtle texture */}
      <div className="relative bg-surface px-6 py-6 overflow-hidden">
        {/* Background pattern - subtle diagonal lines */}
        <div className="absolute inset-0 opacity-5">
          <svg width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <pattern id="diagonalLines" patternUnits="userSpaceOnUse" width="10" height="10">
                <path d="M-1,1 l2,-2 M0,10 l10,-10 M9,11 l2,-2" stroke="white" strokeWidth="1"/>
              </pattern>
            </defs>
            <rect width="100%" height="100%" fill="url(#diagonalLines)" />
          </svg>
        </div>

        <div className="relative flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <div className="flex items-center justify-center w-8 h-8 bg-accent-teal/20 rounded-sm">
                <Hexagon className="w-5 h-5 text-accent-teal" strokeWidth={2} />
              </div>
              <span className="font-mono text-xs uppercase tracking-widest text-accent-teal font-semibold">
                {isComplete ? '✓ Complete' : '◉ Processing'}
              </span>
            </div>
            <h3 className="font-display text-2xl text-white font-medium">
              {isComplete ? 'Import Complete!' : 'Building Knowledge Graph...'}
            </h3>
            <p className="text-white/80 text-sm mt-2">
              {isComplete
                ? `Created ${job.result?.nodes_created || 0} nodes and ${job.result?.edges_created || 0} edges`
                : IMPORT_STEPS[currentStepIndex]?.description || 'Processing...'}
            </p>
          </div>
          <div className="text-right">
            <div className="font-mono text-5xl text-white font-bold tracking-tight">
              {Math.round(job.progress)}
              <span className="text-2xl text-accent-teal">%</span>
            </div>
          </div>
        </div>

        {/* Progress bar - Glowing style */}
        <div className="mt-5 h-2 bg-white/10 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-accent-teal to-accent-teal/80 rounded-full transition-all duration-500 ease-out shadow-[0_0_10px_rgba(46,196,182,0.5)]"
            style={{ width: `${job.progress}%` }}
          />
        </div>
      </div>

      {/* Steps - Enhanced editorial design */}
      <div className="p-6 pt-4">
        {/* Section header */}
        <div className="flex items-center gap-2 mb-4 pb-3 border-b border-ink/10 dark:border-paper/10">
          <span className="font-mono text-xs uppercase tracking-widest text-muted">Progress Steps</span>
          <div className="flex-1 h-px bg-ink/5 dark:bg-paper/5" />
          <span className="font-mono text-xs text-accent-teal">{currentStepIndex + 1}/{IMPORT_STEPS.length}</span>
        </div>

        <div className="space-y-0">
          {IMPORT_STEPS.map((step, index) => {
            const isCurrentStep = index === currentStepIndex && !isComplete;
            const isPastStep = index < currentStepIndex || isComplete;
            const isFutureStep = index > currentStepIndex && !isComplete;

            return (
              <div
                key={step.id}
                className={`relative flex items-center gap-4 py-3 px-4 transition-all border-l-2 ${
                  isCurrentStep
                    ? 'bg-accent-amber/5 border-l-accent-amber'
                    : isPastStep
                    ? 'border-l-accent-teal'
                    : 'border-l-transparent opacity-50'
                }`}
              >
                {/* Step number */}
                <div className={`flex-shrink-0 w-7 h-7 flex items-center justify-center rounded-sm font-mono text-xs font-bold ${
                  isPastStep
                    ? 'bg-accent-teal text-white'
                    : isCurrentStep
                    ? 'bg-accent-amber text-white'
                    : 'bg-ink/10 dark:bg-paper/10 text-muted'
                }`}>
                  {isPastStep ? (
                    <CheckCircle className="w-4 h-4" />
                  ) : isCurrentStep ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <span>{String(index + 1).padStart(2, '0')}</span>
                  )}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <p
                    className={`font-medium text-sm ${
                      isPastStep
                        ? 'text-accent-teal'
                        : isCurrentStep
                        ? 'text-ink dark:text-paper'
                        : 'text-muted'
                    }`}
                  >
                    {step.label}
                  </p>
                  <p
                    className={`text-xs mt-0.5 ${
                      isPastStep
                        ? 'text-accent-teal/60'
                        : isCurrentStep
                        ? 'text-muted'
                        : 'text-muted/50'
                    }`}
                  >
                    {step.description}
                  </p>
                </div>

                {/* Status indicator */}
                {isCurrentStep && (
                  <div className="flex-shrink-0">
                    <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-accent-amber/10 border border-accent-amber/30 text-accent-amber text-xs font-mono font-semibold rounded-sm">
                      <span className="w-2 h-2 bg-accent-amber rounded-full animate-pulse" />
                      ACTIVE
                    </span>
                  </div>
                )}

                {isPastStep && (
                  <div className="flex-shrink-0">
                    <span className="text-accent-teal text-xs font-mono">Done</span>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Complete action */}
        {isComplete && job.result?.project_id && (
          <div className="mt-6 pt-6 border-t-2 border-accent-teal/20">
            <button
              onClick={() => router.push(`/projects/${job.result!.project_id}`)}
              className="group relative w-full py-4 bg-accent-teal text-white font-medium rounded-sm overflow-hidden transition-all hover:bg-accent-teal/90 hover:shadow-lg hover:shadow-accent-teal/20"
            >
              {/* Animated shine effect */}
              <div className="absolute inset-0 -translate-x-full group-hover:translate-x-full transition-transform duration-700 bg-gradient-to-r from-transparent via-white/20 to-transparent" />
              <span className="relative flex items-center justify-center gap-2">
                <span className="font-semibold">Open Project</span>
                <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
