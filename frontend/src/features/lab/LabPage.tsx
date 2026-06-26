import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "../auth/AuthProvider";
import { getLabStatus, startLabRun } from "../../api/client";
import { LabView } from "./LabView";

const ACTIVE_STATUSES = new Set(["queued", "running", "processing"]);

export function LabPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();

  const canRun =
    user?.role === "analyst" || user?.role === "admin";

  const statusQuery = useQuery({
    queryKey: ["lab", "status"],
    queryFn: getLabStatus,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data !== null && data !== undefined && ACTIVE_STATUSES.has(data.status)) {
        return 2_000;
      }
      return false;
    },
    staleTime: 0,
  });

  const runMutation = useMutation({
    mutationFn: startLabRun,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["lab"] });
    },
  });

  const handleRun = (scenario: string) => {
    runMutation.mutate(scenario);
  };

  const handleRetry = () => {
    void statusQuery.refetch();
  };

  const currentStatus = statusQuery.data ?? null;

  const isActive = currentStatus !== null && ACTIVE_STATUSES.has(currentStatus.status);
  const isRunning =
    isActive ||
    runMutation.isPending;

  return (
    <LabView
      status={currentStatus}
      loading={statusQuery.isLoading}
      error={statusQuery.isError}
      canRun={canRun && !isRunning}
      onRun={handleRun}
      onRetry={handleRetry}
    />
  );
}
