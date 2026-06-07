import { useMemo, useState } from "react";
import { chatRecommendation } from "../api/client.js";

const INITIAL_MESSAGE = {
  role: "assistant",
  content: "告诉我预算、使用场景和最在意的问题，我会先问清楚，再按真实数据生成推荐。",
};

function compactMessages(messages) {
  return messages
    .filter((message) => message.role === "user" || message.role === "assistant")
    .map((message) => ({
      role: message.role,
      content: message.content,
    }))
    .slice(-12);
}

export default function ChatAssistant({ currentFilters, onRecommendationsReady }) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([INITIAL_MESSAGE]);
  const [input, setInput] = useState("");
  const [intentState, setIntentState] = useState({});
  const [quickReplies, setQuickReplies] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const canSend = useMemo(() => input.trim().length > 0 && !loading, [input, loading]);

  async function submitChatMessage(text) {
    if (!text || loading) return;

    const userMessage = { role: "user", content: text };
    const nextMessages = [...messages, userMessage];
    setMessages(nextMessages);
    setInput("");
    setQuickReplies([]);
    setLoading(true);
    setError("");

    try {
      const data = await chatRecommendation({
        messages: compactMessages(nextMessages),
        intent_state: intentState,
        current_filters: currentFilters,
      });
      const assistantMessage = {
        role: "assistant",
        content: data.assistant_message || "我已经收到。",
      };
      setMessages((current) => [...current, assistantMessage]);
      setIntentState(data.intent_state || {});

      if (data.status === "ready" && data.filters && Array.isArray(data.recommendations)) {
        onRecommendationsReady(data.filters, data.recommendations);
      } else if (data.status === "needs_clarification") {
        setQuickReplies(Array.isArray(data.quick_replies) ? data.quick_replies : []);
      }
    } catch (requestError) {
      const message = requestError.message || "聊天接口调用失败";
      setError(message);
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: `这一步没有完成：${message}`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  async function sendMessage(event) {
    event.preventDefault();
    await submitChatMessage(input.trim());
  }

  async function chooseQuickReply(reply) {
    const message = reply?.message || reply?.label || "";
    await submitChatMessage(message.trim());
  }

  function resetChat() {
    setMessages([INITIAL_MESSAGE]);
    setIntentState({});
    setQuickReplies([]);
    setInput("");
    setError("");
  }

  return (
    <aside className={`chat-assistant ${open ? "open" : ""}`} aria-label="AI 选购助手">
      {open && (
        <section className="chat-panel">
          <header className="chat-header">
            <div>
              <strong>AI 选购助手</strong>
              <span>只做需求澄清，结果走真实推荐流程</span>
            </div>
            <button type="button" className="chat-icon-button" onClick={resetChat} aria-label="重置对话">
              ↺
            </button>
          </header>

          <div className="chat-messages" aria-live="polite">
            {messages.map((message, index) => (
              <p key={`${message.role}-${index}`} className={`chat-message ${message.role}`}>
                {message.content}
              </p>
            ))}
            {loading && <p className="chat-message assistant">正在判断需求是否完整...</p>}
          </div>

          {error && <p className="chat-error">{error}</p>}

          {!error && quickReplies.length > 0 && (
            <div className="chat-quick-replies" aria-label="可选回复">
              {quickReplies.map((reply) => (
                <button
                  key={`${reply.label}-${reply.message}`}
                  type="button"
                  className="chat-reply-chip"
                  onClick={() => chooseQuickReply(reply)}
                  disabled={loading}
                >
                  {reply.label}
                </button>
              ))}
            </div>
          )}

          <form className="chat-form" onSubmit={sendMessage}>
            <textarea
              value={input}
              rows="2"
              maxLength="800"
              placeholder="例如：预算 800 内，周末公园露营，怕漏水也想好搭"
              onChange={(event) => setInput(event.target.value)}
            />
            <button type="submit" disabled={!canSend}>
              发送
            </button>
          </form>
        </section>
      )}

      <button type="button" className="chat-toggle" onClick={() => setOpen((value) => !value)} aria-expanded={open}>
        AI
      </button>
    </aside>
  );
}
