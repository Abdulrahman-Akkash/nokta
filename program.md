# program.md — Nokta v0.1

> Karpathy-style instruction file for building Nokta mobile app.
> This file IS the product spec. Humans write this, agents build from it.
> Inspired by: github.com/karpathy/autoresearch

---

## 0. IMMUTABLE INFRA

The following files are the backbone of the project. Contributors MUST NOT modify them. CI enforces this.

- `.github/workflows/`: CI pipeline. Modifying this breaks the ratchet. Only maintainer can edit.
- `scripts/section_score.py`: The scoring engine. Changing this would let PRs game the metric.
- `checklists/*.yml`: Scoring rubrics. These define truth. Only maintainer edits.
- `app.json`: Expo app identity. Changing this breaks builds for everyone.
- `tsconfig.json`: TypeScript strictness settings. Loosening these defeats type safety.
- `babel.config.js`: Transpilation config. Touching this causes phantom build errors.
- `.eslintrc.js`: Lint rules. These are hard gates in CI; changing them bypasses quality control.
- `package.json`: Only maintainer may add/remove dependencies. Contributors propose via issue.
- `jest.config.js`: Test harness structure. Changing this circumvents testing standard gates.

**Why:** Karpathy's pattern works because infrastructure is fixed and only the editable surface changes. These files are the fixed infrastructure. Everything else is the editable surface.

---

## 1. IDENTITY

Nokta is a mobile app that captures idea sparks as small as a single word and matures them into structured product specs through guided questioning. It is not a chatbot, not a note-taking app, not a general-purpose AI assistant. It is an idea incubator.

The user starts with a dot — a single word, a fragment, a hunch. The system asks targeted questions. The dot becomes a line (a title), then a paragraph (a problem statement), then a page (a full spec with audience, solution, metrics, and effort estimate). The metaphor is cosmological: a singularity expands into a universe.

Target user: anyone with ideas but no structured process to mature them — founders, students, researchers, product managers.

Nokta is NOT:
- A general chatbot (conversations are structured interrogations, not open-ended)
- A note-taking app (the system actively challenges and shapes your input)
- A project management tool (it ends at spec, not at execution)
- A code generator (it produces specs, not software — the agent layer comes later)

---

## 2. SETUP PROTOCOL

**Target: Running app + passing tests in under 5 minutes.**

### Prerequisites

- Node.js >= 18.x, npm >= 9.x
- Expo CLI: `npm install -g expo-cli` (or use npx)
- Git configured with GitHub access
- Physical device with Expo Go OR Android emulator / iOS simulator

### Init

```bash
npx create-expo-app nokta --template blank-typescript
cd nokta
```

### Install Dependencies

Only these dependencies are permitted for v0.1. Adding new ones requires a maintainer-approved issue.

```bash
# Core
npx expo install expo-router expo-constants expo-linking expo-status-bar

# Storage
npx expo install @react-native-async-storage/async-storage

# Dev/Test
npm install --save-dev jest @testing-library/react-native @types/jest typescript
```

### Folder Structure

```
nokta/
├── app/                          # Expo Router screens
│   ├── _layout.tsx               # Root layout with navigation
│   ├── index.tsx                 # Screen 1: Idea List (Home)
│   ├── idea/
│   │   ├── [id].tsx              # Screen 2: Idea Chat (Refinement)
│   │   └── spec/[id].tsx         # Screen 3: Idea Spec Card
├── src/
│   ├── features/
│   │   └── idea/
│   │       ├── components/       # UI components for idea feature
│   │       ├── services/         # LLM service, storage service
│   │       ├── hooks/            # Custom hooks (useIdea, useChat)
│   │       ├── types.ts          # TypeScript interfaces (source of truth)
│   │       └── __tests__/        # Co-located tests
│   ├── config/
│   │   ├── screens.json          # UI config (lightweight backend-driven UI)
│   │   └── features.ts           # Feature flags
│   ├── mock/
│   │   ├── llm-responses.json    # Mock LLM transcripts for testing
│   │   └── golden-ideas.json     # Golden test fixtures
│   └── services/
│       └── llm.ts                # LLM abstraction (mock/live switch)
├── scripts/                      # CI scoring scripts
├── checklists/                   # Section scoring YAMLs
├── program.md                     # This file
├── app.json
├── tsconfig.json
└── package.json
```

### Verify Setup

```bash
npm test                    # Jest tests pass
npx expo start              # App launches without crash
npx tsc --noEmit            # TypeScript compiles clean
npx eslint . --ext .ts,.tsx # Lint passes
```

