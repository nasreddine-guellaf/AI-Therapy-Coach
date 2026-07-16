"use client";

export function VoiceRecorder() {
  return (
    <button
      className="icon-button"
      type="button"
      disabled
      aria-label="Voice recording is coming soon"
      title="Voice recording will be added in a future version"
    >
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M12 15a3 3 0 0 0 3-3V6a3 3 0 1 0-6 0v6a3 3 0 0 0 3 3Z" />
        <path d="M18 11a6 6 0 0 1-12 0M12 17v4M9 21h6" />
      </svg>
    </button>
  );
}
