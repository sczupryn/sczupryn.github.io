const STORAGE_KEY = "quiz-history-v1";

const state = {
  subjectMeta: null,
  subject: null,
  questions: [],
  activeIndices: [],
  order: [],
  currentIndex: 0,
  score: 0,
  confirmed: false,
  mode: "full",
  sessionResults: {},
};

const $ = (sel) => document.querySelector(sel);

const screens = {
  subjects: $("#screen-subjects"),
  mode: $("#screen-mode"),
  quiz: $("#screen-quiz"),
  results: $("#screen-results"),
};

function showScreen(name) {
  Object.values(screens).forEach((el) => el.classList.remove("active"));
  screens[name].classList.add("active");
}

function shuffle(arr) {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function isAnswerCorrect(selected, answers) {
  const correctIndices = answers
    .map((a, i) => (a.correct ? i : -1))
    .filter((i) => i >= 0);

  if (correctIndices.length === 0) return selected.length === 0;

  const selectedSet = new Set(selected);
  const correctSet = new Set(correctIndices);

  if (selectedSet.size !== correctSet.size) return false;

  for (const idx of correctSet) {
    if (!selectedSet.has(idx)) return false;
  }

  return true;
}

function loadAllHistory() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
  } catch {
    return {};
  }
}

function loadSubjectHistory(subjectId) {
  return loadAllHistory()[subjectId] || null;
}

function saveSubjectHistory(subjectId, data) {
  const all = loadAllHistory();
  all[subjectId] = data;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(all));
}

function clearSubjectHistory(subjectId) {
  const all = loadAllHistory();
  delete all[subjectId];
  localStorage.setItem(STORAGE_KEY, JSON.stringify(all));
}

function getUnknownIndices(history) {
  if (!history || !Array.isArray(history.unknownIndices)) return [];
  return history.unknownIndices;
}

function ensureSubjectHistory(subjectId) {
  return loadSubjectHistory(subjectId) || {
    unknownIndices: [],
    answers: {},
  };
}

function setQuestionKnown(subjectId, questionIndex, knows) {
  const history = ensureSubjectHistory(subjectId);
  const unknownSet = new Set(getUnknownIndices(history));

  if (knows) {
    unknownSet.delete(questionIndex);
  } else {
    unknownSet.add(questionIndex);
  }

  history.unknownIndices = [...unknownSet].sort((a, b) => a - b);
  saveSubjectHistory(subjectId, history);
  return history;
}

function modeLabel(mode) {
  if (mode === "difficult") return "trudne pytania";
  return "pełny test";
}

async function loadSubjects() {
  const res = await fetch("data/subjects.json");
  const subjects = await res.json();
  const list = $("#subjects-list");
  list.innerHTML = "";

  subjects.forEach((s) => {
    const history = loadSubjectHistory(s.id);
    const unknownCount = getUnknownIndices(history).length;

    const li = document.createElement("li");
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "subject-btn";

    const badge =
      unknownCount > 0
        ? `<span class="subject-badge subject-badge-unknown">${unknownCount} trudnych</span>`
        : "";

    btn.innerHTML = `<strong>${s.name}</strong><span>${s.questionCount} pytań</span>${badge}`;
    btn.addEventListener("click", () => openModeScreen(s));
    li.appendChild(btn);
    list.appendChild(li);
  });
}

async function openModeScreen(subjectMeta) {
  const res = await fetch(subjectMeta.dataFile);
  const data = await res.json();

  state.subjectMeta = subjectMeta;
  state.subject = data;
  state.questions = data.questions;

  const history = loadSubjectHistory(data.id);
  const unknownIndices = getUnknownIndices(history);
  const total = data.questions.length;

  $("#mode-subject-name").textContent = data.name;
  $("#mode-full-count").textContent = `Wszystkie pytania (${total})`;
  $("#mode-difficult-count").textContent =
    unknownIndices.length > 0
      ? `${unknownIndices.length} pytań z błędnych odpowiedzi`
      : "Brak trudnych pytań — pojawią się po złej odpowiedzi";

  const lastResult = $("#mode-last-result");
  if (history && history.lastCompletedAt) {
    const date = new Date(history.lastCompletedAt).toLocaleString("pl-PL");
    lastResult.textContent = `Ostatnia sesja (${modeLabel(history.lastMode)}, ${date}): ${history.lastScore}/${history.lastTotal} pkt`;
    lastResult.classList.remove("hidden");
  } else {
    lastResult.classList.add("hidden");
  }

  $("#btn-mode-difficult").disabled = unknownIndices.length === 0;

  const clearBtn = $("#btn-clear-history");
  if (history) {
    clearBtn.classList.remove("hidden");
  } else {
    clearBtn.classList.add("hidden");
  }

  $("#header-subtitle").textContent = data.name;
  showScreen("mode");
}