All four commands must pass before any PR is opened.

---

## 3. NON-GOALS

These are explicitly out of scope for v0.1. Building any of these will result in PR rejection.

- **Backend server** — No Express, no NestJS, no Supabase server. All data is local (AsyncStorage). Reason: reduces infrastructure complexity to zero; students focus on product logic.
- **Authentication / login** — No user accounts, no OAuth, no JWT. The app is single-user, local-first. Reason: auth adds 2+ weeks of work and is irrelevant to the core idea-maturation flow.
- **App Store / Play Store publish** — No EAS Build, no signing, no store listing. APK is for demo only. Reason: store submission is a distraction from product iteration.
- **Real-time collaboration** — No multiplayer, no shared ideas, no WebSocket. Reason: single-user MVP must work perfectly before multi-user.
- **Payment / monetization** — No in-app purchases, no subscriptions, no ads. Reason: premature monetization kills MVP focus.
- **Analytics / telemetry** — No Mixpanel, no Amplitude, no crash reporting. Reason: adds dependency weight and privacy concerns for zero v0.1 value.
- **Offline-first sync** — Data lives in AsyncStorage, period. No conflict resolution, no delta sync. Reason: sync is a hard distributed systems problem — defer to v0.2+.
- **Internationalization (i18n)** — English only for v0.1. Turkish can be added in v0.2. Reason: i18n adds string management overhead that slows iteration.

---

## 4. DATA CONTRACTS

These TypeScript interfaces are the single source of truth. All components, services, and tests reference these types. They live in `src/features/idea/types.ts`.

```typescript
// === MATURITY STAGES ===

export enum MaturityStage {
  DOT = "dot",
  LINE = "line",
  PARAGRAPH = "paragraph",
  PAGE = "page",
}

// === CORE ENTITIES ===

export interface Idea {
  id: string;
  title: string;
  spark: string;
  maturity: MaturityStage;
  messages: Message[];
  spec: IdeaSpec | null;
  createdAt: string;
  updatedAt: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  turnNumber: number;
}

export interface IdeaSpec {
  problem: string;
  audience: string;
  solution: string;
  successMetrics: string;
  effortEstimate: string;
  uniqueness: string;
}

// === MATURITY TRANSITION RULES ===

export interface MaturityRule {
  from: MaturityStage;
  to: MaturityStage;
  requiredFields: (keyof IdeaSpec)[];
  minTurns: number;
}

export const MATURITY_RULES: MaturityRule[] = [
  { from: MaturityStage.DOT, to: MaturityStage.LINE, requiredFields: [], minTurns: 1 },
  { from: MaturityStage.LINE, to: MaturityStage.PARAGRAPH, requiredFields: ["problem", "audience"], minTurns: 3 },
  { from: MaturityStage.PARAGRAPH, to: MaturityStage.PAGE, requiredFields: ["problem", "audience", "solution", "successMetrics", "effortEstimate", "uniqueness"], minTurns: 5 },
];

// === STORAGE SCHEMA ===
// AsyncStorage keys: @nokta/ideas → string[] (ID list), @nokta/idea/<uuid> → Idea JSON
// All reads/writes go through src/features/idea/services/storage.ts
// Direct AsyncStorage access from components is FORBIDDEN.
```

---

## 5. SCREEN & FEATURE SPEC

### User Journey (canonical)

The primary flow starts with a spark and ends at a structured spec. Every screen transition is router-driven via Expo Router.

```
Open app → See idea list (empty state on first launch)
  → Tap FAB (+) → Enter spark ("drone cargo delivery")
  → System creates DOT → Navigate to Idea Chat
  → LLM asks: "What problem does this idea solve?"
  → User answers → Maturity: DOT → LINE
  → LLM asks: "Who experiences this problem the most?"
  → User answers → LLM asks more → Maturity: LINE → PARAGRAPH
  → Continue until PARAGRAPH → PAGE
  → Navigate to Spec Card → See structured spec
  → Return to list → See updated maturity indicator
```

**Navigation flow summary (Expo Router):**
- `router.push('/idea/[id]')` — Home → Chat
- `router.push('/idea/spec/[id]')` — Chat → Spec Card
- `router.back()` — returns to previous screen in navigation stack

### Screen 1: Idea List (Home) — `app/index.tsx`

The home screen renders all ideas using a `FlatList` for performant scrolling. Each idea appears as a card showing title, spark preview, maturity badge, and timestamp.

