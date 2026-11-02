<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { api } from './api'

const BREATHING_ID = 'breathing-4-6'
const GROUNDING_ID = 'grounding-54321'
const BREATHING_MS = 60_000
const STEP_MS = 15_000
const GROUNDING_MS = 75_000
const RECOVERY_KEY = 'still-active-session'
const MOTION_KEY = 'still-reduce-motion'
const VOICE_KEY = 'still-spoken-cues'
const PROFILE_KEY = 'still-active-profile'
const speechSupported = typeof window !== 'undefined'
  && 'speechSynthesis' in window
  && 'SpeechSynthesisUtterance' in window

const EXERCISES = reactive({
  [BREATHING_ID]: {
    id: BREATHING_ID,
    name: 'Paced breathing',
    shortName: 'In for four, out for six',
    description: 'Six fixed cycles of a four-second inhale and six-second exhale.',
    kind: 'cycles',
    durationMs: BREATHING_MS,
    durationLabel: '60 seconds',
    progressLabel: 'cycles',
    progressCount: 6,
    cycleMs: 10_000,
    inhale_seconds: 4,
    exhale_seconds: 6,
    beginLabel: 'Begin breathing',
  },
  [GROUNDING_ID]: {
    id: GROUNDING_ID,
    name: '5-4-3-2-1 sensory grounding',
    shortName: 'Notice your surroundings',
    description: 'Five fixed sensory prompts, one at a time. Nothing needs to be typed.',
    kind: 'steps',
    durationMs: GROUNDING_MS,
    durationLabel: '75 seconds',
    stepSeconds: 15,
    progressLabel: 'prompts',
    progressCount: 5,
    beginLabel: 'Begin grounding',
    steps: [
      { count: 5, sense: 'see', cue: 'Notice five things you can see.' },
      { count: 4, sense: 'feel', cue: 'Notice four things you can feel.' },
      { count: 3, sense: 'hear', cue: 'Notice three things you can hear.' },
      { count: 2, sense: 'smell', cue: 'Notice two things you can smell.' },
      { count: 1, sense: 'taste', cue: 'Notice one thing you can taste.' },
    ],
  },
  'visual-anchor': {
    id: 'visual-anchor',
    name: 'Visual anchor',
    shortName: 'Focus on one object',
    description: 'Three gentle 15-second prompts to rest your gaze on one nearby object.',
    kind: 'steps',
    durationMs: 45_000,
    durationLabel: '45 seconds',
    stepSeconds: 15,
    progressLabel: 'prompts',
    progressCount: 3,
    beginLabel: 'Begin visual anchor',
    steps: [
      { cue: 'Choose one object in view, or simply rest your gaze.' },
      { cue: 'Notice one color or shape.' },
      { cue: 'Notice an edge, light, or shadow; nothing needs to be named.' },
    ],
  },
  'sound-noticing': {
    id: 'sound-noticing',
    name: 'Sound noticing',
    shortName: 'Listen to nearby sounds',
    description: 'Three gentle 15-second prompts; quiet is fine, and no sound needs to be identified.',
    kind: 'steps',
    durationMs: 45_000,
    durationLabel: '45 seconds',
    stepSeconds: 15,
    progressLabel: 'prompts',
    progressCount: 3,
    beginLabel: 'Begin sound noticing',
    steps: [
      { cue: 'Notice a sound that is nearby, if there is one.' },
      { cue: 'Notice a sound that seems farther away, or enjoy a moment of quiet.' },
      { cue: 'Let sounds come and go; you do not need to identify them.' },
    ],
  },
  'contact-points': {
    id: 'contact-points',
    name: 'Support points',
    shortName: 'Notice what supports you',
    description: 'Three gentle 15-second prompts to notice a point of support; there is nothing to change.',
    kind: 'steps',
    durationMs: 45_000,
    durationLabel: '45 seconds',
    stepSeconds: 15,
    progressLabel: 'prompts',
    progressCount: 3,
    beginLabel: 'Begin support points',
    steps: [
      { cue: 'Notice where you feel supported by the chair or floor.' },
      { cue: 'If comfortable, notice your feet or hands resting; you can choose just one point.' },
      { cue: 'Let that support be there; nothing needs to change.' },
    ],
  },
})

const page = ref('home')
const loading = ref(false)
const historyLoading = ref(false)
const profilesLoading = ref(false)
const creatingProfile = ref(false)
const error = ref('')
const notice = ref('')
const appInfo = ref(null)
const history = ref({ sessions: [], conversations: [], messages: [], recommendations: [] })
const profiles = ref([])
const profileDraft = ref('')
const selectedProfileId = ref(localStorage.getItem(PROFILE_KEY) || '')
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
const completedSteps = ref(0)
const saveState = ref('')
const completionSaving = ref(false)
let timerId = null
let lastRecoveryWrite = 0
let lastSpokenCue = ''

