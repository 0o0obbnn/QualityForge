import { useEffect, useRef, useState } from "react";
import { useOutletContext } from "react-router-dom";
import {
  appendConversationMessage,
  createConversation,
  fetchConversationMessages,
  fetchConversations,
} from "../services/dataService";
import type { ConversationMessageRow, ConversationRow } from "../types";
import type { Profile } from "../types";
import { IconPlus } from "../app/Icons";
import { Modal } from "../app/Modal";
import { useToast } from "../app/Toast";

/**
 * 协作对话页（WP-03 前端接入，批次六十；QF-PD-052 用户与协调 Agent 对话的首个真实承载面）：
 * 左栏会话列表（最近活跃优先，服务端口径）+ 新建会话；右栏只追加消息流 + 发送。
 * contentRef 策略：PUBLIC/INTERNAL 低敏正文内联；CONFIDENTIAL/RESTRICTED 显示为引用 chip
 * （正文服务端按引用存储，不落明文——与后端 dataClass 语义一致）。
 */

const DATA_CLASSES = [
  "PUBLIC",
  "INTERNAL",
  "CONFIDENTIAL",
  "RESTRICTED",
] as const;

export function ConversationPage() {
  const { profile } = useOutletContext<{ profile: Profile }>();
  const toast = useToast();
  const [conversations, setConversations] = useState<ConversationRow[]>([]);
  const [selectedId, setSelectedId] = useState<string>("");
  const [messages, setMessages] = useState<ConversationMessageRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [threadLoading, setThreadLoading] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [creating, setCreating] = useState(false);
  const [draft, setDraft] = useState("");
  const [dataClass, setDataClass] =
    useState<(typeof DATA_CLASSES)[number]>("INTERNAL");
  const [sending, setSending] = useState(false);
  const threadRef = useRef<HTMLDivElement | null>(null);

  const loadConversations = () => {
    void fetchConversations(profile)
      .then((rows) => {
        setConversations(rows);
        setSelectedId((current) => current || rows[0]?.id || "");
      })
      .catch(() => toast("会话列表加载失败", "err"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    setLoading(true);
    loadConversations();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profile]);

  useEffect(() => {
    if (!selectedId) {
      setMessages([]);
      return;
    }
    setThreadLoading(true);
    void fetchConversationMessages(selectedId)
      .then(setMessages)
      .catch(() => toast("消息加载失败", "err"))
      .finally(() => setThreadLoading(false));
  }, [selectedId, toast]);

  useEffect(() => {
    threadRef.current?.scrollTo?.({ top: threadRef.current.scrollHeight });
  }, [messages]);

  const submitCreate = async () => {
    if (!title.trim()) return;
    setCreating(true);
    try {
      const created = await createConversation(profile, {
        title: title.trim(),
      });
      setCreateOpen(false);
      setTitle("");
      loadConversations();
      setSelectedId(created.id);
      toast("会话已创建", "ok");
    } catch {
      toast("创建失败，请重试", "err");
    } finally {
      setCreating(false);
    }
  };

  const submitSend = async () => {
    const content = draft.trim();
    if (!content || !selectedId) return;
    setSending(true);
    try {
      const appended = await appendConversationMessage(profile, selectedId, {
        content,
        dataClass,
      });
      setDraft("");
      setMessages((list) => [...list, appended]);
      loadConversations();
    } catch {
      toast("发送失败，请重试", "err");
    } finally {
      setSending(false);
    }
  };

  const selected = conversations.find((c) => c.id === selectedId);

  return (
    <section className="page">
      <div
        className="page-head"
        style={{ display: "flex", alignItems: "center", gap: 12 }}
      >
        <h1>协作对话</h1>
        <button className="btn btn-primary" onClick={() => setCreateOpen(true)}>
          <IconPlus /> 新建会话
        </button>
      </div>
      <div
        style={{
          display: "flex",
          gap: 16,
          alignItems: "stretch",
          minHeight: "60dvh",
        }}
      >
        <aside
          className="mini-card"
          style={{ width: 280, flexShrink: 0, padding: 8 }}
        >
          {loading && (
            <div className="row">
              <span className="k">加载中…</span>
            </div>
          )}
          {!loading && conversations.length === 0 && (
            <div className="row">
              <span className="k">暂无会话，点击右上角新建</span>
            </div>
          )}
          {conversations.map((conversation) => (
            <div
              key={conversation.id}
              role="button"
              tabIndex={0}
              className="row"
              style={{
                cursor: "pointer",
                borderRadius: 8,
                padding: "10px 12px",
                background:
                  conversation.id === selectedId
                    ? "var(--qf-accent-100, #f4e8dc)"
                    : "transparent",
                alignItems: "flex-start",
              }}
              onClick={() => setSelectedId(conversation.id)}
              onKeyDown={(event) => {
                if (event.key === "Enter") setSelectedId(conversation.id);
              }}
            >
              <div style={{ flex: 1, minWidth: 0 }}>
                <div
                  style={{
                    fontWeight: 600,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                  }}
                >
                  {conversation.title}
                </div>
                <div className="small muted">
                  最近活跃{" "}
                  {conversation.lastActivityAt.slice(5, 16).replace("T", " ")}
                </div>
              </div>
            </div>
          ))}
        </aside>

        <div
          className="mini-card"
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            padding: 0,
          }}
        >
          <div
            style={{
              padding: "10px 16px",
              borderBottom: "1px solid var(--qf-line-2, #e4ddd2)",
              fontWeight: 600,
            }}
          >
            {selected ? selected.title : "未选择会话"}
          </div>
          <div
            ref={threadRef}
            style={{
              flex: 1,
              overflowY: "auto",
              padding: 16,
              display: "flex",
              flexDirection: "column",
              gap: 12,
            }}
          >
            {threadLoading && <div className="small muted">消息加载中…</div>}
            {!threadLoading && selectedId && messages.length === 0 && (
              <div className="small muted">尚无消息，发送第一条协作消息</div>
            )}
            {messages.map((message) => {
              const isSensitive =
                message.dataClass === "CONFIDENTIAL" ||
                message.dataClass === "RESTRICTED";
              const isRef = isSensitive && message.contentRef.includes("://");
              const mine = message.actorType === "USER";
              return (
                <div
                  key={message.id}
                  style={{
                    alignSelf: mine ? "flex-end" : "flex-start",
                    maxWidth: "76%",
                  }}
                >
                  <div
                    className="small muted"
                    style={{
                      marginBottom: 2,
                      textAlign: mine ? "right" : "left",
                    }}
                  >
                    {message.actorType === "USER"
                      ? "我"
                      : message.actorType === "AGENT"
                        ? "Agent"
                        : "系统"}{" "}
                    · {message.createdAt.slice(11, 16)} · {message.dataClass}
                  </div>
                  <div
                    style={{
                      borderRadius: 10,
                      padding: "8px 12px",
                      background: mine
                        ? "var(--qf-accent-100, #f4e8dc)"
                        : "var(--qf-bg-2, #faf7f2)",
                      border: "1px solid var(--qf-line-2, #e4ddd2)",
                      wordBreak: "break-word",
                    }}
                  >
                    {isRef ? (
                      <span className="chip b-warn" title={message.contentRef}>
                        敏感内容按引用存储 · {message.contentRef.slice(0, 28)}…
                      </span>
                    ) : (
                      message.contentRef
                    )}
                  </div>
                </div>
              );
            })}
          </div>
          <div
            style={{
              padding: 12,
              borderTop: "1px solid var(--qf-line-2, #e4ddd2)",
              display: "flex",
              gap: 8,
            }}
          >
            <input
              type="text"
              aria-label="消息内容"
              placeholder={
                selectedId
                  ? dataClass === "CONFIDENTIAL" || dataClass === "RESTRICTED"
                    ? "输入引用 URI（ref://…）或正文（将转引用）"
                    : "输入协作消息…"
                  : "请先选择会话"
              }
              value={draft}
              disabled={!selectedId || sending}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") void submitSend();
              }}
              style={{ flex: 1 }}
            />
            <select
              aria-label="数据分级"
              value={dataClass}
              onChange={(event) =>
                setDataClass(
                  event.target.value as (typeof DATA_CLASSES)[number],
                )
              }
            >
              {DATA_CLASSES.map((cls) => (
                <option key={cls} value={cls}>
                  {cls}
                </option>
              ))}
            </select>
            <button
              className="btn btn-primary"
              disabled={!selectedId || !draft.trim() || sending}
              onClick={() => void submitSend()}
            >
              发送
            </button>
          </div>
        </div>
      </div>

      <Modal
        id="m-new-conversation"
        open={createOpen}
        title="新建协作会话"
        width="narrow"
        triggerNote="触发入口: 协作对话页右上角"
        onClose={() => setCreateOpen(false)}
        footer={
          <>
            <button
              className="btn btn-ghost"
              onClick={() => setCreateOpen(false)}
            >
              取消
            </button>
            <button
              className="btn btn-primary"
              disabled={!title.trim() || creating}
              onClick={() => void submitCreate()}
            >
              创建
            </button>
          </>
        }
      >
        <label className="small muted" htmlFor="new-conversation-title">
          会话主题
        </label>
        <input
          id="new-conversation-title"
          type="text"
          value={title}
          maxLength={200}
          placeholder="例如：退款策略协作"
          onChange={(event) => setTitle(event.target.value)}
          style={{ width: "100%", marginTop: 6 }}
        />
        <div className="small muted" style={{ marginTop: 10 }}>
          会话归属当前 Release（{profile.releaseName ?? "未选择"}
          ）；敏感正文按引用存储，不入对话明文。
        </div>
      </Modal>
    </section>
  );
}
