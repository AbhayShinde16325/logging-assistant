/**
 * ChatComposer — text input + Web Speech mic (T-110). Voice transcripts land as chat text;
 * server-side transcription is intentionally not used (contract 501 path is never called).
 */

import { useState } from "react";
import { Button, ErrorBanner } from "../../components/ui";
import type { ErrorEnvelope } from "../../types";
import { useVoiceCapture } from "../../hooks/useVoiceCapture";

export function ChatComposer({
  onSend,
  sending,
  disabled,
}: {
  onSend: (message: string) => void;
  sending: boolean;
  disabled?: boolean;
}) {
  const [text, setText] = useState("");
  const [error, setError] = useState<ErrorEnvelope | null>(null);
  const voice = useVoiceCapture((transcript) => setText((prev) => (prev ? `${prev} ${transcript}` : transcript)));

  const submit = () => {
    const message = text.trim();
    if (!message || sending || disabled) return;
    setText("");
    onSend(message);
  };

  return (
    <div className="border-t border-slate-200 bg-white p-3">
      <ErrorBanner error={error} onDismiss={() => setError(null)} />
      {voice.state === "unsupported" ? (
        <p className="mb-2 text-xs text-slate-400">
          Voice input needs a Chromium browser (Web Speech API); typing always works.
        </p>
      ) : null}
      <div className="flex items-end gap-2">
        <textarea
          value={voice.interim || text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
          rows={2}
          placeholder="Type a work instruction… e.g. 'I need to research competitors by Friday'"
          className="flex-1 resize-none rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
          aria-label="Message to the assistant"
        />
        {voice.state !== "unsupported" ? (
          <Button
            variant={voice.state === "listening" ? "danger" : "ghost"}
            onClick={() => (voice.state === "listening" ? voice.stop() : voice.start())}
            title={
              voice.state === "listening"
                ? "Stop listening"
                : voice.state === "error"
                  ? "Mic error — click to retry"
                  : "Dictate"
            }
          >
            {voice.state === "listening" ? "● Stop" : "🎙 Speak"}
          </Button>
        ) : null}
        <Button onClick={submit} disabled={sending || disabled || !text.trim()}>
          {sending ? "…" : "Send"}
        </Button>
      </div>
    </div>
  );
}
