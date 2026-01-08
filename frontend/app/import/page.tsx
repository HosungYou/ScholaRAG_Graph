'use client';

import { useState, useRef, DragEvent, useCallback } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  Network,
  FolderOpen,
  Upload,
  CheckCircle,
  XCircle,
  AlertCircle,
  Loader2,
  FolderSearch,
  ClipboardPaste,
  FileText,
  Database,
  BookOpen,
  Info,
} from 'lucide-react';
import { useMutation } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { Header } from '@/components/layout';
import { ThemeToggle, ErrorBoundary, ErrorDisplay } from '@/components/ui';
import { ImportProgress } from '@/components/import/ImportProgress';
import type { ImportValidationResult } from '@/types';

/**
 * Normalize ScholaRAG project folder path.
 */
function normalizeScholarAGPath(inputPath: string): { path: string; wasNormalized: boolean; originalPath: string } {
  const trimmedPath = inputPath.trim();
  const originalPath = trimmedPath;

  const subfolderPatterns = [
    /\/data\/0[1-7]_[^/]+.*$/,
    /\/data\/04_rag\/.*$/,
    /\/\.scholarag.*$/,
    /\/output.*$/,
    /\/logs.*$/,
  ];

  let normalizedPath = trimmedPath;
  let wasNormalized = false;

  for (const pattern of subfolderPatterns) {
    if (pattern.test(normalizedPath)) {
      normalizedPath = normalizedPath.replace(pattern, '');
      wasNormalized = true;
      break;
    }
  }

  if (normalizedPath.endsWith('/data')) {
    normalizedPath = normalizedPath.replace(/\/data$/, '');
    wasNormalized = true;
  }

  return { path: normalizedPath, wasNormalized, originalPath };
}

