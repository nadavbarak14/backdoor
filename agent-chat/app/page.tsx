"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Send, Activity, TrendingUp, Users, Zap } from "lucide-react";
import { useState, useRef, useEffect } from "react";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

const quickPrompts = [
  { icon: TrendingUp, label: "Top Scorers", prompt: "Who are the top scorers this season?" },
  { icon: Users, label: "Team Stats", prompt: "Show me team comparison stats" },
  { icon: Activity, label: "Live Games", prompt: "What games are happening today?" },
  { icon: Zap, label: "Hot Streaks", prompt: "Which players are on hot streaks?" },
];

export default function ChatPage() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsTyping(true);

    // Simulate AI response (will be replaced with actual API call)
    setTimeout(() => {
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "I'm ready to analyze basketball data for you. This feature will be fully connected in the next update.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, aiMessage]);
      setIsTyping(false);
    }, 1500);
  };

  const handleQuickPrompt = (prompt: string) => {
    setInput(prompt);
  };

  return (
    <div className="chat-container">
      {/* Animated Background */}
      <div className="court-background">
        <div className="court-lines">
          <div className="center-circle" />
          <div className="three-point-line left" />
          <div className="three-point-line right" />
          <div className="half-court-line" />
        </div>
        <div className="ambient-glow" />
        <div className="noise-overlay" />
      </div>

      {/* Header */}
      <header className="chat-header">
        <div className="logo-section">
          <div className="logo-icon">
            <svg viewBox="0 0 40 40" className="basketball-icon">
              <circle cx="20" cy="20" r="18" className="ball-outline" />
              <path d="M2 20 Q20 15 38 20" className="ball-seam" />
              <path d="M2 20 Q20 25 38 20" className="ball-seam" />
              <path d="M20 2 Q15 20 20 38" className="ball-seam" />
              <path d="M20 2 Q25 20 20 38" className="ball-seam" />
            </svg>
          </div>
          <div className="logo-text">
            <h1>BACKDOOR</h1>
            <span className="logo-subtitle">AI ANALYTICS</span>
          </div>
        </div>
        <div className="live-indicator">
          <span className="pulse-dot" />
          <span>LIVE DATA</span>
        </div>
      </header>

      {/* Main Chat Area */}
      <main className="chat-main">
        {messages.length === 0 ? (
          <div className="welcome-state">
            <div className="welcome-content">
              <div className="stats-graphic">
                <div className="stat-bar" style={{ height: "60%" }} />
                <div className="stat-bar" style={{ height: "85%" }} />
                <div className="stat-bar" style={{ height: "45%" }} />
                <div className="stat-bar" style={{ height: "95%" }} />
                <div className="stat-bar" style={{ height: "70%" }} />
              </div>
              <h2>READY TO ANALYZE</h2>
              <p>Ask me anything about basketball stats, player performance, team analytics, and game predictions.</p>

              <div className="quick-prompts">
                {quickPrompts.map((item, index) => (
                  <button
                    key={index}
                    className="quick-prompt-btn"
                    onClick={() => handleQuickPrompt(item.prompt)}
                    style={{ animationDelay: `${index * 0.1}s` }}
                  >
                    <item.icon className="prompt-icon" />
                    <span>{item.label}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="messages-container">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`message ${message.role}`}
              >
                {message.role === "assistant" && (
                  <div className="message-avatar">
                    <svg viewBox="0 0 24 24" className="ai-icon">
                      <circle cx="12" cy="12" r="10" />
                      <path d="M8 12 L11 15 L16 9" />
                    </svg>
                  </div>
                )}
                <div className="message-content">
                  <div className="message-bubble">
                    {message.content}
                  </div>
                  <span className="message-time">
                    {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
              </div>
            ))}
            {isTyping && (
              <div className="message assistant">
                <div className="message-avatar">
                  <svg viewBox="0 0 24 24" className="ai-icon">
                    <circle cx="12" cy="12" r="10" />
                    <path d="M8 12 L11 15 L16 9" />
                  </svg>
                </div>
                <div className="message-content">
                  <div className="typing-indicator">
                    <span />
                    <span />
                    <span />
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </main>

      {/* Input Area */}
      <footer className="chat-footer">
        <form onSubmit={handleSubmit} className="input-form">
          <div className="input-wrapper">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about players, teams, stats..."
              className="chat-input"
            />
            <Button type="submit" className="send-button" disabled={!input.trim()}>
              <Send className="send-icon" />
              <span>SEND</span>
            </Button>
          </div>
        </form>
        <div className="footer-info">
          <span>Powered by advanced basketball analytics</span>
        </div>
      </footer>
    </div>
  );
}
