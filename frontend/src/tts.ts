/**
 * TTS client — streams audio directly from Cartesia API for low latency.
 * Falls back to backend proxy if no API key configured.
 */

const CARTESIA_API_KEY = (import.meta as any).env?.VITE_CARTESIA_API_KEY || "";
const CARTESIA_URL = "https://api.cartesia.ai/tts/bytes";
const MODEL_ID = "sonic-2";
const VOICE_ID = "a0e99841-438c-4a64-b679-ae501e7d6091";

let currentAudio: HTMLAudioElement | null = null;
let speakingCallback: ((speaking: boolean) => void) | null = null;

export function onSpeakingChange(cb: (speaking: boolean) => void) {
  speakingCallback = cb;
}

export function stopSpeaking() {
  if (currentAudio) {
    currentAudio.pause();
    currentAudio.src = "";
    currentAudio = null;
  }
  speakingCallback?.(false);
  // Clear the queue
  queue.length = 0;
  processing = false;
}

let queue: string[] = [];
let processing = false;

async function processQueue() {
  if (processing || queue.length === 0) return;
  processing = true;

  while (queue.length > 0) {
    const text = queue.shift()!;
    try {
      await playTTS(text);
    } catch (e) {
      console.warn("TTS failed:", e);
    }
  }

  processing = false;
}

async function playTTS(text: string): Promise<void> {
  let blob: Blob;

  if (CARTESIA_API_KEY) {
    // Direct to Cartesia — fast, no backend hop
    const response = await fetch(CARTESIA_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": CARTESIA_API_KEY,
        "Cartesia-Version": "2024-06-10",
      },
      body: JSON.stringify({
        model_id: MODEL_ID,
        transcript: text,
        voice: { mode: "id", id: VOICE_ID },
        output_format: { container: "mp3", bit_rate: 128000, sample_rate: 44100 },
        language: "en",
      }),
    });

    if (!response.ok) {
      console.warn("Cartesia TTS returned", response.status);
      return;
    }
    blob = await response.blob();
  } else {
    // Fallback to backend proxy
    const response = await fetch("/api/tts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (!response.ok) return;
    blob = await response.blob();
  }

  const url = URL.createObjectURL(blob);

  return new Promise<void>((resolve) => {
    const audio = new Audio(url);
    currentAudio = audio;
    speakingCallback?.(true);

    audio.onended = () => {
      URL.revokeObjectURL(url);
      currentAudio = null;
      speakingCallback?.(false);
      resolve();
    };

    audio.onerror = () => {
      URL.revokeObjectURL(url);
      currentAudio = null;
      speakingCallback?.(false);
      resolve();
    };

    audio.play().catch(() => {
      speakingCallback?.(false);
      resolve();
    });
  });
}

export function speak(text: string) {
  if (!text.trim()) return;
  queue.push(text);
  processQueue();
}
