import { forwardRef, type InputHTMLAttributes } from "react";

export interface InputProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, "onChange"> {
  label?: string;
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, className = "", style, ...rest }, ref) => {
    return (
      <label className="flex flex-col gap-1">
        {label && (
          <span
            className="text-xs font-medium"
            style={{ color: "var(--tg-hint-color)" }}
          >
            {label}
          </span>
        )}
        <input
          ref={ref}
          className={`rounded-xl px-3 py-2.5 text-sm outline-none ${className}`}
          style={{
            backgroundColor: "var(--tg-section-bg-color)",
            color: "var(--tg-text-color)",
            border: "1px solid var(--tg-section-separator-color, transparent)",
            minHeight: 44,
            ...style,
          }}
          {...rest}
        />
      </label>
    );
  },
);

Input.displayName = "Input";