# 003 — Attack intensity slider in the UI

**Commit audited:** `b1cd7a8` · **Category:** Direction (demo UX) · **Effort:** S

## Why

`AttackPanel.jsx` launches every attack with a hardcoded `intensity=0.6`
(see `handleLaunch` — `launchAttack(attackType, intensity, sessionId)` is
called with the constant). The backend now varies results dynamically, so a
slider lets judges *see* intensity affecting the trust score — the strongest
interactive beat in the demo.

## Files in scope

- `frontend/src/components/attack/AttackPanel.jsx`

## Files out of scope

- `AttackButton.jsx` (already accepts an `intensity` prop)
- Backend routes (intensity is already a query param)

## Steps

1. Add `const [intensity, setIntensity] = useState(0.6);` in `AttackPanel`.
2. Render a labelled range input above the buttons:

```jsx
<div className="mb-4 flex items-center gap-3 text-xs text-slate-400">
  <span>attack intensity:</span>
  <input type="range" min="0.1" max="1" step="0.05" value={intensity}
    onChange={(e) => setIntensity(Number(e.target.value))}
    className="flex-1 accent-rose-400" />
  <span className="w-10 font-mono text-rose-300">{intensity.toFixed(2)}</span>
</div>
```

3. Pass it through: `onLaunch={handleLaunch}` already forwards to
   `AttackButton`, and `AttackButton` passes its `intensity` prop — replace
   the hardcoded `intensity={0.6}` on each `AttackButton` with
   `intensity={intensity}`.

## Done criteria

- `npm run build` green.
- Manual: set intensity to 0.95 → Coherent attack → trust drops lower than
  at 0.3; the event log line shows the higher intensity.

## Maintenance

If per-attack parameters land later (e.g. duration for replay), promote the
slider into `AttackButton` props.
