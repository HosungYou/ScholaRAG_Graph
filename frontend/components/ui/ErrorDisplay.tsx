'use client';

import { AlertCircle, RefreshCw, WifiOff, ServerCrash, FileQuestion } from 'lucide-react';
import { useCallback } from 'react';

type ErrorType = 'network' | 'server' | 'notFound' | 'generic';

interface ErrorDisplayProps {
  error?: Error | string | null;
  title?: string;
  message?: string;
  type?: ErrorType;
  onRetry?: () => void;
  compact?: boolean;
}

const errorConfig: Record<ErrorType, { icon: typeof AlertCircle; defaultTitle: string; defaultMessage: string }> = {
  network: {
    icon: WifiOff,
    defaultTitle: '네트워크 오류',
    defaultMessage: '서버에 연결할 수 없습니다. 인터넷 연결을 확인하고 다시 시도해주세요.',
  },
  server: {
    icon: ServerCrash,
    defaultTitle: '서버 오류',
    defaultMessage: '서버에서 오류가 발생했습니다. 잠시 후 다시 시도해주세요.',
  },
  notFound: {
    icon: FileQuestion,
    defaultTitle: '찾을 수 없음',
    defaultMessage: '요청하신 리소스를 찾을 수 없습니다.',
  },
  generic: {
    icon: AlertCircle,
    defaultTitle: '오류가 발생했습니다',
    defaultMessage: '예기치 않은 오류가 발생했습니다. 다시 시도해주세요.',
  },
};

function getErrorType(error?: Error | string | null): ErrorType {
  if (!error) return 'generic';

  const errorMessage = typeof error === 'string' ? error : error.message;

  if (errorMessage.includes('fetch') || errorMessage.includes('network') || errorMessage.includes('Network')) {
    return 'network';
  }
  if (errorMessage.includes('500') || errorMessage.includes('server')) {
    return 'server';
  }
  if (errorMessage.includes('404') || errorMessage.includes('not found')) {
    return 'notFound';
  }

  return 'generic';
}

export function ErrorDisplay({
  error,
  title,
  message,
  type,
  onRetry,
  compact = false,
}: ErrorDisplayProps) {
  const errorType = type || getErrorType(error);
  const config = errorConfig[errorType];
  const Icon = config.icon;

  const displayTitle = title || config.defaultTitle;
  const displayMessage = message || (typeof error === 'string' ? error : error?.message) || config.defaultMessage;

  const handleRetry = useCallback(() => {
    if (onRetry) {
      onRetry();
    }
  }, [onRetry]);

  if (compact) {
    return (
      <div className="flex items-center gap-3 p-3 bg-red-50 border border-red-200 rounded-lg">
        <Icon className="w-5 h-5 text-red-500 flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="text-sm text-red-700 truncate">{displayMessage}</p>
        </div>
        {onRetry && (
          <button
            onClick={handleRetry}
            className="flex-shrink-0 p-1.5 text-red-600 hover:bg-red-100 rounded transition-colors"
            aria-label="다시 시도"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center p-8 text-center">
      <div className="p-4 bg-red-100 rounded-full mb-4">
        <Icon className="w-8 h-8 text-red-500" />
      </div>
      <h3 className="text-lg font-semibold text-gray-900 mb-2">{displayTitle}</h3>
      <p className="text-gray-600 mb-6 max-w-md">{displayMessage}</p>
      {onRetry && (
        <button
          onClick={handleRetry}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          다시 시도
        </button>
      )}
    </div>
  );
}
