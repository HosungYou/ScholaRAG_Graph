import React from 'react';
import { render, screen, act, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ToastProvider, useToast } from '@/components/ui/Toast';

// Helper component that triggers toast
function ToastTrigger({ message, type }: { message: string; type?: 'success' | 'error' | 'warning' | 'info' }) {
  const { showToast } = useToast();
  return (
    <button onClick={() => showToast(message, type)}>
      Show Toast
    </button>
  );
}

describe('Toast', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('renders toast message on trigger', async () => {
    const user = userEvent.setup({ delay: null });
    render(
      <ToastProvider>
        <ToastTrigger message="Test message" type="success" />
      </ToastProvider>
    );

    await user.click(screen.getByText('Show Toast'));
    expect(screen.getByText('Test message')).toBeInTheDocument();
  });

  it('renders with correct role for accessibility', async () => {
    const user = userEvent.setup({ delay: null });
    render(
      <ToastProvider>
        <ToastTrigger message="Alert test" type="error" />
      </ToastProvider>
    );

    await user.click(screen.getByText('Show Toast'));
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('auto-dismisses after duration', async () => {
    render(
      <ToastProvider>
        <ToastTrigger message="Auto dismiss" type="info" />
      </ToastProvider>
    );

    // Trigger toast
    const button = screen.getByText('Show Toast');
    await act(async () => {
      button.click();
    });

    expect(screen.getByText('Auto dismiss')).toBeInTheDocument();

    // Fast-forward past the default 4s duration
    act(() => {
      jest.advanceTimersByTime(5000);
    });

    await waitFor(() => {
      expect(screen.queryByText('Auto dismiss')).not.toBeInTheDocument();
    });
  });

  it('shows success toast with correct styling', async () => {
    const user = userEvent.setup({ delay: null });
    render(
      <ToastProvider>
        <ToastTrigger message="Success!" type="success" />
      </ToastProvider>
    );

    await user.click(screen.getByText('Show Toast'));
    const toast = screen.getByRole('alert');
    expect(toast).toHaveClass('border-l-emerald-500');
  });

  it('shows error toast with correct styling', async () => {
    const user = userEvent.setup({ delay: null });
    render(
      <ToastProvider>
        <ToastTrigger message="Error!" type="error" />
      </ToastProvider>
    );

    await user.click(screen.getByText('Show Toast'));
    const toast = screen.getByRole('alert');
    expect(toast).toHaveClass('border-l-red-500');
  });

  it('shows warning toast with correct styling', async () => {
    const user = userEvent.setup({ delay: null });
    render(
      <ToastProvider>
        <ToastTrigger message="Warning!" type="warning" />
      </ToastProvider>
    );

    await user.click(screen.getByText('Show Toast'));
    const toast = screen.getByRole('alert');
    expect(toast).toHaveClass('border-l-amber-500');
  });

  it('shows info toast with correct styling', async () => {
    const user = userEvent.setup({ delay: null });
    render(
      <ToastProvider>
        <ToastTrigger message="Info!" type="info" />
      </ToastProvider>
    );

    await user.click(screen.getByText('Show Toast'));
    const toast = screen.getByRole('alert');
    expect(toast).toHaveClass('border-l-sky-500');
  });

  it('allows manual dismissal via close button', async () => {
    const user = userEvent.setup({ delay: null });
    render(
      <ToastProvider>
        <ToastTrigger message="Dismissable" type="info" />
      </ToastProvider>
    );

    await user.click(screen.getByText('Show Toast'));
    expect(screen.getByText('Dismissable')).toBeInTheDocument();

    // Find and click the close button (X icon button)
    const closeButtons = screen.getAllByRole('button');
    const closeButton = closeButtons.find(btn => btn.querySelector('.lucide-x'));

    if (closeButton) {
      await user.click(closeButton);
      await waitFor(() => {
        expect(screen.queryByText('Dismissable')).not.toBeInTheDocument();
      });
    }
  });

  it('shows multiple toasts stacked', async () => {
    const user = userEvent.setup({ delay: null });

    function MultiToastTrigger() {
      const { showToast } = useToast();
      return (
        <div>
          <button onClick={() => showToast('First notification', 'success')}>Show First</button>
          <button onClick={() => showToast('Second notification', 'error')}>Show Second</button>
        </div>
      );
    }

    render(
      <ToastProvider>
        <MultiToastTrigger />
      </ToastProvider>
    );

    await user.click(screen.getByText('Show First'));
    await user.click(screen.getByText('Show Second'));

    expect(screen.getByText('First notification')).toBeInTheDocument();
    expect(screen.getByText('Second notification')).toBeInTheDocument();
  });

  it('uses default type when not specified', async () => {
    const user = userEvent.setup({ delay: null });

    function DefaultToast() {
      const { showToast } = useToast();
      return <button onClick={() => showToast('Default')}>Show</button>;
    }

    render(
      <ToastProvider>
        <DefaultToast />
      </ToastProvider>
    );

    await user.click(screen.getByText('Show'));
    const toast = screen.getByRole('alert');
    // Default type is 'info'
    expect(toast).toHaveClass('border-l-sky-500');
  });
});
