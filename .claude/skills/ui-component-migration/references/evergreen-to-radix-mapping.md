# Evergreen UI to Radix UI Component Mapping

Reference guide for mapping Evergreen UI components to Radix UI primitives and Tailwind CSS.

## Form Components

### Button
**Evergreen:** `<Button>`
**Radix:** `@radix-ui/react-slot` (for asChild pattern) or native `<button>`
**Tailwind Base:** `inline-flex items-center justify-center rounded-md font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 disabled:pointer-events-none disabled:opacity-50`

**Props mapping:**
- `appearance="primary"` → `variant="primary"` with `bg-blue-600 text-white hover:bg-blue-700`
- `appearance="minimal"` → `variant="ghost"` with `hover:bg-gray-100`
- `intent="success"` → `variant="success"` with `bg-green-600 text-white`
- `intent="danger"` → `variant="destructive"` with `bg-red-600 text-white`
- `isLoading` → Custom loading state with spinner

### TextInput / TextInputField
**Evergreen:** `<TextInput>`, `<TextInputField>`
**Radix:** Native `<input>` with label composition
**Tailwind Base:** `flex h-10 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-50`

**Props mapping:**
- `isInvalid` → `aria-invalid="true"` with `border-red-500 focus:ring-red-500`
- `validationMessage` → Error text component below input
- `placeholder` → Native `placeholder`
- `disabled` → Native `disabled`

### Select / SelectField
**Evergreen:** `<Select>`, `<SelectField>`
**Radix:** `@radix-ui/react-select`
**Key features:**
- Custom trigger styling
- Portal-based dropdown
- Keyboard navigation
- Accessible by default

**Implementation:**
```tsx
<Select.Root>
  <Select.Trigger className="..." />
  <Select.Portal>
    <Select.Content className="...">
      <Select.Item value="..." className="..." />
    </Select.Content>
  </Select.Portal>
</Select.Root>
```

### Textarea
**Evergreen:** `<Textarea>`
**Radix:** Native `<textarea>`
**Tailwind Base:** `flex min-h-[80px] w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-50`

### Switch
**Evergreen:** `<Switch>`
**Radix:** `@radix-ui/react-switch`
**Key features:**
- Accessible toggle
- Custom styling via Tailwind
- Controlled/uncontrolled support

**Implementation:**
```tsx
<Switch.Root className="w-11 h-6 bg-gray-200 rounded-full data-[state=checked]:bg-blue-600">
  <Switch.Thumb className="block w-5 h-5 bg-white rounded-full transition-transform data-[state=checked]:translate-x-5" />
</Switch.Root>
```

## Layout Components

### Pane
**Evergreen:** `<Pane>`
**Radix:** Native `<div>` or semantic HTML
**Migration strategy:**
- Convert Evergreen style props to Tailwind classes
- `display="flex"` → `flex`
- `elevation={2}` → `shadow-md`
- `padding={16}` → `p-4`
- `borderRadius={8}` → `rounded-lg`

**Common patterns:**
```tsx
// Evergreen
<Pane display="flex" padding={16} elevation={1} borderRadius={8}>

// Radix + Tailwind
<div className="flex p-4 shadow-sm rounded-lg">
```

## Typography Components

### Heading
**Evergreen:** `<Heading>`
**Radix:** Native `<h1>`, `<h2>`, etc.
**Tailwind Base:** Semantic heading with size utilities

**Size mapping:**
- `size={900}` → `text-4xl font-bold` (h1)
- `size={800}` → `text-3xl font-bold` (h1)
- `size={700}` → `text-2xl font-bold` (h2)
- `size={600}` → `text-xl font-semibold` (h2)
- `size={500}` → `text-lg font-semibold` (h3)
- `size={400}` → `text-base font-semibold` (h3)
- `size={300}` → `text-sm font-medium` (h4)

### Text
**Evergreen:** `<Text>`
**Radix:** Native `<p>`, `<span>`
**Tailwind Base:** `text-sm` or `text-base`

**Props mapping:**
- `size={300}` → `text-xs`
- `size={400}` → `text-sm`
- `size={500}` → `text-base`
- `color="muted"` → `text-gray-500`
- `fontWeight={500}` → `font-medium`

## Display Components

### Badge
**Evergreen:** `<Badge>`
**Radix:** Native `<span>` or `@radix-ui/react-badge` (if available)
**Tailwind Base:** `inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold`

