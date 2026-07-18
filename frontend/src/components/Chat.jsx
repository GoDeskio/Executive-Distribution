import { useEffect, useRef, useState } from "react";
import { Send, Sparkles } from "lucide-react";
import { streamChat } from "@/lib/chat";

function sid() {
  let s = sessionStorage.getItem("ed_chat_sid");
  if (!s) { s = "c_" + Math.random().toString(36).slice(2); sessionStorage.setItem("ed_chat_sid", s); }
  return s;
}

export function Chat({ endpoint, scope = "public", suggestions = [], placeholder = "Ask anything…", compact = false }) {
  const [messages, setMessages] = useState([
    { role: "assistant", content: scope === "admin"
        ? "I'm your operations assistant. Ask me to calculate shipping fees, list required customs documents, or help draft a quote."
        : "Hi! I can estimate shipping fees, tell you which documents you'll need, and answer questions about our services. How can I help?" },
  ]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef();

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const send = async (text) => {
    const msg = (text ?? input).trim();
    if (!msg || busy) return;
    setInput("");
    const history = messages.filter((m) => m.role !== "system").map((m) => ({ role: m.role, content: m.content }));
    setMessages((m) => [...m, { role: "user", content: msg }, { role: "assistant", content: "" }]);
    setBusy(true);
    await streamChat({
      endpoint,
      body: { session_id: sid(), message: msg, history, scope },
      onChunk: (chunk) => setMessages((m) => {
        const copy = [...m];
        copy[copy.length - 1] = { role: "assistant", content: copy[copy.length - 1].content + chunk };
        return copy;
      }),
      onError: () => setMessages((m) => {
        const copy = [...m];
        copy[copy.length - 1] = { role: "assistant", content: "Sorry, I couldn't reach the AI service. Please try again." };
        return copy;
      }),
    });
    setBusy(false);
  };

  return (
    <div className="flex flex-col h-full">
      <div ref={scrollRef} data-testid="chat-messages" className="flex-1 overflow-y-auto space-y-4 p-4">
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[85%] rounded-md px-4 py-3 text-sm leading-relaxed whitespace-pre-line ${
              m.role === "user" ? "bg-[#4A7C94] text-white" : "bg-[#1A1A1D] text-[#E4E4E7] border border-[#27272A]"
            }`}>
              {m.content || (busy && i === messages.length - 1 ? <span className="text-[#71717A]">Thinking…</span> : "")}
            </div>
          </div>
        ))}
        {messages.length <= 1 && suggestions.length > 0 && (
          <div className="flex flex-wrap gap-2 pt-2">
            {suggestions.map((s, i) => (
              <button key={i} data-testid={`chat-suggestion-${i}`} onClick={() => send(s)}
                className="text-xs border border-[#27272A] hover:border-[#4A7C94] text-[#A1A1AA] hover:text-white rounded-full px-3 py-1.5 transition-colors">
                {s}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="border-t border-[#27272A] p-3">
        <div className="flex items-end gap-2">
          <textarea data-testid="chat-input" rows={1} value={input} onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
            placeholder={placeholder}
            className="flex-1 resize-none bg-[#0A0A0B] border border-[#27272A] focus:border-[#4A7C94] outline-none rounded-sm px-3 py-2.5 text-sm max-h-32 transition-colors" />
          <button data-testid="chat-send" onClick={() => send()} disabled={busy}
            className="bg-[#4A7C94] hover:bg-[#5A8CA4] disabled:opacity-50 text-white rounded-sm p-2.5 transition-colors">
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}
