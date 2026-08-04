# Source-ingestion capability scan

Migrated from planning ticket CORE-124 (resolved 2026-07-31). The content-rights findings here became `docs/rights.md`.

## Recommended v1 source lineup (one-week build)

1. **Local files** (md/txt/csv/json/docx/pdf/epub): day one, zero risk, proves the retrieval layer before network flakiness enters. Gotchas: iCloud/Drive placeholder stubs read as empty (skip loudly), macOS TCC permission prompts on ~/Documents (pre-flight check).
2. **PDFs + EPUB**: PyMuPDF4LLM + EbookLib, pip-installable, no models. Detect zero-text-layer (scanned) pages and *offer* OCR (ocrmypdf + tesseract) as opt-in, never a default dependency. Never touch Kindle/DRM.
3. **YouTube transcripts, bulk**: yt-dlp end to end. Discovery via `ytsearchN:`/channel/playlist with `--flat-playlist` (no API key, no quota), subtitles via `--skip-download --write-auto-subs`, `--download-archive` for idempotent resume, sleeps between requests, self-update yt-dlp on start (a pinned version will break), explicit empty-transcript detection (throttle poisoning must not be silent). Decisive finding: the block epidemic is a datacentre-IP problem; a member's home machine is the good environment. The Android-client MCP fetcher from the earlier skill is a per-video fallback only (no npm build requirement; it has no bulk mode anyway).
4. **Web articles**: trafilatura primary (benchmark leader, heuristic, fast, local), r.jina.ai opt-in fallback (20 RPM free), paywall-stub quarantine (min-length + "subscribe" heuristic; silent 200-word teasers are the nastiest KB poison).

**Out of the original scan's v1:** podcasts/audio, scanned-PDF OCR by default, anything DRM, anything hosted/shared. (The scope decision later pulled Apple Podcasts + generic RSS into v1, transcript-first with ElevenLabs Scribe v2 as the transcription fallback; audio-in-general and OCR stay out.)

**Highest-risk item to prototype first:** bulk YouTube on a fresh Windows machine, no cookies; that is where the bot-check wall shows or doesn't. Documented user-side fix if it trips: `--cookies-from-browser firefox`.

Volume reality: a few hundred videos per session on a residential IP is routine; low thousands per day is where throttles start (24-48h soft resets). Auto-captions have no punctuation or speaker labels: fine for retrieval, weak for verbatim quoting.