function plannedDuration(practiceId = session.value?.practice_id) {
  return EXERCISES[practiceId]?.durationMs || BREATHING_MS
}

function progressFor(practiceId, active) {
  const exercise = EXERCISES[practiceId]
  if (!exercise) return { cycles_completed: 0, steps_completed: 0 }
  return exercise.kind === 'cycles'
    ? { cycles_completed: Math.min(exercise.progressCount, Math.floor(active / exercise.cycleMs)), steps_completed: 0 }
    : { cycles_completed: 0, steps_completed: Math.min(exercise.progressCount, Math.floor(active / (exercise.stepSeconds * 1000))) }
}

function conversationStorageKey(profileId = selectedProfileId.value) {
  return `still-conversation-${profileId || 'anonymous'}`
}

const activeProfile = computed(() => profiles.value.find((item) => item.id === selectedProfileId.value) || null)
const activeDuration = computed(() => plannedDuration())
const activeExercise = computed(() => EXERCISES[session.value?.practice_id] || EXERCISES[BREATHING_ID])
const completeExercise = computed(() => activeExercise.value)
const currentStepIndex = computed(() => {
  const exercise = activeExercise.value
  if (exercise.kind !== 'steps') return 0
  return Math.min(Math.max(0, exercise.progressCount - 1), Math.floor(activeMs.value / (exercise.stepSeconds * 1000)))
})
const currentStep = computed(() => activeExercise.value.steps?.[currentStepIndex.value] || { cue: '' })
const phase = computed(() => {
  if (page.value !== 'exercise' || isPaused.value || activeMs.value >= activeDuration.value) return 'paused'
  if (activeExercise.value.kind !== 'cycles') return 'step'
  const inhaleMs = activeExercise.value.inhale_seconds * 1000
  return activeMs.value % activeExercise.value.cycleMs < inhaleMs ? 'inhale' : 'exhale'
})
const secondsLeft = computed(() => {
  if (activeMs.value >= activeDuration.value) return 0
  if (activeExercise.value.kind === 'steps') {
    const stepLength = activeExercise.value.stepSeconds * 1000
    const stepElapsed = activeMs.value % stepLength
    return Math.max(1, Math.ceil((stepLength - stepElapsed) / 1000))
  }
  const inhaleMs = activeExercise.value.inhale_seconds * 1000
  const exhaleMs = activeExercise.value.exhale_seconds * 1000
  const cycleElapsed = activeMs.value % activeExercise.value.cycleMs
  const phaseElapsed = cycleElapsed < inhaleMs ? cycleElapsed : cycleElapsed - inhaleMs
  const phaseDuration = cycleElapsed < inhaleMs ? inhaleMs : exhaleMs
  return Math.max(1, Math.ceil((phaseDuration - phaseElapsed) / 1000))
})
const currentCycle = computed(() => Math.min(activeExercise.value.progressCount, Math.floor(activeMs.value / activeExercise.value.cycleMs) + 1))
const currentGroundingIndex = computed(() => currentStepIndex.value)
const progressPercent = computed(() => Math.min(100, Math.floor((activeMs.value / activeDuration.value) * 100)))
const practiceText = computed(() => phase.value === 'inhale' ? 'Inhale gently' : 'Exhale slowly')
const currentRecommendation = computed(() => {
  if (latestReply.value) return latestReply.value.recommendation
  const saved = activeProfile.value?.recommendations?.[0]
  if (!saved) return null
  const exercise = EXERCISES[saved.exercise_id]
  if (!exercise) return null
  return {
    ...exercise,
    recommendation_id: saved.id,
    saved_to_profile: true,
    source: saved.source,
  }
})
const currentConversationMessages = computed(() => {
  if (!conversationId.value) return []
  return history.value.messages
    .filter((message) => message.conversation_id === conversationId.value)
    .slice(-8)
})

watch(crisisOpen, async (open) => {
  if (open) {
    await nextTick()
    crisisDialog.value?.focus()
  }
})

