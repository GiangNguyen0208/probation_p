export type TranslationKey =
  | "nav.subjects" | "nav.dashboard" | "nav.credentials" | "nav.settings"
  | "settings.title" | "settings.appearance" | "settings.theme" | "settings.colorScheme"
  | "settings.system" | "settings.light" | "settings.dark" | "settings.currentMode"
  | "settings.charts" | "settings.chartStyle" | "settings.defaultChart"
  | "settings.lineChart" | "settings.barChart" | "settings.areaChart"
  | "settings.showGrid" | "settings.showGridDesc" | "settings.compactView" | "settings.compactViewDesc"
  | "settings.about" | "settings.version" | "settings.platform" | "settings.telegramMiniApp"
  | "settings.language" | "settings.selectLanguage" | "settings.english" | "settings.vietnamese"
  | "dashboard.title" | "dashboard.overview" | "dashboard.totalSubjects" | "dashboard.mostActive"
  | "dashboard.facebook" | "dashboard.youtube" | "dashboard.tracked" | "dashboard.lastSync"
  | "dashboard.browseSubjects"
  | "subjects.title" | "subjects.noResults" | "subjects.resetFilters"
  | "subject.metrics" | "subject.followers" | "subject.posts" | "subject.activity" | "subject.lastSync"
  | "subject.alerts" | "subject.syncNow" | "subject.syncing" | "subject.syncScheduled" | "subject.syncFailed"
  | "subject.active" | "subject.inactive" | "subject.suspended"
  | "subject.loading" | "subject.error" | "subject.empty"
  | "credentials.title" | "credentials.createdSuccess" | "credentials.empty" | "credentials.add"
  | "credentials.newTitle" | "credentials.label" | "credentials.create" | "credentials.creating"
  | "credentials.edit" | "credentials.save" | "credentials.cancel"
  | "credentials.revoke" | "credentials.revoking" | "credentials.revokedStatus"
  | "credentials.activeStatus" | "credentials.configuredFields" | "credentials.noFields"
  | "credentials.platform" | "credentials.created" | "credentials.lastVerified"
  | "credentials.placeholderLabel"
  | "common.loading" | "common.error" | "common.retry" | "common.noData" | "common.previous" | "common.next"
  | "filter.all" | "filter.platform" | "filter.status" | "filter.search" | "filter.searchPlaceholder"
  | "activity.followerGrowth" | "activity.frequency"
  | "video.title" | "video.noVideos" | "video.loading" | "video.views" | "video.likes" | "video.comments"
  | "engagement.section" | "engagement.totalReactions" | "engagement.avgReactions"
  | "engagement.commentEngagement" | "engagement.shareEngagement"
  | "engagement.totalViews" | "engagement.avgViews"
  | "engagement.subscribers" | "engagement.avgEngRate"
  | "alert.configTitle" | "alert.historyTitle" | "alert.noRules" | "alert.noLogs"
  | "alert.newRule" | "alert.addRule" | "alert.editRule" | "alert.deleteRule"
  | "alert.ruleType" | "alert.threshold" | "alert.cooldown" | "alert.channel"
  | "alert.followerDrop" | "alert.followerGrowthLabel" | "alert.activityDrop";

export type Translations = Record<TranslationKey, string>;

