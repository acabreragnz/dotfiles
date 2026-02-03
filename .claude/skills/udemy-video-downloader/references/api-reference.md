# Udemy API Reference

## Lecture Media Sources Endpoint

```
GET /api-2.0/users/me/subscribed-courses/{course_id}/lectures/{lecture_id}/?fields[asset]=media_sources,captions,title,filename,data,body,media_license_token&fields[lecture]=asset,supplementary_assets
```

### Response Structure

```json
{
  "asset": {
    "media_sources": [
      {
        "type": "video/mp4",
        "src": "https://...master.m3u8?...",
        "label": "Auto"
      }
    ],
    "length": 1234,
    "title": "Lecture Title"
  },
  "course_is_drmed": false
}
```

### Key Fields

| Field | Description |
|-------|-------------|
| `asset.media_sources[0].src` | HLS m3u8 URL for video stream |
| `asset.length` | Duration in seconds |
| `asset.title` | Lecture title |
| `course_is_drmed` | `true` if DRM protected (cannot download) |

---

## ffmpeg Download Command

Full command with required headers:

```bash
ffmpeg -y \
  -headers "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36" \
  -headers "Referer: https://www.udemy.com/" \
  -headers "Origin: https://www.udemy.com" \
  -i "HLS_M3U8_URL" \
  -c copy \
  -bsf:a aac_adtstoasc \
  "output.mp4"
```

### Flags Explained

| Flag | Purpose |
|------|---------|
| `-y` | Overwrite output without asking |
| `-headers "User-Agent: ..."` | Required for authentication |
| `-headers "Referer: ..."` | Required for authentication |
| `-c copy` | Copy streams without re-encoding (preserves quality) |
| `-bsf:a aac_adtstoasc` | Fix audio stream for MP4 container |

---

## Finding the API Request

In the network requests list, look for:

1. URL pattern: `/api-2.0/users/me/subscribed-courses/*/lectures/*`
2. Query params containing `fields[asset]=media_sources`
3. Resource type: `fetch` or `xhr`

The response body contains the `media_sources` array with HLS URLs.

---

## Common Issues

### DRM Protected Content

If `course_is_drmed: true` in response, the video uses Widevine DRM and cannot be downloaded with this method.

### Expired URLs

HLS URLs contain tokens that expire. If download fails with 403, reload the page to get fresh URLs.

### Missing Headers

Without proper User-Agent and Referer headers, the CDN will reject requests with 403 Forbidden.
