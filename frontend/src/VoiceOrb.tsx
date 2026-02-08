import React from "react";
import { VoiceMode } from "./types";

interface VoiceOrbProps {
  isActive: boolean;
  isSpeaking: boolean;
  mode: VoiceMode;
  statusText?: string;
  struggleSignal?: string | null;
}

const keyframesCSS = `
@keyframes orbBreathe {
  0%, 100% { transform: scale(1); opacity: 0.85; }
  50% { transform: scale(1.04); opacity: 1; }
}

@keyframes orbPulseActive {
  0%, 100% { transform: scale(1); opacity: 0.9; }
  50% { transform: scale(1.08); opacity: 1; }
}

@keyframes orbPulseSpeaking {
  0%, 100% { transform: scale(1); opacity: 0.95; }
  30% { transform: scale(1.12); opacity: 1; }
  60% { transform: scale(0.97); opacity: 0.9; }
}

@keyframes ringExpand {
  0% { transform: scale(1); opacity: 0.6; }
  100% { transform: scale(2.2); opacity: 0; }
}

@keyframes ringExpandFast {
  0% { transform: scale(1); opacity: 0.7; }
  100% { transform: scale(2.6); opacity: 0; }
}

@keyframes glowPulse {
  0%, 100% { box-shadow: 0 0 40px 8px rgba(0, 212, 255, 0.3), 0 0 80px 20px rgba(0, 212, 255, 0.1); }
  50% { box-shadow: 0 0 60px 15px rgba(0, 212, 255, 0.5), 0 0 120px 40px rgba(0, 212, 255, 0.15); }
}

@keyframes glowPulseSpeaking {
  0%, 100% { box-shadow: 0 0 50px 12px rgba(0, 212, 255, 0.5), 0 0 100px 30px rgba(139, 92, 246, 0.2); }
  50% { box-shadow: 0 0 80px 25px rgba(0, 212, 255, 0.7), 0 0 150px 50px rgba(139, 92, 246, 0.3); }
}

@keyframes barBounce1 {
  0%, 100% { height: 8px; }
  50% { height: 32px; }
}

@keyframes barBounce2 {
  0%, 100% { height: 6px; }
  40% { height: 40px; }
}

@keyframes barBounce3 {
  0%, 100% { height: 10px; }
  60% { height: 28px; }
}

@keyframes barBounce4 {
  0%, 100% { height: 5px; }
  45% { height: 36px; }
}

@keyframes barBounce5 {
  0%, 100% { height: 7px; }
  55% { height: 24px; }
}

@keyframes barBounce6 {
  0%, 100% { height: 9px; }
  35% { height: 34px; }
}

@keyframes barBounce7 {
  0%, 100% { height: 6px; }
  50% { height: 20px; }
}

@keyframes barIdle {
  0%, 100% { height: 4px; }
  50% { height: 8px; }
}

@keyframes strugglePulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(255, 160, 0, 0); }
  50% { box-shadow: 0 0 40px 15px rgba(255, 160, 0, 0.3), 0 0 80px 30px rgba(255, 68, 68, 0.15); }
}

@keyframes innerOrbRotate {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
`;

const modeLabels: Record<VoiceMode, string> = {
  bot_drives: "BOT DRIVES",
  human_drives: "HUMAN DRIVES",
};

