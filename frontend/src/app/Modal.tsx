import { useEffect, useRef, type ReactNode } from "react";
import { IconClose } from "./Icons";

/**
 * qf 弹窗（对齐 qf-components.css .modal 与 qf-shell.js 交互语义）：
 * - ESC 关闭 + 遮罩点击关闭 + 焦点圈定（Tab 循环）
 * - 打开时锁定 body 滚动，关闭后恢复焦点到触发元素
 */

export interface ModalProps {
  id: string;
  open: boolean;
  title: string;
  width?: "default" | "wide" | "narrow";
  triggerNote?: string;
  children: ReactNode;
  footer?: ReactNode;
  onClose: () => void;
}

export function Modal({ id, open, title, width = "default", triggerNote, children, footer, onClose }: ModalProps) {
  const boxRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const previous = document.activeElement as HTMLElement | null;
    document.body.style.overflow = "hidden";
    const focusables = () =>
      Array.from(
        boxRef.current?.querySelectorAll<HTMLElement>(
          "button, [href], input, select, textarea, [tabindex]:not([tabindex='-1'])",
        ) ?? [],
      ).filter((el) => !el.hasAttribute("disabled"));
    const timer = setTimeout(() => focusables()[0]?.focus(), 50);
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.stopPropagation();
        onClose();
        return;
      }
      if (event.key !== "Tab") return;
      const list = focusables();
      if (!list.length) return;
      const first = list[0];
      const last = list[list.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      clearTimeout(timer);
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = "";
      previous?.focus?.();
    };
  }, [open, onClose]);

  if (!open) return null;

  const boxClass = width === "wide" ? "modal-box wide" : width === "narrow" ? "modal-box narrow" : "modal-box";

  return (
    <div className="modal open" id={id} role="dialog" aria-modal="true" aria-labelledby={`${id}-title`}>
      <div className="mask" onClick={onClose} />
      <div className={boxClass} ref={boxRef} tabIndex={-1}>
        <div className="modal-head">
          <h3 id={`${id}-title`}>{title}</h3>
          <button className="modal-close" aria-label="关闭" onClick={onClose}>
            <IconClose />
          </button>
        </div>
        <div className="modal-body">
          {triggerNote && <div className="modal-tag">{triggerNote}</div>}
          {children}
        </div>
        {footer && <div className="modal-foot">{footer}</div>}
      </div>
    </div>
  );
}