watch([page, phase, spokenCues, currentStep], ([currentPage, currentPhase, voiceEnabled]) => {
  if (!speechSupported) return
  if (!voiceEnabled || currentPage !== 'exercise' || isPaused.value) {
    window.speechSynthesis.cancel()
    lastSpokenCue = ''
    return
  }
  const cue = activeExercise.value.kind === 'steps'
    ? currentStep.value.cue
    : currentPhase === 'inhale' ? "Inhale gently. You've got this." : 'Exhale slowly. No rush.'
  if (cue === lastSpokenCue) return
  window.speechSynthesis.cancel()
  const utterance = new SpeechSynthesisUtterance(cue)
  const voices = window.speechSynthesis.getVoices()
  const englishVoices = voices.filter((voice) => voice.lang.toLowerCase().startsWith('en'))
  const preferredVoice = englishVoices.find((voice) => /natural|premium|enhanced|neural/i.test(voice.name))
    || englishVoices.find((voice) => voice.localService)
    || englishVoices[0]
  if (preferredVoice) {
    utterance.voice = preferredVoice
    utterance.lang = preferredVoice.lang
  }
  utterance.rate = 0.96
  utterance.pitch = 1.06
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

function exerciseFor(id) {
  return EXERCISES[id] || { name: 'Saved course exercise', shortName: 'Saved course exercise' }
}

function profileConversationFromStorage(profileId = selectedProfileId.value) {
  conversationId.value = localStorage.getItem(conversationStorageKey(profileId)) || null
}

function switchProfile(profileId) {
  const nextId = profileId || ''
  selectedProfileId.value = nextId
  if (nextId) localStorage.setItem(PROFILE_KEY, nextId)
  else localStorage.removeItem(PROFILE_KEY)
  profileConversationFromStorage(nextId)
  latestReply.value = null
  messageDraft.value = ''
}

async function loadProfiles() {
  profilesLoading.value = true
  try {
    const result = await api.profiles()
    profiles.value = result.profiles
    if (selectedProfileId.value && !profiles.value.some((item) => item.id === selectedProfileId.value)) {
      switchProfile('')
    }
  } catch (exception) {
    setError(exception.message)
  } finally {
    profilesLoading.value = false
  }
}

async function createProfile() {
  const name = profileDraft.value.trim()
  if (!name || creatingProfile.value) return
  setError('')
  creatingProfile.value = true
  try {
    const profile = await api.createProfile(name)
    profiles.value = [profile, ...profiles.value]
    profileDraft.value = ''
    switchProfile(profile.id)
    setNotice(`${profile.display_name} is selected. New recommendations will be saved to this local profile.`)
  } catch (exception) {
    setError(exception.message)
  } finally {
    creatingProfile.value = false
  }
}

async function deleteProfile(profile) {
  const confirmed = window.confirm(`Delete ${profile.display_name} and its saved recommendations? Linked exercise and conversation history will remain, without a profile label.`)
  if (!confirmed) return
  setError('')
  try {
    await api.deleteProfile(profile.id)
    localStorage.removeItem(conversationStorageKey(profile.id))
    if (selectedProfileId.value === profile.id) switchProfile('')
    await loadProfiles()
    await loadHistory()
    setNotice('Profile and its saved recommendations were deleted.')
  } catch (exception) {
    setError(exception.message)
  }
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
    const result = await api.info()
    for (const exercise of result.exercises || []) {
      const durationSeconds = exercise.duration_seconds
      const isCycles = exercise.kind === 'cycles'
      const localStepSeconds = EXERCISES[exercise.id]?.stepSeconds
      const backendStepSeconds = Number(exercise.step_seconds)
      EXERCISES[exercise.id] = {
        ...exercise,
        shortName: exercise.short_name,
        beginLabel: exercise.begin_label,
        durationMs: durationSeconds * 1000,
        durationLabel: `${durationSeconds} seconds`,
        progressLabel: isCycles ? 'cycles' : 'prompts',
        progressCount: isCycles ? exercise.cycle_count : exercise.steps.length,
        cycleMs: isCycles ? (exercise.inhale_seconds + exercise.exhale_seconds) * 1000 : 0,
        stepSeconds: isCycles ? 0 : (
          Number.isFinite(backendStepSeconds) && backendStepSeconds > 0
            ? backendStepSeconds
            : localStepSeconds || STEP_MS / 1000
        ),
        steps: exercise.steps || [],
      }
    }
    appInfo.value = result
  } catch {
    appInfo.value = null
  }
}

function persistRecovery() {
  if (!session.value || page.value !== 'exercise') return
  const now = Date.now()
  const limit = plannedDuration(session.value.practice_id)
  const currentActive = isPaused.value
    ? savedActiveMs.value
    : Math.min(limit, savedActiveMs.value + now - segmentStart.value)
  const currentElapsed = sessionStart.value ? Math.max(0, now - sessionStart.value) : 0
  localStorage.setItem(RECOVERY_KEY, JSON.stringify({
    id: session.value.id,
    practice_id: session.value.practice_id,
    active_duration_ms: currentActive,
    elapsed_duration_ms: currentElapsed,
    ...progressFor(session.value.practice_id, currentActive),
  }))
}

async function recoverInterruptedSession() {
  const raw = localStorage.getItem(RECOVERY_KEY)
  if (!raw) return
  localStorage.removeItem(RECOVERY_KEY)
  try {
    const saved = JSON.parse(raw)
    if (!saved.id) return
    const limit = plannedDuration(saved.practice_id)
    await api.updateSession(saved.id, {
      status: 'interrupted',
      active_duration_ms: Math.max(0, Math.min(limit, saved.active_duration_ms || 0)),
      elapsed_duration_ms: Math.max(0, saved.elapsed_duration_ms || 0),
      cycles_completed: Math.max(0, Math.min(EXERCISES[saved.practice_id]?.progressCount || 6, saved.cycles_completed || 0)),
      steps_completed: Math.max(0, Math.min(EXERCISES[saved.practice_id]?.progressCount || 5, saved.steps_completed || 0)),
    })
    setNotice('An unfinished exercise was saved as interrupted. You can choose a practice again if you like.')
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
    const limit = plannedDuration(session.value?.practice_id)
    activeMs.value = Math.min(limit, savedActiveMs.value + now - segmentStart.value)
    elapsedMs.value = Math.max(0, now - sessionStart.value)
    const progress = progressFor(session.value?.practice_id, activeMs.value)
    completedCycles.value = progress.cycles_completed
    completedSteps.value = progress.steps_completed
    if (activeMs.value >= limit) finishExercise()
    else if (now - lastRecoveryWrite >= 1000) {
      persistRecovery()
      lastRecoveryWrite = now
    }
  }, 100)
}

