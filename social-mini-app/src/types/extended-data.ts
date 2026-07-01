export interface InsightMetricValue {
  value: number;
  end_time: string;
}

export interface InsightMetric {
  name: string;
  title: string;
  period?: string;
  values: InsightMetricValue[];
}

export interface FacebookExtendedData {
  insights?: Record<string, InsightMetric>;
  photos?: Record<string, unknown>[];
  videos?: Record<string, unknown>[];
  talking_about_count?: number;
  overall_star_rating?: number;
  rating_count?: number;
  verification_status?: string;
  category?: string;
  category_list?: string[];
  checkins?: number;
  about?: string;
  website?: string;
  username?: string;
  link?: string;
  phone?: string;
  cover?: Record<string, unknown>;
}

export interface YouTubeExtendedData {
  view_count?: number;
  sample_video_count?: number;
  sample_view_count?: number;
  sample_like_count?: number;
  sample_comment_count?: number;
  sample_engagement_rate?: number;
  analytics?: InsightMetric[];
}

export function castFacebookExtended(
  data: Record<string, unknown> | null | undefined,
): FacebookExtendedData | null {
  if (!data) {
    return null;
  }
  const insightsRaw = data.insights;
  let insights: Record<string, InsightMetric> | undefined;
  if (insightsRaw && typeof insightsRaw === "object" && !Array.isArray(insightsRaw)) {
    insights = insightsRaw as Record<string, InsightMetric>;
  }
  return {
    insights,
    photos: data.photos as Record<string, unknown>[] | undefined,
    videos: data.videos as Record<string, unknown>[] | undefined,
    talking_about_count: Number(data.talking_about_count) || undefined,
    overall_star_rating: Number(data.overall_star_rating) || undefined,
    rating_count: Number(data.rating_count) || undefined,
    verification_status: String(data.verification_status) || undefined,
    category: String(data.category) || undefined,
    category_list: data.category_list as string[] | undefined,
    checkins: Number(data.checkins) || undefined,
    about: String(data.about) || undefined,
    website: String(data.website) || undefined,
    username: String(data.username) || undefined,
    link: String(data.link) || undefined,
    phone: String(data.phone) || undefined,
    cover: data.cover as Record<string, unknown> | undefined,
  };
}

export function castYouTubeExtended(
  data: Record<string, unknown> | null | undefined,
): YouTubeExtendedData | null {
  if (!data) {
    return null;
  }
  const analyticsRaw = data.analytics;
  let analytics: InsightMetric[] | undefined;
  if (Array.isArray(analyticsRaw)) {
    analytics = analyticsRaw as InsightMetric[];
  }
  return {
    view_count: Number(data.view_count) || undefined,
    sample_video_count: Number(data.sample_video_count) || undefined,
    sample_view_count: Number(data.sample_view_count) || undefined,
    sample_like_count: Number(data.sample_like_count) || undefined,
    sample_comment_count: Number(data.sample_comment_count) || undefined,
    sample_engagement_rate: Number(data.sample_engagement_rate) || undefined,
    analytics,
  };
}

export interface TikTokExtendedData {
  following_count?: number;
  likes_count?: number;
  video_count?: number;
  is_verified?: boolean;
  avatar_url?: string;
  display_name?: string;
  username?: string;
}

export function castTikTokExtended(
  data: Record<string, unknown> | null | undefined,
): TikTokExtendedData | null {
  if (!data) {
    return null;
  }
  return {
    following_count: Number(data.following_count) || undefined,
    likes_count: Number(data.likes_count) || undefined,
    video_count: Number(data.video_count) || undefined,
    is_verified: Boolean(data.is_verified) || undefined,
    avatar_url: String(data.avatar_url) || undefined,
    display_name: String(data.display_name) || undefined,
    username: String(data.username) || undefined,
  };
}

export function getMetricLatestValue(metric?: InsightMetric): number | null {
  if (!metric || !metric.values || metric.values.length === 0) {
    return null;
  }
  const last = metric.values[metric.values.length - 1];
  if (last.value === null || last.value === undefined) {
    return null;
  }
  if (typeof last.value === "number") {
    return last.value;
  }
  if (typeof last.value === "object") {
    const vals = Object.values(last.value as Record<string, unknown>) as unknown[];
    const sum = vals.reduce<number>((s, v) => s + (Number(v) || 0), 0);
    return sum || null;
  }
  return null;
}

function _resolveValue(value: unknown): number {
  if (value === null || value === undefined) {
    return 0;
  }
  if (typeof value === "number") {
    return value;
  }
  if (typeof value === "object") {
    const vals = Object.values(value as Record<string, unknown>) as unknown[];
    return vals.reduce<number>((s, v) => s + (Number(v) || 0), 0);
  }
  return Number(value) || 0;
}

export function getMetricSparklineData(metric?: InsightMetric): number[] {
  if (!metric || !metric.values) {
    return [];
  }
  return metric.values.map((v) => _resolveValue(v.value));
}