Components:
- `FlatList` — renders `IdeaCard` items via `keyExtractor` by id, sorted by `updatedAt` desc
- `IdeaCard` — title, spark preview (max 50 chars), `MaturityBadge`, relative timestamp
- `MaturityBadge` — ● gray/DOT, ━ yellow/LINE, ¶ blue/PARAGRAPH, 📄 green/PAGE
- `EmptyState` — "Start with a dot." + pulsing dot animation, visible when FlatList data is empty
- `FAB` — floating Button at bottom-right; opens bottom sheet with `TextInput` for spark entry

Behavior: FlatList sorted by `updatedAt` desc. Tap card → `router.push('/idea/[id]')`. Long-press → delete confirmation dialog → confirm → remove from Zustand store and AsyncStorage. FAB → bottom sheet → type spark → send → create DOT idea → auto-navigate to Chat via router.

Acceptance Criteria:
- GIVEN no ideas WHEN app opens THEN empty state shown with FAB visible
- GIVEN 5 ideas WHEN app opens THEN all 5 cards visible in FlatList, sorted by updatedAt desc
- GIVEN user taps FAB and types "drone delivery" WHEN user presses send THEN new DOT idea created and chat opens
- GIVEN user long-presses idea WHEN delete confirmed THEN idea removed from list and storage
- GIVEN user returns from Chat WHEN maturity changed THEN IdeaCard shows updated MaturityBadge
- GIVEN device storage is empty WHEN app first opens THEN EmptyState renders without crash

### Screen 2: Idea Chat (Refinement) — `app/idea/[id].tsx`

SMS-style chat screen where the system guides idea refinement through structured questioning. This is the core interaction flow of Nokta.

Components:
- `ChatBubble` — user messages right/blue; assistant messages left/gray
- `MessageInput` — TextInput + send Button; disabled and shows loading indicator while LLM responds
- `MaturityProgress` — top bar progress indicator: dot→line→paragraph→page, color-coded per stage
- `SpecPreviewButton` — Button that calls `router.push('/idea/spec/[id]')`; appears at PARAGRAPH+ only

Behavior: First load with no messages → LLM service called → system question displayed as first bubble. Each user message triggers LLM call → next question returned. Maturity transitions automatically per `MATURITY_RULES`. Transition toast: "Your idea is now a line! 🎉". Messages persisted after each turn. FlatList auto-scrolls to bottom on new message. On LLM timeout: fallback response shown, input re-enabled.

Acceptance Criteria:
- GIVEN new DOT idea WHEN chat opens THEN system's first message visible in FlatList
- GIVEN 3 answered questions WHEN maturity rules met THEN maturity transitions automatically and toast shown
- GIVEN maturity is PARAGRAPH WHEN user views chat THEN SpecPreviewButton visible
- GIVEN user closes/reopens chat WHEN messages existed THEN all messages restored from storage
- GIVEN LLM is loading WHEN user tries to send THEN send Button is disabled until response arrives
- GIVEN LLM request times out WHEN waiting for response THEN fallback message shown, no crash, input re-enabled
- GIVEN idea reaches PAGE WHEN maturity transition occurs THEN MaturityProgress shows full completion

### Screen 3: Idea Spec Card — `app/idea/spec/[id].tsx`

Read-only structured spec view showing the matured result of the chat flow. All six IdeaSpec fields are displayed with clear labels.

Components:
- `SpecField` — labeled field component rendered for each of: Problem, Audience, Solution, Success Metrics, Effort Estimate, Uniqueness
- `MaturityBadge` — shows current maturity stage at top of screen
- `SparkOrigin` — displays "Your starting point: [spark]" to anchor the idea to its origin dot
- `ShareButton` — Button that copies full spec as formatted markdown to clipboard, then shows success toast

Behavior: Six `SpecField` components rendered; unpopulated fields show "Not yet defined" in muted style. Data always reflects latest Zustand store state (live updates when returning from chat). Share flow: format all fields as markdown → copy to clipboard → show "Copied!" toast. Navigation: `router.back()` returns to Chat screen.

Acceptance Criteria:
- GIVEN PAGE maturity WHEN spec opens THEN all 6 SpecField components show populated content
- GIVEN LINE maturity WHEN spec opens THEN available fields show content, rest show "Not yet defined"
- GIVEN user taps share WHEN spec has content THEN formatted markdown copied and "Copied!" toast shown
- GIVEN user taps share WHEN spec has empty fields THEN only populated fields included in copied text
- GIVEN user navigates back from Spec Card to Chat WHEN new answers given THEN Spec Card reflects updates on next visit
- GIVEN spec card opened WHEN SparkOrigin rendered THEN original spark text visible at top of screen

