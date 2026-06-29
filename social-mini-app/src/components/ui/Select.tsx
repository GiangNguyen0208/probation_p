import { forwardRef, type SelectHTMLAttributes } from "react";

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectProps
  extends Omit<SelectHTMLAttributes<HTMLSelectElement>, "onChange"> {
  id?: string;
  label?: string;
  options: SelectOption[];
  onChange?: (e: React.ChangeEvent<HTMLSelectElement>) => void;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  (
    { id, label, options, className = "", style, ...rest },
    ref,
  ) => {
    return (
      <label className="flex flex-col gap-1" htmlFor={id}>
        {label && (
          <span
            className="text-xs font-medium"
            style={{ color: "var(--tg-hint-color)" }}
          >
            {label}
          </span>
        )}
        <select
          ref={ref}
          id={id}
          className={`rounded-xl px-3 py-2.5 text-sm outline-none appearance-none ${className}`}
          style={{
            backgroundColor: "var(--tg-section-bg-color)",
            color: "var(--tg-text-color)",
            border: "1px solid var(--tg-section-separator-color, transparent)",
            minHeight: 44,
            backgroundImage:
              "url(\"data:image/svg+xml,%3Csvg width='10' height='6' viewBox='0 0 10 6' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M1 1L5 5L9 1' stroke='%23999' stroke-width='1.5' strokeLinecap='round' strokeLinejoin='round'/%3E%3C/svg%3E\")",
            backgroundRepeat: "no-repeat",
            backgroundPosition: "right 12px center",
            paddingRight: 32,
            ...style,
          }}
          {...rest}
        >
          {options.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </label>
    );
  },
);

Select.displayName = "Select";