const VoiceOrb: React.FC<VoiceOrbProps> = ({
  isActive,
  isSpeaking,
  mode,
  statusText,
  struggleSignal,
}) => {
  const isStruggling = !!struggleSignal;
  const resolvedStatus =
    statusText ?? (isSpeaking ? "Speaking..." : isActive ? "Listening..." : "Idle");

  const orbAnimation = isSpeaking
    ? "orbPulseSpeaking 0.8s ease-in-out infinite"
    : isActive
      ? "orbPulseActive 2s ease-in-out infinite"
      : "orbBreathe 4s ease-in-out infinite";

  const glowAnimation = isSpeaking
    ? "glowPulseSpeaking 0.6s ease-in-out infinite"
    : isActive
      ? "glowPulse 2s ease-in-out infinite"
      : "glowPulse 4s ease-in-out infinite";

  const ringCount = isSpeaking ? 5 : isActive ? 3 : 0;
  const ringDuration = isSpeaking ? 1.2 : 2.4;
  const ringKeyframe = isSpeaking ? "ringExpandFast" : "ringExpand";

  const barAnimations = [
    "barBounce1",
    "barBounce2",
    "barBounce3",
    "barBounce4",
    "barBounce5",
    "barBounce6",
    "barBounce7",
  ];
  const barDurations = [0.5, 0.6, 0.45, 0.55, 0.5, 0.65, 0.4];
  const barDelays = [0, 0.1, 0.05, 0.15, 0.08, 0.12, 0.03];

  return (
    <>
      <style>{keyframesCSS}</style>
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 24,
          padding: 40,
          userSelect: "none",
        }}
      >
        {/* Orb container */}
        <div
          style={{
            position: "relative",
            width: 250,
            height: 250,
          }}
        >
          {/* Expanding rings */}
          {Array.from({ length: ringCount }).map((_, i) => (
            <div
              key={i}
              style={{
                position: "absolute",
                inset: 0,
                borderRadius: "50%",
                border: `1.5px solid ${isSpeaking ? "rgba(0, 212, 255, 0.4)" : "rgba(0, 212, 255, 0.25)"}`,
                animation: `${ringKeyframe} ${ringDuration}s ease-out infinite`,
                animationDelay: `${(i * ringDuration) / ringCount}s`,
                pointerEvents: "none",
              }}
            />
          ))}

          {/* Struggle pulse ring */}
          {isStruggling && (
            <div
              style={{
                position: "absolute",
                inset: -8,
                borderRadius: "50%",
                border: "2px solid rgba(255, 160, 0, 0.6)",
                animation: "strugglePulse 1.5s ease-in-out infinite",
                pointerEvents: "none",
              }}
            />
          )}

          {/* Outer glow shell */}
          <div
            style={{
              position: "absolute",
              inset: -4,
              borderRadius: "50%",
              animation: glowAnimation,
              pointerEvents: "none",
            }}
          />

          {/* Main orb */}
          <div
            style={{
              position: "relative",
              width: 250,
              height: 250,
              borderRadius: "50%",
              background: `
                radial-gradient(circle at 38% 35%, rgba(0, 212, 255, 0.35) 0%, transparent 55%),
                radial-gradient(circle at 65% 70%, rgba(139, 92, 246, 0.25) 0%, transparent 50%),
                radial-gradient(circle at 50% 50%, rgba(0, 212, 255, 0.12) 0%, rgba(10, 10, 20, 0.95) 70%)
              `,
              animation: orbAnimation,
              boxShadow: `
                inset 0 0 60px 10px rgba(0, 212, 255, 0.15),
                inset 0 0 20px 5px rgba(139, 92, 246, 0.08),
                0 0 30px 5px rgba(0, 212, 255, 0.2)
              `,
              overflow: "hidden",
            }}
          >
            {/* Inner rotating accent */}
            <div
              style={{
                position: "absolute",
                inset: 30,
                borderRadius: "50%",
                border: "1px solid rgba(0, 212, 255, 0.15)",
                borderTop: "1px solid rgba(0, 212, 255, 0.5)",
                animation: `innerOrbRotate ${isSpeaking ? "2s" : "8s"} linear infinite`,
              }}
            />
            <div
              style={{
                position: "absolute",
                inset: 55,
                borderRadius: "50%",
                border: "1px solid rgba(139, 92, 246, 0.1)",
                borderBottom: "1px solid rgba(139, 92, 246, 0.4)",
                animation: `innerOrbRotate ${isSpeaking ? "1.5s" : "6s"} linear infinite reverse`,
              }}
            />

            {/* Core glow */}
            <div
              style={{
                position: "absolute",
                inset: 70,
                borderRadius: "50%",
                background: `radial-gradient(circle, rgba(0, 212, 255, ${isSpeaking ? 0.3 : 0.15}) 0%, transparent 70%)`,
                filter: "blur(8px)",
              }}
            />
          </div>
        </div>

        {/* Sound wave bars */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 4,
            height: 44,
          }}
        >
          {barAnimations.map((anim, i) => (
            <div
              key={i}
              style={{
                width: 3,
                borderRadius: 2,
                background: `linear-gradient(to top, #00d4ff, ${i % 2 === 0 ? "#00d4ff" : "#8b5cf6"})`,
                animation: isSpeaking
                  ? `${anim} ${barDurations[i]}s ease-in-out infinite`
                  : `barIdle ${2 + i * 0.2}s ease-in-out infinite`,
                animationDelay: isSpeaking ? `${barDelays[i]}s` : `${i * 0.15}s`,
                height: 4,
                opacity: isSpeaking ? 1 : 0.4,
                transition: "opacity 0.3s ease",
              }}
            />
          ))}
        </div>

        {/* Mode label */}
        <div
          style={{
            fontFamily: "'SF Mono', 'Monaco', 'Inconsolata', 'Fira Code', monospace",
            fontSize: 13,
            fontWeight: 600,
            letterSpacing: 3,
            color: mode === "bot_drives" ? "#00d4ff" : "#8b5cf6",
            textTransform: "uppercase",
          }}
        >
          {modeLabels[mode]}
        </div>

        {/* Status line */}
        <div
          style={{
            fontFamily: "'SF Mono', 'Monaco', 'Inconsolata', 'Fira Code', monospace",
            fontSize: 11,
            letterSpacing: 1.5,
            color: "rgba(255, 255, 255, 0.5)",
            textTransform: "uppercase",
          }}
        >
          {resolvedStatus}
        </div>
      </div>
    </>
  );
};

export default VoiceOrb;
