import { render, screen } from '@testing-library/react';
import {
  Skeleton,
  ProjectCardSkeleton,
  ProjectListSkeleton,
  ChatMessageSkeleton,
  GraphSkeleton,
} from '@/components/ui/Skeleton';

describe('Skeleton', () => {
  describe('Base Skeleton', () => {
    it('should render with default props', () => {
      const { container } = render(<Skeleton />);
      const skeleton = container.firstChild as HTMLElement;

      expect(skeleton).toBeInTheDocument();
      expect(skeleton).toHaveClass('bg-gray-200');
      expect(skeleton).toHaveClass('animate-pulse');
    });

    it('should apply text variant by default', () => {
      const { container } = render(<Skeleton />);
      const skeleton = container.firstChild as HTMLElement;

      expect(skeleton).toHaveClass('rounded');
      expect(skeleton).toHaveClass('h-4');
    });

    it('should apply circular variant', () => {
      const { container } = render(<Skeleton variant="circular" />);
      const skeleton = container.firstChild as HTMLElement;

      expect(skeleton).toHaveClass('rounded-full');
    });

    it('should apply rounded variant', () => {
      const { container } = render(<Skeleton variant="rounded" />);
      const skeleton = container.firstChild as HTMLElement;

      expect(skeleton).toHaveClass('rounded-lg');
    });

    it('should apply custom width and height (number)', () => {
      const { container } = render(<Skeleton width={100} height={50} />);
      const skeleton = container.firstChild as HTMLElement;

      expect(skeleton).toHaveStyle({ width: '100px', height: '50px' });
    });

    it('should apply custom width and height (string)', () => {
      const { container } = render(<Skeleton width="50%" height="2rem" />);
      const skeleton = container.firstChild as HTMLElement;

      expect(skeleton).toHaveStyle({ width: '50%', height: '2rem' });
    });

    it('should apply custom className', () => {
      const { container } = render(<Skeleton className="custom-class" />);
      const skeleton = container.firstChild as HTMLElement;

      expect(skeleton).toHaveClass('custom-class');
    });

    it('should have aria-hidden attribute', () => {
      const { container } = render(<Skeleton />);
      const skeleton = container.firstChild as HTMLElement;

      expect(skeleton).toHaveAttribute('aria-hidden', 'true');
    });

    it('should apply no animation when animation is none', () => {
      const { container } = render(<Skeleton animation="none" />);
      const skeleton = container.firstChild as HTMLElement;

      expect(skeleton).not.toHaveClass('animate-pulse');
      expect(skeleton).not.toHaveClass('animate-shimmer');
    });
  });

  describe('ProjectCardSkeleton', () => {
    it('should render project card skeleton', () => {
      const { container } = render(<ProjectCardSkeleton />);

      expect(container.firstChild).toHaveClass('animate-pulse');
      expect(container.firstChild).toHaveClass('bg-white');
    });
  });

  describe('ProjectListSkeleton', () => {
    it('should render default 6 project cards', () => {
      const { container } = render(<ProjectListSkeleton />);

      const cards = container.querySelectorAll('.animate-pulse');
      expect(cards.length).toBe(6);
    });

    it('should render custom count of project cards', () => {
      const { container } = render(<ProjectListSkeleton count={3} />);

      const cards = container.querySelectorAll('.animate-pulse');
      expect(cards.length).toBe(3);
    });
  });

  describe('ChatMessageSkeleton', () => {
    it('should render assistant message skeleton', () => {
      const { container } = render(<ChatMessageSkeleton />);
      const message = container.firstChild as HTMLElement;

      expect(message).toHaveClass('bg-gray-50');
      expect(message).toHaveClass('mr-12');
    });

    it('should render user message skeleton', () => {
      const { container } = render(<ChatMessageSkeleton isUser />);
      const message = container.firstChild as HTMLElement;

      expect(message).toHaveClass('bg-blue-50');
      expect(message).toHaveClass('ml-12');
    });
  });

  describe('GraphSkeleton', () => {
    it('should render graph loading skeleton', () => {
      render(<GraphSkeleton />);

      expect(screen.getByText('그래프 로딩 중...')).toBeInTheDocument();
    });
  });
});
