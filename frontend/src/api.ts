import axios from "axios";
import { ExecuteResponse, QuestionResponse, SessionInfo, VoiceMessageResponse, VoiceMode, VoiceState } from "./types";

const client = axios.create({
  baseURL: "/api",
});

export async function listQuestions(): Promise<string[]> {
  const res = await client.get("/questions");
  return res.data.questions || [];
}

export async function fetchQuestion(questionName: string): Promise<QuestionResponse> {
  const res = await client.get(`/questions/${questionName}`);
  return res.data;
}

export async function startAssessment(questionName: string, duration?: number): Promise<SessionInfo> {
  const res = await client.post("/assessment/start", { question_name: questionName, duration_minutes: duration });
  return res.data;
}

export async function fetchAssessment(sessionId: string): Promise<SessionInfo> {
  const res = await client.get(`/assessment/${sessionId}`);
  return res.data;
}

export async function execute(sessionId: string, questionName: string, files: Record<string, string>): Promise<ExecuteResponse> {
  const res = await client.post("/execute", {
    session_id: sessionId,
    question_name: questionName,
    files,
  });
  return res.data;
}

export async function logActivity(sessionId: string, questionName: string, action: string, payload?: Record<string, any>): Promise<void> {
  try {
    await client.post("/log", {
      session_id: sessionId,
      question_name: questionName,
      action,
      payload,
    });
  } catch {
    // Silently fail logging to not interrupt user experience
  }
}

export async function getVoiceState(sessionId: string): Promise<VoiceState> {
  const res = await client.get(`/voice/${sessionId}`);
  return res.data;
}

export async function setVoiceMode(sessionId: string, mode: VoiceMode): Promise<VoiceMessageResponse> {
  const res = await client.post("/voice/mode", { session_id: sessionId, mode });
  return res.data;
}

export async function sendVoiceInput(sessionId: string, utterance: string, currentLevel: number): Promise<VoiceMessageResponse> {
  const res = await client.post("/voice/input", {
    session_id: sessionId,
    utterance,
    current_level: currentLevel,
  });
  return res.data;
}

export async function sendCodeUpdate(sessionId: string, code: string, currentLevel: number): Promise<VoiceMessageResponse> {
  const res = await client.post("/voice/code_update", {
    session_id: sessionId,
    code,
    current_level: currentLevel,
  });
  return res.data;
}

export async function checkVoiceSignals(
  sessionId: string,
  currentLevel: number,
  testsStillFailing: boolean,
): Promise<VoiceMessageResponse> {
  const res = await client.post("/voice/check", {
    session_id: sessionId,
    current_level: currentLevel,
    tests_still_failing: testsStillFailing,
  });
  return res.data;
}

export async function lookupConcept(sessionId: string, query: string): Promise<VoiceMessageResponse> {
  const res = await client.post("/voice/lookup", {
    session_id: sessionId,
    query,
  });
  return res.data;
}

export async function botStep(sessionId: string, currentLevel: number): Promise<{
  narration: string;
  file_updates: Record<string, string>;
  mode: VoiceMode;
}> {
  const res = await client.post("/voice/bot_step", {
    session_id: sessionId,
    current_level: currentLevel,
  });
  return res.data;
}

export async function publishSession(sessionId: string): Promise<{ status: string; notion_url?: string }> {
  const res = await client.post("/session/publish", { session_id: sessionId });
  return res.data;
}
