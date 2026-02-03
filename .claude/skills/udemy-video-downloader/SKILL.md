---
name: udemy-video-downloader
description: "Download non-DRM Udemy course videos by intercepting HLS streams through Chrome DevTools MCP, downloading with ffmpeg, and automatically optimizing with compress skill. When Claude needs to: (1) Download videos from Udemy lecture pages (requires active browser session), (2) Extract HLS URLs from network traffic for non-DRM courses, (3) Save course content offline with optimized compression, (4) Batch download entire course sections. Triggers when user wants to download Udemy videos, save lectures offline, or says 'download this Udemy lecture' or 'save Udemy course for offline viewing'. Note: Only works with non-DRM protected courses."
allowed-tools: mcp__chrome-devtools__*, Bash(*), AskUserQuestion, Skill(optimize-video-course)
metadata:
  version: "1.0.0"
  argument-hint: (interactive - requires active Chrome session on Udemy lecture page)
  requires:
    - chrome-devtools-mcp
    - ffmpeg
    - optimize-video-course skill
  limitations:
    - DRM-protected courses cannot be downloaded
    - Requires user to be logged into Udemy
    - Page reload needed to capture network traffic
---

# Udemy Video Downloader

Download and optimize Udemy course videos via Chrome DevTools MCP and ffmpeg.

**Architecture:** LLM-driven - Claude captures network requests and extracts HLS URLs, ffmpeg handles download, optimize-video-course handles compression.

---

## Decision Tree

```
User on Udemy lecture page
├─ Check prerequisites
│  ├─ Chrome DevTools MCP connected?
│  ├─ ffmpeg installed?
│  └─ User logged into Udemy?
│
├─ Confirm download location
│
├─ Capture video data
│  ├─ Take snapshot → Extract course/lecture info
│  ├─ Ask user permission to reload
│  ├─ Reload page → Capture network requests
│  ├─ Find media_sources API request
│  └─ Check DRM status
│
├─ Download video
│  ├─ Extract HLS m3u8 URL
│  ├─ Download with ffmpeg
│  └─ Verify file created
│
└─ Optimize video
   └─ Call optimize-video-course skill
```

---

## Prerequisites

**MANDATORY - Verify before starting:**
- ✅ Chrome DevTools MCP server connected
- ✅ ffmpeg installed (`ffmpeg -version`)
- ✅ User logged into Udemy with course access

---

## Workflow

### 1. Ask Output Directory

**⚠️ MANDATORY - Do NOT proceed without user confirmation.**

Use `AskUserQuestion` to get the output directory:

```
Question: "Where should I save the video?"
Options:
  - "Current directory: /path/to/cwd"
  - "Custom path"
```

**❌ DO NOT continue to step 2 until you have a confirmed output directory.**

Store the path for use in step 7 (ffmpeg download).

### 2. List Browser Pages

```
mcp__chrome-devtools__list_pages
```

**Identify Udemy lecture page:** URL pattern `udemy.com/course/*/learn/lecture/*`

### 3. Select Page

```
mcp__chrome-devtools__select_page(pageId=N)
```

### 4. Extract Video Info

**Take snapshot** to get lecture metadata:

```
mcp__chrome-devtools__take_snapshot
```

**Extract:** course name, lecture title/number, duration

**✅ DO:**
- Parse section/lecture numbers from page structure
- Extract clean course name (remove "- Udemy" suffix)
- Note the lecture index for sequential naming

### 5. Capture Network Traffic

**⚠️ CRITICAL - Ask user permission first:**

```
Question: "Reload page to capture video URL? (May reset video progress)"
Options: ["Yes, reload now", "No, cancel"]
```

**Only if user confirms:**

```
mcp__chrome-devtools__navigate_page(type="reload", ignoreCache=true)
mcp__chrome-devtools__list_network_requests
```

### 6. Find Media Sources

**MANDATORY - Consult [references/api-reference.md](references/api-reference.md)** for API structure.

**Find request** containing `media_sources`:

```
mcp__chrome-devtools__get_network_request(reqid=N)
```

**Parse response:**
- `asset.media_sources[0].src` → HLS m3u8 URL
- `course_is_drmed` → Must be `false`

**❌ DON'T:**
- Attempt download if `course_is_drmed: true`
- Use requests without `media_sources` field

### 7. Download with ffmpeg

**Execute ffmpeg download:**

```bash
ffmpeg -y \
  -headers "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36" \
  -headers "Referer: https://www.udemy.com/" \
  -i "HLS_M3U8_URL" \
  -c copy \
  -bsf:a aac_adtstoasc \
  "output-directory/{lecture_number}-{lecture_title}.mp4"
```

**Naming convention:** `{lecture_number}-{lecture_title}.mp4`

**✅ DO:**
- Use absolute path for output directory
- Sanitize title (remove special chars: `/`, `\`, `:`)
- Zero-pad lecture numbers (01, 02, ...)

**❌ DON'T:**
- Skip `-c copy` (causes re-encoding, very slow)
- Omit Referer header (may cause 403 errors)

**See:** [references/api-reference.md](references/api-reference.md) for complete command details.

### 8. Optimize Video

**MANDATORY - Compress and standardize naming.**

**⚠️ ALWAYS use the Skill tool with only the video path:**

```
Skill(optimize-video-course, args: "/path/to/video.mp4")
```

The `optimize-video-course` skill will:
- Extract metadata from path/filename
- Ask user for any missing info (year, course, module, lesson)
- Apply compression and naming conventions

**❌ DON'T:**
- Call the script directly
- Pass extra parameters - let the skill handle it

**Result:**
- 60-70% size reduction
- Universal naming: `YYYY - Course - MXX - LXX - Title.mp4`

---

## DRM Check

**If `course_is_drmed: true`:**

❌ **Video is DRM-protected and cannot be downloaded.**

**Inform user:**
```
This course uses DRM (Digital Rights Management) protection.
Videos cannot be downloaded due to copyright protection.

Alternatives:
- Watch online through Udemy
- Use Udemy's official offline viewing app
- Request non-DRM version from instructor
```

---

## Common Tasks

### Download Single Lecture
```
User: "Download this Udemy lecture"
1. list_pages → select Udemy page
2. take_snapshot → extract lecture info
3. Ask permission to reload
4. navigate_page(reload) → list_network_requests
5. get_network_request → find media_sources
6. ffmpeg download
7. optimize with optimize-video-course skill
```

### Download Entire Section
```
User: "Download all videos from this section"
For each lecture:
  1. Navigate to lecture page
  2. Follow single lecture workflow
  3. Track progress with Tasks
  4. Show summary when complete
```

### Quick Check if Downloadable
```bash
# Take snapshot → check page content for DRM indicators
# Or: Reload → Check network request for course_is_drmed field
```

---

## Error Handling

**Common errors:**

| Error | Cause | Solution |
|-------|-------|----------|
| `course_is_drmed: true` | DRM protection | Inform user, cannot download |
| 403 Forbidden | Missing Referer | Add `-headers "Referer: https://www.udemy.com/"` |
| Empty media_sources | Not on lecture page | Navigate to actual lecture, not course overview |
| ffmpeg hangs | Network issue | Add timeout: `-timeout 30000000` |

**✅ Best practices:**
- Always ask permission before reloading
- Verify file created before optimizing
- Show download progress to user
- Handle network errors gracefully

---

## References

**MANDATORY - Read for details:**
- **[references/api-reference.md](references/api-reference.md)** - API endpoints, response structure, ffmpeg command details
