"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  Bot,
  X,
  Send,
  Sparkles,
  Copy,
  Check,
  Shield,
  Layers,
  ChevronRight,
  Flame,
  AlertTriangle,
} from "lucide-react";
import { api } from "@/lib/api/client";
import { CoPilotResponse } from "@/lib/api/types";

interface Message {
  id: string;
  sender: "user" | "copilot";
  text: string;
  type?: string;
  draftPayload?: Record<string, any>;
  citations?: string[];
  timestamp: string;
}

export function CoPilotDrawer() {
  const [isOpen, setIsOpen] = useState(false);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "msg-welcome",
      sender: "copilot",
      text: "👋 **Aegis Incident Commander AI Co-Pilot** ready. I can draft public status page updates, analyze multi-window error budget burn rates, explain rejected hypotheses, and match SRE runbooks.\n\n*Safety Guard*: I provide analysis and recommendations; all operational actions require authorized human approval.",
      citations: ["Aegis SRE Core"],
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    },
  ]);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    if (typeof messagesEndRef.current?.scrollIntoView === "function") {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  };

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
    }
  }, [messages, isOpen]);

  const handleSend = async (textToSend?: string) => {
    const query = (textToSend || input).trim();
    if (!query || loading) return;

    const userMsg: Message = {
      id: `usr-${Date.now()}`,
      sender: "user",
      text: query,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!textToSend) setInput("");
    setLoading(true);

    try {
      const res: CoPilotResponse = await api.queryCoPilot(query);
      const botMsg: Message = {
        id: `bot-${Date.now()}`,
        sender: "copilot",
        text: res.reply,
        type: res.type,
        draftPayload: res.draft_payload,
        citations: res.citations,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, botMsg]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          id: `bot-err-${Date.now()}`,
          sender: "copilot",
          text: `⚠️ Error querying Incident Commander: ${err.message || "Failed to reach AI service"}`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2500);
  };

  const promptChips = [
    "What is burning our error budget?",
    "Draft customer status update",
    "Explain root cause hypotheses",
    "What runbooks should we run?",
  ];

  return (
    <>
      {/* Floating Toggle Button (Bottom-Right) */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        aria-label="Toggle AI Incident Commander"
        className="fixed bottom-6 right-6 z-40 flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-indigo-600 to-violet-600 text-white rounded-full shadow-lg shadow-indigo-950/50 hover:shadow-indigo-900/80 hover:scale-105 transition-all text-xs font-medium border border-indigo-400/30"
      >
        <Sparkles className="w-4 h-4 text-indigo-200 animate-pulse" />
        <span>SRE Co-Pilot</span>
      </button>

      {/* Slide-over Drawer Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-xs z-50 transition-opacity"
          onClick={() => setIsOpen(false)}
        />
      )}

      {/* Slide-over Drawer Panel */}
      <div
        className={`fixed inset-y-0 right-0 z-50 w-full max-w-lg bg-slate-950 border-l border-slate-800 shadow-2xl flex flex-col transform transition-transform duration-300 ease-in-out ${
          isOpen ? "translate-x-0" : "translate-x-full"
        }`}
      >
        {/* Drawer Header */}
        <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/60">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-indigo-950 border border-indigo-700/60 flex items-center justify-center text-indigo-300">
              <Bot className="w-4 h-4" />
            </div>
            <div>
              <div className="text-sm font-semibold text-slate-100 flex items-center gap-2">
                Incident Commander AI
                <span className="text-[10px] uppercase font-mono px-1.5 py-0.2 rounded bg-indigo-950 text-indigo-400 border border-indigo-800">
                  Online
                </span>
              </div>
              <div className="text-[11px] text-slate-400">Context-Aware Operational SRE Assistant</div>
            </div>
          </div>
          <button
            onClick={() => setIsOpen(false)}
            className="p-1.5 text-slate-400 hover:text-slate-100 hover:bg-slate-800 rounded transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Governance Safety Bar */}
        <div className="px-4 py-1.5 bg-slate-900/40 border-b border-slate-800/80 text-[11px] text-slate-400 flex items-center gap-2">
          <Shield className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
          <span>Zero autonomous writes. Human sign-off enforced for all mutations.</span>
        </div>

        {/* Messages Body */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex flex-col ${msg.sender === "user" ? "items-end" : "items-start"}`}
            >
              <div
                className={`max-w-[92%] rounded-lg p-3 text-xs leading-relaxed ${
                  msg.sender === "user"
                    ? "bg-indigo-600 text-white rounded-br-none"
                    : "bg-slate-900 border border-slate-800 text-slate-200 rounded-bl-none shadow-sm"
                }`}
              >
                <div className="whitespace-pre-wrap space-y-2">{msg.text}</div>

                {/* Draft Status Page Announcement Action */}
                {msg.draftPayload?.status_page_body && (
                  <div className="mt-3 pt-2.5 border-t border-slate-800 flex items-center justify-between">
                    <span className="text-[10px] text-slate-400 font-mono">StatusPage Payload Ready</span>
                    <button
                      onClick={() => handleCopy(msg.draftPayload?.status_page_body, msg.id)}
                      className="inline-flex items-center gap-1.5 px-2 py-1 text-[11px] font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 rounded transition"
                    >
                      {copiedId === msg.id ? (
                        <>
                          <Check className="w-3 h-3 text-emerald-400" /> Copied
                        </>
                      ) : (
                        <>
                          <Copy className="w-3 h-3" /> Copy Announcement
                        </>
                      )}
                    </button>
                  </div>
                )}

                {/* Citations */}
                {msg.citations && msg.citations.length > 0 && (
                  <div className="mt-2.5 pt-2 border-t border-slate-800/60 flex flex-wrap gap-1.5">
                    {msg.citations.map((c, idx) => (
                      <span
                        key={idx}
                        className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-950 text-slate-400 border border-slate-800"
                      >
                        {c}
                      </span>
                    ))}
                  </div>
                )}
              </div>
              <span className="text-[10px] text-slate-500 mt-1 px-1">{msg.timestamp}</span>
            </div>
          ))}

          {loading && (
            <div className="flex items-center gap-2 p-3 bg-slate-900 border border-slate-800 rounded-lg max-w-[70%] text-xs text-slate-400">
              <Sparkles className="w-3.5 h-3.5 text-indigo-400 animate-spin" />
              <span>Analyzing telemetry & incidents...</span>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Quick Suggestion Chips */}
        <div className="px-4 py-2 border-t border-slate-800/80 bg-slate-950 flex flex-wrap gap-1.5">
          {promptChips.map((chip, idx) => (
            <button
              key={idx}
              onClick={() => handleSend(chip)}
              disabled={loading}
              className="text-[11px] px-2.5 py-1 rounded-full bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700 transition"
            >
              {chip}
            </button>
          ))}
        </div>

        {/* Input Bar */}
        <div className="p-3 border-t border-slate-800 bg-slate-900/60">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="flex items-center gap-2"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask Commander (e.g. 'Draft status page update')..."
              className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
            <button
              type="submit"
              disabled={!input.trim() || loading}
              className="p-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-500 disabled:opacity-40 transition"
            >
              <Send className="w-3.5 h-3.5" />
            </button>
          </form>
        </div>
      </div>
    </>
  );
}
