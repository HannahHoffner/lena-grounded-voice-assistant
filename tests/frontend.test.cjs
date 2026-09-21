/* Executes the actual browser scripts with local DOM/transport doubles. */
const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { test } = require("node:test");

class Element {
  constructor() {
    this.children = [];
    this.handlers = {};
    this.dataset = {};
    this.classList = { add() {}, remove() {}, toggle() {} };
  }
  addEventListener(name, handler) { this.handlers[name] = handler; }
  setAttribute() {}
  removeAttribute() {}
  replaceChildren() { this.children = []; }
  appendChild(child) { this.children.push(child); }
  querySelector() { return this.children[0]; }
  querySelectorAll() { return this.children; }
  focus() {}
  scrollIntoView() {}
}

function client() {
  const nodes = new Map();
  const get = (id) => {
    if (!nodes.has(id)) nodes.set(id, new Element());
    return nodes.get(id);
  };
  const revoked = [];
  const timers = new Map();
  let timerId = 0;
  const sandbox = {
    window: { setTimeout: (fn) => { timers.set(++timerId, fn); return timerId; }, clearTimeout: (id) => timers.delete(id) }, navigator: {}, console, AbortController,
    document: { documentElement: {}, getElementById: get, createElement: () => new Element(), querySelectorAll: () => [] },
    setTimeout: () => 1, clearTimeout() {},
    fetch: () => new Promise(() => {}), // Initial copy request stays local and pending.
    URL: { createObjectURL: () => "blob:local-audio", revokeObjectURL: (url) => revoked.push(url) },
    Audio: class {
      pause() {} removeAttribute() {} load() {} async play() {}
    },
  };
  const context = vm.createContext(sandbox);
  for (const name of ["dialogue.js", "app.js"]) {
    const source = readFileSync(path.join(__dirname, "../app/static", name), "utf8");
    vm.runInContext(source, context, { filename: name });
  }
  // Rendering details have separate static/API coverage; retain real request,
  // dialogue and audio lifecycle functions in these behavioral tests.
  vm.runInContext(`
    copy.de = { categories: {} };
    renderSafetyState = () => false;
    renderQuestionEcho = renderHistory = renderResultList = renderMap = renderCategories = () => {};
    globalThis.api = { state, dialogueUI, submitQuery, speakText, stopSpeechOutput,
      startServerRecording, stopListening, transcribeRecordedAudio, resetView, setLanguage };
  `, context);
  return { context, ...context.api, get, revoked, timers };
}

const clarification = (id) => ({
  dialog_id: id, type: "general_need", prompt: "Was brauchst du?", submit_label: "Weiter",
  multiple_facts_allowed: false, choices: [{ value: "food", label: "Essen" }],
});

function recordingClient() {
  const browser = client();
  browser.context.Blob = Blob;
  vm.runInContext(`Object.assign(copy.de, {
    voiceReady: 'ready', voiceListening: 'listening', voiceStartRecording: 'click to record',
    voiceRecording: 'recording; click to finish', voiceServiceError: 'service unavailable',
    voiceTryAgain: 'not understood', voiceDenied: 'permission denied', voiceHeard: 'heard: {text}'
  });`, browser.context);
  browser.state.serverTranscriptionAvailable = true;
  return browser;
}

test("Firefox-style Ogg recording keeps recording status and releases microphone before STT", async () => {
  const { context, state, get, startServerRecording, stopListening } = recordingClient();
  let stopped = 0;
  context.navigator.mediaDevices = { getUserMedia: async () => ({ getTracks: () => [{ stop: () => stopped++ }] }) };
  context.MediaRecorder = class {
    static isTypeSupported(type) { return type === 'audio/ogg;codecs=opus'; }
    constructor(stream, options) { this.mimeType = options.mimeType; }
    start() { this.state = 'recording'; }
    stop() {
      this.state = 'inactive';
      this.ondataavailable({ data: new Blob(['synthetic-ogg'], { type: this.mimeType }) });
      this.onstop();
    }
  };
  const requests = [];
  context.fetch = async (url, options) => {
    requests.push({ url, type: options.headers['Content-Type'] });
    assert.equal(stopped, 1);
    return { ok: true, json: async () => ({ text: 'Wo kann ich duschen?' }) };
  };
  await startServerRecording();
  assert.equal(state.isListening, true);
  assert.equal(get('voiceStatus').textContent, 'recording; click to finish');
  stopListening();
  await new Promise(setImmediate);
  assert.deepEqual(requests, [{ url: '/api/speech/transcribe?language=de', type: 'audio/ogg;codecs=opus' }]);
  assert.equal(state.mediaStream, null);
  assert.equal(get('queryInput').value, 'Wo kann ich duschen?');
  assert.equal(state.queryInputMode, 'speech');
});

