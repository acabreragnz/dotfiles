# Workflow Guide for Claude

This document provides detailed step-by-step instructions for Claude when processing video optimization requests.

---

## Overview

The skill follows an **LLM-driven architecture**:
- **Claude (this skill)** handles all intelligent decisions: scanning, analysis, naming, coordination
- **Scripts** are simple utilities that perform specific tasks (optimize one video, check metadata)
- **References** contain rules and patterns that Claude consults for decisions

---

## Main Workflow: Optimize Course Directory

When user requests to optimize videos in a directory:

### Step 1: Scan Directory
**Goal:** Find all video files in the provided path

**Actions:**
1. Use `Glob` tool with pattern `**/*.mp4` from the provided directory
2. Filter out any system/hidden files if present
3. Count total videos found

**Example:**
```
Glob pattern: "**/*.mp4"
Path: "/path/to/OWASP Top 10 - Web Security 2026/"
Result: 50 .mp4 files found
```

**Handle edge cases:**
- If no videos found: inform user, exit gracefully
- If only 1 video: switch to single-video mode (simpler workflow)

---

### Step 2: Analyze Directory Structure
**Goal:** Understand the hierarchy and extract metadata

#### 2.1 Determine Hierarchy Level
Parse directory paths to identify structure:

1. **Check if all videos are at the same depth**
   - All at root → Flat structure (Level 0)
   - One level of subdirs → Modules (Level 1)
   - Two levels of subdirs → Modules + Sections (Level 2)

2. **Consult `references/hierarchy-detection.md` for patterns**
   - Match directory names against module/section patterns
   - Extract numbers from directory names

**Example analysis:**
```
Files found:
  Section 1 - About Course/1 - Introduction.mp4
  Section 1 - About Course/2 - Overview.mp4
  Section 2 - Getting Started/1 - Setup.mp4

Analysis:
  - Hierarchy: Level 1 (Modules)
  - "Section 1" → Module 01
  - "Section 2" → Module 02
  - Filenames "1 - ", "2 - " → Lesson numbers
```

#### 2.2 Extract Course Name
Determine the course name:

1. **From root directory name:**
   - Get the basename of the root path
   - Remove any year suffixes (e.g., "Course 2026" → "Course 2026")

2. **From `--course` argument if provided**

3. **Sanitize per `references/naming-conventions.md`:**
   - Replace internal hyphens with middle dot (·)
   - Example: `OWASP Top 10 - Web Security` → `OWASP Top 10 · Web Security`

**Example:**
```
Root path: /home/user/courses/OWASP Top 10 - Web Application Security 2026/
Extracted: "OWASP Top 10 - Web Application Security 2026"
Sanitized: "OWASP Top 10 · Web Application Security 2026"
```

#### 2.3 Extract Year
Find the year using these methods (in order):

1. **From `--year` argument if provided** (highest priority)

2. **Search path for 4-digit year:**
   - Regex: `[12][0-9]{3}` (matches 1000-2999)
   - Example: `/courses/Web-Security-2026/` → 2026

3. **If not found, ask user:**
   - Use `AskUserQuestion` tool
   - Question: "What year is this course from?"
   - Options: Current year, previous years, custom input

**Example:**
```
Path: /home/user/courses/OWASP Top 10 - Web Application Security 2026/
Regex match: 2026
Year: 2026
```

---

### Step 3: Check for Already Optimized Videos
**Goal:** Avoid re-processing videos

For each video found:

1. **Check metadata using the check script:**
   ```bash
   ~/.claude/skills/optimize-video-course/scripts/check_video_metadata.sh "video.mp4"
   ```

2. **Parse output:**
   - If contains "[OPTIMIZED]" → mark as skip
   - Otherwise → mark as processable

3. **Alternative filename check:**
   - Check if a file with the target output name already exists
   - If yes → mark as skip

**Track:**
- Total videos found
- Videos to process
- Videos to skip (already optimized)

---

### Step 4: Preview & Confirm
**Goal:** Get user approval before processing

Show user a preview with:

1. **Summary:**
   - Total videos found: X
   - Already optimized (skip): Y
   - To process: Z

2. **Settings:**
   - CRF: 23 (or custom value)
   - Preset: medium
   - Audio bitrate: 128k
   - Delete originals: No (default)

3. **Preview first 3 output names:**
   ```
   2026 - OWASP Top 10 · Web Application Security - M01 - L01 - Introduction.mp4
   2026 - OWASP Top 10 · Web Application Security - M01 - L02 - Course Overview.mp4
   2026 - OWASP Top 10 · Web Application Security - M02 - L01 - Getting Started.mp4
   ```

