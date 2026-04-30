import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster, toast } from "sonner";
import { WorkspaceProvider } from "@/context/WorkspaceContext";
import { Workspace } from "@/workspace";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,
      retry: 1,
      onError: (error) => {
        const message = error instanceof Error ? error.message : "Request failed";
        toast.error(message);
      },
    },
    mutations: {
      onError: (error) => {
        const message = error instanceof Error ? error.message : "Request failed";
        toast.error(message);
      },
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
