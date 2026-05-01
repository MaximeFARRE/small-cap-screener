import {
  MutationCache,
  QueryCache,
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import { Toaster, toast } from "sonner";
import { WorkspaceProvider } from "@/context/WorkspaceContext";
import { Workspace } from "@/workspace";

const queryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: (error) => {
      const message = error instanceof Error ? error.message : "Request failed";
      toast.error(message);
    },
  }),
  mutationCache: new MutationCache({
    onError: (error) => {
      const message = error instanceof Error ? error.message : "Request failed";
      toast.error(message);
    },
  }),
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,
      retry: 1,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <WorkspaceProvider>
        <Workspace />
        <Toaster
          position="bottom-right"
          theme="dark"
          richColors
          closeButton
          toastOptions={{
            style: {
              border: "1px solid var(--color-border)",
              background: "var(--color-bg-elevated)",
              color: "var(--color-text-primary)",
              fontFamily: "var(--font-mono)",
            },
          }}
        />
      </WorkspaceProvider>
    </QueryClientProvider>
  );
}
