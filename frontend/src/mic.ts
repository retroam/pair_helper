/**
 * Microphone input via Web Speech API (browser-native STT).
 * Works in Chrome, Edge, Safari. No API key needed.
 */

type MicCallback = (transcript: string, isFinal: boolean) => void;

let recognition: any = null;
let isListening = false;

export function isMicSupported(): boolean {
  return !!(window as any).webkitSpeechRecognition || !!(window as any).SpeechRecognition;
}

export function startListening(onResult: MicCallback, onEnd?: () => void): boolean {
  if (!isMicSupported()) return false;
  if (isListening) stopListening();

  const SpeechRecognition = (window as any).webkitSpeechRecognition || (window as any).SpeechRecognition;
  recognition = new SpeechRecognition();
  recognition.continuous = false;
  recognition.interimResults = true;
  recognition.lang = "en-US";

  recognition.onresult = (event: any) => {
    let finalTranscript = "";
    let interimTranscript = "";
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const result = event.results[i];
      if (result.isFinal) {
        finalTranscript += result[0].transcript;
      } else {
        interimTranscript += result[0].transcript;
      }
    }
    if (finalTranscript) {
      onResult(finalTranscript, true);
    } else if (interimTranscript) {
      onResult(interimTranscript, false);
    }
  };

  recognition.onend = () => {
    isListening = false;
    onEnd?.();
  };

  recognition.onerror = (event: any) => {
    console.error("SpeechRecognition error:", event.error, event.message);
    isListening = false;
    onEnd?.();
  };

  recognition.start();
  isListening = true;
  return true;
}

export function stopListening() {
  if (recognition) {
    try { recognition.stop(); } catch {}
    recognition = null;
  }
  isListening = false;
}

export function getMicListening(): boolean {
  return isListening;
}
