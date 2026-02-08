export type QuestionConfig = {
  name: string;
  visible_files: string[];
  entrypoint: string;
  environment: Record<string, string>;
  default_duration_minutes: number;
  tags?: string[];
  estimated_difficulty?: string;
};

export type QuestionResponse = {
  question: QuestionConfig;
  files: Record<string, string>;
  stages?: string[];
};

export type ExecuteResponse = {
  visible: { passed: number; total: number; output: string };
  hidden: { passed: number; total: number };
  runtime_ms: number;
  final_score: number;
  stage: { current_index: number; total_stages: number; current_passed: boolean; unlocked_next: boolean; name: string };
  unlocked_stage_index?: number | null;
  unlocked_stage_name?: string | null;
  new_visible_files?: Record<string, string>;
};

export type SessionInfo = {
  session_id: string;
  question_name: string;
  remaining_seconds: number;
  expires_at: number;
  status: string;
  current_stage_index: number;
  stages: string[];
  final_score?: number | null;
};

export type VoiceMode = "bot_drives" | "human_drives";

export type VoiceState = {
  session_id: string;
  mode: VoiceMode;
  run_history_size: number;
};

export type VoiceMessageResponse = {
  mode: VoiceMode;
  messages?: string[];
  message?: string | null;
  summary?: string;
};