4. **Use `AskUserQuestion` to confirm:**
   ```
   Question: "Proceed with optimization?"
   Options:
     - Yes (start processing)
     - No (cancel)
     - Change settings (ask for custom CRF, preset, etc.)
   ```

**If user wants to change settings:**
- Ask for custom values (CRF, preset, audio bitrate)
- Update preview
- Ask confirmation again

---

### Step 5: Process Videos
**Goal:** Optimize each video by calling the script

For each video to process:

#### 5.1 Extract Video-Specific Metadata
Parse the video's path and filename:

1. **Extract hierarchy numbers:**
   - Module number from directory
   - Section number from subdirectory (if Level 2)
   - Lesson number from filename

2. **Extract title:**
   - Remove number prefix from filename
   - Remove .mp4 extension
   - Sanitize per `references/naming-conventions.md`

**Example:**
```
Path: Section 1 - About Course/2 - Why You Should Learn OWASP.mp4

Extracted:
  - Module: 01 (from "Section 1")
  - Lesson: 02 (from "2 - ")
  - Title: "Why You Should Learn OWASP" (sanitized)
```

#### 5.2 Construct Output Name
Consult `references/naming-conventions.md` to build the output filename:

**Format:**
- Flat: `YYYY - Course - LXX - Title.mp4`
- Level 1: `YYYY - Course - MXX - LXX - Title.mp4`
- Level 2: `YYYY - Course - MXX - SXX - LXX - Title.mp4`

**Example:**
```
Year: 2026
Course: "OWASP Top 10 · Web Application Security"
Module: 01
Lesson: 02
Title: "Why You Should Learn OWASP"

Output: 2026 - OWASP Top 10 · Web Application Security - M01 - L02 - Why You Should Learn OWASP.mp4
```

#### 5.3 Call Optimization Script
Invoke the script with all parameters:

```bash
~/.claude/skills/optimize-video-course/scripts/optimize_video.sh \
  --input "/full/path/to/Section 1/2 - Why You Should Learn OWASP.mp4" \
  --year 2026 \
  --course "OWASP Top 10 · Web Application Security" \
  --module 1 \
  --lesson 2 \
  --title "Why You Should Learn OWASP" \
  --crf 23
```

**For Level 2 hierarchy (with sections):**
```bash
~/.claude/skills/optimize-video-course/scripts/optimize_video.sh \
  --input "/path/to/Module 1/Week 2/3 - Video.mp4" \
  --year 2025 \
  --course "Clean Architecture" \
  --module 1 \
  --section 2 \
  --lesson 3 \
  --title "Video Title" \
  --crf 23
```

#### 5.4 Track Results
For each script invocation:

1. **Check exit code:**
   - 0 = success
   - Non-zero = error

2. **Parse output:**
   - Extract statistics (original size, optimized size, reduction)
   - Extract any error messages

3. **Update counters:**
   - Increment: processed_count
   - Increment: success_count or error_count
   - Track: total_space_saved

**Error handling:**
- If script fails, log error but continue with next video
- Don't stop entire batch on single failure
- Report all errors in final summary

---

### Step 6: Report Results
**Goal:** Show comprehensive summary

After all videos processed, display:

1. **Processing Summary:**
   ```
   Total videos found: 50
   Already optimized (skipped): 5
   Processed: 45
   Successful: 43
   Failed: 2
   ```

2. **Space Savings:**
   ```
   Original total size: 2.8 GB
   Optimized total size: 950 MB
   Total saved: 1.85 GB (66% reduction)
   ```

3. **Time:**
   ```
   Total processing time: 12 minutes 34 seconds
   Average per video: 16 seconds
   ```

4. **Errors (if any):**
   ```
   Failed videos:
   - Section 3/5 - Advanced Topics.mp4 (Error: corrupted input file)
   - Section 5/2 - Demo.mp4 (Error: insufficient disk space)
   ```

5. **Next Steps:**
   - If errors: suggest how to fix
   - If all successful: confirm completion

---

## Alternative Workflow: Single Video Mode

When user provides a single video file (not a directory):

### Step 1: Detect Context
1. Check if file is already optimized (metadata check)
2. If optimized, inform user and ask if they want to re-process

### Step 2: Gather Metadata
Since we can't infer from directory structure:

1. **Use `AskUserQuestion` for missing metadata:**
   - Year (if not in path or `--year` arg)
   - Course name (if not provided as `--course` arg)
   - Module number (optional)
   - Lesson number (required, can infer from filename)

2. **Extract from filename:**
   - Lesson number (if pattern matches)
   - Title (sanitized filename)

