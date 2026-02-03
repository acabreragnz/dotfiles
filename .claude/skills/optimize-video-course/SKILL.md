---
name: optimize-video-course
description: "Compress and standardize educational course videos with H.264 encoding optimized for text-heavy content (code, presentations, diagrams) and universal naming convention. When Claude needs to: (1) Optimize course videos for storage/distribution, (2) Rename videos with hierarchical naming (YYYY - Course - Module - Lesson), (3) Batch process course directories, (4) Reduce file sizes while preserving text clarity. Triggers on tasks involving video compression, course video organization, or when user says 'optimize videos in directory' or 'compress and rename course videos'."
allowed-tools: Bash(*), Read, Glob, Grep, AskUserQuestion
metadata:
  version: "1.0.0"
  argument-hint: <directory-or-file> [--year YYYY] [--course "Name"] [--crf N]
---

# Optimize Video Course

Optimize and rename educational course videos with a universal, human-readable naming convention.

**Architecture:** LLM-driven - Claude analyzes structure and decides naming, scripts are simple utilities.

---

## Decision Tree

```
User request
├─ Single video file
│  ├─ Extract metadata from path
│  ├─ Ask for missing info (year, course, module/lesson)
│  └─ Process → Show stats
│
└─ Directory of videos
   ├─ Scan with Glob (*.mp4)
   ├─ Detect hierarchy (Flat/Module/Module+Section)
   ├─ Extract year from path or ask user
   ├─ Check already optimized (skip)
   ├─ If --delete-originals: Confirm with user
   └─ Process batch → Show summary report
```

---

## Workflow

### 1. Scan Directory
**Use `Glob`** with pattern `**/*.mp4` from user-provided path. Count videos found.

### 2. Analyze Structure
**MANDATORY - Consult [references/hierarchy-detection.md](references/hierarchy-detection.md)** for directory patterns.

- **Detect hierarchy:** Flat (Level 0), Modules (Level 1), or Modules+Sections (Level 2)
- **Extract course name:** From root directory basename
- **Sanitize course name:** Replace internal `-` with `·` (see [references/naming-conventions.md](references/naming-conventions.md))
- **Extract year:** Regex `[12][0-9]{3}` from path, or use `AskUserQuestion` if not found

### 3. Check Already Optimized
For each video:
```bash
~/.claude/skills/optimize-video-course/scripts/check_video_metadata.sh "video.mp4"
```
Skip if output contains `[OPTIMIZED]`.

### 4. Confirm if Deleting Originals
**Only if user requested `--delete-originals` flag:**

Show warning and use `AskUserQuestion`:
```
⚠️  WARNING: You requested to delete original files after optimization.

Settings:
- Total videos to process: X
- CRF: 23, preset: medium, audio: 128k
- Delete originals: YES (cannot be undone)

Question: "Are you sure you want to delete original files?"
Options:
  - "Yes, delete originals after optimization"
  - "No, keep original files (recommended)"
```

**If not deleting originals:** Skip confirmation, proceed directly to processing.

### 5. Process Videos

**Use Tasks for progress tracking** (batches of 5+ videos):

1. **Create task per video:**
   ```
   TaskCreate:
     subject: "Optimize M01-L02 - Why Learn OWASP"
     description: "Process Section 1/2 - Why Learn OWASP.mp4"
     activeForm: "Optimizing M01-L02"
   ```

