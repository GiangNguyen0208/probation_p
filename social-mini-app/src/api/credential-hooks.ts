import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { adminDelete, adminGet, adminPost, adminPut } from "./admin-client";
import type { Credential, CredentialDetail, Platform } from "./admin-types";

export function usePlatforms(activeOnly = true) {
  return useQuery({
    queryKey: ["admin", "platforms", { activeOnly }],
    queryFn: () => adminGet<Platform[]>("/v1/admin/platforms", { active_only: activeOnly }),
    staleTime: 300_000,
  });
}

export function usePlatform(platformId: string) {
  return useQuery({
    queryKey: ["admin", "platform", platformId],
    queryFn: () => adminGet<Platform>(`/v1/admin/platforms/${platformId}`),
    enabled: !!platformId,
  });
}

export function useCredentials(platformId?: string) {
  return useQuery({
    queryKey: ["admin", "credentials", { platformId }],
    queryFn: () => {
      const params = platformId ? { platform_id: platformId } : undefined;
      return adminGet<Credential[]>("/v1/admin/credentials", params);
    },
    placeholderData: keepPreviousData,
    staleTime: 60_000,
  });
}

export function useCredential(credentialId: string) {
  return useQuery({
    queryKey: ["admin", "credential", credentialId],
    queryFn: () => adminGet<CredentialDetail>(`/v1/admin/credentials/${credentialId}`),
    enabled: !!credentialId,
  });
}

export function useCreateCredential() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { platform_slug: string; label: string; credentials: Record<string, string> }) =>
      adminPost<Credential>("/v1/admin/credentials", body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "credentials"] });
      qc.invalidateQueries({ queryKey: ["subjects"] });
    },
  });
}

export function useUpdateCredential() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ credentialId, body }: { credentialId: string; body: Record<string, unknown> }) =>
      adminPut<Credential>(`/v1/admin/credentials/${credentialId}`, body),
    onSuccess: (_data, { credentialId }) => {
      qc.invalidateQueries({ queryKey: ["admin", "credential", credentialId] });
      qc.invalidateQueries({ queryKey: ["admin", "credentials"] });
    },
  });
}

export function useRevokeCredential() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (credentialId: string) => adminDelete(`/v1/admin/credentials/${credentialId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "credentials"] });
      qc.invalidateQueries({ queryKey: ["subjects"] });
    },
  });
}
