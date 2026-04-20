const recordButton = document.getElementById("recordButton");
const languageSelect = document.getElementById("language");
const statusText = document.getElementById("status");
const answerText = document.getElementById("answerText");
const manualQuestionForm = document.getElementById("manualQuestionForm");
const manualQuestionInput = document.getElementById("manualQuestion");
const manualSubmitButton = document.getElementById("manualSubmitButton");

let mediaRecorder = null;
let chunks = [];
let recording = false;
let runtimeHealth = null;
let browserRecognition = null;
let submitting = false;

const languageMap = {
  de: "de-DE",
  en: "en-US",
  pl: "pl-PL",
  ro: "ro-RO",
  ru: "ru-RU",
};

function setStatus(value) {
  statusText.textContent = value;
}

function canUseBrowserSpeechFallback() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  return Boolean(SpeechRecognition);
}

function shouldUseBrowserSpeechFallback() {
  return runtimeHealth && runtimeHealth.stt_provider === "mock" && canUseBrowserSpeechFallback();
}

function shouldUseTypedFallback() {
  return runtimeHealth && runtimeHealth.stt_provider === "mock" && !canUseBrowserSpeechFallback();
}

function setReadyStatus() {
  if (shouldUseTypedFallback()) {
    setStatus("Speech input unavailable in this browser. Type a question below.");
    return;
  }
  if (shouldUseBrowserSpeechFallback()) {
    setStatus("Browser speech fallback active");
    return;
  }
  setStatus("Idle");
}

function focusManualQuestion() {
  manualQuestionInput.focus();
  manualQuestionInput.select();
}

function updateInputModeUi() {
  recordButton.textContent = recording ? "Stop" : "Speak";
  const speechUnavailable = Boolean(runtimeHealth) && shouldUseTypedFallback();
  recordButton.disabled = submitting || speechUnavailable;
  manualQuestionInput.disabled = submitting || recording;
  manualSubmitButton.disabled = submitting || recording;
}

async function loadHealth() {
  try {
    const response = await fetch("/api/health");
    if (!response.ok) {
      return null;
    }
    runtimeHealth = await response.json();
    updateInputModeUi();
    if (!recording && !submitting) {
      setReadyStatus();
    }
    return runtimeHealth;
  } catch {
    return null;
  }
}

async function transcribeAudio(blob, language, debugTranscript = null) {
  const form = new FormData();
  form.append("audio", blob, "recording.webm");
  form.append("language", language);
  if (debugTranscript) {
    form.append("debug_transcript", debugTranscript);
  }
  const response = await fetch("/api/speech/transcribe", {
    method: "POST",
    body: form,
  });
  if (!response.ok) {
    throw new Error("Transcription failed");
  }
  return response.json();
}

async function answerQuery(transcript, language) {
  const response = await fetch("/api/query/answer", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ transcript, language }),
  });
  if (!response.ok) {
    throw new Error("Answer generation failed");
  }
  return response.json();
}

async function synthesizeAnswer(text, language) {
  const response = await fetch("/api/speech/synthesize", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, language }),
  });
  if (!response.ok) {
    return null;
  }
  const body = await response.json();
  return body.audio_url || null;
}

async function playAudio(url) {
  const audio = new Audio(url);
  await audio.play();
}

function handleUiError(error) {
  answerText.textContent = error.message || "Something went wrong.";
  setStatus("Error");
}

async function submitTranscript(transcript, language) {
  submitting = true;
  updateInputModeUi();

  try {
    const answer = await answerQuery(transcript, language);
    answerText.textContent = answer.answer_text;
    setStatus(answer.status === "clarification_needed" ? "Clarifying" : "Speaking");

    const audioUrl = await synthesizeAnswer(answer.answer_text, language);
    if (audioUrl) {
      await playAudio(audioUrl);
    } else if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(answer.answer_text);
      utterance.lang = languageMap[language] || "en-US";
      window.speechSynthesis.speak(utterance);
    }
  } finally {
    submitting = false;
    recording = false;
    updateInputModeUi();
    if (statusText.textContent !== "Error") {
      setReadyStatus();
    }
  }
}

async function processAudio(blob) {
  const language = languageSelect.value;
  setStatus("Processing");
  const transcription = await transcribeAudio(blob, language);
  if (transcription.status !== "ok") {
    answerText.textContent = transcription.detail || "Speech recognition is unavailable.";
    setStatus("Error");
    return;
  }

  await submitTranscript(transcription.transcript, language);
}

async function ensureRecorder() {
  if (mediaRecorder) {
    return mediaRecorder;
  }
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  mediaRecorder = new MediaRecorder(stream);
  mediaRecorder.addEventListener("dataavailable", (event) => {
    if (event.data.size > 0) {
      chunks.push(event.data);
    }
  });
  mediaRecorder.addEventListener("stop", async () => {
    const blob = new Blob(chunks, { type: "audio/webm" });
    chunks = [];
    try {
      await processAudio(blob);
    } catch (error) {
      handleUiError(error);
      recording = false;
      updateInputModeUi();
    }
  });
  return mediaRecorder;
}

function createBrowserRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    return null;
  }
  const recognition = new SpeechRecognition();
  recognition.continuous = false;
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;
  recognition.addEventListener("result", async (event) => {
    try {
      const transcript = event.results[0][0].transcript;
      setStatus("Processing");
      await submitTranscript(transcript, languageSelect.value);
    } catch (error) {
      handleUiError(error);
      recording = false;
      updateInputModeUi();
    }
  });
  recognition.addEventListener("error", () => {
    recording = false;
    updateInputModeUi();
    setStatus("Speech recognition could not start. Type a question below.");
    focusManualQuestion();
  });
  recognition.addEventListener("end", () => {
    if (recording) {
      recording = false;
      updateInputModeUi();
      if (!submitting) {
        setReadyStatus();
      }
    }
  });
  return recognition;
}

recordButton.addEventListener("click", async () => {
  try {
    if (!runtimeHealth) {
      await loadHealth();
    }

    if (shouldUseTypedFallback()) {
      setStatus("Speech input unavailable in this browser. Type a question below.");
      focusManualQuestion();
      return;
    }

    if (shouldUseBrowserSpeechFallback()) {
      if (!browserRecognition) {
        browserRecognition = createBrowserRecognition();
      }
      if (!browserRecognition) {
        setStatus("Browser speech recognition is unavailable. Type a question below.");
        focusManualQuestion();
        return;
      }

      if (!recording) {
        browserRecognition.lang = languageMap[languageSelect.value] || "en-US";
        browserRecognition.start();
        recording = true;
        updateInputModeUi();
        setStatus("Listening");
        return;
      }

      browserRecognition.stop();
      recording = false;
      updateInputModeUi();
      return;
    }

    const recorder = await ensureRecorder();
    if (!recording) {
      chunks = [];
      recorder.start();
      recording = true;
      updateInputModeUi();
      setStatus("Listening");
      return;
    }

    recorder.stop();
    recording = false;
    updateInputModeUi();
  } catch (error) {
    recording = false;
    updateInputModeUi();
    handleUiError(error);
    focusManualQuestion();
  }
});

manualQuestionForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const transcript = manualQuestionInput.value.trim();
  if (!transcript || submitting || recording) {
    return;
  }

  setStatus("Processing");
  try {
    await submitTranscript(transcript, languageSelect.value);
    manualQuestionInput.value = "";
  } catch (error) {
    handleUiError(error);
  }
});

loadHealth().then(() => {
  updateInputModeUi();
  if (!runtimeHealth) {
    setReadyStatus();
  }
});
