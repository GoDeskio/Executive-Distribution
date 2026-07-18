import { useState } from "react";
import { MessageSquare, X, Sparkles } from "lucide-react";
import { Chat } from "@/components/Chat";

export function ChatWidget() {
  const [open, setOpen] = useState(false);

  return (
    <div className="fixed bottom-6 right-6 z-[60]">
      {open && (
        <div data-testid="public-chat-panel"
          className="mb-4 w-[calc(100vw-3rem)] sm:w-[380px] h-[540px] max-h-[75vh] bg-[#121214] border border-[#27272A] rounded-lg shadow-2xl overflow-hidden flex flex-col animate-in fade-in slide-in-from-bottom-4">
          <div className="flex items-center justify-between px-4 py-3 border-b border-[#27272A] bg-[#0A0A0B]">
            <div className="flex items-center gap-2">
              <Sparkles size={16} className="text-[#4A7C94]" />
              <span className="font-display text-sm">Executive AI Concierge</span>
            </div>
            <button data-testid="close-chat" onClick={() => setOpen(false)} className="text-[#71717A] hover:text-white"><X size={18} /></button>
          </div>
          <div className="flex-1 overflow-hidden">
            <Chat
              endpoint="/ai/chat"
              scope="public"
              placeholder="Ask about fees, documents, services…"
              suggestions={[
                "Estimate fees to ship 200kg cigars to Miami",
                "What documents do I need to import coffee?",
                "Tell me about your Larimar sourcing",
              ]}
            />
          </div>
        </div>
      )}

      <button data-testid="open-chat" onClick={() => setOpen(!open)}
        className="ml-auto flex items-center gap-2 bg-[#4A7C94] hover:bg-[#5A8CA4] text-white rounded-full pl-4 pr-5 py-3.5 shadow-xl transition-colors">
        {open ? <X size={20} /> : <MessageSquare size={20} />}
        {!open && <span className="text-sm font-medium">Ask AI</span>}
      </button>
    </div>
  );
}
