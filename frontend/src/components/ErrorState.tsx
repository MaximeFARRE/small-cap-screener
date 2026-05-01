import { Button } from "@/components/ui/button";

interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
}

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div className="flex h-full w-full items-center justify-center p-4">
      <div className="max-w-xl space-y-3 rounded-sm border border-[var(--color-negative)]/35 bg-[var(--color-negative)]/10 p-4">
        <p className="font-mono text-sm text-[var(--color-negative)]">{message}</p>
        {onRetry ? (
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="font-mono text-xs"
            onClick={onRetry}
          >
            Retry
          </Button>
        ) : null}
      </div>
    </div>
  );
}
