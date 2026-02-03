# Video Encoding Options Reference

This document explains the encoding parameters available in the optimization script and when to use each option.

---

## CRF (Constant Rate Factor)

**What it is:** Quality-based compression setting for H.264 encoding

**Range:** 0-51 (lower = better quality, larger file)

**Recommended range for course videos:** 18-28

### CRF Values Guide

| CRF | Quality Level | Use Case | Expected Reduction | Visual Impact |
|-----|---------------|----------|-------------------|---------------|
| 18  | High Quality  | High-motion videos, detailed diagrams | 40-50% | Virtually no quality loss |
| 20  | Very Good     | Important visual content | 50-60% | Minimal quality loss |
| 23  | **Default**   | **Most course videos** | **60-70%** | **Barely noticeable loss** |
| 26  | Acceptable    | Voice-over slides, simple presentations | 70-75% | Slight blur on text |
| 28  | Lower Quality | Archive, low-priority content | 75-80% | Noticeable on detailed content |

### When to Use Each CRF

**CRF 18-20 (High Quality):**
- Videos with code editors (syntax highlighting must be crisp)
- Detailed diagrams or charts
- High-motion demos (animations, UI interactions)
- Professional production courses
- First recording/master copy

**CRF 23 (Recommended Default):**
- Standard educational videos
- Presentations with text
- Most coding tutorials
- Screencasts
- General-purpose course content

**CRF 26-28 (Smaller Size):**
- Voice-over slides (minimal visual change)
- Audio-focused content
- Archive copies
- Bandwidth-limited distribution

---

## Preset (Encoding Speed)

**What it is:** Trade-off between encoding speed and compression efficiency

**Available presets:** ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow

**Recommended for courses:** medium, slow

### Preset Comparison

| Preset | Encoding Speed | File Size | Compression Quality | Use Case |
|--------|---------------|-----------|---------------------|----------|
| ultrafast | Very Fast | Largest | Poor | Real-time encoding only |
| fast | Fast | Larger | Below average | Quick previews |
| **medium** | **Moderate** | **Balanced** | **Good** | **Default choice** |
| slow | Slow (2-3x longer) | Smaller (5-10%) | Very good | Final distribution |
| veryslow | Very slow (5x longer) | Smallest (10-15%) | Excellent | Archival, professional |

### When to Use Each Preset

**medium (Default):**
- Most scenarios
- Good balance of speed and compression
- Processing large course libraries (50+ videos)

**slow:**
- Final version for distribution
- Maximum quality retention important
- Smaller file size critical
- Time is not a constraint

**fast:**
- Quick tests or previews
- Time-sensitive processing
- Acceptable to sacrifice some compression

**veryslow:**
- Rarely needed for course videos
- Archival purposes only
- Professional production with ample time

---

## Audio Bitrate

**What it is:** Quality of audio encoding

**Format:** AAC (Advanced Audio Coding)

**Recommended range:** 96k-192k

### Audio Bitrate Guide

| Bitrate | Quality | Use Case | File Size Impact |
|---------|---------|----------|------------------|
| 96k | Acceptable | Voice-only, mono audio | Minimal |
| **128k** | **Good** | **Standard voice-over (default)** | **Small** |
| 160k | Very good | Music + voice | Moderate |
| 192k | High quality | Professional audio, music-heavy | Larger |

### When to Use Each Bitrate

**96k:**
- Voice-only narration
- Mono audio
- Bandwidth-limited scenarios

**128k (Default):**
- Standard voice-over courses
- Stereo voice narration
- Most educational content

**160-192k:**
- Courses with background music
- Professional audio production
- Podcast-style courses
- Music theory or audio-focused courses

---

## Tune (Encoding Optimization)

**What it is:** Optimizes encoding for specific content types

**Used in script:** `stillimage`

**Why stillimage for course videos:**
- Preserves sharpness on static content (code, text, diagrams)
- Reduces blur/artifacts on presentations
- Less aggressive temporal compression (between frames)
- Better for screen recordings with text

**Other tune options (not used):**
- `film`: For live-action video (movies, lectures with cameras)
- `animation`: For animated content
- `grain`: For preserving film grain (not relevant for courses)

**Do not change:** The script uses `stillimage` by default, which is optimal for course videos.

---

## AQ Mode (Adaptive Quantization)

**What it is:** How the encoder distributes bitrate across the frame

**Used in script:** `aq-mode 3`

**Why AQ mode 3:**
- Auto-variance: dynamically adjusts to content
- Preserves detail in text-heavy regions
- Reduces bitrate in uniform areas (backgrounds)
- Best for mixed content (text + images)

**Do not change:** The script uses the optimal setting for educational content.

---

## Recommended Configurations by Content Type

### 1. Standard Course Videos (Text + Voiceover)
```bash
--crf 23 --preset medium --audio-bitrate 128k
```
**Best for:** Most educational content, coding tutorials, presentations

---

### 2. High-Detail Code/Diagrams
```bash
--crf 20 --preset slow --audio-bitrate 128k
```
**Best for:** Detailed code walkthroughs, complex diagrams, important visual content

---

### 3. Simple Slides/Voice-over
```bash
--crf 26 --preset medium --audio-bitrate 96k
```
**Best for:** Slides with minimal animation, voice-focused content

---

### 4. Archival (Maximum Compression)
```bash
--crf 28 --preset veryslow --audio-bitrate 96k
```
**Best for:** Archive copies, low-priority storage

---

### 5. Professional Distribution (Highest Quality)
```bash
--crf 18 --preset slow --audio-bitrate 192k
```
**Best for:** Premium courses, professional production, master copies

---

## Decision Tree for Settings

