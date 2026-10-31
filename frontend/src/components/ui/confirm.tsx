"use client";
import * as AlertDialog from "@radix-ui/react-alert-dialog";
import { Button, buttonVariants } from "./button";
export function Confirm({
  open,
  onOpenChange,
  title,
  description,
  action,
  onConfirm,
  pending,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  action: string;
  onConfirm: () => void;
  pending?: boolean;
}) {
  return (
    <AlertDialog.Root open={open} onOpenChange={onOpenChange}>
      <AlertDialog.Portal>
        <AlertDialog.Overlay className="dialog-overlay" />
        <AlertDialog.Content className="dialog-content confirm-dialog">
          <span className="eyebrow text-amber">CONTROLLED SANDBOX ACTION</span>
          <AlertDialog.Title>{title}</AlertDialog.Title>
          <AlertDialog.Description>{description}</AlertDialog.Description>
          <div className="dialog-actions">
            <AlertDialog.Cancel asChild>
              <Button variant="secondary">Go back</Button>
            </AlertDialog.Cancel>
            <AlertDialog.Action
              className={buttonVariants({ variant: "default" })}
              disabled={pending}
              onClick={onConfirm}
            >
              {pending ? "Submitting…" : action}
            </AlertDialog.Action>
          </div>
        </AlertDialog.Content>
      </AlertDialog.Portal>
    </AlertDialog.Root>
  );
}