function beginQuiz(mode) {
  const history = loadSubjectHistory(state.subject.id);
  const unknownIndices = getUnknownIndices(history);

  let activeIndices;
  if (mode === "difficult") {
    activeIndices = unknownIndices.filter((i) => i >= 0 && i < state.questions.length);
    if (activeIndices.length === 0) return;
  } else {
    activeIndices = state.questions.map((_, i) => i);
  }

  state.mode = mode;
  state.activeIndices = activeIndices;
  state.order = shuffle(activeIndices.map((_, i) => i));
  state.currentIndex = 0;
  state.score = 0;
  state.confirmed = false;
  state.sessionResults = {};

  $("#score-live").textContent = "0";
  $("#score-total").textContent = String(activeIndices.length);

  const badge = $("#quiz-mode-badge");
  if (mode === "difficult") {
    badge.textContent = "Tryb: trudne pytania";
    badge.classList.remove("hidden");
  } else {
    badge.classList.add("hidden");
  }

  showScreen("quiz");
  renderQuestion();
}

function getCurrentQuestionIndex() {
  return state.activeIndices[state.order[state.currentIndex]];
}

function getCurrentQuestion() {
  return state.questions[getCurrentQuestionIndex()];
}

function getSelectedIndices() {
  return [...document.querySelectorAll("#answers-list input:checked")].map((el) =>
    Number(el.value)
  );
}

function renderQuestion() {
  const q = getCurrentQuestion();
  const total = state.activeIndices.length;
  const num = state.currentIndex + 1;

  state.confirmed = false;

  $("#progress-fill").style.width = `${(num / total) * 100}%`;
  $("#progress-text").textContent = `Pytanie ${num} z ${total}`;
  $("#question-number").textContent = `Pytanie ${num}`;
  $("#question-text").textContent = q.question;

  const media = $("#question-media");
  const img = $("#question-image");
  if (q.image) {
    img.src = q.image;
    img.alt = "Ilustracja do pytania";
    media.classList.remove("hidden");
  } else {
    media.classList.add("hidden");
    img.removeAttribute("src");
  }

  const list = $("#answers-list");
  list.innerHTML = "";

  q.answers.forEach((ans, i) => {
    const li = document.createElement("li");
    li.className = "answer-item";

    const label = document.createElement("label");
    label.className = "answer-label";
    label.htmlFor = `ans-${i}`;

    const input = document.createElement("input");
    input.type = "checkbox";
    input.id = `ans-${i}`;
    input.value = String(i);

    const span = document.createElement("span");
    span.textContent = ans.text;

    label.appendChild(input);
    label.appendChild(span);
    li.appendChild(label);
    list.appendChild(li);
  });

  const feedback = $("#feedback");
  feedback.className = "feedback hidden";
  feedback.textContent = "";

  $("#btn-check").disabled = false;
  $("#btn-check").textContent = "Zatwierdź";
  $("#btn-next").disabled = true;
  $("#btn-next").textContent =
    state.currentIndex < state.activeIndices.length - 1 ? "Dalej" : "Zobacz wynik";
}

function confirmAnswer() {
  if (state.confirmed) return;

  const selected = getSelectedIndices();
  const q = getCurrentQuestion();
  const qIndex = getCurrentQuestionIndex();
  const correct = isAnswerCorrect(selected, q.answers);

  state.confirmed = true;
  state.sessionResults[qIndex] = {
    selected,
    correct,
    at: new Date().toISOString(),
  };

  if (correct) {
    state.score += 1;
    $("#score-live").textContent = String(state.score);
    setQuestionKnown(state.subject.id, qIndex, true);
  } else {
    setQuestionKnown(state.subject.id, qIndex, false);
  }

  const labels = document.querySelectorAll("#answers-list .answer-label");
  labels.forEach((label, i) => {
    const isCorrect = q.answers[i].correct;
    const isSelected = selected.includes(i);

    label.classList.add("disabled");
    label.querySelector("input").disabled = true;

    if (isCorrect && isSelected) {
      label.classList.add("correct");
    } else if (!isCorrect && isSelected) {
      label.classList.add("incorrect");
    } else if (isCorrect && !isSelected) {
      label.classList.add("missed");
    } else if (isCorrect) {
      label.classList.add("correct");
    }
  });

  $("#btn-check").disabled = true;

  const feedback = $("#feedback");
  feedback.classList.remove("hidden");

  if (correct) {
    feedback.className = "feedback success";
    feedback.textContent = "+1 pkt — dobrze!";
  } else {
    feedback.className = "feedback error";
    if (selected.length === 0) {
      feedback.textContent = "0 pkt — nie zaznaczono odpowiedzi. Pytanie dodano do trudnych.";
    } else {
      feedback.textContent = "0 pkt — źle. Pytanie dodano do trudnych.";
    }
  }

  $("#btn-next").disabled = true;
  window.setTimeout(() => {
    if (state.confirmed) {
      $("#btn-next").disabled = false;
    }
  }, 400);
}