---

## 6. UI CONFIG

Nokta uses a lightweight local config system. This is NOT a remote server — it is a local `config/screens.json` that controls screen layout. The app shell reads this to render components.

### Config Schema

```json
{
  "version": "0.1.0",
  "screens": {
    "home": {
      "components": [
        { "type": "IdeaList", "props": { "sortBy": "updatedAt", "sortOrder": "desc", "showMaturityBadge": true, "maxPreviewLength": 50 } },
        { "type": "FAB", "props": { "position": "bottom-right", "icon": "plus" } },
        { "type": "EmptyState", "props": { "message": "Start with a dot.", "showAnimation": true } }
      ]
    },
    "chat": {
      "components": [
        { "type": "MaturityProgress", "props": { "position": "top" } },
        { "type": "ChatBubble", "props": { "userColor": "#007AFF", "assistantColor": "#E5E5EA" } },
        { "type": "MessageInput", "props": { "placeholder": "Refine your idea...", "disableWhileLoading": true } }
      ]
    },
    "specCard": {
      "components": [
        { "type": "SparkOrigin", "props": { "highlighted": true } },
        { "type": "SpecField", "props": { "fields": ["problem", "audience", "solution", "successMetrics", "effortEstimate", "uniqueness"], "emptyText": "Not yet defined" } },
        { "type": "ShareButton", "props": { "format": "markdown" } }
      ]
    }
  }
}
```

### Component Mapping

```typescript
// src/config/component-map.ts
const COMPONENT_MAP: Record<string, React.ComponentType<any>> = {
  IdeaList: IdeaListComponent,
  FAB: FABComponent,
  EmptyState: EmptyStateComponent,
  MaturityProgress: MaturityProgressComponent,
  ChatBubble: ChatBubbleComponent,
  MessageInput: MessageInputComponent,
  SparkOrigin: SparkOriginComponent,
  SpecField: SpecFieldComponent,
  ShareButton: ShareButtonComponent,
};
```

### Feature Flags

```typescript
// src/config/features.ts
export const FEATURES = {
  MOCK_LLM: true,
  SHOW_MATURITY_ANIMATION: true,
  ENABLE_DELETE: true,
  ENABLE_SHARE: true,
  MAX_IDEAS: 50,
  LLM_TIMEOUT_MS: 10000,
} as const;
```

**Note:** Full remote config (fetching screens.json from server) is deferred to v0.2.

---

## 7. LLM CONTRACT

The LLM asks structured refinement questions. In CI/testing: MOCK mode. In production: real API.

### Mock Mode (Default)

When `FEATURES.MOCK_LLM` is `true`, returns deterministic responses. No API calls.

```typescript
// src/services/llm.ts
export async function getNextQuestion(idea: Idea, messages: Message[]): Promise<string> {
  if (FEATURES.MOCK_LLM) return getMockResponse(idea.maturity, messages.length);
  return callLiveAPI(idea, messages);
}
```

### Mock Response Map

```json
{
  "dot_turn_0": "Interesting spark! What real-world problem does this idea solve? Who faces this problem?",
  "dot_turn_2": "I see. Who suffers from this problem the most? Can you define your target audience?",
  "line_turn_4": "Audience is clear. Now let's make your solution concrete — how exactly will you solve this problem?",
  "line_turn_6": "Solution is taking shape. How will you measure success? What metrics prove your idea works?",
  "paragraph_turn_8": "Great metrics. What is the key differentiator that sets this idea apart from similar ones?",
  "paragraph_turn_10": "Your idea is now a complete spec! Can you estimate the effort? (S/M/L/XL)",
  "fallback": "Can you elaborate on that? More detail will help us refine your idea further."
}
```

### Golden Transcripts

**Transcript 1: "Drone Cargo"**
```
User: drone cargo delivery
Assistant: Interesting spark! What real-world problem does this idea solve?
User: Last-mile delivery is too expensive, especially in rural areas
Assistant: Who suffers from this problem the most?
User: E-commerce customers in rural areas and small logistics companies
Assistant: Let's make your solution concrete — how will you solve it?
User: Autonomous drone fleet, sub-5kg packages from central depots, 30-min delivery
Assistant: How will you measure success?
User: 60% reduction in cost per delivery, average delivery under 30 minutes
Assistant: What sets this idea apart from similar ones?
User: Existing drone companies focus on urban areas, we optimize for rural
Assistant: Effort estimate?
User: XL
→ MaturityStage.PAGE
```

