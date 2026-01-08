'use client';

interface SkeletonProps {
  className?: string;
  width?: string | number;
  height?: string | number;
  variant?: 'text' | 'circular' | 'rectangular' | 'rounded';
  animation?: 'pulse' | 'wave' | 'none';
}

export function Skeleton({
  className = '',
  width,
  height,
  variant = 'text',
  animation = 'pulse',
}: SkeletonProps) {
  const baseClasses = 'bg-gray-200';

  const variantClasses = {
    text: 'rounded h-4',
    circular: 'rounded-full',
    rectangular: '',
    rounded: 'rounded-lg',
  };

  const animationClasses = {
    pulse: 'animate-pulse',
    wave: 'animate-shimmer',
    none: '',
  };

  const style: React.CSSProperties = {};
  if (width) style.width = typeof width === 'number' ? `${width}px` : width;
  if (height) style.height = typeof height === 'number' ? `${height}px` : height;

  return (
    <div
      className={`${baseClasses} ${variantClasses[variant]} ${animationClasses[animation]} ${className}`}
      style={style}
      aria-hidden="true"
    />
  );
}

// Project Card Skeleton
export function ProjectCardSkeleton() {
  return (
    <div className="bg-white rounded-xl border shadow-sm p-6 animate-pulse">
      <div className="flex items-start justify-between mb-4">
        <Skeleton variant="rounded" width={48} height={48} />
        <Skeleton variant="text" width={100} height={16} />
      </div>
      <Skeleton variant="text" width="80%" height={24} className="mb-2" />
      <Skeleton variant="text" width="100%" height={16} className="mb-1" />
      <Skeleton variant="text" width="70%" height={16} className="mb-4" />
      <div className="flex gap-4">
        <Skeleton variant="text" width={80} height={16} />
        <Skeleton variant="text" width={80} height={16} />
      </div>
    </div>
  );
}

// Project List Skeleton
export function ProjectListSkeleton({ count = 6 }: { count?: number }) {
  return (
    <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
      {Array.from({ length: count }).map((_, i) => (
        <ProjectCardSkeleton key={i} />
      ))}
    </div>
  );
}

// Chat Message Skeleton
export function ChatMessageSkeleton({ isUser = false }: { isUser?: boolean }) {
  return (
    <div
      className={`p-4 rounded-lg animate-pulse ${
        isUser ? 'bg-blue-50 ml-12' : 'bg-gray-50 mr-12'
      }`}
    >
      <Skeleton variant="text" width={60} height={12} className="mb-3" />
      <Skeleton variant="text" width="100%" height={16} className="mb-2" />
      <Skeleton variant="text" width="90%" height={16} className="mb-2" />
      <Skeleton variant="text" width="75%" height={16} />
    </div>
  );
}

// Node Details Skeleton
export function NodeDetailsSkeleton() {
  return (
    <div className="p-4 animate-pulse">
      <div className="flex items-center gap-3 mb-4">
        <Skeleton variant="rounded" width={40} height={40} />
        <div className="flex-1">
          <Skeleton variant="text" width="60%" height={20} className="mb-2" />
          <Skeleton variant="text" width={80} height={14} />
        </div>
      </div>
      <Skeleton variant="text" width="100%" height={14} className="mb-2" />
      <Skeleton variant="text" width="100%" height={14} className="mb-2" />
      <Skeleton variant="text" width="80%" height={14} className="mb-4" />
      <div className="flex gap-2">
        <Skeleton variant="rounded" width={100} height={36} />
        <Skeleton variant="rounded" width={120} height={36} />
      </div>
    </div>
  );
}

// Graph Skeleton (for initial load)
export function GraphSkeleton() {
  return (
    <div className="w-full h-full bg-gray-50 flex items-center justify-center animate-pulse">
      <div className="relative">
        {/* Central node */}
        <Skeleton variant="circular" width={60} height={60} className="mb-4" />
        {/* Surrounding nodes */}
        <div className="absolute -top-12 left-1/2 -translate-x-1/2">
          <Skeleton variant="circular" width={40} height={40} />
        </div>
        <div className="absolute -bottom-12 left-1/2 -translate-x-1/2">
          <Skeleton variant="circular" width={40} height={40} />
        </div>
        <div className="absolute top-1/2 -left-16 -translate-y-1/2">
          <Skeleton variant="circular" width={40} height={40} />
        </div>
        <div className="absolute top-1/2 -right-16 -translate-y-1/2">
          <Skeleton variant="circular" width={40} height={40} />
        </div>
      </div>
      <p className="absolute bottom-8 text-gray-400 text-sm">그래프 로딩 중...</p>
    </div>
  );
}

// Table Row Skeleton
export function TableRowSkeleton({ columns = 4 }: { columns?: number }) {
  return (
    <tr className="animate-pulse">
      {Array.from({ length: columns }).map((_, i) => (
        <td key={i} className="px-4 py-3">
          <Skeleton variant="text" width={`${60 + Math.random() * 40}%`} height={16} />
        </td>
      ))}
    </tr>
  );
}