function persistSessionResults() {
  const history = ensureSubjectHistory(state.subject.id);
  const answers = { ...history.answers };

  for (const [idx, r] of Object.entries(state.sessionResults)) {
    answers[idx] = {
      selected: r.selected,
      correct: r.correct,
      at: r.at,
    };
  }

  saveSubjectHistory(state.subject.id, {
    ...history,
    lastCompletedAt: new Date().toISOString(),
    lastMode: state.mode,
    lastScore: state.score,
    lastTotal: state.activeIndices.length,
    answers,
  });
}

function advanceToNext() {
  if (!state.confirmed) return;

  if (state.currentIndex < state.activeIndices.length - 1) {
    state.currentIndex += 1;
    renderQuestion();
  } else {
    persistSessionResults();
    showResults();
  }
}

function showResults() {
  const total = state.activeIndices.length;
  const pct = total > 0 ? Math.round((state.score / total) * 100) : 0;
  const unknownCount = getUnknownIndices(loadSubjectHistory(state.subject.id)).length;

  $("#results-subject").textContent = state.subject.name;
  $("#results-score").textContent = String(state.score);
  $("#results-max").textContent = String(total);
  $("#results-percent").textContent = `${pct}% poprawnych odpowiedzi`;

  const modeNote = $("#results-mode-note");
  if (state.mode === "difficult") {
    modeNote.textContent =
      unknownCount > 0
        ? `${unknownCount} trudnych pytań pozostało do powtórki.`
        : "Świetnie — opanowałeś wszystkie trudne pytania!";
  } else {
    modeNote.textContent =
      unknownCount > 0
        ? `${unknownCount} pytań zapisano jako trudne — możesz je powtórzyć osobno.`
        : "Świetnie — w tej sesji nie było błędnych odpowiedzi!";
  }
  modeNote.classList.remove("hidden");

  const difficultBtn = $("#btn-review-difficult");
  difficultBtn.disabled = unknownCount === 0;
  difficultBtn.textContent =
    unknownCount > 0 ? `Trudne pytania (${unknownCount})` : "Trudne pytania";

  showScreen("results");
}

function restartQuiz() {
  if (!state.subject) return;
  beginQuiz(state.mode);
}

function goHome() {
  $("#header-subtitle").textContent = "Wybierz przedmiot";
  state.subjectMeta = null;
  state.subject = null;
  loadSubjects();
  showScreen("subjects");
}

$("#btn-check").addEventListener("click", (e) => {
  e.preventDefault();
  confirmAnswer();
});
$("#btn-next").addEventListener("click", (e) => {
  e.preventDefault();
  if (state.confirmed && !$("#btn-next").disabled) {
    advanceToNext();
  }
});
$("#btn-restart").addEventListener("click", restartQuiz);
$("#btn-review-difficult").addEventListener("click", () => beginQuiz("difficult"));
$("#btn-home").addEventListener("click", goHome);
$("#btn-mode-full").addEventListener("click", () => beginQuiz("full"));
$("#btn-mode-difficult").addEventListener("click", () => beginQuiz("difficult"));
$("#btn-mode-back").addEventListener("click", goHome);
$("#btn-clear-history").addEventListener("click", () => {
  if (!state.subject) return;
  if (confirm("Wyczyścić zapisaną historię odpowiedzi dla tego przedmiotu w tej przeglądarce?")) {
    clearSubjectHistory(state.subject.id);
    openModeScreen(state.subjectMeta);
  }
});

document.addEventListener("keydown", (e) => {
  if (e.key !== "Enter" || !screens.quiz.classList.contains("active")) return;
  e.preventDefault();
});

loadSubjects().catch((err) => {
  console.error(err);
  $("#subjects-list").innerHTML =
    '<li><p class="hint">Nie udało się wczytać przedmiotów. Uruchom stronę przez serwer HTTP (np. GitHub Pages).</p></li>';
});
