import { useEffect, useMemo, useRef, useState, useCallback } from "react";
import {
  Box,
  Button,
  Flex,
  Heading,
  HStack,
  Input,
  InputGroup,
  InputLeftElement,
  SimpleGrid,
  Card,
  CardBody,
  CardHeader,
  Spinner,
  Text,
  VStack,
  useToast,
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import Editor from "@monaco-editor/react";
import Split from "react-split";
import VoiceOrb from "./VoiceOrb";
import {
  botStep,
  checkVoiceSignals,
  execute,
  fetchAssessment,
  fetchQuestion,
  getVoiceState,
  listQuestions,
  logActivity,
  lookupConcept,
  publishSession,
  sendCodeUpdate,
  sendVoiceInput,
  setVoiceMode,
  startAssessment,
} from "./api";
import { ExecuteResponse, QuestionResponse, SessionInfo, VoiceMode } from "./types";
import { speak, onSpeakingChange, stopSpeaking } from "./tts";
import { isMicSupported, startListening, stopListening } from "./mic";

type RunState = {
  output: string;
  visiblePassed: number;
  visibleTotal: number;
  hiddenPassed: number;
  hiddenTotal: number;
  runtimeMs: number;
};

type VoiceEntry = {
  role: "bot" | "user";
  text: string;
};

/* ─── Question Selection (Landing) ─── */

const QuestionSelectionScreen = ({
  questions,
  loading,
  searchQuery,
  onSearchChange,
  onSelectQuestion,
  onRandomQuestion,
}: {
  questions: string[];
  loading: boolean;
  searchQuery: string;
  onSearchChange: (v: string) => void;
  onSelectQuestion: (name: string) => void;
  onRandomQuestion: () => void;
}) => (
  <Flex direction="column" align="center" justify="center" minH="100vh" bg="#0a0a0f" p={8}>
    <VStack spacing={8} w="full" maxW="900px">
      <VStack spacing={2}>
        <Text
          fontFamily="'JetBrains Mono', monospace"
          fontSize="xs"
          letterSpacing="4px"
          color="#00d4ff"
          textTransform="uppercase"
        >
          Pair Programming Voice Bot
        </Text>
        <Heading size="xl" color="white" fontWeight={600} letterSpacing="-0.02em">
          Select a Challenge
        </Heading>
        <Text color="#6a6a80" fontSize="sm">
          Choose a coding challenge to start your pair-programming session
        </Text>
      </VStack>

      <HStack w="full" spacing={4}>
        <InputGroup flex={1}>
          <InputLeftElement pointerEvents="none" color="#6a6a80">
            /
          </InputLeftElement>
          <Input
            placeholder="Search..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            bg="#12121e"
            border="1px solid #2a2a3e"
            color="white"
            fontFamily="'JetBrains Mono', monospace"
            fontSize="sm"
            _placeholder={{ color: "#4a4a60" }}
            _hover={{ borderColor: "#3a3a50" }}
            _focus={{ borderColor: "#00d4ff", boxShadow: "0 0 0 1px #00d4ff" }}
          />
        </InputGroup>
        <Button
          bg="transparent"
          border="1px solid #2a2a3e"
          color="#9a9ab0"
          fontFamily="'JetBrains Mono', monospace"
          fontSize="xs"
          letterSpacing="1px"
          _hover={{ borderColor: "#00d4ff", color: "#00d4ff" }}
          onClick={onRandomQuestion}
          isDisabled={loading || questions.length === 0}
          px={6}
        >
          RANDOM
        </Button>
      </HStack>

      {loading ? (
        <Spinner size="lg" color="#00d4ff" />
      ) : questions.length === 0 ? (
        <Text color="#6a6a80">No questions found</Text>
      ) : (
        <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4} w="full">
          {questions.map((q) => (
            <Card
              key={q}
              bg="#12121e"
              border="1px solid #2a2a3e"
              _hover={{
                borderColor: "#00d4ff",
                boxShadow: "0 0 20px rgba(0, 212, 255, 0.1)",
                cursor: "pointer",
              }}
              transition="all 0.2s"
              onClick={() => onSelectQuestion(q)}
            >
              <CardHeader pb={0}>
                <Heading
                  size="md"
                  color="white"
                  fontFamily="'JetBrains Mono', monospace"
                  fontWeight={500}
                >
                  {q}
                </Heading>
              </CardHeader>
              <CardBody pt={2}>
                <Text color="#6a6a80" fontSize="xs" fontFamily="'JetBrains Mono', monospace">
                  Click to begin →
                </Text>
              </CardBody>
            </Card>
          ))}
        </SimpleGrid>
      )}
    </VStack>
  </Flex>
);