**Color mapping:**
- `color="neutral"` → `bg-gray-100 text-gray-800`
- `color="blue"` → `bg-blue-100 text-blue-800`
- `color="green"` → `bg-green-100 text-green-800`
- `color="red"` → `bg-red-100 text-red-800`
- `color="yellow"` → `bg-yellow-100 text-yellow-800`

### Avatar
**Evergreen:** `<Avatar>`
**Radix:** `@radix-ui/react-avatar`
**Key features:**
- Image with fallback
- Initials generation
- Accessible

**Implementation:**
```tsx
<Avatar.Root className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-gray-100">
  <Avatar.Image src="..." alt="..." />
  <Avatar.Fallback className="text-sm font-medium">AB</Avatar.Fallback>
</Avatar.Root>
```

### IconButton
**Evergreen:** `<IconButton>`
**Radix:** Native `<button>` with icon
**Tailwind Base:** `inline-flex h-10 w-10 items-center justify-center rounded-md hover:bg-gray-100`

## Navigation Components

### Tab / TabNavigation
**Evergreen:** `<TabNavigation>`, `<Tab>`
**Radix:** `@radix-ui/react-tabs`
**Key features:**
- Accessible tab navigation
- Controlled/uncontrolled
- Keyboard support

**Implementation:**
```tsx
<Tabs.Root defaultValue="tab1">
  <Tabs.List className="border-b">
    <Tabs.Trigger value="tab1" className="...">Tab 1</Tabs.Trigger>
    <Tabs.Trigger value="tab2" className="...">Tab 2</Tabs.Trigger>
  </Tabs.List>
  <Tabs.Content value="tab1">Content 1</Tabs.Content>
  <Tabs.Content value="tab2">Content 2</Tabs.Content>
</Tabs.Root>
```

## Feedback Components

### Toaster
**Evergreen:** `toaster.success()`, `toaster.notify()`, `toaster.danger()`
**Radix:** `@radix-ui/react-toast` + custom hook
**Migration:**
- Create `useToast()` hook
- Implement `<Toaster>` component
- Replace `toaster.success()` with `toast({ variant: "success", title: "..." })`

**Example hook:**
```tsx
export function useToast() {
  return {
    toast: ({ title, description, variant }) => {
      // Toast implementation
    }
  }
}
```

## Utility Components

### SearchInput
**Evergreen:** `<SearchInput>`
**Radix:** Native `<input type="search">` with icon
**Tailwind Base:** `flex h-10 w-full rounded-md border border-gray-300 bg-white pl-10 pr-3 py-2 text-sm`

**Pattern:**
```tsx
<div className="relative">
  <SearchIcon className="absolute left-3 top-2.5 h-5 w-5 text-gray-400" />
  <input type="search" className="pl-10 ..." />
</div>
```

## Common Migration Patterns

### Spacing Props to Tailwind
Evergreen uses numeric spacing (4px increments):
- `padding={4}` → `p-1` (4px)
- `padding={8}` → `p-2` (8px)
- `padding={16}` → `p-4` (16px)
- `padding={24}` → `p-6` (24px)
- `padding={32}` → `p-8` (32px)

### Elevation to Shadow
- `elevation={0}` → `shadow-none`
- `elevation={1}` → `shadow-sm`
- `elevation={2}` → `shadow-md`
- `elevation={3}` → `shadow-lg`
- `elevation={4}` → `shadow-xl`

### Color Intent to Variants
- `intent="success"` → `variant="success"` with green colors
- `intent="warning"` → `variant="warning"` with yellow colors
- `intent="danger"` → `variant="destructive"` with red colors
- `intent="none"` → Default variant

## TypeScript Considerations

### Event Handlers
Evergreen often uses loose types:
```tsx
// Evergreen (loose)
onChange={(e: any) => setValue(e.target.value)}

// DS (strict)
onChange={(e: React.ChangeEvent<HTMLInputElement>) => setValue(e.target.value)}
```

### Prop Types
Define strict prop interfaces:
```tsx
export interface DSButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'destructive'
  size?: 'sm' | 'md' | 'lg'
  isLoading?: boolean
}
```

## Accessibility Considerations

Radix components are accessible by default, but ensure:
- Proper ARIA labels
- Keyboard navigation
- Focus management
- Screen reader support
- Color contrast (WCAG AA minimum)

**Use Radix when:**
- Component has complex interactions (Select, Dialog, Dropdown)
- Accessibility is critical
- Keyboard navigation required

**Use native HTML when:**
- Simple components (Button, Input)
- No complex state management needed
- Tailwind styling is sufficient