async function startExercise(practiceId = BREATHING_ID) {
  setError('')
  if (spokenCues.value && speechSupported) window.speechSynthesis.resume()
  loading.value = true
  try {
    const created = await api.startSession(practiceId, selectedProfileId.value)
    session.value = created
    page.value = 'exercise'
    isPaused.value = false
    activeMs.value = 0
    savedActiveMs.value = 0
    elapsedMs.value = 0
    completedCycles.value = 0
    completedSteps.value = 0
    saveState.value = ''
    sessionStart.value = Date.now()
    localStorage.setItem(RECOVERY_KEY, JSON.stringify({
      id: created.id,
      practice_id: practiceId,
      active_duration_ms: 0,
      elapsed_duration_ms: 0,
      cycles_completed: 0,
      steps_completed: 0,
    }))
    startTimer()
    await loadProfiles()
    await nextTick()
  } catch (exception) {
    setError(`${exception.message} The exercises and Crisis support remain available when the local server is running.`)
  } finally {
    loading.value = false
  }
}

function updateProgressFor(active) {
  return progressFor(session.value?.practice_id, active)
}

async function updateServerSession(status, active = activeMs.value, elapsed = elapsedMs.value) {
  if (!session.value) return false
  try {
    await api.updateSession(session.value.id, {
      status,
      active_duration_ms: Math.round(active),
      elapsed_duration_ms: Math.round(elapsed),
      ...updateProgressFor(active),
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
  const limit = plannedDuration(session.value?.practice_id)
  const active = isPaused.value
    ? savedActiveMs.value
    : Math.min(limit, savedActiveMs.value + (segmentStart.value ? now - segmentStart.value : 0))
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
  if (saved) setNotice('Paused. Your time away will not count toward the exercise.')
}

async function resumeExercise() {
  if (!session.value || !isPaused.value) return
  isPaused.value = false
  segmentStart.value = Date.now()
  startTimer()
  const saved = await updateServerSession('in_progress')
  if (saved) setNotice('The practice has resumed.')
}

async function finishExercise() {
  if (page.value !== 'exercise' || !session.value) return
  const limit = plannedDuration(session.value.practice_id)
  if (activeMs.value < limit) return
  stopTimer()
  page.value = 'complete'
  const times = { active: limit, elapsed: sessionStart.value ? Math.max(limit, Date.now() - sessionStart.value) : limit }
  activeMs.value = limit
  savedActiveMs.value = limit
  const progress = progressFor(session.value.practice_id, times.active)
  completedCycles.value = progress.cycles_completed
  completedSteps.value = progress.steps_completed
  isPaused.value = true
  segmentStart.value = null
  completionSaving.value = true
  const saved = await updateServerSession('completed', times.active, times.elapsed)
  completionSaving.value = false
  if (saved) localStorage.removeItem(RECOVERY_KEY)
  else localStorage.setItem(RECOVERY_KEY, JSON.stringify({
    id: session.value.id,
    practice_id: session.value.practice_id,
    active_duration_ms: times.active,
    elapsed_duration_ms: times.elapsed,
    ...progress,
  }))
  await loadHistory()
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
  else if (sessionId) persistRecovery()
  setNotice('Practice ended. Saved history records the time completed so far.')
  await loadHistory()
}

async function returnHome() {
  page.value = 'home'
  session.value = null
  sessionStart.value = null
  segmentStart.value = null
  isPaused.value = false
  await Promise.all([loadHistory(), loadProfiles()])
}

function startRecommendedExercise() {
  if (currentRecommendation.value?.id) startExercise(currentRecommendation.value.id)
}

async function sendMessage() {
  if (sendingMessage.value || !messageDraft.value.trim()) return
  setError('')
  sendingMessage.value = true
  latestReply.value = null
  try {
    let response
    try {
      response = await api.sendMessage(messageDraft.value.trim(), conversationId.value, selectedProfileId.value)
    } catch (exception) {
      // A cleared/recreated local database can leave an obsolete conversation ID in this browser.
      // The API rejects it before saving or forwarding the message, so start a fresh thread once.
      if (exception.message !== 'Conversation not found.') throw exception
      conversationId.value = null
      localStorage.removeItem(conversationStorageKey())
      response = await api.sendMessage(messageDraft.value.trim(), null, selectedProfileId.value)
    }
    conversationId.value = response.conversation_id
    localStorage.setItem(conversationStorageKey(), response.conversation_id)
    messageDraft.value = ''
    latestReply.value = {
      text: response.reply,
      source: response.source,
      notice: response.notice,
      recommendation: response.recommendation,
    }
    if (response.crisis_route) crisisOpen.value = true
    await Promise.all([loadHistory(), loadProfiles()])
  } catch (exception) {
    setError(exception.message)
  } finally {
    sendingMessage.value = false
  }
}

async function clearHistory() {
  const confirmed = window.confirm('Delete saved fictional conversations, sessions, and profile recommendations? Profiles remain, but their saved practice preference is reset.')
  if (!confirmed) return
  setError('')
  try {
    await api.clearHistory()
    conversationId.value = null
    localStorage.removeItem(conversationStorageKey(''))
    for (const profile of profiles.value) localStorage.removeItem(conversationStorageKey(profile.id))
    latestReply.value = null
    await Promise.all([loadHistory(), loadProfiles()])
    setNotice('Saved history and recommendations were deleted. Profiles remain.')
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

function goProfiles() {
  setError('')
  page.value = 'profiles'
  loadProfiles()
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
  profileConversationFromStorage()
  document.addEventListener('visibilitychange', onVisibilityChange)
  window.addEventListener('pagehide', onPageHide)
  window.addEventListener('keydown', onKeydown)
  await recoverInterruptedSession()
  await Promise.all([refreshInfo(), loadHistory(), loadProfiles()])
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
        <button class="nav-button" :aria-current="page === 'profiles' ? 'page' : undefined" @click="goProfiles">Profile</button>
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
        <p class="home-intro">Choose from five short, fixed options. Chat can guide you to one, but only you can start it.</p>

        <div class="profile-picker">
          <label for="active-profile">Saved profile</label>
          <select id="active-profile" :value="selectedProfileId" @change="switchProfile($event.target.value)">
            <option value="">No profile selected</option>
            <option v-for="profile in profiles" :key="profile.id" :value="profile.id">{{ profile.display_name }}</option>
          </select>
          <span v-if="activeProfile">Recommendations and practice choices save to {{ activeProfile.display_name }} on this device.</span>
          <span v-else>Choose a profile to save suggested exercises, or continue without one.</span>
          <button class="text-button" @click="goProfiles">Manage profiles</button>
        </div>

        <h2 class="section-heading">Choose a fixed practice</h2>
        <div class="practice-options">
          <article v-for="(exercise, index) in Object.values(EXERCISES)" :key="exercise.id" class="practice-card practice-option">
            <div class="card-number">{{ String(index + 1).padStart(2, '0') }}</div>
            <div class="practice-copy">
              <p class="eyebrow">{{ exercise.name }} · {{ exercise.durationLabel }}</p>
              <h2>{{ exercise.shortName }}</h2>
              <p>{{ exercise.description }}</p>
              <button class="primary-button" :disabled="loading" @click="startExercise(exercise.id)">
                {{ loading ? 'Preparing…' : exercise.beginLabel }}
                <span aria-hidden="true">→</span>
              </button>
            </div>
            <div class="practice-art" aria-hidden="true"><div class="art-orb"></div></div>
          </article>
        </div>

        <div class="home-options">
          <div class="motion-setting">
            <div><strong>Motion</strong><span>Choose a static cue if you prefer.</span></div>
            <button class="switch-button" :aria-pressed="reducedMotion" @click="toggleMotion">{{ reducedMotion ? 'Static cue on' : 'Reduce animation' }}</button>
          </div>
          <div class="motion-setting">
            <div><strong>Spoken cues</strong><span>{{ speechSupported ? 'Optional, upbeat prompts; voice style depends on your device.' : 'Not supported here; visual cues remain available.' }}</span></div>
            <button class="switch-button" :aria-pressed="spokenCues" :disabled="!speechSupported" @click="toggleSpeech">{{ spokenCues ? 'Voice on' : 'Voice off' }}</button>
          </div>
        </div>

        <section class="reflection-card" aria-labelledby="reflection-title">
          <div class="reflection-heading">
            <div><p class="eyebrow">Optional · fictional examples only</p><h2 id="reflection-title">Chat and find a short practice</h2></div>
            <span class="reflection-symbol" aria-hidden="true">↗</span>
          </div>
          <p class="reflection-description">Optional chat uses Google’s Gemini API when available. Still keeps all five practice scripts fixed, and you choose whether to start one.</p>
          <div v-if="currentConversationMessages.length" class="chat-thread" aria-label="Current conversation" aria-live="polite">
            <article v-for="message in currentConversationMessages" :key="message.id" class="chat-message" :class="`chat-${message.role}`">
              <span>{{ message.role === 'user' ? 'You' : 'Still' }}</span>
              <p>{{ message.text }}</p>
            </article>
          </div>
          <label class="sr-only" for="checkin">Optional fictional scenario</label>
          <textarea id="checkin" v-model="messageDraft" maxlength="500" rows="3" placeholder="Say hi or share a fictional classroom example. Do not enter personal or real distress information."></textarea>
          <div class="reflection-actions">
            <span>{{ messageDraft.length }}/500 characters</span>
            <button class="secondary-button" :disabled="sendingMessage || !messageDraft.trim()" @click="sendMessage">{{ sendingMessage ? 'Thinking…' : 'Send message' }}</button>
          </div>
          <div v-if="latestReply?.notice" class="model-reply" :class="`reply-${latestReply.source}`" role="status">
            <p>{{ latestReply.notice }}</p>
          </div>
          <article v-if="currentRecommendation" class="recommendation-card chat-recommendation">
            <div>
              <p class="eyebrow">One optional suggestion from this chat and saved activity</p>
              <h2>{{ currentRecommendation.shortName || currentRecommendation.short_name }}</h2>
              <p>{{ currentRecommendation.description }}</p>
              <small v-if="currentRecommendation.saved_to_profile && activeProfile">Saved to {{ activeProfile.display_name }}’s profile.</small>
              <small v-else>Not saved to a profile. Choose one in Profile to save future suggestions.</small>
            </div>
            <button class="primary-button" @click="startRecommendedExercise">Try suggestion <span aria-hidden="true">→</span></button>
          </article>
        </section>

        <div class="design-note">
          <span class="note-mark" aria-hidden="true">i</span>
          <p>Still can suggest only one of the five fixed practices. Every step and timer is part of the app. Chat cannot start, pause, or end a practice; you choose its button when you are ready.</p>
        </div>
      </section>

      <section v-else-if="page === 'exercise'" class="exercise-view" aria-labelledby="exercise-title">
        <div class="exercise-topline">
          <span class="exercise-title-label">{{ activeExercise.name }}</span>
          <span class="exercise-duration">{{ formatDuration(activeMs) }} / {{ formatDuration(activeDuration) }}</span>
        </div>
        <div class="exercise-progress" role="progressbar" :aria-label="`${activeExercise.name} progress`" :aria-valuenow="progressPercent" aria-valuemin="0" aria-valuemax="100"><span :style="{ width: `${progressPercent}%` }"></span></div>
        <div v-if="!isPaused && session?.practice_id === BREATHING_ID" class="breathing-stage">
          <p class="eyebrow">Cycle {{ currentCycle }} of {{ activeExercise.progressCount }}</p>
          <div class="breath-orb" :class="phase" :style="{ transitionDuration: phase === 'inhale' ? '4s' : '6s' }" aria-hidden="true"></div>
          <h1 id="exercise-title" class="breath-instruction" aria-live="polite" aria-atomic="true">{{ practiceText }}</h1>
          <div class="count-row" aria-live="off"><span class="count-number">{{ secondsLeft }}</span><span class="count-label">{{ phase === 'inhale' ? 'seconds in' : 'seconds out' }}</span></div>
          <p class="breath-helper">Let the count guide you. Keep the breath comfortable.</p>
        </div>
        <div v-else-if="!isPaused && activeExercise.kind === 'steps'" class="breathing-stage grounding-stage">
          <p class="eyebrow">Prompt {{ currentGroundingIndex + 1 }} of {{ activeExercise.progressCount }}</p>
          <div class="grounding-mark" aria-hidden="true">{{ currentStep.count || currentGroundingIndex + 1 }}</div>
          <h1 id="exercise-title" class="breath-instruction" aria-live="polite" aria-atomic="true">{{ currentStep.cue }}</h1>
          <div class="count-row" aria-live="off"><span class="count-number">{{ secondsLeft }}</span><span class="count-label">seconds for this prompt</span></div>
          <p class="breath-helper">There is nothing to type or say aloud. Any prompt can pass; pause or end whenever you choose.</p>
        </div>
        <div v-else class="paused-stage">
          <div class="pause-mark" aria-hidden="true">Ⅱ</div>
          <p class="eyebrow">Paused · {{ activeExercise.kind === 'steps' ? `${completedSteps} of ${activeExercise.progressCount} prompts` : `${completedCycles} of ${activeExercise.progressCount} cycles` }}</p>
          <h1 id="exercise-title">Take the time you need.</h1>
          <p>Your pause is not included in the planned exercise time.</p>
          <button class="primary-button" @click="resumeExercise">Resume practice <span aria-hidden="true">→</span></button>
        </div>
        <div class="exercise-controls">
          <button class="secondary-button" @click="isPaused ? resumeExercise() : pauseExercise()">{{ isPaused ? 'Resume' : 'Pause' }}</button>
          <button class="text-button end-button" @click="endExercise">End practice</button>
        </div>
        <p class="save-indicator" aria-live="polite">{{ saveState === 'saved' ? 'Session progress saved locally.' : saveState === 'error' ? 'Latest progress not saved.' : 'Crisis support stays available above.' }}</p>
      </section>

      <section v-else-if="page === 'complete'" class="complete-view" aria-labelledby="complete-title">
        <div class="complete-check" aria-hidden="true">✓</div>
        <p class="eyebrow">{{ completeExercise.durationLabel }} · {{ completeExercise.name }}</p>
        <h1 id="complete-title">Practice complete.</h1>
        <p>You can take a moment, try the practice again, or return to the home screen. Nothing else is required.</p>
        <div class="complete-actions">
          <button class="primary-button" :disabled="completionSaving" @click="startExercise(session?.practice_id || BREATHING_ID)">{{ completionSaving ? 'Saving…' : 'Begin again' }} <span aria-hidden="true">→</span></button>
          <button class="secondary-button" @click="returnHome">Return home</button>
          <button class="text-button" @click="goHistory">View saved history</button>
        </div>
        <p class="save-indicator">{{ completionSaving ? 'Saving this session locally…' : saveState === 'saved' ? 'Completed session saved to local history.' : 'Completion is shown, but the final update may not have saved.' }}</p>
      </section>

      <section v-else-if="page === 'profiles'" class="history-view profiles-view" aria-labelledby="profiles-title">
        <div class="history-heading">
          <div><p class="eyebrow">Stored on this device</p><h1 id="profiles-title">Profiles</h1><p class="history-intro">Add a local profile label. Saved exercise choices and recommendations can guide future suggestions.</p></div>
          <button class="secondary-button" @click="goHome">Return to practice</button>
        </div>
        <div class="profile-privacy-note">Use a fictional display name for class demos. Profiles are local labels, not secure accounts. Do not save real health details.</div>
        <form class="profile-form" @submit.prevent="createProfile">
          <label for="profile-name">New profile label</label>
          <div class="profile-form-row"><input id="profile-name" v-model="profileDraft" maxlength="40" placeholder="For example, Jordan (demo)" /><button class="primary-button" type="submit" :disabled="creatingProfile || !profileDraft.trim()">{{ creatingProfile ? 'Saving…' : 'Add profile' }}</button></div>
        </form>
        <div v-if="profilesLoading" class="empty-state">Loading saved profiles…</div>
        <div v-else-if="!profiles.length" class="empty-state"><div class="empty-orb" aria-hidden="true"></div><h2>No profiles yet</h2><p>Add an optional local label to save recommendations and practice choices together.</p></div>
        <div v-else class="profile-list">
          <article v-for="profile in profiles" :key="profile.id" class="profile-card">
            <div class="profile-card-heading"><div><p class="eyebrow">{{ selectedProfileId === profile.id ? 'Currently selected' : 'Saved profile' }}</p><h2>{{ profile.display_name }}</h2></div><button class="delete-button" @click="deleteProfile(profile)">Delete profile</button></div>
            <p class="profile-preference">Most recently chosen practice: <strong>{{ profile.preferred_exercise_id ? exerciseFor(profile.preferred_exercise_id).name : 'No practice selected yet' }}</strong></p>
            <div class="profile-recommendations">
              <h3>Saved recommendations <span>{{ profile.recommendations.length }}</span></h3>
              <p v-if="!profile.recommendations.length" class="profile-empty">Recommendations from a selected-profile chat will appear here.</p>
              <ul v-else><li v-for="item in profile.recommendations" :key="item.id"><span>{{ exerciseFor(item.exercise_id).name }}</span><small>{{ formatDate(item.created_at) }}</small></li></ul>
            </div>
            <button class="secondary-button" :aria-pressed="selectedProfileId === profile.id" @click="switchProfile(profile.id)">{{ selectedProfileId === profile.id ? 'Selected for this device' : `Use ${profile.display_name}` }}</button>
          </article>
        </div>
      </section>

      <section v-else class="history-view" aria-labelledby="history-title">
        <div class="history-heading">
          <div><p class="eyebrow">Stored on this device</p><h1 id="history-title">Your history</h1><p class="history-intro">Review or delete fictional practice sessions, conversations, and recommendations saved in the local SQLite database.</p></div>
          <button v-if="history.sessions.length || history.conversations.length || history.recommendations.length" class="delete-button" @click="clearHistory">Delete all history</button>
        </div>
        <div v-if="historyLoading" class="empty-state">Loading local history…</div>
        <div v-else-if="!history.sessions.length && !history.conversations.length && !history.recommendations.length" class="empty-state">
          <div class="empty-orb" aria-hidden="true"></div><h2>No saved history yet</h2><p>When you choose a practice or send an optional fictional message with a profile selected, saved activity will appear here and in that profile.</p><button class="primary-button" @click="goHome">Return to practice <span aria-hidden="true">→</span></button>
        </div>
        <div v-else class="history-columns">
          <section class="history-section" aria-labelledby="sessions-heading">
            <h2 id="sessions-heading">Practice sessions <span>{{ history.sessions.length }}</span></h2>
            <article v-for="item in history.sessions" :key="item.id" class="history-card">
              <div class="history-card-top"><strong>{{ exerciseFor(item.practice_id).name }}</strong><span class="session-status" :class="`status-${item.status}`">{{ item.status.replace('_', ' ') }}</span></div>
              <p>{{ formatDate(item.started_at) }}<span v-if="item.profile_name"> · {{ item.profile_name }}</span></p>
              <div class="history-meta"><span>Active time: {{ formatDuration(item.active_duration_ms) }}</span><span v-if="exerciseFor(item.practice_id).kind === 'cycles'">Cycles: {{ item.cycles_completed }}/{{ exerciseFor(item.practice_id).progressCount }}</span><span v-else>Prompts: {{ item.steps_completed }}/{{ exerciseFor(item.practice_id).progressCount }}</span></div>
            </article>
          </section>
          <section class="history-section" aria-labelledby="conversations-heading">
            <h2 id="conversations-heading">Conversations <span>{{ history.conversations.length }}</span></h2>
            <article v-for="thread in history.conversations" :key="thread.id" class="history-card conversation-card">
              <div class="history-card-top"><strong>Exercise suggestion chat</strong><span>{{ formatDate(thread.updated_at) }}</span></div>
              <p v-if="thread.profile_name" class="thread-profile">Profile: {{ thread.profile_name }}</p>
              <div v-for="message in history.messages.filter((row) => row.conversation_id === thread.id)" :key="message.id" class="message-row" :class="`message-${message.role}`">
                <span class="message-role">{{ message.role === 'user' ? 'You' : 'Still' }}</span><p>{{ message.text }}</p>
              </div>
            </article>
          </section>
        </div>
      </section>
    </main>

    <footer class="footer"><span>Still · Assignment 3 · localhost only</span><button class="footer-crisis" @click="crisisOpen = true">Crisis support</button></footer>

    <div v-if="crisisOpen" class="dialog-backdrop" @click.self="crisisOpen = false">
      <section ref="crisisDialog" class="crisis-dialog" role="dialog" aria-modal="true" aria-labelledby="crisis-title" tabindex="-1">
        <button class="dialog-close" aria-label="Close Crisis support" @click="crisisOpen = false">×</button>
        <p class="eyebrow">Independent information</p><h1 id="crisis-title">Crisis support</h1>
        <p class="crisis-copy">This coursework prototype is not a crisis service. In the United States, call 911 for immediate danger. The 988 Lifeline offers call, text, and chat support. These links open outside this local app.</p>
        <div class="crisis-options"><a href="tel:911">Call 911 for immediate danger <span aria-hidden="true">↗</span></a><a href="tel:988">Call 988 <span aria-hidden="true">↗</span></a><a href="sms:988">Text 988 <span aria-hidden="true">↗</span></a><a href="https://chat.988lifeline.org/" target="_blank" rel="noreferrer">Chat with the 988 Lifeline <span aria-hidden="true">↗</span></a></div>
        <p class="crisis-footnote">This information is bundled into the page and remains available if the local server or model is unavailable. Calls, texts, and external links require a compatible device or internet connection.</p><button class="secondary-button" @click="crisisOpen = false">Close panel</button>
      </section>
    </div>
  </div>
</template>
