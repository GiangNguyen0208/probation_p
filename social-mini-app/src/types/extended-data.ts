export interface FacebookExtendedData {
  insights?: Record<string, unknown>;
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
}

export function castFacebookExtended(
  data: Record<string, unknown> | null | undefined,
): FacebookExtendedData | null {
  if (!data) {
    return null;
  }
  return {
    insights: data.insights as Record<string, unknown> | undefined,
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
  return {
    view_count: Number(data.view_count) || undefined,
    sample_video_count: Number(data.sample_video_count) || undefined,
    sample_view_count: Number(data.sample_view_count) || undefined,
    sample_like_count: Number(data.sample_like_count) || undefined,
    sample_comment_count: Number(data.sample_comment_count) || undefined,
    sample_engagement_rate: Number(data.sample_engagement_rate) || undefined,
  };
}
