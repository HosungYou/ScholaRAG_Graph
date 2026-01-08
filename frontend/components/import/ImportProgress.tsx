'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { CheckCircle, Circle, Loader2, XCircle, ArrowRight } from 'lucide-react';
import { api } from '@/lib/api';
import type { ImportJob } from '@/types';

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
      <div className="bg-red-50 border border-red-200 rounded-xl p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-red-100 rounded-full">
            <XCircle className="w-6 h-6 text-red-600" />
          </div>
          <div>
            <h3 className="font-semibold text-red-700">Import Failed</h3>
            <p className="text-sm text-red-600">{error}</p>
          </div>
        </div>
        <button
          onClick={() => router.back()}
          className="px-4 py-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition-colors text-sm font-medium"
        >
          Try Again
        </button>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="bg-white border rounded-xl p-6">
        <div className="flex items-center justify-center gap-3">
          <Loader2 className="w-5 h-5 animate-spin text-blue-600" />
          <span className="text-gray-600">Initializing import...</span>
        </div>
      </div>
    );
  }

  const currentStepIndex = job.current_step ? getStepIndex(job.current_step) : 0;
  const isComplete = job.status === 'completed';

  return (
    <div className="bg-white border rounded-xl overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-white">
              {isComplete ? 'Import Complete!' : 'Importing Project...'}
            </h3>
            <p className="text-blue-100 text-sm">
              {isComplete
                ? `Created ${job.result?.nodes_created || 0} nodes and ${job.result?.edges_created || 0} edges`
                : `Step ${currentStepIndex + 1} of ${IMPORT_STEPS.length}`}
            </p>
          </div>
          <div className="text-right">
            <div className="text-3xl font-bold text-white">
              {Math.round(job.progress)}%
            </div>
          </div>
        </div>

        {/* Progress bar */}
        <div className="mt-4 h-2 bg-blue-900/30 rounded-full overflow-hidden">
          <div
            className="h-full bg-white transition-all duration-500 ease-out rounded-full"
            style={{ width: `${job.progress}%` }}
          />
        </div>
      </div>

      {/* Steps */}
      <div className="p-6">
        <div className="space-y-3">
          {IMPORT_STEPS.map((step, index) => {
            const isCurrentStep = index === currentStepIndex && !isComplete;
            const isPastStep = index < currentStepIndex || isComplete;
            const isFutureStep = index > currentStepIndex && !isComplete;

            return (
              <div
                key={step.id}
                className={`flex items-center gap-4 p-3 rounded-lg transition-all ${
                  isCurrentStep
                    ? 'bg-blue-50 border border-blue-200'
                    : isPastStep
                    ? 'bg-green-50/50'
                    : 'opacity-50'
                }`}
              >
                {/* Icon */}
                <div className="flex-shrink-0">
                  {isPastStep ? (
                    <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
                      <CheckCircle className="w-5 h-5 text-green-600" />
                    </div>
                  ) : isCurrentStep ? (
                    <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                      <Loader2 className="w-5 h-5 text-blue-600 animate-spin" />
                    </div>
                  ) : (
                    <div className="w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center">
                      <Circle className="w-5 h-5 text-gray-400" />
                    </div>
                  )}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <p
                    className={`font-medium ${
                      isPastStep
                        ? 'text-green-700'
                        : isCurrentStep
                        ? 'text-blue-700'
                        : 'text-gray-500'
                    }`}
                  >
                    {step.label}
                  </p>
                  <p
                    className={`text-sm ${
                      isPastStep
                        ? 'text-green-600'
                        : isCurrentStep
                        ? 'text-blue-600'
                        : 'text-gray-400'
                    }`}
                  >
                    {step.description}
                  </p>
                </div>

                {/* Status indicator */}
                {isCurrentStep && (
                  <div className="flex-shrink-0">
                    <span className="inline-flex items-center gap-1 px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded-full">
                      <span className="w-1.5 h-1.5 bg-blue-600 rounded-full animate-pulse" />
                      In Progress
                    </span>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Complete action */}
        {isComplete && job.result?.project_id && (
          <div className="mt-6 pt-4 border-t">
            <button
              onClick={() => router.push(`/projects/${job.result!.project_id}`)}
              className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-gradient-to-r from-green-600 to-emerald-600 text-white rounded-lg hover:from-green-700 hover:to-emerald-700 transition-all font-medium"
            >
              Open Project
              <ArrowRight className="w-5 h-5" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
