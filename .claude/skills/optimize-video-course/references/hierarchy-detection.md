# Directory Hierarchy Detection Rules

This document defines how to detect and map course directory structures to the universal naming convention.

## Hierarchy Levels

### Level 0: Flat Structure (No Modules)
All videos are in the root directory or a single directory.

**Detection:**
- No subdirectories with module indicators
- All .mp4 files at the same level

**Mapping:**
- Use only lesson numbers (L01, L02, ...)
- No module or section prefixes

**Example:**
```
Course Root/
├── 01 - Introduction.mp4
├── 02 - Setup.mp4
└── 03 - Basics.mp4

Output:
YYYY - Course - L01 - Introduction.mp4
YYYY - Course - L02 - Setup.mp4
YYYY - Course - L03 - Basics.mp4
```

---

### Level 1: Modules (2-Level Hierarchy)
Course has modules/sections, videos directly inside them.

**Detection:**
- Subdirectories with module indicators (see Module Name Patterns below)
- Videos are direct children of module directories

**Mapping:**
- Directory → Module number (M01, M02, ...)
- Filename → Lesson number (L01, L02, ...)

**Example:**
```
Course Root/
├── Section 1 - About Course/
│   ├── 1 - Introduction.mp4
│   └── 2 - Why Learn OWASP.mp4
└── Section 2 - Getting Started/
    └── 1 - Setup Environment.mp4

Output:
YYYY - Course - M01 - L01 - Introduction.mp4
YYYY - Course - M01 - L02 - Why Learn OWASP.mp4
YYYY - Course - M02 - L01 - Setup Environment.mp4
```

---

### Level 2: Modules + Sections (3-Level Hierarchy)
Course has modules, then sections/weeks within modules.

**Detection:**
- Subdirectories with module indicators
- Second level of subdirectories within modules (sections/weeks/units)
- Videos are children of the second-level subdirectories

**Mapping:**
- First level → Module number (M01, M02, ...)
- Second level → Section number (S01, S02, ...)
- Filename → Lesson number (L01, L02, ...)

**Example:**
```
Course Root/
├── Module 1/
│   ├── Week 1/
│   │   └── 1 - Basics.mp4
│   └── Week 2/
│       ├── 1 - Advanced.mp4
│       └── 2 - Practice.mp4
└── Module 2/
    └── Week 1/
        └── 1 - Review.mp4

Output:
YYYY - Course - M01 - S01 - L01 - Basics.mp4
YYYY - Course - M01 - S02 - L01 - Advanced.mp4
YYYY - Course - M01 - S02 - L02 - Practice.mp4
YYYY - Course - M02 - S01 - L01 - Review.mp4
```

---

## Directory Name Patterns

### Module Name Patterns
Directories matching these patterns should be treated as modules:

**Explicit module indicators:**
- `Section N`
- `Module N`
- `Chapter N`
- `Part N`
- `Unit N` (if top-level)

**Pattern matching (case-insensitive):**
- Starts with a number: `1 - Introduction`, `01-Basics`
- Contains "Section": `Section 1`, `SECTION-1`
- Contains "Module": `Module 01`, `Mod-1`
- Contains "Chapter": `Chapter 1`, `Ch1`
- Contains "Part": `Part 1`, `Part-1`

**Examples:**
- `Section 1` → Module 01
- `Module 12` → Module 12
- `1 - Introduction` → Module 01
- `Part 2 - Advanced Topics` → Module 02

### Section Name Patterns (Second Level)
Subdirectories within modules matching these patterns:

**Explicit section indicators:**
- `Week N`
- `Unit N` (when inside a module)
- `Day N`
- `Lesson N` (as a grouping, not individual lesson)

**Pattern matching:**
- Starts with a number: `1 - Basic Concepts`
- Contains "Week": `Week 1`, `WEEK-2`
- Contains "Unit": `Unit 3`
- Contains "Day": `Day 1`

**Examples:**
- `Week 2` → Section 02
- `Unit 5` → Section 05
- `3 - Advanced` → Section 03

---

## Lesson Number Extraction

### From Filenames
Extract lesson numbers from video filenames using these patterns:

**Pattern 1: Leading number with separator**
- `3 - Title.mp4` → Lesson 03
- `05 - Title.mp4` → Lesson 05
- `12-Title.mp4` → Lesson 12

