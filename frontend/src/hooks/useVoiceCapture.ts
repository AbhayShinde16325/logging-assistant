/**
 * MVP voice capture (T-110): Web Speech API in-browser only (frontend/AGENTS.md) — Chrome.
 * Unsupported browsers receive a graceful `unsupported` state, never an SDK import.
 */

import { useCallback, useRef, useState } from "react";
import type { SpeechRecognitionEventLike, SpeechRecognitionLike } from "../types/speech";

export type VoiceCaptureState = "idle" | "listening" | "unsupported" | "error";

export function useVoiceCapture(onTranscript: (text: string) => void) {
  const [state, setState] = useState<VoiceCaptureState>(() =>
    getRecognitionCtor() ? "idle" : "unsupported",
  );
  const [interim, setInterim] = useState("");
  // keep the latest recognition instance so stop() reaches the session (no any: typed ctor)
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);

  const start = useCallback(() => {
    const Ctor = getRecognitionCtor();
    if (!Ctor) {
      setState("unsupported");
      return;
    }
    const recognition = new Ctor();
    recognition.lang = "en-US";
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;
    recognitionRef.current = recognition;

    recognition.onresult = (event: SpeechRecognitionEventLike) => {
      let finalText = "";
      let interimText = "";
      for (let i = 0; i < event.results.length; i += 1) {
        const result = event.results[i];
        const [alternative] = [result[0]];
        if (result.isFinal) finalText += alternative.transcript;
        else interimText += alternative.transcript;
      }
      setInterim(interimText || finalText);
      if (finalText) {
        onTranscript(finalText.trim());
        setInterim("");
      }
    };
    recognition.onerror = () => setState("error");
    recognition.onend = () => setState((s) => (s === "listening" ? "idle" : s));
    try {
      recognition.start();
      setState("listening");
    } catch {
      setState("error");
    }
  }, [onTranscript]);

  const stop = useCallback(() => {
    recognitionRef.current?.stop();
  }, []);

  return { state, interim, start, stop };
}

function getRecognitionCtor(): (new () => SpeechRecognitionLike) | undefined {
  if (typeof window === "undefined") return undefined;
  return window.SpeechRecognition ?? window.webkitSpeechRecognition;
}
