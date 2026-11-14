// Listen buttons. A line with a recorded clip (audio/<key>.m4a, made by
// `uv run voice`) plays it; any other line is read by the device's own
// Japanese voice (Web Speech API) from the build's speech text: our reading
// in kana, in phrases, so it never guesses a kanji. Buttons with neither a
// clip nor a Japanese voice stay hidden (CSS keys off html[data-speech]).
import { esc } from "./ruby.js";

const synth = "speechSynthesis" in window ? window.speechSynthesis : null;
let voice = null;

function pickVoice() {
  const ja = synth.getVoices().filter((v) => v.lang.replace("_", "-").toLowerCase().startsWith("ja"));
  voice = ja.find((v) => v.localService) || ja[0] || null;
  document.documentElement.dataset.speech = voice ? "on" : "off";
}

let playing = null;

function play(clip) {
  playing?.pause();
  synth?.cancel();
  playing = new Audio(new URL(`../../audio/${clip}.m4a`, import.meta.url));
  playing.play();
}

export function say(text) {
  playing?.pause();
  if (!synth || !voice) return;
  synth.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.voice = voice;
  u.lang = voice.lang;
  u.rate = 0.9;
  synth.speak(u);
}

const ICON = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M11 5 6 9H2v6h4l5 4z"/><path d="M15.5 8.5a5 5 0 0 1 0 7M19 5a10 10 0 0 1 0 14"/></svg>';

export const sayButton = (text, clip) => (text
  ? `<button type="button" class="listen" data-say="${esc(text)}"${clip ? ` data-clip="${esc(clip)}"` : ""} aria-label="Listen">${ICON}</button>`
  : "");

// Capture, so a listen button inside a clickable card does not also open the card.
document.addEventListener("click", (e) => {
  const b = e.target.closest("[data-say]");
  if (!b) return;
  e.stopPropagation();
  if (b.dataset.clip) play(b.dataset.clip); else say(b.dataset.say);
}, true);

if (synth) {
  pickVoice();
  synth.addEventListener("voiceschanged", pickVoice);
} else {
  document.documentElement.dataset.speech = "off";
}