**Transcript 2: "Student Budget App"**
```
User: student budget tracker
Assistant: What problem does this idea solve?
User: Students run out of money by end of month
Assistant: Who suffers from this problem the most?
User: University students aged 18-25
Assistant: Let's make your solution concrete.
User: SMS-based micro-reminders + weekly budget report
Assistant: How will you measure success?
User: 70% of users retain more than 10% of their budget by end of month
Assistant: What sets this apart from similar ones?
User: Existing apps are too complex; this is as simple as SMS
Assistant: Effort estimate?
User: S
→ MaturityStage.PAGE
```

**Transcript 3: "Academic Plagiarism Detector"**
```
User: AI-powered academic plagiarism detection
Assistant: What problem does this idea solve?
User: Existing plagiarism tools cannot catch AI-generated text
Assistant: Who suffers from this problem the most?
User: University professors and journal editors
Assistant: Let's make your solution concrete.
User: Hybrid detection using stylometric analysis + LLM fingerprinting
Assistant: How will you measure success?
User: 95%+ accuracy, less than 5% false positive rate
Assistant: What sets this apart from similar ones?
User: Turnitin does text matching; we add writing style analysis
Assistant: Effort estimate?
User: L
→ MaturityStage.PAGE
```

### Prompt Template (Live Mode)

```
You are Nokta, an idea maturation assistant. Ask ONE focused question at a time.

Current maturity: {{maturity}}
Populated fields: {{populated_fields}}
Missing fields: {{missing_fields}}
Turn: {{turn_number}}

Rules:
1. ONE question per response. Never multiple.
2. Target the next missing spec field.
3. Be specific. No vague "tell me more."
4. When all fields populated, congratulate and summarize.
5. Respond in user's language.
6. Under 50 words.
```

### Rate Limit & Fallback
- Timeout: 10s (`FEATURES.LLM_TIMEOUT_MS`)
- On error: return fallback mock response
- Max 20 LLM calls per idea per session
- Exceeded: "Enough iteration for today. Let's continue tomorrow!"

---

## 8. OBJECTIVE FUNCTION

### Hard Gates (Binary — fail any = instant reject)

| Gate | Command | Pass Condition |
|------|---------|----------------|
| TypeScript | `npx tsc --noEmit` | Zero errors |
| ESLint | `npx eslint . --ext .ts,.tsx` | Zero errors |
| Bundle Size | `npx expo export --dump-sourcemap` | JS bundle < 2MB |
| Dep Lock | `diff package.json` | No unauthorized new deps |

### Scalar Metric: Golden Flow Pass Rate

```
metric = (passing_golden_flow_tests / total_golden_flow_tests) × 100
```

Golden flow tests (Jest + React Native Testing Library):
1. **Create Idea** — FAB → enter spark → DOT idea created
2. **Refinement** — Chat opens → system question → answer → maturity transitions
3. **Spec View** — Spec card → populated fields match conversation
4. **Persistence** — Create → close → reopen → data intact

### Merge Rule

**PR merges if: all hard gates pass AND golden_flow_pass_rate(PR) ≥ golden_flow_pass_rate(main).**

---

## 9. THE RATCHET LOOP

```
Push code → PR opened
    ↓
CI triggers
    ↓
Hard Gates: tsc → eslint → bundle → deps
    ├── ANY FAIL → ❌ REJECT (stop)
    └── ALL PASS ↓
Golden Flow Tests
    ├── pr_score = run tests on PR
    ├── main_score = run tests on main
    └── pr_score >= main_score?
        ├── YES → ✅ ELIGIBLE
        └── NO  → ❌ REJECT: "Score {pr}% < main {main}%"
    ↓
Auto-merge (squash)
    ↓
New baseline established
```

**Score never drops. This is the ratchet.**

Merge queue: one PR at a time. After merge, remaining PRs re-run against new main.

Fail message posted as PR comment with gate results + score comparison + action required.

**Queue enforcement details:**
- The active PR is treated as the lock holder; maintainers never merge around it.
- Waiting PRs automatically receive a fresh CI run after the lock holder merges.
- Manual overrides are forbidden; skipping the queue would break the ratchet math.