export const en: Translations = {
  "nav.subjects": "Subjects",
  "nav.dashboard": "Dashboard",
  "nav.credentials": "Credentials",
  "nav.settings": "Settings",

  "settings.title": "Settings",
  "settings.appearance": "Appearance",
  "settings.theme": "Theme",
  "settings.colorScheme": "Color scheme",
  "settings.system": "System (Telegram)",
  "settings.light": "Light",
  "settings.dark": "Dark",
  "settings.currentMode": "Current: {mode} mode",
  "settings.charts": "Charts & Visualization",
  "settings.chartStyle": "Chart Style",
  "settings.defaultChart": "Default chart type",
  "settings.lineChart": "Line Chart",
  "settings.barChart": "Bar Chart",
  "settings.areaChart": "Area Chart",
  "settings.showGrid": "Show grid lines",
  "settings.showGridDesc": "Display background grid in charts",
  "settings.compactView": "Compact view",
  "settings.compactViewDesc": "Smaller charts to fit more data",
  "settings.about": "About",
  "settings.version": "Version",
  "settings.platform": "Platform",
  "settings.telegramMiniApp": "Telegram Mini App",
  "settings.language": "Language",
  "settings.selectLanguage": "Display language",
  "settings.english": "English",
  "settings.vietnamese": "Tiếng Việt",

  "dashboard.title": "Dashboard",
  "dashboard.overview": "Overview",
  "dashboard.totalSubjects": "Total Subjects",
  "dashboard.mostActive": "Most Active",
  "dashboard.facebook": "Facebook",
  "dashboard.youtube": "YouTube",
  "dashboard.tracked": "{count} tracked",
  "dashboard.lastSync": "Last sync: {time}",
  "dashboard.browseSubjects": "Browse Subjects",

  "subjects.title": "Subjects",
  "subjects.noResults": "No subjects found",
  "subjects.resetFilters": "Reset filters",

  "subject.metrics": "Metrics",
  "subject.followers": "Followers",
  "subject.posts": "Posts",
  "subject.activity": "Activity",
  "subject.lastSync": "Last Sync",
  "subject.alerts": "Alerts",
  "subject.syncNow": "Sync Now",
  "subject.syncing": "Syncing...",
  "subject.syncScheduled": "Sync scheduled (task: {taskId}...)",
  "subject.syncFailed": "Failed to trigger sync",
  "subject.active": "Active",
  "subject.inactive": "Inactive",
  "subject.suspended": "Suspended",
  "subject.loading": "Loading subject...",
  "subject.error": "Failed to load subject",
  "subject.empty": "Subject not found",

  "credentials.title": "Credentials",
  "credentials.createdSuccess": "Credential created successfully",
  "credentials.empty": "No credentials yet",
  "credentials.add": "Add Credential",
  "credentials.newTitle": "New Credential",
  "credentials.label": "Label",
  "credentials.create": "Create Credential",
  "credentials.creating": "Creating...",
  "credentials.edit": "Edit",
  "credentials.save": "Save",
  "credentials.cancel": "Cancel",
  "credentials.revoke": "Revoke Credential",
  "credentials.revoking": "Revoking...",
  "credentials.revokedStatus": "Revoked",
  "credentials.activeStatus": "Active",
  "credentials.configuredFields": "Configured Fields",
  "credentials.noFields": "No fields configured",
  "credentials.platform": "Platform: {slug}",
  "credentials.created": "Created {time}",
  "credentials.lastVerified": "Last verified {time}",
  "credentials.placeholderLabel": "e.g. GHN Careers Facebook",

  "common.loading": "Loading...",
  "common.error": "Something went wrong",
  "common.retry": "Retry",
  "common.noData": "No data available",
  "common.previous": "Previous",
  "common.next": "Next",

  "filter.all": "All",
  "filter.platform": "Platform",
  "filter.status": "Status",
  "filter.search": "Search",
  "filter.searchPlaceholder": "Search by name...",

  "activity.followerGrowth": "Follower Growth",
  "activity.frequency": "Activity Frequency",

  "video.title": "Videos",
  "video.noVideos": "No videos tracked yet. Sync the subject to collect video data.",
  "video.loading": "Loading videos...",
  "video.views": "{count} views",
  "video.likes": "{count} likes",
  "video.comments": "{count} comments",

  "engagement.section": "Engagement",
  "engagement.totalReactions": "Total Reactions",
  "engagement.avgReactions": "Avg. Reactions/Post",
  "engagement.commentEngagement": "Comment Engagement",
  "engagement.shareEngagement": "Share Engagement",
  "engagement.totalViews": "Total Views",
  "engagement.avgViews": "Avg. Views/Video",
  "engagement.subscribers": "Subscribers",
  "engagement.avgEngRate": "Avg. Engagement Rate",

  "alert.configTitle": "Alert Rules",
  "alert.historyTitle": "Alert History",
  "alert.noRules": "No alert rules configured",
  "alert.noLogs": "No alert events yet",
  "alert.newRule": "New Rule",
  "alert.addRule": "Add Rule",
  "alert.editRule": "Edit Rule",
  "alert.deleteRule": "Delete Rule",
  "alert.ruleType": "Rule Type",
  "alert.threshold": "Threshold",
  "alert.cooldown": "Cooldown (s)",
  "alert.channel": "Channel ID",
  "alert.followerDrop": "Follower Drop",
  "alert.followerGrowthLabel": "Follower Growth",
  "alert.activityDrop": "Activity Drop",
};

