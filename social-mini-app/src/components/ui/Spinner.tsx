export function Spinner({ size = "md" }: { size?: "sm" | "md" | "lg" }) {
  const dim = size === "sm" ? 20 : size === "lg" ? 36 : 28;
  return (
    <div
      className="animate-spin rounded-full"
      style={{
        width: dim,
        height: dim,
        borderWidth: 2,
        borderStyle: "solid",
        borderColor: "var(--tg-hint-color)",
        borderTopColor: "transparent",
      }}
      role="status"
      aria-label="Loading"
    />
  );
}