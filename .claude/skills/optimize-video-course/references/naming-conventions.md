# Video Naming Conventions

## Standard Format

```
YYYY - Course · Name - MXX - LXX - Title.mp4
```

For videos with sections (3-level hierarchy):
```
YYYY - Course · Name - MXX - SXX - LXX - Title.mp4
```

## Components

### 1. Year (YYYY)
- 4-digit year
- Examples: 2026, 2025, 2024

### 2. Course Name
- Use middle dot (·) for internal separators
- Replaces hyphens (-) within course name to avoid confusion with the primary separator
- The middle dot visually distinguishes course name parts from the main hierarchy separator (hyphen)

**Sanitization Rules:**
- Replace internal hyphens with middle dot (·)
- Preserve spaces
- Remove trailing/leading whitespace
- Keep alphanumeric characters and common punctuation

**Examples:**
- `OWASP Top 10 - Web Security` → `OWASP Top 10 · Web Security`
- `React - Complete Guide` → `React · Complete Guide`
- `Clean Architecture - SOLID Principles` → `Clean Architecture · SOLID Principles`
- `JavaScript Basics` → `JavaScript Basics` (no change needed)

### 3. Module (MXX)
- M + zero-padded 2-digit number
- Always use 2 digits (01-99)
- Examples: M01, M02, M12, M99

### 4. Section (SXX) - Optional
- S + zero-padded 2-digit number
- Only used for 3-level hierarchies
- Examples: S01, S02, S12, S99

### 5. Lesson (LXX)
- L + zero-padded 2-digit number
- Always use 2 digits (01-99)
- Examples: L01, L02, L12, L99

### 6. Title
- Remove number prefixes (e.g., `3 - Title` → `Title`)
- Remove file extension
- Replace underscores with spaces
- Trim whitespace
- Keep original capitalization
- Preserve special characters in titles

**Title Sanitization Examples:**
- `2 - Why You Should Learn OWASP.mp4` → `Why You Should Learn OWASP`
- `03_Introduction_to_React.mp4` → `Introduction to React`
- `Setup Environment.mp4` → `Setup Environment`
- `  5 - Advanced Topics  .mp4` → `Advanced Topics`

## Full Examples

### Flat Structure (No Modules)
```
Input:  01 - Introduction.mp4
Output: 2025 - React Basics - L01 - Introduction.mp4
```

### 2-Level Hierarchy (Modules + Lessons)
```
Input:  Section 1 - About Course/2 - Why You Should Learn OWASP.mp4
Output: 2026 - OWASP Top 10 · Web Application Security - M01 - L02 - Why You Should Learn OWASP.mp4
```

### 3-Level Hierarchy (Modules + Sections + Lessons)
```
Input:  Module 2/Week 3/5 - Advanced Topics.mp4
Output: 2025 - Clean Architecture - M02 - S03 - L05 - Advanced Topics.mp4
```

### Complex Course Name
```
Input:  Part 1/01 - Getting Started.mp4
Course: "OWASP Top 10 - Web Application Security 2026"
Output: 2026 - OWASP Top 10 · Web Application Security 2026 - M01 - L01 - Getting Started.mp4
```

## Special Cases

### Course Names with Numbers
If the course name contains a year, preserve it:
- Input course: `Web Security 2026`
- Output: `2026 - Web Security 2026 - M01 - L01 - Intro.mp4`

### Multiple Hyphens in Course Name
Replace all internal hyphens:
- `Front-End - React - Advanced` → `Front·End · React · Advanced`

### Short Course Names
No minimum length requirement:
- `Go` → `2025 - Go - M01 - L01 - Basics.mp4`

## Character Set

- **Allowed in output names:**
  - Letters (a-z, A-Z)
  - Numbers (0-9)
  - Spaces
  - Hyphens (-) for main separators
  - Middle dot (·) for course name internal separators
  - Common punctuation in titles

- **Avoid if possible:**
  - Special characters that may cause filesystem issues: `/ \ : * ? " < > |`
  - Leading/trailing dots or spaces

## Validation Checklist

When generating a filename, verify:
- [ ] Year is 4 digits
- [ ] Course name uses middle dot (·) instead of internal hyphens
- [ ] Module/Section/Lesson numbers are zero-padded to 2 digits
- [ ] Title has no number prefixes or file extensions
- [ ] All components are separated by ` - ` (space-hyphen-space)
- [ ] No double spaces or trailing whitespace
