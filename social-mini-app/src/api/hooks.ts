import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { components } from "./types";
import { apiDelete, apiGet, apiGetPaginated, apiPost, apiPut } from "./client";

type Subject = components["schemas"]["Subject"];
type ActivitySnapshot = components["schemas"]["ActivitySnapshot"];
type Video = components["schemas"]["Video"];

export interface SubjectFilters {
  platform?: string | null;
  status?: string | null;
  q?: string | null;
}

const SUBJECTS_PAGE_SIZE = 20;

export function useInfiniteSubjects(filters: SubjectFilters) {
  return useInfiniteQuery({
    queryKey: ["subjects-infinite", filters],
    queryFn: ({ pageParam }) =>
      apiGetPaginated<Subject[]>("/v1/subjects", {
        ...filters,
        page: pageParam,
        limit: SUBJECTS_PAGE_SIZE,
      }),
    initialPageParam: 1,
    getNextPageParam: (lastPage, _allPages, lastPageParam) => {
      const fetched = lastPageParam * SUBJECTS_PAGE_SIZE;
      return fetched < lastPage.total ? lastPageParam + 1 : undefined;
    },
    staleTime: 60_000,
  });
}

export function useSubject(subjectId: string) {
  return useQuery({
    queryKey: ["subject", subjectId],
    queryFn: () => apiGet<Subject>(`/v1/subjects/${subjectId}`),
    enabled: !!subjectId,
  });
}

export function useActivity(subjectId: string) {
  return useQuery({
    queryKey: ["activity", subjectId],
    queryFn: () => apiGet<ActivitySnapshot[]>(`/v1/subjects/${subjectId}/activity`),
    enabled: !!subjectId,
    staleTime: 60_000,
  });
}

export function useVideos(subjectId: string) {
  return useQuery({
    queryKey: ["videos", subjectId],
    queryFn: () => apiGet<Video[]>(`/v1/subjects/${subjectId}/videos`),
    enabled: !!subjectId,
    staleTime: 60_000,
  });
}

export function useTriggerSync() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (subjectId: string) => apiPost<{ status: string; task_id: string }>(`/v1/subjects/${subjectId}/sync`),
    onSuccess: (_data, subjectId) => {
      setTimeout(() => {
        qc.invalidateQueries({ queryKey: ["subject", subjectId] });
        qc.invalidateQueries({ queryKey: ["activity", subjectId] });
      }, 5000);
    },
  });
}

type AlertRule = components["schemas"]["AlertRule"];

export function useAlerts(subjectId: string) {
  return useQuery({
    queryKey: ["alerts", subjectId],
    queryFn: () => apiGet<AlertRule[]>(`/v1/subjects/${subjectId}/alerts`),
    enabled: !!subjectId,
  });
}

export function useCreateAlert(subjectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: components["schemas"]["AlertRuleCreate"]) =>
      apiPost<AlertRule>(`/v1/subjects/${subjectId}/alerts`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["alerts", subjectId] });
    },
  });
}

export function useUpdateAlert(subjectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ ruleId, body }: { ruleId: string; body: components["schemas"]["AlertRuleUpdate"] }) =>
      apiPut<AlertRule>(`/v1/alerts/${ruleId}`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["alerts", subjectId] });
    },
  });
}

export function useDeleteAlert(subjectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (ruleId: string) => apiDelete(`/v1/alerts/${ruleId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["alerts", subjectId] });
    },
  });
}

export interface DashboardStats {
  totalSubjects: number;
  facebookCount: number;
  youtubeCount: number;
  tiktokCount: number;
  mostActivePlatform: string;
  lastSyncTimestamp: string | null;
}

export function useAlertLogs(subjectId: string) {
  return useQuery({
    queryKey: ["alert-logs", subjectId],
    queryFn: () => apiGet<components["schemas"]["AlertLog"][]>(`/v1/subjects/${subjectId}/alerts/logs`),
    enabled: !!subjectId,
  });
}

export function useDashboardStats() {
  return useQuery({
    queryKey: ["dashboard"],
    queryFn: async (): Promise<DashboardStats> => {
      const PAGE_SIZE = 100;
      let allSubjects: Subject[] = [];
      let page = 1;
      let hasMore = true;
      while (hasMore) {
        const batch = await apiGet<Subject[]>("/v1/subjects", { page, limit: PAGE_SIZE });
        allSubjects = allSubjects.concat(batch);
        hasMore = batch.length === PAGE_SIZE;
        page++;
      }
      const facebook = allSubjects.filter((s) => s.platform === "facebook");
      const youtube = allSubjects.filter((s) => s.platform === "youtube");
      const tiktok = allSubjects.filter((s) => s.platform === "tiktok");
      const fbFreq = facebook.reduce((sum, s) => sum + s.activity_frequency, 0);
      const ytFreq = youtube.reduce((sum, s) => sum + s.activity_frequency, 0);
      const ttFreq = tiktok.reduce((sum, s) => sum + s.activity_frequency, 0);
      const lastSync = allSubjects.reduce(
        (latest, s) => (!latest || s.last_synced_at > latest ? s.last_synced_at : latest),
        "" as string,
      );
      const maxFreq = Math.max(fbFreq, ytFreq, ttFreq);
      return {
        totalSubjects: allSubjects.length,
        facebookCount: facebook.length,
        youtubeCount: youtube.length,
        tiktokCount: tiktok.length,
        mostActivePlatform: maxFreq === fbFreq ? "facebook" : maxFreq === ytFreq ? "youtube" : "tiktok",
        lastSyncTimestamp: lastSync || null,
      };
    },
    staleTime: 60_000,
  });
}