test("a failed recorder constructor still releases the granted microphone", async () => {
  const { context, state, startServerRecording } = recordingClient();
  let stopped = 0;
  context.navigator.mediaDevices = { getUserMedia: async () => ({ getTracks: () => [{ stop: () => stopped++ }] }) };
  context.MediaRecorder = class {
    static isTypeSupported() { return true; }
    constructor() { throw new Error('recorder unavailable'); }
  };
  await startServerRecording();
  assert.equal(stopped, 1);
  assert.equal(state.isListening, false);
  assert.equal(state.mediaStream, null);
});

test("STT service failure differs from unintelligible or invalid audio", async () => {
  const { context, get, transcribeRecordedAudio } = recordingClient();
  for (const [status, expected] of [[503, 'service unavailable'], [422, 'not understood']]) {
    context.fetch = async () => ({ ok: false, status });
    await transcribeRecordedAudio(new Blob(['audio']));
    assert.equal(get('voiceStatus').textContent, expected);
  }
  context.fetch = async () => { throw new Error('network failed'); };
  await transcribeRecordedAudio(new Blob(['audio']));
  assert.equal(get('voiceStatus').textContent, 'service unavailable');
});

test("a successful response enables the next clarification", () => {
  const { dialogueUI, get } = client();
  const submitted = [];
  dialogueUI.onSubmit = (id) => submitted.push(id);
  dialogueUI.render(clarification("first"));
  get("clarificationChoices").children[0].handlers.click();
  dialogueUI.render(clarification("second"));
  get("clarificationChoices").children[0].handlers.click();
  assert.deepEqual(submitted, ["first", "second"]);
});

test("relocalizing an in-flight choice does not allow duplicate submission", () => {
  const { dialogueUI, get } = client();
  let submissions = 0;
  dialogueUI.onSubmit = () => submissions++;
  dialogueUI.render(clarification("first"));
  get("clarificationChoices").children[0].handlers.click();
  dialogueUI.relocalize({ prompts: {}, choices: { food: "Food" } });
  get("clarificationChoices").children[0].handlers.click();
  assert.equal(submissions, 1);
});

test("typing leaves the dialogue usable and sends no request", () => {
  const { state, dialogueUI, get } = client();
  dialogueUI.render(clarification("first"));
  get("queryInput").handlers.input();
  assert.equal(state.isSubmitting, false);
  assert.equal(dialogueUI.busy, false);
});

test("query submission is single-flight and choice payload excludes category", async () => {
  const { context, state, submitQuery } = client();
  let release;
  const requests = [];
  context.fetch = (url, options) => {
    requests.push(JSON.parse(options.body));
    return new Promise((resolve) => { release = resolve; });
  };
  state.category = "food";
  const first = submitQuery("", { dialogId: "first", values: ["food"] });
  await submitQuery("duplicate");
  assert.equal(requests.length, 1);
  assert.equal(requests[0].category, null);
  assert.deepEqual(requests[0].choice_values, ["food"]);
  release({ ok: true, json: async () => ({ answer: "Antwort", session_id: "session" }) });
  await first;
  assert.equal(state.isSubmitting, false);
  assert.equal(state.sessionId, "session");
});

test("query failure releases the guard and restores dialogue choices", async () => {
  const { context, state, dialogueUI, submitQuery } = client();
  dialogueUI.render(clarification("first"));
  context.fetch = async () => { throw new Error("offline failure"); };
  await submitQuery("Hilfe");
  assert.equal(state.isSubmitting, false);
  assert.equal(dialogueUI.busy, false);
  assert.equal(dialogueUI.active.dialog_id, "first");
});

test("TTS sends the active session and releases audio on interruption", async () => {
  const { context, state, speakText, stopSpeechOutput, revoked } = client();
  state.serverSynthesisAvailable = true;
  state.sessionId = "session-token";
  const requests = [];
  context.fetch = async (url, options) => {
    requests.push({ url, payload: JSON.parse(options.body) });
    return { ok: true, blob: async () => ({}) };
  };
  const speaking = speakText("Geprüfte Antwort");
  await new Promise(setImmediate);
  assert.deepEqual(requests, [{ url: "/api/speech/synthesize", payload: {
    text: "Geprüfte Antwort", language: "de", session_id: "session-token",
  } }]);
  assert.ok(state.currentSpeechAudio);
  stopSpeechOutput();
  await speaking;
  assert.equal(state.currentSpeechAudio, null);
  assert.deepEqual(revoked, ["blob:local-audio"]);
});

test("Start clears private content and ignores an old query without unlocking a new query", async () => {
  const { context, state, get, submitQuery, resetView } = client();
  const pending = [];
  context.fetch = (_url, options) => new Promise((resolve) => pending.push({ resolve, options }));
  state.sessionId = 'old-session';
  get('questionEchoText').textContent = 'private question';
  const old = submitQuery('private question');
  resetView();
  assert.equal(pending[0].options.signal.aborted, true);
  assert.equal(state.sessionId, null);
  assert.equal(get('questionEchoText').textContent, '');
  assert.equal(get('answerText').textContent, '');
  assert.equal(get('resultView').hidden, true);
  const current = submitQuery('new question');
  pending[0].resolve({ ok: true, json: async () => ({ answer: 'old answer', session_id: 'old-session' }) });
  await old;
  assert.equal(state.isSubmitting, true);
  assert.equal(state.sessionId, null);
  assert.notEqual(get('answerText').textContent, 'old answer');
  pending[1].resolve({ ok: true, json: async () => ({ answer: 'new answer', session_id: 'new-session' }) });
  await current;
  assert.equal(state.sessionId, 'new-session');
});

