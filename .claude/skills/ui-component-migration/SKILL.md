---
name: ui-component-migration
description: Incremental UI component migration from Evergreen UI to Radix + Tailwind CSS. Use when migrating individual components to a design system with DS prefix, ensuring visual parity through feature flags, screenshots validation, and coexistence of legacy and new implementations. Handles override detection (inline styles, className, spread props), Figma design spec consultation, and systematic replacement tracking.
---

# UI Component Migration

Incremental migration workflow for replacing Evergreen UI components with Radix + Tailwind design system components, one component at a time.

## Starting a Migration

**IMPORTANT:** When starting a new component migration, ALWAYS create the 7-step workflow as tasks using TaskCreate. This provides a clear roadmap and tracks progress.

**Use TaskCreate to create these tasks at the beginning:**

```typescript
// Example: Migrating Button component
// Replace [ComponentName] with actual component name (e.g., "Button")

const tasks = [
  {
    subject: "AUDIT - Analyze [ComponentName] usage",
    description: "Find all usages of [ComponentName], detect inline styles/className/spread props, count total occurrences, identify common prop patterns and edge cases",
    activeForm: "Auditing [ComponentName] usage across codebase"
  },
  {
    subject: "SPECS - Consult Figma for [ComponentName] design",
    description: "Query Figma MCP for variants, states, spacing/color/typography tokens. Document findings: variants, tokens mapped to Tailwind, interactive states, deviations from Evergreen",
    activeForm: "Consulting Figma specs for [ComponentName]"
  },
  {
    subject: "BUILD - Create DS[ComponentName] component",
    description: "Create component structure in src/components/ds/DS[ComponentName]/. Use Radix primitive as base, apply Tailwind classes, implement all variants, add TypeScript types, match accessibility",
    activeForm: "Building DS[ComponentName] with Radix + Tailwind"
  },
  {
    subject: "MAP - Document [ComponentName] props mapping",
    description: "Create migration-map.md with prop equivalencies (Evergreen → DS), removed props, breaking changes, before/after usage examples",
    activeForm: "Mapping props from [ComponentName] to DS[ComponentName]"
  },
  {
    subject: "MIGRATE - Replace [ComponentName] with feature flags",
    description: "Replace usage file by file with feature flag pattern. Test with flags ON/OFF. Track progress in MIGRATION_STATUS.md",
    activeForm: "Migrating [ComponentName] usage with feature flags"
  },
  {
    subject: "VALIDATE - Visual regression for [ComponentName]",
    description: "Capture before/after screenshots of all affected pages. Compare visually (layout, colors, spacing, interactive states). Document findings",
    activeForm: "Validating visual parity with screenshots"
  },
  {
    subject: "CLEANUP - Remove legacy [ComponentName] code",
    description: "Remove legacy imports, feature flag conditionals, component selector variables. Update all imports. Archive migration-map.md",
    activeForm: "Cleaning up legacy [ComponentName] code"
  }
]
```

**Task dependencies (use TaskUpdate after creating tasks):**
- Task 3 (BUILD) blockedBy Task 2 (SPECS)
- Task 4 (MAP) blockedBy Task 3 (BUILD)
- Task 5 (MIGRATE) blockedBy Task 4 (MAP)
- Task 6 (VALIDATE) blockedBy Task 5 (MIGRATE)
- Task 7 (CLEANUP) blockedBy Task 6 (VALIDATE)

**Workflow:**
1. Create all 7 tasks with TaskCreate
2. Set up dependencies with TaskUpdate using addBlockedBy
3. Start with Task 1 (AUDIT) - mark as in_progress
4. Complete each task, update status to completed
5. Move to next unblocked task

## Migration Workflow

### 1. AUDIT - Component Usage Analysis

Find all usages of the legacy component and detect customization patterns.

**Search for component imports:**
```bash
# Find all imports of the target component
grep -r "import.*{.*ComponentName.*}.*from.*evergreen-ui" src/
```

**Identify usage patterns with context:**
```bash
# Get full context of component usage
grep -r "<ComponentName" src/ -A 5 -B 2
```

**Detect overrides to watch for:**
- Inline styles: `style={{...}}`
- className additions: `className="custom-class"`
- Spread props: `{...props}`
- sx prop (if using styled-system): `sx={{...}}`

