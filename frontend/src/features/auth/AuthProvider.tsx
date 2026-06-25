import {
  createContext,
  useContext,
  type PropsWithChildren,
} from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type {
  LoginRequestWritable,
  UserResponse,
} from "../../api/generated/types.gen";
import {
  ApiError,
  getCurrentUser,
  login,
  logout,
} from "../../api/client";

type AuthContextValue = {
  user: UserResponse | null;
  isLoading: boolean;
  login: (credentials: LoginRequestWritable) => Promise<UserResponse>;
  logout: () => Promise<void>;
  loginPending: boolean;
  loginError: boolean;
};

const AuthContext = createContext<AuthContextValue | null>(null);
const authKey = ["auth", "me"] as const;

export function AuthProvider({ children }: PropsWithChildren) {
  const queryClient = useQueryClient();
  const userQuery = useQuery({
    queryKey: authKey,
    queryFn: getCurrentUser,
    retry: (count, error) =>
      error instanceof ApiError && error.status === 401 ? false : count < 1,
  });
  const loginMutation = useMutation({
    mutationFn: login,
    onSuccess: (user) => queryClient.setQueryData(authKey, user),
  });
  const logoutMutation = useMutation({
    mutationFn: logout,
    onSettled: () => {
      queryClient.setQueryData(authKey, null);
      queryClient.removeQueries({ queryKey: ["analytics"] });
    },
  });

  return (
    <AuthContext.Provider
      value={{
        user: userQuery.data ?? null,
        isLoading: userQuery.isLoading,
        login: loginMutation.mutateAsync,
        logout: logoutMutation.mutateAsync,
        loginPending: loginMutation.isPending,
        loginError: loginMutation.isError,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("AuthProvider is missing");
  }
  return context;
}
