---
name: figma-css-json
description: Use when extracting CSS properties from a Figma node as structured JSON, grouped by component parts. Applies when the user shares a Figma URL and wants design tokens, sizes, colors, and typography organized by visual sections (label, input, hint, icon, etc.).
argument-hint: '[figma-url]'
---

# figma-css-json

## Overview

Extract CSS from a Figma node as structured JSON grouped by visual parts, using `get_metadata` for real pixel sizes and `get_design_context` for visual styles. Never use Tailwind-generated sizes for component instances — they may reflect the master component, not the actual instance.

**Target node:** `$ARGUMENTS`

## Process

### Step 1 — Get visual styles

Call `get_design_context` on the root node extracted from `$ARGUMENTS`. Collect all `data-node-id` attributes from the generated code — these are your child nodes to verify.

### Step 2 — Verify sizes in parallel

For every `<instance>` node found in the generated code, call `get_metadata` in parallel. Instance sizes in Tailwind (e.g. `size-[24px]`) may come from the master component, not this usage.

### Step 3 — Merge with source-of-truth rules

| Property                                     | Source of truth      |
| -------------------------------------------- | -------------------- |
| `width`, `height` on instances               | `get_metadata`       |
| Colors, tokens, border-radius                | `get_design_context` |
| Typography (font, size, weight, line-height) | `get_design_context` |
| Layout (flex, align, justify)                | `get_design_context` |
| `gap`, `padding` (token-based)               | `get_design_context` |

### Step 4 — Output

Two sections:

1. **CSS JSON** grouped by visual parts of the component (e.g. `label`, `input.wrapper`, `input.iconLeading`, `input.placeholder`, `input.helpIcon`, `hint`)
2. **`mismatches`** — every property where `get_metadata` contradicted Tailwind

## Output format

```json
{
  "componentName": {
    "label": { ... },
    "input": {
      "wrapper": { ... },
      "content": { ... },
      "iconLeading": { ... },
      "placeholder": { ... },
      "helpIcon": { ... }
    },
    "hint": { ... }
  },
  "mismatches": [
    {
      "node": "mail-01 (3531:402967)",
      "property": "width/height",
      "tailwind": "24px (size-[24px])",
      "real": "20px (get_metadata)",
      "overwritten": true
    }
  ]
}
```

## Common Mistakes

| Mistake                                                       | Fix                                                                |
| ------------------------------------------------------------- | ------------------------------------------------------------------ |
| Using `size-[Npx]` from Tailwind for instances                | Always call `get_metadata` on instances                            |
| Attributing parent layout props (flex, shrink) to child nodes | Only include props that belong to the node itself                  |
| Calling `get_metadata` only on root (misses children)         | Call it on each `<instance>` node-id individually                  |
| Mixing `size-full` as a size value                            | `size-full` is relative — use `get_metadata` for the real px value |
