import {
  forwardRef,
  type ButtonHTMLAttributes,
  type ReactNode,
} from "react";
import { Spinner } from "./Spinner";

type Variant = "primary" | "secondary" | "ghost";
type Size = "sm" | "md" | "lg";

export interface ButtonProps
  extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, "loading"> {
  variant?: Variant;
  size?: Size;
  fullWidth?: boolean;
  loading?: boolean;
  children: ReactNode;
}

const sizeStyles: Record<Size, string> = {
  sm: "px-3 py-1.5 text-sm min-h-36",
  md: "px-4 py-2.5 text-sm min-h-44",
  lg: "px-5 py-3 text-base min-h-52",
};

const variantStyles: Record<Variant, string> = {
  primary: "",
  secondary: "",
  ghost: "",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = "primary",
      size = "md",
      fullWidth = false,
      loading = false,
      disabled,
      className = "",
      children,
      ...rest
    },
    ref,
  ) => {
    const bgColor = variant === "secondary"
      ? "var(--tg-secondary-bg-color)"
      : variant === "ghost"
        ? "transparent"
        : "var(--tg-button-color)";
    const txtColor = variant === "primary"
      ? "var(--tg-button-text-color)"
      : "var(--tg-text-color)";
    return (
      <button
        ref={ref}
        className={`inline-flex items-center justify-center gap-2 rounded-xl font-medium transition-colors active:opacity-80 disabled:opacity-40 disabled:cursor-not-allowed ${sizeStyles[size]} ${variantStyles[variant]} ${fullWidth ? "w-full" : ""} ${className}`}
        style={{
          backgroundColor: bgColor,
          color: txtColor,
          border: variant === "ghost" ? "none" : "none",
          cursor: loading || disabled ? "not-allowed" : "pointer",
        }}
        disabled={disabled || loading}
        aria-busy={loading || undefined}
        {...rest}
      >
        {loading && <Spinner size="sm" />}
        {children}
      </button>
    );
  },
);

Button.displayName = "Button";