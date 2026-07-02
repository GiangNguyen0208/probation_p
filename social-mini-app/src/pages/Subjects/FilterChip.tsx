interface FilterChipProps {
  label: string;
  isActive: boolean;
  onClick: () => void;
}

export const FilterChip = ({ label, isActive, onClick }: FilterChipProps) => (
  <button
    className="rounded-full px-4 py-1.5 text-xs font-medium whitespace-nowrap shrink-0"
    style={{
      backgroundColor: isActive ? "var(--si-accent)" : "var(--si-surface-elevated)",
      color: isActive ? "var(--si-on-accent)" : "var(--si-text-secondary)",
    }}
    onClick={onClick}
  >
    {label}
  </button>
);