test("inactivity clears visible content, session and audio and returns to language selection", async () => {
  const { context, state, get, timers, resetView, speakText, revoked } = client();
  resetView();
  state.sessionId = 'private';
  state.serverSynthesisAvailable = true;
  context.fetch = async () => ({ ok: true, blob: async () => ({}) });
  get('answerText').textContent = 'private answer';
  get('historyList').appendChild(new Element());
  const speaking = speakText('private answer');
  await new Promise(setImmediate);
  timers.get(state.idleTimer)();
  await speaking;
  assert.equal(state.sessionId, null);
  assert.equal(get('answerText').textContent, '');
  assert.equal(get('historyList').children.length, 0);
  assert.equal(get('appView').hidden, true);
  assert.equal(get('languageView').hidden, false);
  assert.deepEqual(revoked, ['blob:local-audio']);
});

test("reset discards deferred STT success and failure", async () => {
  for (const failure of [false, true]) {
    const { context, get, resetView, transcribeRecordedAudio } = recordingClient();
    let resolve, reject;
    context.fetch = () => new Promise((yes, no) => { resolve = yes; reject = no; });
    const pending = transcribeRecordedAudio(new Blob(['private audio']));
    resetView();
    const status = get('voiceStatus').textContent;
    if (failure) reject(new Error('late failure'));
    else resolve({ ok: true, json: async () => ({ text: 'old transcript' }) });
    await pending;
    assert.equal(get('queryInput').value, '');
    assert.equal(get('voiceStatus').textContent, status);
  }
});

test("a microphone grant arriving after reset is immediately released", async () => {
  const { context, state, resetView, startServerRecording } = recordingClient();
  let grant, stopped = 0;
  context.navigator.mediaDevices = { getUserMedia: () => new Promise((resolve) => { grant = resolve; }) };
  context.MediaRecorder = class { constructor() { throw new Error('must not record'); } };
  const pending = startServerRecording();
  resetView();
  grant({ getTracks: () => [{ stop: () => stopped++ }] });
  await pending;
  assert.equal(stopped, 1);
  assert.equal(state.mediaStream, null);
  assert.equal(state.isListening, false);
});

test("reset stops recording without submitting the discarded audio", async () => {
  const { context, state, resetView, startServerRecording } = recordingClient();
  let stopped = 0, requests = 0;
  context.navigator.mediaDevices = { getUserMedia: async () => ({ getTracks: () => [{ stop: () => stopped++ }] }) };
  context.MediaRecorder = class {
    static isTypeSupported() { return true; }
    start() { this.state = 'recording'; }
    stop() { this.state = 'inactive'; this.onstop?.(); }
  };
  context.fetch = () => { requests++; throw new Error('discarded audio must not leave browser'); };
  await startServerRecording();
  resetView();
  await new Promise(setImmediate);
  assert.equal(stopped, 1);
  assert.equal(requests, 0);
  assert.equal(state.isListening, false);
});

test("a failed old query cannot replace the reset view with an error", async () => {
  const { context, state, get, resetView, submitQuery } = client();
  let reject;
  context.fetch = () => new Promise((_resolve, no) => { reject = no; });
  const pending = submitQuery('old');
  resetView();
  reject(new Error('late failure'));
  await pending;
  assert.equal(get('answerText').textContent, '');
  assert.equal(get('resultView').hidden, true);
  assert.equal(state.sessionId, null);
});

test("same playback button stops instead of issuing a second TTS call", async () => {
  const { context, state, speakText } = client();
  state.serverSynthesisAvailable = true;
  let requests = 0;
  context.fetch = async () => { requests++; return { ok: true, blob: async () => ({}) }; };
  const button = new Element();
  const speaking = speakText('answer', button);
  await new Promise(setImmediate);
  await speakText('answer', button);
  await speaking;
  assert.equal(requests, 1);
  assert.equal(state.currentSpeechAudio, null);
});

test("language change ignores a previous-language query response while retaining the session", async () => {
  const { context, state, get, submitQuery, setLanguage } = client();
  vm.runInContext('copy.en = { categories: {} };', context);
  state.sessionId = 'same-session';
  let release;
  context.fetch = (url) => url === '/api/query'
    ? new Promise((resolve) => { release = resolve; })
    : Promise.resolve({ ok: true, json: async () => ({}) });
  const pending = submitQuery('alte Frage');
  await setLanguage('en');
  release({ ok: true, json: async () => ({ answer: 'alte Antwort', session_id: 'stale' }) });
  await pending;
  assert.equal(state.language, 'en');
  assert.equal(state.sessionId, 'same-session');
  assert.notEqual(get('answerText').textContent, 'alte Antwort');
});
