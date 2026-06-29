import type { components } from "../api/types";

export type Subject = components["schemas"]["Subject"];

export const platformLabels: Record<string, string> = {
  facebook: "Facebook",
  youtube: "YouTube",
};

export const platformColors: Record<string, string> = {
  facebook: "#1877f2",
  youtube: "#ff0000",
};

export const statusConfig: Record<
  string,
  { variant: "success" | "warning" | "danger"; label: string }
> = {
  active: { variant: "success", label: "Active" },
  inactive: { variant: "warning", label: "Inactive" },
  suspended: { variant: "danger", label: "Suspended" },
};