**Rerun + rescore protocol:**
1. Pull latest main, rebase, and resolve conflicts locally.
2. Re-run hard gates locally to catch failures faster than CI.
3. Push fixes; the sticky CI comment refreshes its section score delta table in-place.

Every `git push` re-triggers CI. Fix → push → wait.

---

## 10. CONTRIBUTION PROTOCOL

### Branch Naming
```
feature/<short-description>    # feature/idea-list-screen
fix/<short-description>        # fix/maturity-transition-bug
test/<short-description>       # test/golden-flow-persistence
improve/<short-description>    # improve/mobile-md-section-7
```

### Commit Format (Conventional Commits)
```
feat(screen-home): add idea list with maturity badges
test(golden-flow): add persistence flow test
fix(service-llm): handle timeout in mock mode
docs(mobile-md): improve LLM contract section
```

### PR Template

```markdown
## What Changed
[Brief description]

## Evidence (REQUIRED for code PRs)
- [ ] 📸 Screenshot(s) of working feature
- [ ] 🎥 YouTube short / screen recording (< 60 seconds)
- [ ] 📦 APK download link (Google Drive / GitHub Release)
- [ ] 📱 QR code for Expo Go (if applicable)

## Checklist
- [ ] All hard gates pass locally (tsc, eslint, bundle)
- [ ] Golden flow tests pass locally
- [ ] No new dependencies added
- [ ] No immutable files modified
- [ ] PR is ≤ 10 files, ≤ 500 lines changed
```

### Quarantine (Manual Review Required)
- `.github/workflows/` changes
- `package.json` / `package-lock.json` changes
- `app.json`, `tsconfig.json` changes
- `scripts/`, `checklists/` changes
- Any file containing API keys or secrets

### Size Limits
- Max 10 files changed per PR
- Max 500 lines changed per PR
- Exceeding → auto-reject: "PR too large. Break into smaller PRs."

---

## 11. ARCHITECTURAL INVARIANTS

### State Management
- **Zustand** only. All global state in `src/features/idea/store.ts`
- Components access via hooks (`useIdeaStore`)
- Direct AsyncStorage from components is FORBIDDEN

### Component Boundaries
- Idea components: `src/features/idea/components/`
- Screen files (`app/`): thin wrappers, no business logic
- Shared UI: `src/components/ui/`

### Service Layer
- LLM: `src/services/llm.ts` (single entry point)
- Storage: `src/features/idea/services/storage.ts`
- Components never call AsyncStorage or LLM directly
- Services are pure functions, no React hooks

### Naming
- Files: `kebab-case.ts` / `.tsx`
- Components: `PascalCase`
- Hooks: `useCamelCase`
- Types: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Tests: `<name>.test.ts(x)`, co-located in `__tests__/`

### Forbidden
- No module-level `let`
- No singletons with mutable state
- No `window` / `global` assignments

---

## 12. TESTING PHILOSOPHY

### Valid Test = Tests User Behavior
"If I refactored internals but kept same UX, would this test pass?" Yes → valid. No → rewrite.

### Anti-Patterns (AUTO-REJECT)
- `expect(true).toBe(true)` — tests nothing
- Snapshot spam on every component — breaks on every change
- Mock everything — if you mock storage, LLM, navigation, AND the component, you're testing nothing
- Duplicate tests with different variable names
- Tests without assertions

### Minimum Requirements
- New component → at least 1 render test
- New service function → at least 2 tests (happy + error)
- Every maturity transition → covered by test
- Every golden flow → integration test

### Golden Flow Test Example

```typescript
test("user can create a new idea from spark", async () => {
  render(<App />);
  fireEvent.press(screen.getByTestId("fab-button"));
  fireEvent.changeText(screen.getByTestId("spark-input"), "drone delivery");
  fireEvent.press(screen.getByTestId("spark-submit"));
  expect(await screen.findByText("drone delivery")).toBeTruthy();
  expect(screen.getByTestId("maturity-badge-dot")).toBeTruthy();
});
```

### Test Location
Co-located: `src/features/idea/components/__tests__/IdeaCard.test.tsx`

---

## AUTONOMY MANDATE

This file is the single source of truth. The CI is the judge. The ratchet never regresses.

If you are an AI agent: follow the spec exactly. Do not add features not described here. Do not remove constraints. Do not modify immutable files. Make the golden flow tests pass. Make the metric go up.

If you are a contributor: your job is the same. Improve the score. Ship evidence. The best version wins.

> "The human might be asleep. The CI never sleeps." — adapted from Karpathy's autoresearch