export default function ImportPage() {
  const [folderPath, setFolderPath] = useState('');
  const [validation, setValidation] = useState<ImportValidationResult | null>(null);
  const [importJobId, setImportJobId] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [pathNormalized, setPathNormalized] = useState<{ wasNormalized: boolean; originalPath: string } | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  const handlePathChange = useCallback((newPath: string) => {
    const { path, wasNormalized, originalPath } = normalizeScholarAGPath(newPath);
    setFolderPath(path);
    setValidation(null);
    if (wasNormalized) {
      setPathNormalized({ wasNormalized, originalPath });
    } else {
      setPathNormalized(null);
    }
  }, []);

  const validateMutation = useMutation({
    mutationFn: (path: string) => api.validateScholarag(path),
    onSuccess: (data) => setValidation(data),
  });

  const importMutation = useMutation({
    mutationFn: (path: string) => api.importScholarag(path),
    onSuccess: (data) => setImportJobId(data.job_id),
  });

  const handleValidate = () => {
    if (!folderPath.trim()) return;
    setValidation(null);
    validateMutation.mutate(folderPath);
  };

  const handleImport = () => {
    if (!folderPath.trim() || !validation?.valid) return;
    importMutation.mutate(folderPath);
  };

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);

    if (e.dataTransfer.items.length > 0) {
      alert(
        '웹 브라우저 보안 정책으로 인해 드래그 앤 드롭으로는 폴더 경로를 가져올 수 없습니다.\n\nFinder에서 폴더를 우클릭 → "정보 가져오기" → 위치를 복사하거나,\n터미널에서 폴더로 이동 후 pwd 명령어로 경로를 복사해주세요.'
      );
    }
  };

  const handlePaste = async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) {
        handlePathChange(text);
      }
    } catch (err) {
      console.error('Failed to read clipboard:', err);
      alert('클립보드를 읽을 수 없습니다. 브라우저 권한을 확인해주세요.');
    }
  };

  const commonPaths = [
    '/Volumes/External SSD/Projects/Research/ScholaRAG/projects',
    '~/Documents/ScholaRAG/projects',
  ];

  if (importJobId) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex flex-col">
        <Header
          breadcrumbs={[{ label: 'Import', href: '/import' }, { label: 'Progress' }]}
          rightContent={<ThemeToggle />}
        />

        <main className="flex-1 max-w-2xl mx-auto px-4 py-8 w-full">
          <ErrorBoundary>
            <ImportProgress
              jobId={importJobId}
              onComplete={(projectId) => {
                setTimeout(() => {
                  router.push(`/projects/${projectId}`);
                }, 2000);
              }}
            />
          </ErrorBoundary>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex flex-col">
      <a href="#main-content" className="skip-link">
        메인 콘텐츠로 건너뛰기
      </a>

      <Header
        breadcrumbs={[{ label: 'Import' }]}
        rightContent={<ThemeToggle />}
      />

      <main id="main-content" className="flex-1 max-w-3xl mx-auto px-4 py-6 sm:py-8 w-full">
        <ErrorBoundary>
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border dark:border-gray-700 p-5 sm:p-8">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center gap-4 mb-6">
              <div className="p-3 bg-gradient-to-br from-blue-100 to-purple-100 dark:from-blue-900/30 dark:to-purple-900/30 rounded-lg w-fit">
                <FolderOpen className="w-8 h-8 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <h2 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white">
                  Import ScholaRAG Project
                </h2>
                <p className="text-gray-600 dark:text-gray-300 text-sm sm:text-base">
                  Import an existing ScholaRAG project folder to build a knowledge graph.
                </p>
              </div>
            </div>

            {/* What will be imported */}
            <div className="mb-6 p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
              <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                Import 과정에서 생성되는 것:
              </p>
              <div className="grid grid-cols-3 gap-2 sm:gap-4 text-center">
                <div className="p-2 sm:p-3 bg-white dark:bg-gray-800 rounded-lg border dark:border-gray-600">
                  <FileText className="w-5 sm:w-6 h-5 sm:h-6 text-blue-600 mx-auto mb-1" />
                  <p className="text-xs text-gray-600 dark:text-gray-300">Papers & Authors</p>
                </div>
                <div className="p-2 sm:p-3 bg-white dark:bg-gray-800 rounded-lg border dark:border-gray-600">
                  <BookOpen className="w-5 sm:w-6 h-5 sm:h-6 text-purple-600 mx-auto mb-1" />
                  <p className="text-xs text-gray-600 dark:text-gray-300">Concepts & Methods</p>
                </div>
                <div className="p-2 sm:p-3 bg-white dark:bg-gray-800 rounded-lg border dark:border-gray-600">
                  <Database className="w-5 sm:w-6 h-5 sm:h-6 text-green-600 mx-auto mb-1" />
                  <p className="text-xs text-gray-600 dark:text-gray-300">Knowledge Graph</p>
                </div>
              </div>
            </div>

            {/* Drag & Drop Zone */}
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => inputRef.current?.focus()}
              className={`
                border-2 border-dashed rounded-xl p-6 sm:p-8 mb-6 text-center transition-all cursor-pointer
                ${isDragOver
                  ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                  : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500 hover:bg-gray-50 dark:hover:bg-gray-700/50'
                }
              `}
              role="button"
              tabIndex={0}
              aria-label="프로젝트 폴더 경로 입력"
            >
              <FolderSearch
                className={`w-10 sm:w-12 h-10 sm:h-12 mx-auto mb-3 sm:mb-4 ${
                  isDragOver ? 'text-blue-500' : 'text-gray-400 dark:text-gray-500'
                }`}
              />
              <p className={`text-base sm:text-lg font-medium ${
                isDragOver ? 'text-blue-600 dark:text-blue-400' : 'text-gray-700 dark:text-gray-300'
              }`}>
                ScholaRAG 프로젝트 폴더 경로를 입력하세요
              </p>
              <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400 mt-2">
                Finder에서 폴더를 우클릭 → "경로명 복사"로 복사한 후 아래에 붙여넣기
              </p>
            </div>

            {/* Folder Path Input */}
            <div className="mb-6">
              <label
                htmlFor="folderPath"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
              >
                프로젝트 폴더 경로
              </label>
              <div className="flex gap-2">
                <div className="flex-1 relative group">
                  <input
                    ref={inputRef}
                    type="text"
                    id="folderPath"
                    value={folderPath}
                    onChange={(e) => handlePathChange(e.target.value)}
                    placeholder="/path/to/ScholaRAG/projects/2025-01-01_ProjectName"
                    className="w-full px-3 sm:px-4 py-3 pr-12 border dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono text-xs sm:text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400"
                    title={folderPath || '프로젝트 폴더 경로를 입력하세요'}
                  />
                  {folderPath && (
                    <div className="absolute left-0 right-0 -bottom-1 translate-y-full z-10 hidden group-hover:block">
                      <div className="bg-gray-900 text-white text-xs p-2 rounded shadow-lg font-mono break-all max-w-full">
                        {folderPath}
                      </div>
                    </div>
                  )}
                  <button
                    onClick={handlePaste}
                    className="absolute right-2 top-1/2 -translate-y-1/2 p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors touch-target"
                    title="클립보드에서 붙여넣기"
                    aria-label="클립보드에서 붙여넣기"
                  >
                    <ClipboardPaste className="w-5 h-5" />
                  </button>
                </div>
                <button
                  onClick={handleValidate}
                  disabled={!folderPath.trim() || validateMutation.isPending}
                  className="px-4 sm:px-6 py-3 bg-gray-800 dark:bg-gray-600 text-white rounded-lg hover:bg-gray-700 dark:hover:bg-gray-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium touch-target"
                >
                  {validateMutation.isPending ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    '검증'
                  )}
                </button>
              </div>

              {folderPath && folderPath.length > 60 && (
                <div className="mt-2 p-2 bg-gray-50 dark:bg-gray-700/50 rounded border dark:border-gray-600 text-xs font-mono text-gray-600 dark:text-gray-300 break-all">
                  <span className="text-gray-400">전체 경로: </span>
                  {folderPath}
                </div>
              )}

              {pathNormalized?.wasNormalized && (
                <div className="mt-3 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                  <div className="flex items-start gap-2">
                    <Info className="w-4 h-4 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0" />
                    <div className="text-sm">
                      <p className="text-blue-700 dark:text-blue-300 font-medium">
                        경로가 자동 수정되었습니다
                      </p>
                      <p className="text-blue-600 dark:text-blue-400 mt-1 text-xs sm:text-sm">
                        하위 폴더 대신 프로젝트 루트 폴더로 경로를 수정했습니다.
                      </p>
                      <p className="text-xs text-blue-500 dark:text-blue-500 mt-1 font-mono break-all">
                        원래 경로: {pathNormalized.originalPath}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              <div className="mt-3">
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">빠른 경로 선택:</p>
                <div className="flex flex-wrap gap-2">
                  {commonPaths.map((path, i) => (
                    <button
                      key={i}
                      onClick={() => handlePathChange(path)}
                      className="text-xs px-3 py-1.5 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded-full hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors font-mono touch-target"
                    >
                      {path.length > 40 ? '...' + path.slice(-37) : path}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Validation Error */}
            {validateMutation.isError && (
              <ErrorDisplay
                error={validateMutation.error as Error}
                title="검증 실패"
                message="폴더 경로를 확인할 수 없습니다. 경로가 올바른지 확인해주세요."
                onRetry={handleValidate}
                compact
              />
            )}

            {/* Validation Results */}
            {validation && (
              <div
                className={`rounded-lg p-4 mb-6 ${
                  validation.valid
                    ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800'
                    : 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800'
                }`}
              >
                <div className="flex items-center gap-2 mb-4">
                  {validation.valid ? (
                    <>
                      <CheckCircle className="w-6 h-6 text-green-600 dark:text-green-400" />
                      <span className="font-semibold text-green-700 dark:text-green-300">검증 성공</span>
                    </>
                  ) : (
                    <>
                      <XCircle className="w-6 h-6 text-red-600 dark:text-red-400" />
                      <span className="font-semibold text-red-700 dark:text-red-300">검증 실패</span>
                    </>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-2 sm:gap-3 text-sm">
                  <div className="flex items-center gap-2">
                    {validation.config_found ? (
                      <CheckCircle className="w-4 h-4 text-green-600 dark:text-green-400 flex-shrink-0" />
                    ) : (
                      <XCircle className="w-4 h-4 text-red-600 dark:text-red-400 flex-shrink-0" />
                    )}
                    <span className="text-gray-700 dark:text-gray-300 text-xs sm:text-sm">config.yaml</span>
                  </div>
                  <div className="flex items-center gap-2">
                    {validation.scholarag_metadata_found ? (
                      <CheckCircle className="w-4 h-4 text-green-600 dark:text-green-400 flex-shrink-0" />
                    ) : (
                      <AlertCircle className="w-4 h-4 text-yellow-600 dark:text-yellow-400 flex-shrink-0" />
                    )}
                    <span className="text-gray-700 dark:text-gray-300 text-xs sm:text-sm">.scholarag</span>
                  </div>
                  <div className="flex items-center gap-2">
                    {validation.papers_csv_found ? (
                      <CheckCircle className="w-4 h-4 text-green-600 dark:text-green-400 flex-shrink-0" />
                    ) : (
                      <XCircle className="w-4 h-4 text-red-600 dark:text-red-400 flex-shrink-0" />
                    )}
                    <span className="text-gray-700 dark:text-gray-300 text-xs sm:text-sm">
                      Papers ({validation.papers_count})
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    {validation.pdfs_count > 0 ? (
                      <CheckCircle className="w-4 h-4 text-green-600 dark:text-green-400 flex-shrink-0" />
                    ) : (
                      <AlertCircle className="w-4 h-4 text-yellow-600 dark:text-yellow-400 flex-shrink-0" />
                    )}
                    <span className="text-gray-700 dark:text-gray-300 text-xs sm:text-sm">
                      PDFs ({validation.pdfs_count})
                    </span>
                  </div>
                  <div className="flex items-center gap-2 col-span-2">
                    {validation.chroma_db_found ? (
                      <CheckCircle className="w-4 h-4 text-green-600 dark:text-green-400 flex-shrink-0" />
                    ) : (
                      <AlertCircle className="w-4 h-4 text-yellow-600 dark:text-yellow-400 flex-shrink-0" />
                    )}
                    <span className="text-gray-700 dark:text-gray-300 text-xs sm:text-sm">ChromaDB embeddings</span>
                  </div>
                </div>

                {validation.errors.length > 0 && (
                  <div className="mt-4 p-3 bg-red-100 dark:bg-red-900/30 rounded">
                    <p className="font-medium text-red-700 dark:text-red-300 mb-1 text-sm">오류:</p>
                    <ul className="list-disc list-inside text-red-600 dark:text-red-400 text-xs sm:text-sm">
                      {validation.errors.map((err, i) => (
                        <li key={i}>{err}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {validation.warnings.length > 0 && (
                  <div className="mt-4 p-3 bg-yellow-100 dark:bg-yellow-900/30 rounded">
                    <p className="font-medium text-yellow-700 dark:text-yellow-300 mb-1 text-sm">경고:</p>
                    <ul className="list-disc list-inside text-yellow-600 dark:text-yellow-400 text-xs sm:text-sm">
                      {validation.warnings.map((warn, i) => (
                        <li key={i}>{warn}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {/* Import Button */}
            <button
              onClick={handleImport}
              disabled={!validation?.valid || importMutation.isPending}
              className="w-full flex items-center justify-center gap-2 px-6 py-4 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg hover:from-blue-700 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all font-medium text-base sm:text-lg shadow-lg shadow-blue-500/25 touch-target"
            >
              {importMutation.isPending ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Starting Import...
                </>
              ) : (
                <>
                  <Upload className="w-5 h-5" />
                  Import & Build Knowledge Graph
                </>
              )}
            </button>

            {/* Help Section */}
            <div className="mt-8 p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
              <h3 className="font-medium text-gray-700 dark:text-gray-300 mb-2">폴더 경로 찾는 방법</h3>
              <ol className="text-xs sm:text-sm text-gray-600 dark:text-gray-400 space-y-2">
                <li>1. Finder에서 ScholaRAG 프로젝트 폴더로 이동</li>
                <li>
                  2. 폴더를 우클릭 → <strong>"경로명 복사"</strong> 선택 (Option 키를 누르면 표시됨)
                </li>
                <li>3. 위 입력창에 붙여넣기 (Cmd+V)</li>
              </ol>
              <p className="text-xs text-gray-500 dark:text-gray-500 mt-3">
                또는 터미널에서:{' '}
                <code className="bg-gray-200 dark:bg-gray-600 px-1 rounded">cd [폴더] && pwd</code>
              </p>
            </div>
          </div>
        </ErrorBoundary>
      </main>
    </div>
  );
}
