import type { ButtonHTMLAttributes, ReactNode } from "react";
import styles from "./Button.module.css";

export type ButtonVariant = "primary" | "secondary" | "text";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  icon?: ReactNode;
};

// A pill control. With an icon and no label it becomes a square icon button, which then needs an aria-label.
export function Button({ variant = "secondary", icon, type = "button", className, children, ...rest }: ButtonProps) {
  const classes = [styles.button, styles[variant], icon && !children ? styles.iconOnly : "", className ?? ""];
  return (
    <button type={type} className={classes.filter(Boolean).join(" ")} {...rest}>
      {icon}
      {children}
    </button>
  );
}