2. **For each video:**

   a. **Mark in progress:** `TaskUpdate status: "in_progress"`

   b. **Extract metadata** from path/filename (consult [references/naming-conventions.md](references/naming-conventions.md))

   c. **Build output name:**
      - Flat: `YYYY - Course - LXX - Title.mp4`
      - Modules: `YYYY - Course - MXX - LXX - Title.mp4`
      - Modules+Sections: `YYYY - Course - MXX - SXX - LXX - Title.mp4`

   d. **Call optimization script:**
      ```bash
      ~/.claude/skills/optimize-video-course/scripts/optimize_video.sh \
        --input "/absolute/path/to/video.mp4" \
        --year 2026 \
        --course "OWASP Top 10 · Web Application Security" \
        --module 1 \
        --lesson 2 \
        --title "Why You Should Learn OWASP" \
        --crf 23
      ```

      **✅ DO:**
      - Use absolute paths for `--input`
      - Pass sanitized course name (with `·`)
      - Include all required parameters explicitly

      **❌ DON'T:**
      - Rely on script auto-detection (it doesn't exist)
      - Use relative paths
      - Omit required parameters

   e. **Mark completed:** `TaskUpdate status: "completed"`

   f. **Track results:** success/fail count, total space saved

### 6. Report Results
Show summary:
- Total processed, successful, failed
- Space savings (original → optimized, % reduction)
- Processing time
- Errors (if any)

---

## Key Rules

**Naming format:** `YYYY - Course - [Hierarchy] - Title.mp4`

**Course sanitization:** Replace internal hyphens with middle dot (·)
- Example: `OWASP Top 10 - Web Security` → `OWASP Top 10 · Web Security`

**Hierarchy:** M01/S01/L01 (zero-padded)

**Details:** See [references/naming-conventions.md](references/naming-conventions.md)

---

## Script Invocation

**CRITICAL:** Always pass ALL parameters explicitly. Script does NOT auto-detect.

**Required:** `--input`, `--year`, `--course`, `--lesson`, `--title`

**Optional:** `--module`, `--section`, `--crf` (18-28), `--preset`, `--audio-bitrate`, `--max-height`, `--delete-originals`

**Resolution scaling (`--max-height`):**
- Common values: 1080, 720, 480
- Only scales down if video is taller
- Preserves aspect ratio
- Omit to keep original resolution (recommended)

**⚠️  `--delete-originals`:** Only if user explicitly requests. Confirm first with `AskUserQuestion`.

**Details:** [references/encoding-options.md](references/encoding-options.md)

---

## Example Transformations

### Udemy-Style (Level 1)
```
Input:  Section 1 - About Course/2 - Why Learn OWASP.mp4
Course: OWASP Top 10 - Web Application Security 2026

Output: 2026 - OWASP Top 10 · Web Application Security - M01 - L02 - Why Learn OWASP.mp4
```

### Coursera-Style (Level 2)
```
Input:  Module 1/Week 2/3 - Advanced Topics.mp4
Course: Clean Architecture 2024

Output: 2024 - Clean Architecture - M01 - S02 - L03 - Advanced Topics.mp4
```

### Flat Structure (Level 0)
```
Input:  01 - Introduction.mp4
Course: React Basics 2025

Output: 2025 - React Basics - L01 - Introduction.mp4
```

---

## Single Video Mode

If user provides a single video file (not directory):

1. Check if already optimized
2. Extract metadata from path or use `AskUserQuestion` to gather:
   - Year (if not in path)
   - Course name
   - Module/lesson numbers
3. **If `--delete-originals` requested:** Show warning and confirm with `AskUserQuestion`
4. Process single video
5. Show result stats

---

## References

**Consult these before processing:**

- **[references/workflow-guide.md](references/workflow-guide.md)** - Detailed step-by-step instructions, error handling
- **[references/naming-conventions.md](references/naming-conventions.md)** - Complete naming rules, sanitization, edge cases
- **[references/hierarchy-detection.md](references/hierarchy-detection.md)** - Directory patterns, structure detection algorithms
- **[references/encoding-options.md](references/encoding-options.md)** - CRF/preset/bitrate guidance, quality trade-offs

---

## Technical Details

**Defaults:** H.264 CRF 23, preset medium, AAC 128k
**Expected:** 60-70% size reduction

**Scripts:** `optimize_video.sh`, `check_video_metadata.sh`, `add_metadata_to_video.sh`

---

## Common Tasks

### Quick Optimize Single Video
```bash
# User: "Optimize this video: /path/to/course/Section 1/video.mp4"
# Extract: year=2026, course="Course Name", module=1, lesson=2
~/.claude/skills/optimize-video-course/scripts/optimize_video.sh \
  --input "/path/to/course/Section 1/video.mp4" \
  --year 2026 --course "Course Name" --module 1 --lesson 2 --title "Video Title"
```

### Batch Process Course Directory
```bash
# User: "Optimize all videos in /path/to/OWASP-2026/"
# 1. Glob: **/*.mp4
# 2. Detect: Level 1 hierarchy (Sections → Modules)
# 3. Process each with script
# 4. Track with Tasks (if 5+ videos)
```

### High Quality Optimization
```bash
# User: "Optimize with high quality settings"
# Add: --crf 18 --preset slow --audio-bitrate 192k
```

### Mobile-Optimized (720p max)
```bash
# User: "Optimize for mobile devices"
# Add: --max-height 720
~/.claude/skills/optimize-video-course/scripts/optimize_video.sh \
  --input "video.mp4" --year 2026 --course "Course" \
  --lesson 1 --title "Title" --max-height 720
```

### Limit 4K to 1080p
```bash
# User has 4K videos (3840x2160) but content doesn't need it
# Add: --max-height 1080
```

### Check if Already Optimized
```bash
~/.claude/skills/optimize-video-course/scripts/check_video_metadata.sh "video.mp4"
# Look for: "Optimization status: yes"
```

---

## Error Handling

- ✅ **Continue on failure:** Don't stop batch on single error
- ✅ **Report all errors:** Show in final summary
- ✅ **Validate first:** Check inputs before calling script
- ✅ **Check dependencies:** Verify ffmpeg, disk space, permissions