**Create audit checklist:**
- [ ] Total usage count
- [ ] Files using the component
- [ ] Common prop patterns
- [ ] Style overrides detected
- [ ] Edge cases or complex variants

### 2. SPECS - Design Specification Consultation

Consult Figma MCP to gather design specifications before building.

**Query Figma for:**
```
"Show me the [ComponentName] design specs including:
- All variants (size, color, state)
- Spacing tokens (padding, margin, gap)
- Typography tokens
- Color tokens
- Interactive states (hover, focus, disabled, active)
- Accessibility requirements"
```

**Document findings in migration notes:**
- Variants: List all design variants
- Tokens: Map design tokens to Tailwind classes
- States: Document all interactive states
- Deviations: Note any differences from Evergreen implementation

### 3. BUILD - Create DS Component

Build the new component with DS prefix using Radix primitives + Tailwind.

**Component structure:**
```
src/
  components/
    ds/
      DSComponentName/
        DSComponentName.tsx       # Main component
        DSComponentName.types.ts  # TypeScript types
        index.ts                  # Barrel export
```

**Implementation checklist:**
- [ ] Use Radix primitive as base (if applicable)
- [ ] Apply Tailwind classes for styling
- [ ] Implement all variants from Figma specs
- [ ] Support all interactive states
- [ ] Add TypeScript types
- [ ] Match accessibility of original component
- [ ] Export from index.ts

**Example skeleton:**
```tsx
// DSComponentName.types.ts
export interface DSComponentNameProps {
  variant?: 'primary' | 'secondary'
  size?: 'small' | 'medium' | 'large'
  // ... other props
}

// DSComponentName.tsx
import * as RadixPrimitive from '@radix-ui/react-primitive'
import { DSComponentNameProps } from './DSComponentName.types'

export function DSComponentName({
  variant = 'primary',
  size = 'medium',
  ...props
}: DSComponentNameProps) {
  // Implementation with Tailwind classes
  return <RadixPrimitive.Root className="..." {...props} />
}
```

### 4. MAP - Document Props Mapping

Create a mapping document for prop equivalencies between legacy and new.

**Create migration-map.md in the component directory:**
```markdown
# ComponentName → DSComponentName Migration Map

## Props Mapping

| Evergreen Prop | DS Prop | Notes |
|----------------|---------|-------|
| `appearance` | `variant` | Renamed for consistency |
| `intent` | `variant` | Merged with appearance |
| `size` | `size` | Values unchanged |
| N/A | `className` | Now exposed for overrides |

## Removed Props
- `elevation` - Use Tailwind shadow utilities
- `marginTop` - Use Tailwind margin utilities

## Breaking Changes
- `onClick` signature changed: Add proper event types
- Default size changed from 'medium' to 'md'

## Usage Examples

### Before (Evergreen)
\`\`\`tsx
<Button appearance="primary" intent="success" size={400}>
  Click me
</Button>
\`\`\`

### After (DS)
\`\`\`tsx
<DSButton variant="primary" size="md">
  Click me
</DSButton>
\`\`\`
```

### 5. MIGRATE - Incremental Replacement with Feature Flags

Replace component usage one file at a time using feature flags for safe rollout.

**Feature flag setup (example pattern):**
```tsx
// Until feature flag system is defined, use environment variable or config
const USE_DS_COMPONENTS = import.meta.env.VITE_USE_DS_BUTTON === 'true'

// Or use a feature flag hook when available
// const { isEnabled } = useFeatureFlag('ds-button')
```

**Migration pattern per file:**
```tsx
// Before
import { Button } from 'evergreen-ui'

// After - dual imports during migration
import { Button } from 'evergreen-ui'
import { DSButton } from '@/components/ds/DSButton'

// In component
const ButtonComponent = USE_DS_COMPONENTS ? DSButton : Button

// In JSX
<ButtonComponent variant="primary">Click me</ButtonComponent>
```

**Migration checklist per file:**
- [ ] Add DS component import
- [ ] Add feature flag check
- [ ] Create component selector
- [ ] Replace JSX usage with selector
- [ ] Update props to match new API
- [ ] Test with flag OFF (legacy)
- [ ] Test with flag ON (new DS)
- [ ] Mark file as migrated in tracking doc