/* ─── Stage indicators ─── */

const StageBadges = ({ stages, currentIndex }: { stages: string[]; currentIndex: number }) => (
  <HStack spacing={1}>
    {stages.map((name, idx) => {
      const done = idx < currentIndex;
      const active = idx === currentIndex;
      return (
        <Box
          key={name + idx}
          px={2}
          py={0.5}
          borderRadius="2px"
          fontSize="10px"
          fontFamily="'JetBrains Mono', monospace"
          letterSpacing="0.5px"
          bg={done ? "rgba(0, 212, 255, 0.15)" : active ? "rgba(0, 212, 255, 0.08)" : "transparent"}
          color={done ? "#00d4ff" : active ? "#00d4ff" : "#4a4a60"}
          border="1px solid"
          borderColor={done ? "rgba(0, 212, 255, 0.3)" : active ? "rgba(0, 212, 255, 0.2)" : "#2a2a3e"}
        >
          {done ? "✓" : active ? `L${idx + 1}` : `L${idx + 1}`}
        </Box>
      );
    })}
  </HStack>
);

/* ─── Main App ─── */

export default function App() {
  const toast = useToast();
  const [question, setQuestion] = useState<QuestionResponse | null>(null);
  const [session, setSession] = useState<SessionInfo | null>(null);
  const [files, setFiles] = useState<Record<string, string>>({});
  const [activeFile, setActiveFile] = useState<string | null>(null);
  const [runState, setRunState] = useState<RunState | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [selectedQuestion, setSelectedQuestion] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [activityLogs, setActivityLogs] = useState<string[]>([]);
  const [currentScore, setCurrentScore] = useState(0);
  const [voiceMode, setVoiceModeState] = useState<VoiceMode>("bot_drives");
  const [voiceMessages, setVoiceMessages] = useState<VoiceEntry[]>([]);
  const [voiceInput, setVoiceInput] = useState("");
  const [isBotSpeaking, setIsBotSpeaking] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [struggleSignal, setStruggleSignal] = useState<string | null>(null);
  const codeUpdateDebounceRef = useRef<number | null>(null);
  const botStepActiveRef = useRef(false);
  const loopTokenRef = useRef(0);
  const voiceModeRef = useRef<VoiceMode>("bot_drives");
  const struggleTimerRef = useRef<number | null>(null);

  // Wire TTS speaking state to orb
  useEffect(() => {
    onSpeakingChange(setIsBotSpeaking);
  }, []);

  useEffect(() => {
    voiceModeRef.current = voiceMode;
  }, [voiceMode]);

  const appendVoice = useCallback((role: "bot" | "user", text: string) => {
    const content = text.trim();
    if (!content) return;
    setVoiceMessages((prev) => [{ role, text: content }, ...prev].slice(0, 30));
    if (role === "bot") {
      // Speak aloud via Cartesia TTS
      speak(content);
    }
  }, []);

  // Show struggle indicator and auto-clear
  const showStruggle = useCallback((signal: string) => {
    setStruggleSignal(signal);
    if (struggleTimerRef.current) window.clearTimeout(struggleTimerRef.current);
    struggleTimerRef.current = window.setTimeout(() => setStruggleSignal(null), 10000);
  }, []);

  const questionsQuery = useQuery({
    queryKey: ["questions"],
    queryFn: listQuestions,
  });

  const descContent = useMemo(() => {
    const parts: string[] = [];
    if (files["desc.md"]) parts.push(files["desc.md"]);
    for (let level = 2; level <= 10; level++) {
      const key = `desc_level${level}.md`;
      if (files[key]) parts.push(files[key]);
    }
    return parts.join("\n\n---\n\n");
  }, [files]);

  const envInfo = question?.question.environment ?? {};
  const stageNames = question?.stages ?? session?.stages ?? [];
  const currentLevel = (session?.current_stage_index ?? 0) + 1;

  const filteredQuestions = useMemo(() => {
    const questions = questionsQuery.data ?? [];
    if (!searchQuery.trim()) return questions;
    const query = searchQuery.toLowerCase();
    return questions.filter((q) => q.toLowerCase().includes(query));
  }, [questionsQuery.data, searchQuery]);

  const addActivityLog = (action: string, details?: string) => {
    const timestamp = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    setActivityLogs((prev) => [`${timestamp} ${action}${details ? ` ${details}` : ""}`, ...prev].slice(0, 14));
  };

  useEffect(() => {
    if (question?.files) {
      const visible = Object.keys(question.files);
      const preferred = visible.find((f) => f !== "desc.md") ?? visible[0];
      setActiveFile(preferred ?? null);
    }
  }, [question]);

  useEffect(() => {
    if (selectedQuestion && Object.keys(files).length > 0) {
      const timer = setTimeout(() => {
        localStorage.setItem(`codesignal_${selectedQuestion}_files`, JSON.stringify(files));
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [files, selectedQuestion]);

  useEffect(() => {
    return () => {
      if (codeUpdateDebounceRef.current !== null) window.clearTimeout(codeUpdateDebounceRef.current);
    };
  }, []);

  const handleRandomQuestion = () => {
    const questions = questionsQuery.data ?? [];
    if (questions.length === 0) return;
    handleSelectQuestion(questions[Math.floor(Math.random() * questions.length)]);
  };

  const handleSelectQuestion = async (name: string) => {
    if (!name) return;
    try {
      setSelectedQuestion(name);
      addActivityLog("start", name);
      const data = await fetchQuestion(name);
      setQuestion(data);

      const storageKey = `codesignal_${name}_files`;
      const savedFiles = localStorage.getItem(storageKey);
      if (savedFiles) {
        try {
          setFiles(JSON.parse(savedFiles));
        } catch {
          setFiles(data.files);
        }
      } else {
        setFiles(data.files);
      }

      const sessionRes = await startAssessment(name);
      setSession(sessionRes);
      setRunState(null);
      setHasUnsavedChanges(false);
      setActivityLogs([]);
      setCurrentScore(0);
      setVoiceMessages([]);

      try {
        const voiceState = await getVoiceState(sessionRes.session_id);
        setVoiceModeState(voiceState.mode);
      } catch {
        setVoiceModeState("bot_drives");
      }

      appendVoice("bot", "Session started. Say 'my turn' to take over or 'you drive' for bot mode.");
    } catch (err: any) {
      toast({ title: "Failed to start", description: err?.message, status: "error" });
    }
  };

  const handleFileSelect = (fileName: string) => {
    setActiveFile(fileName);
    if (session && selectedQuestion) logActivity(session.session_id, selectedQuestion, "open_file", { filename: fileName });
  };

  const scheduleCodeUpdateSignal = (latestCode: string) => {
    if (!session || voiceMode !== "human_drives") return;
    if (codeUpdateDebounceRef.current !== null) window.clearTimeout(codeUpdateDebounceRef.current);
    codeUpdateDebounceRef.current = window.setTimeout(async () => {
      try {
        const res = await sendCodeUpdate(session.session_id, latestCode, currentLevel);
        if (res.mode) setVoiceModeState(res.mode);
        if (res.message) appendVoice("bot", res.message);
      } catch { /* ignore */ }
    }, 800);
  };

  const handleFileChange = (value: string | undefined) => {
    if (!activeFile || value === undefined) return;
    setFiles((prev) => ({ ...prev, [activeFile]: value }));
    setHasUnsavedChanges(true);
    scheduleCodeUpdateSignal(value);
  };

  const handleReset = async () => {
    stopSpeaking();
    if (session && selectedQuestion) {
      await logActivity(session.session_id, selectedQuestion, "session_reset", {
        final_score: currentScore,
      });
      localStorage.removeItem(`codesignal_${selectedQuestion}_files`);
    }
    setQuestion(null);
    setSession(null);
    setFiles({});
    setActiveFile(null);
    setRunState(null);
    setSelectedQuestion(null);
    setHasUnsavedChanges(false);
    setActivityLogs([]);
    setCurrentScore(0);
    setVoiceModeState("bot_drives");
    setVoiceMessages([]);
    setVoiceInput("");
  };

  const handleRun = async () => {
    if (!session || !selectedQuestion) return;
    setIsRunning(true);
    addActivityLog("run", "executing...");
    try {
      const res: ExecuteResponse = await execute(session.session_id, selectedQuestion, files);
      setRunState({
        output: res.visible.output,
        visiblePassed: res.visible.passed,
        visibleTotal: res.visible.total,
        hiddenPassed: res.hidden.passed,
        hiddenTotal: res.hidden.total,
        runtimeMs: res.runtime_ms,
      });
      if (res.final_score !== undefined && res.final_score !== null) setCurrentScore(Math.round(res.final_score));
      addActivityLog("done", `${res.visible.passed}/${res.visible.total} passed ${res.runtime_ms}ms`);
      if (res.new_visible_files && Object.keys(res.new_visible_files).length > 0) {
        setFiles((prev) => ({ ...prev, ...res.new_visible_files }));
        const newCodeFiles = Object.keys(res.new_visible_files).filter((f) => !f.startsWith("desc"));
        if (newCodeFiles.length > 0) setActiveFile(newCodeFiles[0]);
        addActivityLog("unlocked", res.unlocked_stage_name || "next");
      }
      if (res.unlocked_stage_index !== null && res.unlocked_stage_index !== undefined) {
        setSession((prev) => (prev ? { ...prev, current_stage_index: res.unlocked_stage_index! } : prev));
      }
      if (voiceMode === "bot_drives" && res.stage.current_passed && res.stage.unlocked_next) {
        appendVoice("bot", `Level ${res.stage.current_index + 1} passed. Unlocking Level ${res.stage.current_index + 2}.`);
      }
    } catch (err: any) {
      addActivityLog("error", err?.response?.data?.detail ?? err?.message);
    } finally {
      setIsRunning(false);
    }
  };

  const handleToggleVoiceMode = async () => {
    if (!session) return;
    stopSpeaking();
    botStepActiveRef.current = false;
    loopTokenRef.current++;
    const targetMode: VoiceMode = voiceMode === "bot_drives" ? "human_drives" : "bot_drives";
    try {
      const res = await setVoiceMode(session.session_id, targetMode);
      const nextMode = (res.mode ?? targetMode) as VoiceMode;
      setVoiceModeState(nextMode);
      addActivityLog("mode", nextMode);
      appendVoice(
        "bot",
        nextMode === "human_drives"
          ? "You drive now. I'll watch and help if you get stuck."
          : "Taking over. I'll edit code and run tests.",
      );
    } catch (err: any) {
      toast({ title: "Mode switch failed", description: err?.message, status: "error" });
    }
  };

  const executeBotLoop = useCallback(async () => {
    if (voiceModeRef.current !== "bot_drives") return;
    if (!session || botStepActiveRef.current) return;
    const myToken = ++loopTokenRef.current;
    botStepActiveRef.current = true;
    try {
      const res = await botStep(session.session_id, currentLevel);
      if (loopTokenRef.current !== myToken || voiceModeRef.current !== "bot_drives") return;
      if (res.narration) {
        appendVoice("bot", res.narration);
      }
      const updates = res.file_updates || {};
      const updateKeys = Object.keys(updates);
      if (updateKeys.length > 0) {
        setFiles((prev) => {
          const next = { ...prev };
          for (const [filename, content] of Object.entries(updates)) {
            next[filename] = content;
          }
          return next;
        });
        addActivityLog("bot_edit", updateKeys.join(", "));
        botStepActiveRef.current = false;
        if (loopTokenRef.current !== myToken || voiceModeRef.current !== "bot_drives") return;
        await handleRun();
        if (loopTokenRef.current !== myToken || voiceModeRef.current !== "bot_drives") return;
        setTimeout(() => {
          if (loopTokenRef.current !== myToken) return;
          executeBotLoop();
        }, 3000);
      } else {
        botStepActiveRef.current = false;
      }
    } catch (err: any) {
      console.error("Bot step error:", err);
      botStepActiveRef.current = false;
    }
  }, [session, voiceMode, currentLevel, appendVoice]);

  const handleVoiceSend = async () => {
    if (!session) return;
    const utterance = voiceInput.trim();
    if (!utterance) return;
    setVoiceInput("");
    appendVoice("user", utterance);

    try {
      if (utterance.toLowerCase().startsWith("lookup ")) {
        const query = utterance.slice(7).trim();
        if (query) {
          const lookup = await lookupConcept(session.session_id, query);
          if (lookup.summary) appendVoice("bot", lookup.summary);
          if (lookup.mode) setVoiceModeState(lookup.mode);
          return;
        }
      }
      const res = await sendVoiceInput(session.session_id, utterance, currentLevel);
      if (res.mode) setVoiceModeState(res.mode);
      const messages = res.messages ?? [];
      if (messages.length === 0) appendVoice("bot", "Noted.");
      else messages.forEach((m) => appendVoice("bot", m));
    } catch (err: any) {
      toast({ title: "Voice failed", description: err?.message, status: "error" });
    }
  };

  /* ─── Timers ─── */

  useEffect(() => {
    if (!session?.session_id) return;
    const interval = setInterval(() => {
      setSession((prev) => {
        if (!prev) return prev;
        return { ...prev, remaining_seconds: Math.max(0, prev.remaining_seconds - 1) };
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [session?.session_id]);

  useEffect(() => {
    if (!session?.session_id) return;
    const interval = setInterval(async () => {
      try {
        const refreshed = await fetchAssessment(session.session_id);
        setSession((prev) => (prev ? { ...prev, ...refreshed } : refreshed));
        if (refreshed.final_score !== undefined && refreshed.final_score !== null) {
          setCurrentScore(Math.round(refreshed.final_score));
        }
      } catch { /* ignore */ }
    }, 5000);
    return () => clearInterval(interval);
  }, [session?.session_id]);

  useEffect(() => {
    if (!session?.session_id || voiceMode !== "human_drives") return;
    const interval = setInterval(async () => {
      try {
        const testsStillFailing = runState ? runState.visiblePassed < runState.visibleTotal : true;
        const res = await checkVoiceSignals(session.session_id, currentLevel, testsStillFailing);
        if (res.mode) setVoiceModeState(res.mode);
        if (res.message) {
          appendVoice("bot", res.message);
          showStruggle("hint");
        }
      } catch { /* ignore */ }
    }, 5000);
    return () => clearInterval(interval);
  }, [session?.session_id, voiceMode, currentLevel, runState?.visiblePassed, runState?.visibleTotal, appendVoice, showStruggle]);

  useEffect(() => {
    if (voiceMode === "bot_drives" && session?.session_id) {
      const timer = setTimeout(() => executeBotLoop(), 2000);
      return () => {
        clearTimeout(timer);
        loopTokenRef.current++;
        botStepActiveRef.current = false;
      };
    }
  }, [voiceMode, session?.session_id]);

  /* ─── Landing ─── */

  if (!question) {
    return (
      <QuestionSelectionScreen
        questions={filteredQuestions}
        loading={questionsQuery.isLoading}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        onSelectQuestion={handleSelectQuestion}
        onRandomQuestion={handleRandomQuestion}
      />
    );
  }

  const minutes = Math.floor((session?.remaining_seconds ?? 0) / 60);
  const seconds = (session?.remaining_seconds ?? 0) % 60;
  const timeStr = `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  const codeFiles = Object.keys(files).filter((f) => !f.startsWith("desc"));

  return (
    <Flex direction="column" h="100vh" bg="#0a0a0f" overflow="hidden">
      {/* ─── Top Bar ─── */}
      <Flex
        align="center"
        gap={3}
        px={5}
        py={2.5}
        bg="#0e0e16"
        borderBottom="1px solid #1e1e30"
        flexShrink={0}
      >
        <Text
          fontFamily="'JetBrains Mono', monospace"
          fontSize="xs"
          letterSpacing="2px"
          color="#00d4ff"
          fontWeight={600}
          textTransform="uppercase"
          mr={2}
        >
          PPVB
        </Text>

        <Box h="14px" w="1px" bg="#2a2a3e" />

        <Text fontFamily="'JetBrains Mono', monospace" fontSize="xs" color="#9a9ab0">
          {selectedQuestion}
        </Text>

        <StageBadges stages={stageNames} currentIndex={session?.current_stage_index ?? 0} />

        <Box flex="1" />

        <Text fontFamily="'JetBrains Mono', monospace" fontSize="xs" color="#6a6a80">
          {currentScore}/100
        </Text>

        <Box h="14px" w="1px" bg="#2a2a3e" />

        <Text
          fontFamily="'JetBrains Mono', monospace"
          fontSize="xs"
          color={(session?.remaining_seconds ?? 0) <= 60 ? "#ff4444" : "#9a9ab0"}
        >
          {timeStr}
        </Text>

        <Box h="14px" w="1px" bg="#2a2a3e" />

        <Button
          size="xs"
          bg={isRunning ? "#1a1a2e" : "#00d4ff"}
          color={isRunning ? "#6a6a80" : "#0a0a0f"}
          border="none"
          fontFamily="'JetBrains Mono', monospace"
          fontSize="10px"
          letterSpacing="1px"
          fontWeight={600}
          px={4}
          _hover={{ bg: isRunning ? "#1a1a2e" : "#33ddff" }}
          onClick={handleRun}
          isDisabled={!session || isRunning || (session?.remaining_seconds ?? 0) <= 0}
          isLoading={isRunning}
        >
          RUN
        </Button>

        <Button
          size="xs"
          bg="transparent"
          border="1px solid #2a2a3e"
          color="#9a9ab0"
          fontFamily="'JetBrains Mono', monospace"
          fontSize="10px"
          letterSpacing="1px"
          _hover={{ borderColor: "#8b5cf6", color: "#8b5cf6" }}
          onClick={async () => {
            if (!session) return;
            try {
              const res = await publishSession(session.session_id);
              if (res.notion_url) {
                toast({ title: "Published to Notion", description: res.notion_url, status: "success", duration: 5000 });
              } else {
                toast({ title: "Saved locally", status: "info", duration: 3000 });
              }
              addActivityLog("publish", res.notion_url ? "→ Notion" : "→ local");
            } catch (err: any) {
              toast({ title: "Publish failed", description: err?.message, status: "error" });
            }
          }}
          px={3}
        >
          PUBLISH
        </Button>

        <Button
          size="xs"
          variant="ghost"
          color="#6a6a80"
          fontFamily="'JetBrains Mono', monospace"
          fontSize="10px"
          letterSpacing="1px"
          _hover={{ color: "#ff4444" }}
          onClick={handleReset}
        >
          EXIT
        </Button>
      </Flex>

      {/* ─── Main 3-column Layout ─── */}
      <Flex flex="1" overflow="hidden">
        {/* Left: Description Panel */}
        <Box
          w="280px"
          flexShrink={0}
          bg="#0e0e16"
          borderRight="1px solid #1e1e30"
          overflow="auto"
          p={4}
        >
          <Text
            fontFamily="'JetBrains Mono', monospace"
            fontSize="10px"
            letterSpacing="2px"
            color="#6a6a80"
            textTransform="uppercase"
            mb={3}
          >
            Description
          </Text>
          <Box className="markdown-description">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {descContent || "_Loading..._"}
            </ReactMarkdown>
          </Box>
        </Box>

        {/* Center: Editor + Terminal */}
        <Flex flex="1" direction="column" overflow="hidden">
          <Split
            direction="vertical"
            sizes={[65, 35]}
            minSize={100}
            gutterSize={4}
            className="split-vertical"
            style={{ display: "flex", flexDirection: "column", height: "100%" }}
          >
            {/* Editor Area */}
            <Flex overflow="hidden">
              {/* File tree */}
              <VStack
                w="150px"
                flexShrink={0}
                align="stretch"
                spacing={0}
                bg="#0a0a0f"
                borderRight="1px solid #1e1e30"
                py={2}
              >
                <Text
                  fontFamily="'JetBrains Mono', monospace"
                  fontSize="10px"
                  letterSpacing="2px"
                  color="#6a6a80"
                  textTransform="uppercase"
                  px={3}
                  mb={2}
                >
                  Files
                </Text>
                {codeFiles.map((file) => (
                  <Box
                    key={file}
                    px={3}
                    py={1.5}
                    cursor="pointer"
                    fontFamily="'JetBrains Mono', monospace"
                    fontSize="12px"
                    color={file === activeFile ? "#00d4ff" : "#9a9ab0"}
                    bg={file === activeFile ? "rgba(0, 212, 255, 0.06)" : "transparent"}
                    borderLeft="2px solid"
                    borderLeftColor={file === activeFile ? "#00d4ff" : "transparent"}
                    _hover={{ bg: "rgba(255,255,255,0.03)", color: "#e0e0e0" }}
                    onClick={() => handleFileSelect(file)}
                    transition="all 0.15s"
                  >
                    {file}
                  </Box>
                ))}
              </VStack>

              {/* Monaco */}
              <Box flex="1" bg="#0a0a0f">
                {activeFile ? (
                  <Editor
                    height="100%"
                    language="python"
                    theme="vs-dark"
                    value={files[activeFile]}
                    onChange={handleFileChange}
                    options={{
                      minimap: { enabled: false },
                      fontSize: 13,
                      fontFamily: "'JetBrains Mono', monospace",
                      lineHeight: 20,
                      padding: { top: 12 },
                      renderLineHighlight: "gutter",
                      scrollBeyondLastLine: false,
                      overviewRulerBorder: false,
                      hideCursorInOverviewRuler: true,
                    }}
                  />
                ) : (
                  <Flex align="center" justify="center" h="100%">
                    <Text color="#4a4a60" fontFamily="'JetBrains Mono', monospace" fontSize="xs">
                      Select a file
                    </Text>
                  </Flex>
                )}
              </Box>
            </Flex>

            {/* Terminal Output */}
            <Box
              bg="#0a0a0f"
              borderTop="1px solid #1e1e30"
              overflow="auto"
              p={3}
              fontFamily="'JetBrains Mono', monospace"
              fontSize="12px"
            >
              <Flex justify="space-between" align="center" mb={2}>
                <Text fontSize="10px" letterSpacing="2px" color="#6a6a80" textTransform="uppercase">
                  Output
                </Text>
                {runState && (
                  <HStack spacing={3} fontSize="10px">
                    <Text color="#00d4ff">
                      {runState.visiblePassed}/{runState.visibleTotal} visible
                    </Text>
                    <Text color="#8b5cf6">
                      {runState.hiddenPassed}/{runState.hiddenTotal} hidden
                    </Text>
                    <Text color="#6a6a80">{runState.runtimeMs}ms</Text>
                  </HStack>
                )}
              </Flex>
              <Box whiteSpace="pre-wrap" color="#9a9ab0" lineHeight="1.6">
                {runState?.output || "Run to see output..."}
              </Box>
            </Box>
          </Split>
        </Flex>

        {/* Right: Voice Panel */}
        <Flex
          w="320px"
          flexShrink={0}
          direction="column"
          bg="#0a0a0f"
          borderLeft="1px solid #1e1e30"
        >
          {/* Orb Section */}
          <Flex
            flex="1"
            minH={0}
            overflow="hidden"
            direction="column"
            align="center"
            justify="center"
            className="voice-panel"
            position="relative"
          >
            <VoiceOrb
              isActive={!!session}
              isSpeaking={isBotSpeaking}
              mode={voiceMode}
              struggleSignal={struggleSignal}
            />

            {/* Mode toggle */}
            <Box
              as="button"
              mt={2}
              px={4}
              py={1.5}
              borderRadius="2px"
              border="1px solid #2a2a3e"
              bg="transparent"
              color="#9a9ab0"
              fontFamily="'JetBrains Mono', monospace"
              fontSize="10px"
              letterSpacing="1px"
              cursor="pointer"
              _hover={{ borderColor: "#00d4ff", color: "#00d4ff" }}
              transition="all 0.2s"
              onClick={handleToggleVoiceMode}
            >
              {voiceMode === "bot_drives" ? "SWITCH TO HUMAN" : "SWITCH TO BOT"}
            </Box>
          </Flex>

          {/* Chat Section */}
          <Flex
            direction="column"
            h="240px"
            flexShrink={0}
            borderTop="1px solid #1e1e30"
          >
            {/* Messages */}
            <Box flex="1" overflow="auto" px={3} py={2}>
              {voiceMessages.length === 0 ? (
                <Text color="#4a4a60" fontFamily="'JetBrains Mono', monospace" fontSize="11px">
                  No messages yet...
                </Text>
              ) : (
                <VStack align="stretch" spacing={1.5}>
                  {voiceMessages.map((entry, idx) => (
                    <Box key={idx}>
                      <Text
                        fontFamily="'JetBrains Mono', monospace"
                        fontSize="10px"
                        letterSpacing="0.5px"
                        color={entry.role === "bot" ? "#00d4ff" : "#8b5cf6"}
                        mb={0.5}
                      >
                        {entry.role === "bot" ? "AI" : "YOU"}
                      </Text>
                      <Text
                        fontFamily="'Inter', sans-serif"
                        fontSize="12px"
                        color="#c0c0d0"
                        lineHeight="1.5"
                      >
                        {entry.text}
                      </Text>
                    </Box>
                  ))}
                </VStack>
              )}
            </Box>

            {/* Input */}
            <HStack px={3} pb={3} pt={1} spacing={2}>
              {isMicSupported() && (
                <Button
                  size="sm"
                  bg={isRecording ? "rgba(255, 68, 68, 0.15)" : "transparent"}
                  border="1px solid"
                  borderColor={isRecording ? "#ff4444" : "#2a2a3e"}
                  color={isRecording ? "#ff4444" : "#9a9ab0"}
                  fontFamily="'JetBrains Mono', monospace"
                  fontSize="12px"
                  _hover={{ borderColor: isRecording ? "#ff4444" : "#00d4ff", color: isRecording ? "#ff4444" : "#00d4ff" }}
                  onMouseDown={() => {
                    stopSpeaking();
                    setIsRecording(true);
                    startListening(
                      (transcript, isFinal) => {
                        if (isFinal) {
                          setVoiceInput(transcript);
                        } else {
                          setVoiceInput(transcript);
                        }
                      },
                      () => setIsRecording(false),
                    );
                  }}
                  onMouseUp={() => {
                    stopListening();
                    setIsRecording(false);
                    // Auto-send after releasing mic
                    setTimeout(() => {
                      const btn = document.getElementById("voice-send-btn");
                      btn?.click();
                    }, 300);
                  }}
                  px={3}
                  title="Hold to talk"
                >
                  {isRecording ? "●" : "🎤"}
                </Button>
              )}
              <Input
                size="sm"
                bg="#12121e"
                border="1px solid #2a2a3e"
                color="white"
                fontFamily="'JetBrains Mono', monospace"
                fontSize="11px"
                _placeholder={{ color: "#4a4a60" }}
                _focus={{ borderColor: "#00d4ff", boxShadow: "none" }}
                placeholder={isRecording ? "Listening..." : "my turn / you drive / lookup ..."}
                value={voiceInput}
                onChange={(e) => setVoiceInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") handleVoiceSend(); }}
              />
              <Button
                id="voice-send-btn"
                size="sm"
                bg="transparent"
                border="1px solid #2a2a3e"
                color="#9a9ab0"
                fontFamily="'JetBrains Mono', monospace"
                fontSize="10px"
                _hover={{ borderColor: "#00d4ff", color: "#00d4ff" }}
                onClick={handleVoiceSend}
                px={4}
              >
                →
              </Button>
            </HStack>
          </Flex>

          {/* Activity Log */}
          <Box
            borderTop="1px solid #1e1e30"
            px={3}
            py={2}
            maxH="100px"
            overflow="auto"
            flexShrink={0}
          >
            <Text
              fontFamily="'JetBrains Mono', monospace"
              fontSize="9px"
              letterSpacing="2px"
              color="#4a4a60"
              textTransform="uppercase"
              mb={1}
            >
              Log
            </Text>
            {activityLogs.length === 0 ? (
              <Text color="#3a3a50" fontFamily="'JetBrains Mono', monospace" fontSize="10px">
                —
              </Text>
            ) : (
              <VStack align="stretch" spacing={0}>
                {activityLogs.map((log, idx) => (
                  <Text
                    key={idx}
                    fontFamily="'JetBrains Mono', monospace"
                    fontSize="10px"
                    color="#4a4a60"
                    lineHeight="1.6"
                  >
                    {log}
                  </Text>
                ))}
              </VStack>
            )}
          </Box>
        </Flex>
      </Flex>
    </Flex>
  );
}
