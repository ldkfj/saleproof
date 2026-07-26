# SaleProof Design System & Tokens

Dense, data-first block explorer aesthetic optimized for protocol transparency, financial verification, and consensus auditability.

```yaml
tokens:
  color:
    background: "#0d0f12"
    surface: "#14171d"
    surface_elevated: "#1a1e26"
    border: "#262b36"
    border_focus: "#4f46e5"
    text_primary: "#f3f4f6"
    text_secondary: "#9ca3af"
    text_muted: "#6b7280"
    
    # Verdict Semantic Colors (Color + Icon + Text dual signaling)
    verdict:
      genuine:
        bg: "#064e3b"
        text: "#34d399"
        border: "#059669"
      inflated_reference:
        bg: "#78350f"
        text: "#fbbf24"
        border: "#d97706"
      deceptive:
        bg: "#7f1d1d"
        text: "#f87171"
        border: "#dc2626"
      insufficient_evidence:
        bg: "#1e3a8a"
        text: "#93c5fd"
        border: "#2563eb"

    # State Badges
    state:
      open: "#3b82f6"
      judged: "#8b5cf6"
      appealed: "#ec4899"
      final: "#10b981"
      settled: "#059669"

  spacing:
    xs: "4px"
    sm: "8px"
    md: "16px"
    lg: "24px"
    xl: "32px"

  typography:
    font_family_mono: "JetBrains Mono, Fira Code, ui-monospace, monospace"
    font_family_sans: "Inter, system-ui, -apple-system, sans-serif"
    size_xs: "11px"
    size_sm: "13px"
    size_md: "14px"
    size_lg: "16px"
    size_xl: "20px"
    size_2xl: "28px"

  radius:
    sm: "4px"
    md: "8px"
    lg: "12px"
```

## Rationale
1. **Data Density over Marketing**: Monospace typography for addresses, currency amounts, timestamps, and hashes prioritizes scannability for power users and auditors.
2. **Strict Semantic Verdict Colors**: The 4 verdict outcomes use distinct background, text, and border tokens coupled with explicit text labels and SVG icons to satisfy WCAG AA contrast and non-color-only signaling.
3. **High-Contrast Dark Baseline**: Pure dark theme background (#0d0f12) reduces eye strain when inspecting complex state machines and raw AI reasoning output.
4. **Clear Focus Boundaries**: Interactive elements feature prominent 2px focus-visible rings using `#4f46e5` for complete keyboard accessibility.
5. **No Decorative Bloat**: Standardized spacing scale (4px grid) eliminates layout shift and maintains crisp multi-column alignment down to 360px viewports.
