<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { api } from './api'

const PRACTICE_ID = 'breathing-4-6'
const PLANNED_MS = 60_000
const RECOVERY_KEY = 'still-active-session'
const MOTION_KEY = 'still-reduce-motion'
const VOICE_KEY = 'still-spoken-cues'
const speechSupported = typeof window !== 'undefined'
  && 'speechSynthesis' in window
  && 'SpeechSynthesisUtterance' in window

const page = ref('home')
const loading = ref(false)
const historyLoading = ref(false)
const error = ref('')
const notice = ref('')
const appInfo = ref(null)
const history = ref({ sessions: [], conversations: [], messages: [] })
const crisisOpen = ref(false)
const crisisDialog = ref(null)
const reducedMotion = ref(localStorage.getItem(MOTION_KEY) === 'true')
const spokenCues = ref(speechSupported && localStorage.getItem(VOICE_KEY) === 'true')

const messageDraft = ref('')
const sendingMessage = ref(false)
const conversationId = ref(null)
const latestReply = ref(null)

const session = ref(null)
const isPaused = ref(false)
const activeMs = ref(0)
const elapsedMs = ref(0)
const segmentStart = ref(null)
const sessionStart = ref(null)
const savedActiveMs = ref(0)
const completedCycles = ref(0)
const saveState = ref('')
const completionSaving = ref(false)
let timerId = null
let lastRecoveryWrite = 0
let lastSpokenCue = ''

const phase = computed(() => {
  if (page.value !== 'exercise' || isPaused.value || activeMs.value >= PLANNED_MS) return 'paused'
  const cycleElapsed = activeMs.value % 10_000
  return cycleElapsed < 4_000 ? 'inhale' : 'exhale'
})
const secondsLeft = computed(() => {
  if (activeMs.value >= PLANNED_MS) return 0
  const cycleElapsed = activeMs.value % 10_000
  const phaseElapsed = cycleElapsed < 4_000 ? cycleElapsed : cycleElapsed - 4_000
  const phaseDuration = cycleElapsed < 4_000 ? 4_000 : 6_000
  return Math.max(1, Math.ceil((phaseDuration - phaseElapsed) / 1000))
})
const currentCycle = computed(() => Math.min(6, Math.floor(activeMs.value / 10_000) + 1))
const progressPercent = computed(() => Math.min(100, Math.floor((activeMs.value / PLANNED_MS) * 100)))
const practiceText = computed(() => phase.value === 'inhale' ? 'Inhale gently' : 'Exhale slowly')

watch(crisisOpen, async (open) => {
  if (open) {
    await nextTick()
    crisisDialog.value?.focus()
  }
})

watch([page, phase, spokenCues], ([currentPage, currentPhase, voiceEnabled]) => {
  if (!speechSupported) return
  if (!voiceEnabled || currentPage !== 'exercise' || currentPhase === 'paused') {
    window.speechSynthesis.cancel()
    lastSpokenCue = ''
    return
  }

  const cue = currentPhase === 'inhale' ? 'Inhale gently' : 'Exhale slowly'
  if (cue === lastSpokenCue) return
  window.speechSynthesis.cancel()
  const utterance = new SpeechSynthesisUtterance(cue)
  utterance.rate = 0.85
  window.speechSynthesis.speak(utterance)
  lastSpokenCue = cue
})

function setError(message) {
  error.value = message || ''
}

function setNotice(message) {
  notice.value = message || ''
  if (message) window.setTimeout(() => {
    if (notice.value === message) notice.value = ''
  }, 7000)
}

