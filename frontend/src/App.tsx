import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { WorkspaceProvider } from "@/context/WorkspaceContext";

const queryClient = new QueryClient({
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
        {/* Workspace shell implemented in Phase 2 */}
        <div className="flex h-full items-center justify-center bg-[#0a0a0f] text-[#e2e8f0] font-mono text-sm">
          <div className="text-center space-y-2">
            <p className="text-[#3b82f6] text-lg font-semibold">
              Small Cap Analysis Terminal
            </p>
            <p className="text-[#64748b]">Phase 0 — Foundation ready</p>
          </div>
        </div>
      </WorkspaceProvider>
    </QueryClientProvider>
  );
}