```
START: What kind of course video?

├─ Is text clarity critical? (code, detailed diagrams)
│  YES → CRF 18-20, preset slow
│  NO → Continue
│
├─ Is there music or high-quality audio?
│  YES → audio-bitrate 160k-192k
│  NO → audio-bitrate 128k
│
├─ Is file size a major concern?
│  YES → CRF 26, preset slow
│  NO → CRF 23, preset medium (default)
```

---

## File Size Expectations

### Typical 1-hour video (1080p)

| Settings | Original | Optimized | Reduction |
|----------|----------|-----------|-----------|
| CRF 18, slow | 4.5 GB | 2.0 GB | 56% |
| **CRF 23, medium** | **4.5 GB** | **1.5 GB** | **67%** |
| CRF 26, slow | 4.5 GB | 1.2 GB | 73% |
| CRF 28, veryslow | 4.5 GB | 900 MB | 80% |

**Variables affecting size:**
- Resolution (1080p vs 720p)
- Frame rate (30fps vs 60fps)
- Content complexity (static slides vs motion)
- Original encoding quality

---

## Performance Impact

### Processing Time (1-hour video, 1080p)

| Preset | Approximate Time | Relative Speed |
|--------|------------------|----------------|
| fast | 8 minutes | 1.0x |
| medium | 15 minutes | 1.9x |
| slow | 35 minutes | 4.4x |
| veryslow | 75 minutes | 9.4x |

**Note:** Times vary based on CPU, resolution, and content complexity.

---

## When to Ask User for Custom Settings

Claude should ask user if they want custom settings when:

1. **User explicitly mentions quality:**
   - "High quality optimization"
   - "Maximum compression"
   - "Keep quality as high as possible"

2. **Special content type:**
   - "Videos have detailed code"
   - "Course includes music"
   - "Simple presentation slides"

3. **Size constraints:**
   - "Need to fit in X GB"
   - "Optimize for web streaming"
   - "Archive for long-term storage"

**Default behavior:** Use CRF 23, preset medium, audio 128k unless user specifies otherwise.

---

## Example Script Invocations

### Default (Recommended)
```bash
~/.claude/skills/optimize-video-course/scripts/optimize_video.sh \
  --input "video.mp4" \
  --year 2026 \
  --course "Course Name" \
  --lesson 1 \
  --title "Title" \
  --crf 23
```
(Preset defaults to medium, audio defaults to 128k)

### High Quality
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

### Maximum Compression
```bash
~/.claude/skills/optimize-video-course/scripts/optimize_video.sh \
  --input "video.mp4" \
  --year 2026 \
  --course "Course Name" \
  --lesson 1 \
  --title "Title" \
  --crf 28 \
  --preset slow \
  --audio-bitrate 96k
```

---

---

## Resolution Scaling (--max-height)

**What it does:** Limits video height while preserving aspect ratio

**Default:** Keep original resolution (recommended for most cases)

### Common Values

| Value | Resolution Name | Use Case | Additional Reduction vs Original |
|-------|----------------|----------|-----------------------------------|
| (omit) | Original | **Default** - Maximum quality | 0% |
| 1080 | Full HD | Limit 4K videos, most displays | ~30% vs 4K |
| 720 | HD | Mobile devices, bandwidth limited | ~50% vs 1080p |
| 480 | SD | Archive, minimal storage | ~70% vs 1080p |

### When to Use Resolution Scaling

**✅ Use --max-height when:**
- Video is 4K (2160p) but content is simple slides/talking head
- Target audience uses mobile devices primarily
- Bandwidth or storage is severely constrained
- Original was recorded at unnecessarily high resolution
- Content has minimal visual detail (voice-over with static images)

**❌ Don't use --max-height when:**
- Video contains code with small fonts (may become illegible)
- Detailed diagrams, charts, or complex visuals
- High-quality production course worth preserving
- Any doubt about readability after scaling
- Original is already 720p or lower

### Examples

#### Limit 4K to 1080p
```bash
# Original: 3840x2160 (4K), 500 MB
# Result: 1920x1080 (1080p), ~60 MB (88% reduction)
--max-height 1080
```

#### Mobile-Optimized (720p)
```bash
# Original: 1920x1080 (1080p), 300 MB
# Result: 1280x720 (720p), ~90 MB (70% reduction)
--max-height 720
```

#### Archive Copy (480p)
```bash
# Original: 1920x1080 (1080p), 300 MB
# Result: 854x480 (480p), ~40 MB (87% reduction)
--max-height 480
```

### How It Works

The script uses ffmpeg's scale filter:
```bash
-vf "scale=-2:min(ih,$MAX_HEIGHT)"
```

- `min(ih,$MAX_HEIGHT)`: Only scales if height > max-height
- `-2`: Automatically calculates width to preserve aspect ratio (divisible by 2 for H.264)
- No scaling occurs if video is already shorter than max-height

### Size Impact Comparison

**1-hour video, 1080p original:**

| Settings | File Size | Quality | Notes |
|----------|-----------|---------|-------|
| CRF 23 only | 1.5 GB | Excellent | Recommended default |
| CRF 23 + 720p | 500 MB | Good | Mobile-friendly |
| CRF 23 + 480p | 250 MB | Acceptable | Archive only |

**Recommendation:** Start with CRF 23 only. Add --max-height only if file size is still too large.

---

## Future Enhancements

These encoding options may be added in future versions:

- **Two-pass encoding:** For more consistent quality (slower)
- **Hardware acceleration:** Use GPU for faster encoding (quality trade-off)
- **Variable frame rate:** Reduce frame rate for static content

For now, the single-pass H.264 approach with optional resolution scaling balances quality, speed, and compatibility.