export const vi: Translations = {
  "nav.subjects": "Chủ đề",
  "nav.dashboard": "Tổng quan",
  "nav.credentials": "Xác thực",
  "nav.settings": "Cài đặt",

  "settings.title": "Cài đặt",
  "settings.appearance": "Giao diện",
  "settings.theme": "Chủ đề",
  "settings.colorScheme": "Bảng màu",
  "settings.system": "Hệ thống (Telegram)",
  "settings.light": "Sáng",
  "settings.dark": "Tối",
  "settings.currentMode": "Hiện tại: {mode}",
  "settings.charts": "Biểu đồ & Trực quan",
  "settings.chartStyle": "Kiểu biểu đồ",
  "settings.defaultChart": "Kiểu biểu đồ mặc định",
  "settings.lineChart": "Biểu đồ đường",
  "settings.barChart": "Biểu đồ cột",
  "settings.areaChart": "Biểu đồ vùng",
  "settings.showGrid": "Hiện lưới",
  "settings.showGridDesc": "Hiển thị lưới nền trong biểu đồ",
  "settings.compactView": "Xem gọn",
  "settings.compactViewDesc": "Biểu đồ nhỏ hơn để chứa nhiều dữ liệu",
  "settings.about": "Thông tin",
  "settings.version": "Phiên bản",
  "settings.platform": "Nền tảng",
  "settings.telegramMiniApp": "Telegram Mini App",
  "settings.language": "Ngôn ngữ",
  "settings.selectLanguage": "Ngôn ngữ hiển thị",
  "settings.english": "English",
  "settings.vietnamese": "Tiếng Việt",

  "dashboard.title": "Tổng quan",
  "dashboard.overview": "Tổng quan",
  "dashboard.totalSubjects": "Tổng chủ đề",
  "dashboard.mostActive": "Nhiều nhất",
  "dashboard.facebook": "Facebook",
  "dashboard.youtube": "YouTube",
  "dashboard.tracked": "{count} theo dõi",
  "dashboard.lastSync": "Đồng bộ: {time}",
  "dashboard.browseSubjects": "Xem chủ đề",

  "subjects.title": "Chủ đề",
  "subjects.noResults": "Không tìm thấy chủ đề",
  "subjects.resetFilters": "Đặt lại bộ lọc",

  "subject.metrics": "Chỉ số",
  "subject.followers": "Người theo dõi",
  "subject.posts": "Bài viết",
  "subject.activity": "Hoạt động",
  "subject.lastSync": "Đồng bộ cuối",
  "subject.alerts": "Cảnh báo",
  "subject.syncNow": "Đồng bộ ngay",
  "subject.syncing": "Đang đồng bộ...",
  "subject.syncScheduled": "Đã lên lịch (tác vụ: {taskId}...)",
  "subject.syncFailed": "Đồng bộ thất bại",
  "subject.active": "Hoạt động",
  "subject.inactive": "Không hoạt động",
  "subject.suspended": "Đã đình chỉ",
  "subject.loading": "Đang tải chủ đề...",
  "subject.error": "Không thể tải chủ đề",
  "subject.empty": "Không tìm thấy chủ đề",

  "credentials.title": "Xác thực",
  "credentials.createdSuccess": "Tạo xác thực thành công",
  "credentials.empty": "Chưa có xác thực nào",
  "credentials.add": "Thêm xác thực",
  "credentials.newTitle": "Xác thực mới",
  "credentials.label": "Nhãn",
  "credentials.create": "Tạo xác thực",
  "credentials.creating": "Đang tạo...",
  "credentials.edit": "Sửa",
  "credentials.save": "Lưu",
  "credentials.cancel": "Hủy",
  "credentials.revoke": "Thu hồi xác thực",
  "credentials.revoking": "Đang thu hồi...",
  "credentials.revokedStatus": "Đã thu hồi",
  "credentials.activeStatus": "Hoạt động",
  "credentials.configuredFields": "Trường đã cấu hình",
  "credentials.noFields": "Chưa có trường nào",
  "credentials.platform": "Nền tảng: {slug}",
  "credentials.created": "Tạo {time}",
  "credentials.lastVerified": "Xác minh lần cuối {time}",
  "credentials.placeholderLabel": "VD: GHN Careers Facebook",

  "common.loading": "Đang tải...",
  "common.error": "Đã xảy ra lỗi",
  "common.retry": "Thử lại",
  "common.noData": "Không có dữ liệu",
  "common.previous": "Trước",
  "common.next": "Sau",

  "filter.all": "Tất cả",
  "filter.platform": "Nền tảng",
  "filter.status": "Trạng thái",
  "filter.search": "Tìm kiếm",
  "filter.searchPlaceholder": "Tìm theo tên...",

  "activity.followerGrowth": "Tăng trưởng người theo dõi",
  "activity.frequency": "Tần suất hoạt động",

  "video.title": "Video",
  "video.noVideos": "Chưa có video. Đồng bộ để thu thập dữ liệu video.",
  "video.loading": "Đang tải video...",
  "video.views": "{count} lượt xem",
  "video.likes": "{count} lượt thích",
  "video.comments": "{count} bình luận",

  "engagement.section": "Tương tác",
  "engagement.totalReactions": "Tổng tương tác",
  "engagement.avgReactions": "TB tương tác/Bài",
  "engagement.commentEngagement": "Tương tác bình luận",
  "engagement.shareEngagement": "Tương tác chia sẻ",
  "engagement.totalViews": "Tổng lượt xem",
  "engagement.avgViews": "TB lượt xem/Video",
  "engagement.subscribers": "Người đăng ký",
  "engagement.avgEngRate": "TB tỷ lệ tương tác",

  "alert.configTitle": "Quy tắc cảnh báo",
  "alert.historyTitle": "Lịch sử cảnh báo",
  "alert.noRules": "Chưa có quy tắc cảnh báo nào",
  "alert.noLogs": "Chưa có sự kiện cảnh báo nào",
  "alert.newRule": "Quy tắc mới",
  "alert.addRule": "Thêm quy tắc",
  "alert.editRule": "Sửa quy tắc",
  "alert.deleteRule": "Xóa quy tắc",
  "alert.ruleType": "Loại quy tắc",
  "alert.threshold": "Ngưỡng",
  "alert.cooldown": "Thời gian chờ (giây)",
  "alert.channel": "Kênh ID",
  "alert.followerDrop": "Tụt người theo dõi",
  "alert.followerGrowthLabel": "Tăng người theo dõi",
  "alert.activityDrop": "Sụt giảm hoạt động",
};
