import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from "react";

/**
 * qf toast（对齐 qf-components.css .toast-wrap/.toast 与 qf-shell.js 语义：
 * 右上角堆叠，3 秒自动消失，ok/err/info 三种圆点语义色）。
 */

type ToastType = "ok" | "err" | "info";

interface ToastItem {
  id: number;
  type: ToastType;
  message: string;
}

const ToastContext = createContext<(message: string, type?: ToastType) => void>(() => {});

export function useToast() {
  return useContext(ToastContext);
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const nextId = useRef(1);

  const push = useCallback((message: string, type: ToastType = "info") => {
    const id = nextId.current++;
    setItems((list) => [...list, { id, type, message }]);
    setTimeout(() => setItems((list) => list.filter((item) => item.id !== id)), 3000);
  }, []);

  return (
    <ToastContext.Provider value={push}>
      {children}
      <div className="toast-wrap" aria-live="polite">
        {items.map((item) => (
          <div key={item.id} className={`toast ${item.type}`}>
            <span className="t-dot" />
            {item.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
