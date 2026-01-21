import { render, screen, fireEvent } from '@testing-library/react';
import { ErrorDisplay } from '@/components/ui/ErrorDisplay';

describe('ErrorDisplay', () => {
  describe('Error Type Detection', () => {
    it('should detect network error', () => {
      render(<ErrorDisplay error="fetch failed" />);
      expect(screen.getByText(/네트워크 오류|fetch failed/)).toBeInTheDocument();
    });

    it('should detect server error', () => {
      render(<ErrorDisplay error="500 Internal Server Error" />);
      expect(screen.getByText(/500/)).toBeInTheDocument();
    });

    it('should detect not found error', () => {
      render(<ErrorDisplay error="404 not found" />);
      expect(screen.getByText(/404 not found/)).toBeInTheDocument();
    });

    it('should use generic error for unknown types', () => {
      render(<ErrorDisplay error="Something went wrong" />);
      expect(screen.getByText(/Something went wrong/)).toBeInTheDocument();
    });
  });

  describe('Custom Title and Message', () => {
    it('should display custom title', () => {
      render(<ErrorDisplay title="Custom Error Title" />);
      expect(screen.getByText('Custom Error Title')).toBeInTheDocument();
    });

    it('should display custom message', () => {
      render(<ErrorDisplay message="Custom error message" />);
      expect(screen.getByText('Custom error message')).toBeInTheDocument();
    });

    it('should override error message with custom message', () => {
      render(<ErrorDisplay error="Original error" message="Custom message" />);
      expect(screen.getByText('Custom message')).toBeInTheDocument();
      expect(screen.queryByText('Original error')).not.toBeInTheDocument();
    });
  });

  describe('Retry Functionality', () => {
    it('should render retry button when onRetry is provided', () => {
      const onRetry = jest.fn();
      render(<ErrorDisplay onRetry={onRetry} />);
      expect(screen.getByRole('button', { name: /다시 시도/i })).toBeInTheDocument();
    });

    it('should call onRetry when retry button is clicked', () => {
      const onRetry = jest.fn();
      render(<ErrorDisplay onRetry={onRetry} />);

      fireEvent.click(screen.getByRole('button', { name: /다시 시도/i }));
      expect(onRetry).toHaveBeenCalledTimes(1);
    });

    it('should not render retry button when onRetry is not provided', () => {
      render(<ErrorDisplay />);
      expect(screen.queryByRole('button')).not.toBeInTheDocument();
    });
  });

  describe('Compact Mode', () => {
    it('should render compact variant', () => {
      render(<ErrorDisplay compact error="Test error" />);
      // In compact mode, there's no h3 title, just a message in p tag
      expect(screen.getByText(/Test error/)).toBeInTheDocument();
    });

    it('should render retry icon button in compact mode', () => {
      const onRetry = jest.fn();
      render(<ErrorDisplay compact onRetry={onRetry} />);

      const retryButton = screen.getByRole('button', { name: /다시 시도/i });
      expect(retryButton).toBeInTheDocument();

      fireEvent.click(retryButton);
      expect(onRetry).toHaveBeenCalledTimes(1);
    });
  });

  describe('Error Types', () => {
    it('should accept explicit type prop', () => {
      render(<ErrorDisplay type="server" />);
      expect(screen.getByText('서버 오류')).toBeInTheDocument();
    });

    it('should accept type "notFound"', () => {
      render(<ErrorDisplay type="notFound" />);
      expect(screen.getByText('찾을 수 없음')).toBeInTheDocument();
    });
  });
});