**Track progress in MIGRATION_STATUS.md:**
```markdown
## Button Migration Status

Total usages: 23

### Completed (5/23)
- [x] src/pages/LoginPage.tsx
- [x] src/pages/UserDashboard.tsx
- ...

### In Progress (2/23)
- [ ] src/pages/Settings.tsx (complex overrides)
- ...

### Pending (16/23)
- [ ] src/components/Header.tsx
- ...
```

### 6. VALIDATE - Visual Regression Testing

Capture before/after screenshots to ensure visual parity.

**Screenshot workflow:**

1. **Capture baseline (flag OFF):**
   ```bash
   # Set feature flag to use legacy component
   # Capture screenshot of each affected page/component
   ```

2. **Capture comparison (flag ON):**
   ```bash
   # Set feature flag to use DS component
   # Capture screenshot of same views
   ```

3. **Manual visual comparison:**
   - Layout dimensions match
   - Colors match design tokens
   - Spacing is consistent
   - Interactive states look correct
   - Text rendering matches
   - No visual regressions

**Use browser DevTools or Playwright for screenshots:**
```typescript
// Example with Playwright (if available)
await page.goto('http://localhost:5173/login')
await page.screenshot({ path: 'baseline-login.png' })
```

**Document findings:**
```markdown
## Visual Validation Results

### LoginPage.tsx
- ✅ Layout matches
- ✅ Colors match
- ⚠️  Button padding 1px different (acceptable)
- ✅ Interactive states match

### UserDashboard.tsx
- ✅ All checks passed
```

### 7. CLEANUP - Remove Legacy Code

Once feature flag is 100% enabled, remove legacy component code.

**Cleanup checklist:**
- [ ] Remove legacy component import
- [ ] Remove feature flag conditional
- [ ] Remove component selector variable
- [ ] Rename DSComponent to Component (optional)
- [ ] Update all imports across codebase
- [ ] Remove from Evergreen UI dependencies (when all components done)
- [ ] Delete migration map (or archive)
- [ ] Update documentation

**Example cleanup:**
```tsx
// Before (with flag)
import { Button } from 'evergreen-ui'
import { DSButton } from '@/components/ds/DSButton'
const ButtonComponent = USE_DS_COMPONENTS ? DSButton : Button

// After cleanup
import { DSButton } from '@/components/ds/DSButton'

// In JSX - direct usage
<DSButton variant="primary">Click me</DSButton>
```

## Component Priority Guide

Suggested migration order (highest impact first):

1. **Button** - Most frequently used, highest ROI
2. **TextInput/TextInputField** - Forms are critical
3. **Pane** - Layout primitive used everywhere
4. **Heading/Text** - Typography components
5. **Badge** - Simple, good learning component
6. **Avatar** - Isolated, visual component
7. **Switch** - Form control
8. **SelectField** - More complex form control
9. **Tab/TabNavigation** - Navigation components
10. **Textarea** - Form control

## Best Practices

- **One component at a time** - Don't migrate multiple components simultaneously
- **Feature flag discipline** - Always use flags, never direct replacement
- **Visual validation required** - Screenshots are mandatory, not optional
- **Document deviations** - Track any intentional differences from original
- **Communicate progress** - Keep MIGRATION_STATUS.md updated
- **Preserve functionality** - Ensure no behavioral regressions
- **Test both states** - Every file must work with flag ON and OFF until cleanup

## Figma MCP Integration

When Figma MCP is configured, query for component specifications:

```
"What are the design specifications for [ComponentName] including all variants, states, spacing tokens, and color tokens?"
```

Extract and document:
- Variant names and triggers
- Spacing values (map to Tailwind: `p-4`, `gap-2`, etc.)
- Color tokens (map to Tailwind: `bg-blue-500`, `text-gray-700`, etc.)
- Typography (map to Tailwind: `text-sm`, `font-medium`, etc.)

## Troubleshooting

**Override conflicts:**
- If component has many inline style overrides, consider exposing `className` prop
- Document common override patterns in migration map
- Create variant props for frequent overrides

**Type mismatches:**
- Evergreen often uses looser types (`any`)
- DS components should use proper TypeScript types
- Add type assertions during migration if needed
- Clean up types in CLEANUP phase

**Visual differences:**
- Small spacing differences (<2px) are often acceptable
- Color differences should match design tokens exactly
- Document intentional deviations in validation results

## References

See `references/evergreen-to-radix-mapping.md` for common component mappings between Evergreen UI primitives and Radix UI primitives.