**Example questions:**
```
Question 1: "What year is this course from?"
Options: 2026, 2025, 2024, Custom

Question 2: "What is the course name?"
(Free text input)

Question 3: "What module is this video in? (Leave blank if not applicable)"
(Free text, optional)
```

### Step 3: Process Single Video
Call the script with gathered metadata:

```bash
~/.claude/skills/optimize-video-course/scripts/optimize_video.sh \
  --input "path/to/video.mp4" \
  --year 2026 \
  --course "React Basics" \
  --lesson 5 \
  --title "Introduction to Hooks" \
  --crf 23
```

### Step 4: Report Result
Show statistics for the single video:
```
Original: 106.5 MB
Optimized: 34.2 MB
Saved: 72.3 MB (68% reduction)
Processing time: 18 seconds

Output: 2026 - React Basics - L05 - Introduction to Hooks.mp4
```

---

## Parallel Processing (Advanced)

For large course directories (50+ videos), consider parallel processing:

### When to Use
- User explicitly requests faster processing
- More than 50 videos to process
- System has multiple CPU cores

### Implementation
Instead of sequential script calls, use multiple `Bash` tool calls in a single message:

**Example:**
```
Single message with 3 parallel Bash calls:
1. Bash: optimize video 1
2. Bash: optimize video 2
3. Bash: optimize video 3
```

**Batch strategy:**
- Process videos in batches of 3-5 at a time
- Wait for batch to complete before starting next batch
- Track results from all parallel calls

**Caution:**
- Higher CPU/memory usage
- May cause system slowdown on low-spec machines
- User should be informed before parallel processing

---

## Error Handling

### Common Errors and Solutions

#### Error: "No videos found"
- **Cause:** Wrong path or no .mp4 files
- **Solution:** Verify path with user, check for other video formats

#### Error: "ffmpeg not found"
- **Cause:** Missing dependency
- **Solution:** Inform user to install ffmpeg

#### Error: "Corrupted video file"
- **Cause:** Input file is damaged
- **Solution:** Skip file, report to user, suggest manual check

#### Error: "Insufficient disk space"
- **Cause:** Not enough space for output
- **Solution:** Stop processing, inform user, suggest cleanup

#### Error: "Permission denied"
- **Cause:** Can't write to output directory
- **Solution:** Check permissions, suggest alternate output location

---

## Custom Settings Workflow

When user wants custom encoding settings:

### Step 1: Ask for Custom Values
Use `AskUserQuestion` to gather:

1. **CRF (Quality):**
   - Options: 18 (high quality), 23 (balanced), 28 (smaller size)
   - Explain trade-offs

2. **Preset (Speed):**
   - Options: slow (better compression), medium (balanced), fast (quick)
   - Explain impact on file size

3. **Audio Bitrate:**
   - Options: 96k (low), 128k (standard), 192k (high)

### Step 2: Pass to Script
Include custom values in script calls:

```bash
~/.claude/skills/optimize-video-course/scripts/optimize_video.sh \
  --input "video.mp4" \
  --year 2026 \
  --course "Course Name" \
  --lesson 1 \
  --title "Title" \
  --crf 18 \
  --preset slow \
  --audio-bitrate 192k
```

**Note:** Check `references/encoding-options.md` (once created) for guidance on when to use which settings.

---

## Validation Checklist

Before processing each video, validate:

- [ ] Input file exists and is readable
- [ ] Year is 4 digits (YYYY format)
- [ ] Course name is sanitized (middle dot for internal hyphens)
- [ ] Module/Section/Lesson numbers are valid integers
- [ ] Title is sanitized (no prefixes, no extension)
- [ ] CRF is in range 18-28
- [ ] Output path is writable
- [ ] Sufficient disk space (at least 50% of original size needed temporarily)

---

## Best Practices for Claude

1. **Always consult references:**
   - `naming-conventions.md` for output naming
   - `hierarchy-detection.md` for structure analysis
   - `encoding-options.md` (future) for quality settings

2. **Be explicit in script calls:**
   - Never omit required parameters
   - Use full paths for input files
   - Pass all metadata explicitly (no auto-detection in script)

3. **Provide clear feedback:**
   - Show progress for batch operations
   - Report errors with context
   - Summarize results comprehensively

4. **Handle edge cases gracefully:**
   - Ask user when structure is ambiguous
   - Provide sensible defaults
   - Validate all inputs before processing

5. **Respect user preferences:**
   - Confirm before processing (unless user explicitly requests auto-mode)
   - Allow custom settings
   - Preserve original files (don't delete without permission)
