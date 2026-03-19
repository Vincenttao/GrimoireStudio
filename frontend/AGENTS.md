# FRONTEND KNOWLEDGE BASE

**Stack:** React 19 + TypeScript 5.9 + Vite 7 + Tailwind 3.4 + Framer Motion + wouter

## STRUCTURE

```
frontend/src/
├── App.tsx          # Main router + layout
├── main.tsx         # Entry point (StrictMode)
├── components/      # Reusable UI
│   ├── Sidebar.tsx         # Navigation
│   ├── MusePanel.tsx       # AI chat panel
│   ├── CharacterCard.tsx   # Character display
│   ├── CreateCharacterModal.tsx
│   └── DeleteConfirmDialog.tsx
├── pages/           # Route components
│   ├── CharactersPage.tsx
│   ├── StoryboardPage.tsx
│   ├── ArchivePage.tsx
│   └── SettingsPage.tsx
└── lib/
    ├── api.ts       # REST client
    ├── ws.ts        # WebSocket manager
    └── utils.ts     # cn(), uuid()
```

## WHERE TO LOOK

| Task | File |
|------|------|
| Add page | `pages/<Name>Page.tsx` + route in `App.tsx` |
| Add component | `components/<Name>.tsx` |
| Add API call | `lib/api.ts` |
| Add WebSocket event | `lib/ws.ts` |
| Modify theme | `tailwind.config.js`, `index.css` |

## ROUTING

Uses **wouter** (lightweight):
```tsx
<Switch>
  <Route path="/storyboard" component={StoryboardPage} />
  <Route path="/characters" component={CharactersPage} />
  <Route path="/archive" component={ArchivePage} />
  <Route path="/settings" component={SettingsPage} />
  <Route path="/"><Redirect to="/storyboard" /></Route>
</Switch>
```

## STATE MANAGEMENT

- **Local state** — `useState` in components
- **WebSocket** — `wsManager` singleton with pub/sub
- No Redux/Zustand/Jotai

**WebSocket Pattern:**
```tsx
useEffect(() => {
  const unsub = wsManager.on('STATE_CHANGE', (data) => {
    setSandboxState(data.state);
  });
  return unsub; // Cleanup
}, []);
```

## API CLIENT

`lib/api.ts` exports:
- `sandboxApi` — Spark, override, commit
- `grimoireApi` — Entity CRUD
- `storyboardApi` — Nodes, blocks
- `settingsApi` — Project config
- `museApi` — Chat stream (async generator)

## THEME (Grimoire)

Custom dark theme in `tailwind.config.js`:
- `grimoire-bg` — #0a0a0f
- `grimoire-accent` — #7c3aed (purple)
- `grimoire-gold` — #f59e0b
- Fonts: Inter, Lora (serif), JetBrains Mono

**Component Classes** (`index.css`):
- `.glass-card` — Translucent with backdrop blur
- `.btn-glow` — Primary action button
- `.btn-ghost` — Subtle button
- `.btn-danger` — Destructive action
- `.input-dark` — Dark input field

## ANIMATIONS

Framer Motion throughout:
```tsx
<motion.div
  initial={{ opacity: 0, y: 10 }}
  animate={{ opacity: 1, y: 0 }}
  exit={{ opacity: 0 }}
>
```

## CONVENTIONS

- **Props interfaces** — `{ComponentName}Props`
- **Default exports** — `export default Component`
- **Type safety** — Avoid `unknown` when possible (mirror backend types)

## KNOWN ISSUE

`SandboxState` duplicated from `backend/models.py` — keep in sync when modifying.

## DEV SERVER

```bash
npm run dev    # Port 5173, proxies /api and /ws to :8000
npm run build  # TypeScript check + Vite build
npm run lint   # ESLint
```