**Pattern 2: Leading number with underscore**
- `03_Title.mp4` → Lesson 03
- `5_Introduction.mp4` → Lesson 05

**Pattern 3: No explicit number**
- Use file position in directory (sorted alphabetically)
- First file → L01, second → L02, etc.

**Regex pattern:**
```regex
^(\d+)\s*[-_]\s*(.+)\.mp4$
```
- Group 1: Lesson number
- Group 2: Title

---

## Number Extraction Rules

### Zero-Padding
Always convert numbers to zero-padded 2-digit format:
- `1` → `01`
- `5` → `05`
- `12` → `12`
- `99` → `99`

### Handling Large Numbers
If a number exceeds 99:
- Use the full number without padding: `100`, `150`
- This is rare in course structures

---

## Special Cases and Edge Cases

### Case 1: Mixed Numbering
If directories have inconsistent numbering:
```
Course Root/
├── 1 - First/
├── Section 2/
└── Module 3/
```
**Solution:** Extract any number found, treat all as modules.

### Case 2: No Numbers in Directory Names
```
Course Root/
├── Introduction/
├── Basics/
└── Advanced/
```
**Solution:** Use directory position (sorted alphabetically):
- Introduction → M01
- Basics → M02
- Advanced → M03

### Case 3: Nested but Not Hierarchical
If subdirectories don't follow clear hierarchy:
```
Course Root/
├── Resources/
│   └── video.mp4
├── Lectures/
│   └── lecture1.mp4
```
**Solution:** Flatten to module level or ask user to clarify.

### Case 4: Videos at Multiple Levels
```
Course Root/
├── intro.mp4
└── Module 1/
    └── lesson1.mp4
```
**Solution:** Treat root-level videos as M00 or ask user.

---

## Detection Algorithm

When analyzing a course directory:

1. **Scan for .mp4 files recursively**
   - Use Glob: `**/*.mp4`

2. **Analyze directory depth**
   - Count levels between root and video files
   - Determine hierarchy level (0, 1, or 2)

3. **Identify patterns**
   - Check directory names for module/section indicators
   - Extract numbers from directory names
   - Extract numbers from filenames

4. **Map to hierarchy**
   - Apply level-appropriate mapping (flat, modules, or modules+sections)

5. **Handle edge cases**
   - Ask user if structure is ambiguous
   - Default to simplest interpretation if unclear

---

## Examples by Course Platform

### Udemy Structure
```
Course Root/
├── Section 1 - Introduction/
│   ├── 1 - Welcome.mp4
│   └── 2 - Course Overview.mp4
└── Section 2 - Getting Started/
    └── 3 - Setup.mp4
```
**Detection:** Level 1 (Modules)
- `Section N` → Module
- Filename numbers → Lessons

### Coursera Structure
```
Course Root/
├── Module 1/
│   ├── Week 1/
│   │   └── video1.mp4
│   └── Week 2/
│       └── video2.mp4
```
**Detection:** Level 2 (Modules + Sections)
- `Module N` → Module
- `Week N` → Section
- Filename or position → Lesson

### LinkedIn Learning Structure
```
Course Root/
├── 01 - Introduction.mp4
├── 02 - Chapter 1.mp4
└── 03 - Chapter 2.mp4
```
**Detection:** Level 0 (Flat)
- Filename numbers → Lessons only

---

## Decision Tree

```
START
  │
  ├─ Are there subdirectories with videos?
  │   NO → Flat structure (Level 0)
  │   YES → Continue
  │
  ├─ Do subdirectories contain module indicators?
  │   NO → Ask user or flatten
  │   YES → Continue
  │
  ├─ Do modules contain further subdirectories with videos?
  │   NO → Module structure (Level 1)
  │   YES → Module + Section structure (Level 2)
```

---

## Best Practices for Claude

When implementing hierarchy detection:

1. **Use Glob to find all videos first**
   ```
   Glob: **/*.mp4 from course root
   ```

2. **Parse each path to extract structure**
   ```
   /path/to/Section 1/2 - Video.mp4
   → Module: 01 (from "Section 1")
   → Lesson: 02 (from "2 - Video.mp4")
   ```

3. **Consult this reference for pattern matching**

4. **Ask user if structure is ambiguous**
   - Use AskUserQuestion
   - Show detected structure for confirmation

5. **Default to simpler interpretation**
   - If unsure between Level 1 and Level 2, choose Level 1
   - Better to under-specify than over-specify