function formatDuration(ms) {
  const seconds = Math.max(0, Math.round((ms || 0) / 1000))
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`
}

function formatDate(value) {
  if (!value) return 'In progress'
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

async function loadHistory() {
  historyLoading.value = true
  try {
    history.value = await api.history()
  } catch (exception) {
    setError(exception.message)
  } finally {
    historyLoading.value = false
  }
}

async function refreshInfo() {
  try {
    appInfo.value = await api.info()
  } catch {
    appInfo.value = null
  }
}

function persistRecovery() {
  if (!session.value || page.value !== 'exercise') return
  const now = Date.now()
  const currentActive = isPaused.value
    ? savedActiveMs.value
    : Math.min(PLANNED_MS, savedActiveMs.value + now - segmentStart.value)
  const currentElapsed = sessionStart.value ? Math.max(0, now - sessionStart.value) : 0
  localStorage.setItem(RECOVERY_KEY, JSON.stringify({
    id: session.value.id,
    active_duration_ms: currentActive,
    elapsed_duration_ms: currentElapsed,
    cycles_completed: Math.min(6, Math.floor(currentActive / 10_000)),
  }))
}

async function recoverInterruptedSession() {
  const raw = localStorage.getItem(RECOVERY_KEY)
  if (!raw) return
  localStorage.removeItem(RECOVERY_KEY)
  try {
    const saved = JSON.parse(raw)
    if (!saved.id) return
    await api.updateSession(saved.id, {
      status: 'interrupted',
      active_duration_ms: Math.max(0, Math.min(PLANNED_MS, saved.active_duration_ms || 0)),
      elapsed_duration_ms: Math.max(0, saved.elapsed_duration_ms || 0),
      cycles_completed: Math.max(0, Math.min(6, saved.cycles_completed || 0)),
    })
    setNotice('An unfinished breathing session was saved as interrupted. You can start again if you choose.')
  } catch {
    setNotice('The previous exercise ended when the page closed. Its latest progress may not have been saved.')
  }
}

function stopTimer() {
  if (timerId !== null) window.clearInterval(timerId)
  timerId = null
}

function startTimer() {
  stopTimer()
  segmentStart.value = Date.now()
  timerId = window.setInterval(() => {
    if (isPaused.value || !segmentStart.value) return
    const now = Date.now()
    activeMs.value = Math.min(PLANNED_MS, savedActiveMs.value + now - segmentStart.value)
    elapsedMs.value = Math.max(0, now - sessionStart.value)
    completedCycles.value = Math.min(6, Math.floor(activeMs.value / 10_000))
    if (activeMs.value >= PLANNED_MS) finishExercise()
    else if (now - lastRecoveryWrite >= 1000) {
      persistRecovery()
      lastRecoveryWrite = now
    }
  }, 100)
}

async function startExercise() {
  setError('')
  // Unlock browser speech from the user's start tap before the API request awaits.
  if (spokenCues.value && speechSupported) window.speechSynthesis.resume()
  loading.value = true
  try {
    const created = await api.startSession(PRACTICE_ID)
    session.value = created
    page.value = 'exercise'
    isPaused.value = false
    activeMs.value = 0
    savedActiveMs.value = 0
    elapsedMs.value = 0
    completedCycles.value = 0
    saveState.value = ''
    sessionStart.value = Date.now()
    localStorage.setItem(RECOVERY_KEY, JSON.stringify({ id: created.id, active_duration_ms: 0, elapsed_duration_ms: 0, cycles_completed: 0 }))
    startTimer()
    await nextTick()
  } catch (exception) {
    setError(`${exception.message} The breathing steps and Crisis support remain available when the local server is running.`)
  } finally {
    loading.value = false
  }
}

async function updateServerSession(status, active = activeMs.value, elapsed = elapsedMs.value) {
  if (!session.value) return false
  try {
    await api.updateSession(session.value.id, {
      status,
      active_duration_ms: Math.round(active),
      elapsed_duration_ms: Math.round(elapsed),
      cycles_completed: Math.min(6, Math.floor(active / 10_000)),
    })
    saveState.value = 'saved'
    return true
  } catch (exception) {
    saveState.value = 'error'
    setError(`The exercise screen updated, but its latest session status could not be saved. ${exception.message}`)
    return false
  }
}

function currentTimes() {
  const now = Date.now()
  const active = isPaused.value
    ? savedActiveMs.value
    : Math.min(PLANNED_MS, savedActiveMs.value + (segmentStart.value ? now - segmentStart.value : 0))
  const elapsed = sessionStart.value ? Math.max(0, now - sessionStart.value) : 0
  return { active, elapsed }
}

async function pauseExercise() {
  if (!session.value || isPaused.value) return
  const times = currentTimes()
  savedActiveMs.value = times.active
  activeMs.value = times.active
  elapsedMs.value = times.elapsed
  segmentStart.value = null
  isPaused.value = true
  persistRecovery()
  const saved = await updateServerSession('paused', times.active, times.elapsed)
  if (saved) setNotice('Paused. Your time away will not count toward the exercise duration.')
}

async function resumeExercise() {
  if (!session.value || !isPaused.value) return
  isPaused.value = false
  segmentStart.value = Date.now()
  startTimer()
  const saved = await updateServerSession('in_progress')
  if (saved) setNotice('The breathing practice has resumed.')
}

async function finishExercise() {
  if (page.value !== 'exercise' || !session.value || activeMs.value < PLANNED_MS) return
  stopTimer()
  page.value = 'complete'
  const times = { active: PLANNED_MS, elapsed: sessionStart.value ? Math.max(PLANNED_MS, Date.now() - sessionStart.value) : PLANNED_MS }
  activeMs.value = PLANNED_MS
  savedActiveMs.value = PLANNED_MS
  completedCycles.value = 6
  isPaused.value = true
  segmentStart.value = null
  completionSaving.value = true
  const saved = await updateServerSession('completed', times.active, times.elapsed)
  completionSaving.value = false
  if (saved) localStorage.removeItem(RECOVERY_KEY)
  else localStorage.setItem(RECOVERY_KEY, JSON.stringify({
    id: session.value.id,
    active_duration_ms: times.active,
    elapsed_duration_ms: times.elapsed,
    cycles_completed: 6,
  }))
}

async function endExercise() {
  stopTimer()
  const times = currentTimes()
  const sessionId = session.value?.id
  const savePromise = updateServerSession('ended_early', times.active, times.elapsed)
  page.value = 'home'
  session.value = null
  sessionStart.value = null
  segmentStart.value = null
  isPaused.value = false
  const saved = await savePromise
  if (saved) localStorage.removeItem(RECOVERY_KEY)
  else if (sessionId) localStorage.setItem(RECOVERY_KEY, JSON.stringify({
    id: sessionId,
    active_duration_ms: times.active,
    elapsed_duration_ms: times.elapsed,
    cycles_completed: Math.min(6, Math.floor(times.active / 10_000)),
  }))
  setNotice('Practice ended. Your saved history records the time completed so far.')
  await loadHistory()
}

async function returnHome() {
  page.value = 'home'
  session.value = null
  sessionStart.value = null
  segmentStart.value = null
  isPaused.value = false
  await loadHistory()
}

async function sendMessage() {
  if (sendingMessage.value || !messageDraft.value.trim()) return
  setError('')
  sendingMessage.value = true
  latestReply.value = null
  try {
    const response = await api.sendMessage(messageDraft.value.trim(), conversationId.value)
    conversationId.value = response.conversation_id
    if (response.crisis_route) {
      messageDraft.value = ''
      crisisOpen.value = true
      latestReply.value = { text: response.reply, source: response.source, notice: response.notice }
    } else {
      messageDraft.value = ''
      latestReply.value = { text: response.reply, source: response.source, notice: response.notice }
    }
    await loadHistory()
  } catch (exception) {
    setError(exception.message)
  } finally {
    sendingMessage.value = false
  }
}

async function clearHistory() {
  const confirmed = window.confirm('Delete all saved fictional conversations and exercise sessions from this browser’s local database?')
  if (!confirmed) return
  setError('')
  try {
    await api.clearHistory()
    conversationId.value = null
    latestReply.value = null
    await loadHistory()
    setNotice('Saved history was deleted.')
  } catch (exception) {
    setError(exception.message)
  }
}

function goHome() {
  setError('')
  page.value = 'home'
}

function goHistory() {
  setError('')
  page.value = 'history'
  loadHistory()
}

function toggleMotion() {
  reducedMotion.value = !reducedMotion.value
  localStorage.setItem(MOTION_KEY, String(reducedMotion.value))
  document.documentElement.classList.toggle('reduce-motion', reducedMotion.value)
}

function toggleSpeech() {
  if (!speechSupported) return
  spokenCues.value = !spokenCues.value
  localStorage.setItem(VOICE_KEY, String(spokenCues.value))
}

function onVisibilityChange() {
  if (document.visibilityState === 'hidden' && page.value === 'exercise' && !isPaused.value) {
    pauseExercise()
  }
}

function onPageHide() {
  persistRecovery()
}

function onKeydown(event) {
  if (event.key === 'Escape' && crisisOpen.value) crisisOpen.value = false
}

onMounted(async () => {
  document.documentElement.classList.toggle('reduce-motion', reducedMotion.value)
  document.addEventListener('visibilitychange', onVisibilityChange)
  window.addEventListener('pagehide', onPageHide)
  window.addEventListener('keydown', onKeydown)
  await recoverInterruptedSession()
  await Promise.all([refreshInfo(), loadHistory()])
})

onBeforeUnmount(() => {
  stopTimer()
  if (speechSupported) window.speechSynthesis.cancel()
  document.removeEventListener('visibilitychange', onVisibilityChange)
  window.removeEventListener('pagehide', onPageHide)
  window.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <a class="wordmark" href="#home" @click.prevent="goHome" aria-label="Still home">still<span>.</span></a>
      <p class="topbar-note">Local coursework prototype</p>
      <nav class="top-actions" aria-label="Main navigation">
        <button class="nav-button" :aria-current="page === 'home' || page === 'exercise' || page === 'complete' ? 'page' : undefined" @click="goHome">Practice</button>
        <button class="nav-button" :aria-current="page === 'history' ? 'page' : undefined" @click="goHistory">History</button>
        <button class="crisis-button" @click="crisisOpen = true">Crisis support</button>
      </nav>
    </header>

    <div class="prototype-banner" role="note">
      For fictional classroom scenarios only. This is not mental health care, and no one is monitoring this page.
    </div>

    <main class="main-content">
      <div v-if="notice" class="notice" role="status">{{ notice }}</div>
      <div v-if="error" class="error-box" role="alert">
        <span>{{ error }}</span>
        <button class="text-button" @click="setError('')">Dismiss</button>
      </div>

      <section v-if="page === 'home'" class="home-view" aria-labelledby="home-title">
        <div class="eyebrow">A short guided meditation</div>
        <h1 id="home-title">A little room<br /><span>to breathe.</span></h1>
        <p class="home-intro">Follow a steady four-count inhale and six-count exhale. You can pause or leave whenever you choose.</p>

        <article class="practice-card">
          <div class="card-number">01</div>
          <div class="practice-copy">
            <p class="eyebrow">Paced breathing · 60 seconds</p>
            <h2>In for four, out for six</h2>
            <p>Six cycles, one cue at a time. No writing or check-in is needed.</p>
            <button class="primary-button" :disabled="loading" @click="startExercise">
              {{ loading ? 'Preparing…' : 'Begin breathing' }}
              <span aria-hidden="true">→</span>
            </button>
          </div>
          <div class="practice-art" aria-hidden="true"><div class="art-orb"></div></div>
        </article>

        <div class="home-options">
          <div class="motion-setting">
            <div>
              <strong>Motion</strong>
              <span>Choose a static cue if you prefer.</span>
            </div>
            <button class="switch-button" :aria-pressed="reducedMotion" @click="toggleMotion">
              {{ reducedMotion ? 'Static cue on' : 'Reduce animation' }}
            </button>
          </div>
          <div class="motion-setting">
            <div>
              <strong>Spoken cues</strong>
              <span>{{ speechSupported ? 'Optional inhale and exhale voice prompts.' : 'This browser does not support spoken cues; visual cues remain available.' }}</span>
            </div>
            <button class="switch-button" :aria-pressed="spokenCues" :disabled="!speechSupported" @click="toggleSpeech">
              {{ spokenCues ? 'Voice on' : 'Voice off' }}
            </button>
          </div>
          <div class="model-status">
            <span class="status-dot" :class="appInfo?.model_mode === 'live' ? 'live' : 'mock'"></span>
            <span>
              {{ !appInfo ? 'Model status unavailable' : appInfo.model_mode === 'live' ? `Gemini connected · ${appInfo.model_id}` : 'Demo reply mode · no live model key configured' }}
            </span>
          </div>
        </div>

        <section class="reflection-card" aria-labelledby="reflection-title">
          <div class="reflection-heading">
            <div>
              <p class="eyebrow">Optional · fictional examples only</p>
              <h2 id="reflection-title">Try a short check-in</h2>
            </div>
            <span class="reflection-symbol" aria-hidden="true">↗</span>
          </div>
          <p class="reflection-description">A conversational model can offer a brief reflection. It does not choose the exercise or change its steps. You can skip this.</p>
          <label class="sr-only" for="checkin">Optional fictional check-in</label>
          <textarea id="checkin" v-model="messageDraft" maxlength="500" rows="3" placeholder="Use a fictional classroom example. Do not enter personal or real distress information."></textarea>
          <div class="reflection-actions">
            <span>{{ messageDraft.length }}/500 characters</span>
            <button class="secondary-button" :disabled="sendingMessage || !messageDraft.trim()" @click="sendMessage">
              {{ sendingMessage ? 'Thinking…' : 'Get a reflection' }}
            </button>
          </div>
          <div v-if="latestReply" class="model-reply" :class="`reply-${latestReply.source}`" role="status">
            <p>{{ latestReply.text }}</p>
            <small>{{ latestReply.notice }}</small>
          </div>
        </section>

        <div class="design-note">
          <span class="note-mark" aria-hidden="true">i</span>
          <p>The breathing sequence is fixed in the app. The model cannot change its timing, steps, or your choice to stop.</p>
        </div>
      </section>

      <section v-else-if="page === 'exercise'" class="exercise-view" aria-labelledby="exercise-title">
        <div class="exercise-topline">
          <span class="exercise-title-label">Guided breathing</span>
          <span class="exercise-duration">{{ formatDuration(activeMs) }} / 1:00</span>
        </div>
        <div class="exercise-progress" role="progressbar" aria-label="Exercise progress" :aria-valuenow="progressPercent" aria-valuemin="0" aria-valuemax="100">
          <span :style="{ width: `${progressPercent}%` }"></span>
        </div>
        <div v-if="!isPaused" class="breathing-stage">
          <p class="eyebrow">Cycle {{ currentCycle }} of 6</p>
          <div class="breath-orb" :class="phase" :style="{ transitionDuration: phase === 'inhale' ? '4s' : '6s' }" aria-hidden="true"></div>
          <h1 id="exercise-title" class="breath-instruction" aria-live="polite" aria-atomic="true">{{ practiceText }}</h1>
          <div class="count-row" aria-live="off">
            <span class="count-number">{{ secondsLeft }}</span>
            <span class="count-label">{{ phase === 'inhale' ? 'seconds in' : 'seconds out' }}</span>
          </div>
          <p class="breath-helper">Let the count guide you. Keep the breath comfortable.</p>
        </div>
        <div v-else class="paused-stage">
          <div class="pause-mark" aria-hidden="true">Ⅱ</div>
          <p class="eyebrow">Paused · {{ completedCycles }} of 6 cycles</p>
          <h1 id="exercise-title">Take the time you need.</h1>
          <p>Your pause is not included in the one-minute practice.</p>
          <button class="primary-button" @click="resumeExercise">Resume practice <span aria-hidden="true">→</span></button>
        </div>
        <div class="exercise-controls">
          <button class="secondary-button" @click="isPaused ? resumeExercise() : pauseExercise()">{{ isPaused ? 'Resume' : 'Pause' }}</button>
          <button class="text-button end-button" @click="endExercise">End practice</button>
        </div>
        <p class="save-indicator" aria-live="polite">
          {{ saveState === 'saved' ? 'Session progress saved locally.' : saveState === 'error' ? 'Latest progress not saved.' : 'Crisis support stays available above.' }}
        </p>
      </section>

      <section v-else-if="page === 'complete'" class="complete-view" aria-labelledby="complete-title">
        <div class="complete-check" aria-hidden="true">✓</div>
        <p class="eyebrow">Six cycles · one minute</p>
        <h1 id="complete-title">Practice complete.</h1>
        <p>You can take a moment, try the practice again, or return to the home screen. Nothing else is required.</p>
        <div class="complete-actions">
          <button class="primary-button" :disabled="completionSaving" @click="startExercise">{{ completionSaving ? 'Saving…' : 'Begin again' }} <span aria-hidden="true">→</span></button>
          <button class="secondary-button" @click="returnHome">Return home</button>
          <button class="text-button" @click="goHistory">View saved history</button>
        </div>
        <p class="save-indicator">{{ completionSaving ? 'Saving this session locally…' : saveState === 'saved' ? 'Completed session saved to local history.' : 'Completion is shown, but the final update may not have saved.' }}</p>
      </section>

      <section v-else class="history-view" aria-labelledby="history-title">
        <div class="history-heading">
          <div>
            <p class="eyebrow">Stored on this device</p>
            <h1 id="history-title">Your history</h1>
            <p class="history-intro">Review or delete fictional practice sessions and conversations saved in the local SQLite database.</p>
          </div>
          <button v-if="history.sessions.length || history.conversations.length" class="delete-button" @click="clearHistory">Delete all history</button>
        </div>
        <div v-if="historyLoading" class="empty-state">Loading local history…</div>
        <div v-else-if="!history.sessions.length && !history.conversations.length" class="empty-state">
          <div class="empty-orb" aria-hidden="true"></div>
          <h2>No saved history yet</h2>
          <p>When you choose to practice or send an optional fictional check-in, it will appear here.</p>
          <button class="primary-button" @click="goHome">Return to practice <span aria-hidden="true">→</span></button>
        </div>
        <div v-else class="history-columns">
          <section class="history-section" aria-labelledby="sessions-heading">
            <h2 id="sessions-heading">Practice sessions <span>{{ history.sessions.length }}</span></h2>
            <article v-for="item in history.sessions" :key="item.id" class="history-card">
              <div class="history-card-top">
                <strong>4-in / 6-out breathing</strong>
                <span class="session-status" :class="`status-${item.status}`">{{ item.status.replace('_', ' ') }}</span>
              </div>
              <p>{{ formatDate(item.started_at) }}</p>
              <div class="history-meta">
                <span>Active time: {{ formatDuration(item.active_duration_ms) }}</span>
                <span>Cycles: {{ item.cycles_completed }}/6</span>
              </div>
            </article>
          </section>
          <section class="history-section" aria-labelledby="conversations-heading">
            <h2 id="conversations-heading">Conversations <span>{{ history.conversations.length }}</span></h2>
            <article v-for="thread in history.conversations" :key="thread.id" class="history-card conversation-card">
              <div class="history-card-top">
                <strong>Optional reflection</strong>
                <span>{{ formatDate(thread.updated_at) }}</span>
              </div>
              <div v-for="message in history.messages.filter((row) => row.conversation_id === thread.id)" :key="message.id" class="message-row" :class="`message-${message.role}`">
                <span class="message-role">{{ message.role === 'user' ? 'You' : message.source === 'gemini' ? 'Gemini' : message.source === 'mock' ? 'Demo' : message.source === 'fixed' ? 'Still' : 'Fallback' }}</span>
                <p>{{ message.text }}</p>
              </div>
            </article>
          </section>
        </div>
      </section>
    </main>

    <footer class="footer">
      <span>Still · Assignment 3 · localhost only</span>
      <button class="footer-crisis" @click="crisisOpen = true">Crisis support</button>
    </footer>

    <div v-if="crisisOpen" class="dialog-backdrop" @click.self="crisisOpen = false">
      <section ref="crisisDialog" class="crisis-dialog" role="dialog" aria-modal="true" aria-labelledby="crisis-title" tabindex="-1">
        <button class="dialog-close" aria-label="Close Crisis support" @click="crisisOpen = false">×</button>
        <p class="eyebrow">Independent information</p>
        <h1 id="crisis-title">Crisis support</h1>
        <p class="crisis-copy">This coursework prototype is not a crisis service. In the United States, call 911 for immediate danger. The 988 Lifeline offers call, text, and chat support. These links open outside this local app.</p>
        <div class="crisis-options">
          <a href="tel:911">Call 911 for immediate danger <span aria-hidden="true">↗</span></a>
          <a href="tel:988">Call 988 <span aria-hidden="true">↗</span></a>
          <a href="sms:988">Text 988 <span aria-hidden="true">↗</span></a>
          <a href="https://chat.988lifeline.org/" target="_blank" rel="noreferrer">Chat with the 988 Lifeline <span aria-hidden="true">↗</span></a>
        </div>
        <p class="crisis-footnote">The information above is bundled into this page and remains available if the local server or model is unavailable. Calls, texts, and external links require a compatible device or internet connection.</p>
        <button class="secondary-button" @click="crisisOpen = false">Close panel</button>
      </section>
    </div>
  </div>
</template>
