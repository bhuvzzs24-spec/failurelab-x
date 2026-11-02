"use client";
import { useAccess } from "../access";
import { cn } from "@/lib/utils";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";
export const buttonVariants = cva("button", {
  variants: {
    variant: {
      default: "button-primary",
      secondary: "button-secondary",
      ghost: "button-ghost",
      destructive: "button-danger",
    },
    size: { default: "", sm: "button-sm", icon: "button-icon" },
  },
  defaultVariants: { variant: "default", size: "default" },
});
export function Button({
  className,
  variant,
  size,
  asChild = false,
  control,
  disabled,
  ...props
}: React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & { asChild?: boolean; control?: "execute" | "manage" }) {
  const access = useAccess();
  const blocked =
    control === "execute" ? !access.can_execute : control === "manage" ? !access.can_manage : false;
  if (control && access.recorded_demo) return null;
  const Comp = asChild ? Slot : "button";
  return (
    <Comp
      disabled={disabled || blocked}
      title={blocked ? "This role cannot perform this control action" : props.title}
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    />
  );
}
