# SafariKeet design guide

SafariKeet should feel like a small instrument: obvious at first touch, calm
during use, and invisible once the words are copied. It is not a dashboard and
does not need to advertise its intelligence.

## Product principles

1. **One action owns the screen.** Record is the visual and interaction anchor.
2. **Local is a state, not a slogan.** “On this Mac” explains where work happens
   without adding privacy theater.
3. **History is a rail.** Use rows and dividers, not a grid of cards.
4. **Small windows are first-class.** The control remains reachable at 280 CSS
   pixels wide and in short landscape windows.
5. **Every state names the next action.** Record → Pause/Resume → Stop → Copy.

## Visual voice

The default theme is graphite-black with warm ivory type and one chartreuse
signal color. It is Apple-adjacent through restraint, touch geometry, and type
rhythm—not through decorative blur or copied system chrome.

### Color tokens

| Role | Dark | Light | Use |
|---|---|---|---|
| Background | `#0c0d0b` | `#f2f1e9` | App canvas |
| Surface | `#151613` | `#e9e7dc` | Controls and rows |
| Raised | `#1c1e19` | `#fcfbf5` | Sheets and selected segments |
| Primary text | `#f2efe4` | `#171813` | Content and labels |
| Muted text | `#a8a398` | `#656258` | Metadata and guidance |
| Signal | `#cdf42a` | `#96b500` | Ready, record, success |
| Destructive | `#ff8d83` | `#b6372e` | Delete and errors |

Signal color is scarce. It belongs to engine readiness, the recording control,
waveform, focus rings, and completed copy state. It is not a background theme.

## Typography

Use the Apple system stack. Display and transcript copy use slightly tight
tracking (`-0.025em` to `-0.04em`) and natural sentence case. UI chrome remains
at 12–16 px equivalent, with 600–700 weight only for action labels and status.

- Brand: 20–30 px, 650 weight.
- Transcript: fluid 23–38 px, 1.45 line height.
- Section heading: 18 px, 650 weight.
- Body: 15–16 px, 1.5–1.6 line height.
- Metadata: 12–13 px, normal weight.

## Spacing and geometry

Base spacing is 4 px. Common steps are 8, 12, 16, 24, 32, and 48 px. A
comfortable app gutter is 24 px, collapsing to 14 px at narrow widths plus
safe-area insets.

- Small radius: 12 px.
- Panel radius: 18 px.
- Sheet radius: 28 px.
- Circular record control: 190–272 px responsive diameter.
- Minimum primary touch target: 56 × 56 px.
- Minimum expanded-row action: 48 px high.

Avoid nested rounded containers. One result panel and one settings sheet are
enough elevation for the entire surface.

## Component behavior

### Recording control

- **Idle:** solid signal outline, microphone, “Record.”
- **Requesting:** disabled, “Allow mic,” precise permission guidance below.
- **Recording:** subtle breathing ring, animated bars, primary action “Pause,”
  separate Stop control with elapsed time.
- **Paused:** dashed outline, “Resume,” Stop remains present.
- **Transcribing:** quiet spinner and “Transcribing on this Mac…”
- **Success:** transcript becomes the focal point and offers Copy.
- **Error:** keep the control recoverable and state the exact corrective action.

### Transcript

Preserve line breaks. Copy is always visible at the result level. Feedback says
“Copied” for about 1.6 seconds and does not create a toast that covers content.

### History

Collapsed rows show one-line preview, duration, and local timestamp. Expanded
rows reveal complete text plus Copy and Delete. Long histories use browser
content visibility so they do not slow the recorder.

### Settings

Settings is a bottom sheet on touch devices. Theme uses a three-way segmented
control: Dark, Light, System. Engine status shows the exact chosen adapter and
model; installation and diagnostic detail belongs in health, not the main UI.

## Responsive rules

At 520 px and below, collapse the engine label to a status dot, preserve the
brand, reduce the recorder diameter, and stack history metadata beneath its
preview. At 280 px, no primary content may clip horizontally.

In landscape windows below 600 px high, use two regions: a sticky recorder on
the left and transcript/history on the right. The layout must work with iPad
window controls without putting critical actions in the extreme top-left.

All outer padding includes `env(safe-area-inset-*)`. The top-left receives an
additional optical offset in the header; no record, stop, copy, or settings
action occupies that risk zone.

## Motion and sound

Motion clarifies state only: 160 ms press response, 220 ms sheet entrance, and
a slow 1.8 s recording breath. Wave bars animate only while recording. Honor
`prefers-reduced-motion`. SafariKeet emits no UI sounds.

## Accessibility

- Maintain 4.5:1 contrast for copy and metadata text.
- Every icon-only button has a spoken label.
- Focus rings use a 3 px signal-colored outline with 3 px offset.
- Status changes and completed transcript text use live-region semantics.
- Never encode readiness or error using color alone.
- Keep the DOM reading order identical to the visual task order.

## Product language

Copy is short, literal, and calm. Prefer “Transcribing on this Mac…” over
“Processing magic.” Prefer “Microphone access is off” over “Something went
wrong.” Avoid AI claims, model hype, cloud language, and anthropomorphic copy.

## Privacy contract

The browser sends a stopped recording only to the operator’s Mac through the
private origin. The backend removes temporary audio after transcription and
stores only transcript history in the app’s private data directory. The UI and
documentation never imply that FluidVoice exposes an API or can be controlled.
