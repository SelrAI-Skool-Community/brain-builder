#!/usr/bin/env python3
"""Ingest YouTube transcripts into a brain's `raw/` (spec.md §6, video arm).

    python3 ingest_youtube.py <url-or-search> [...] --into <brain-dir>
                              [--limit N] [--transcribe] [--engine <engine>] [--json]

Ported from the seed brain's prototype, which is where every awkward decision
here was paid for once already.

**yt-dlp as a library, updated on start.** A pinned version breaks — YouTube
changes what it takes to see a caption track, and an extractor from last month
returns nothing rather than an error. The arm updates on first use where the
install allows it and says plainly in `log.md` when it cannot.

**An archive file, inside the brain.** Gate 1 is edited by talking, so re-running
after "add this other channel" is the normal case, not the exception. Video ids
that already landed are skipped before a single request goes out, and a video
that *failed* is deliberately not archived — a re-run should retry it.

**Empty-transcript detection, always loud.** Throttling does not return an
error; it returns a caption file with nothing in it. Treated as a video that had
little to say, that is a corpus quietly missing its best sources. Here it is an
`empty` record with the fallback named in the reason.

**Ordering: publisher captions → transcription → fail loudly.** Transcription
costs money, so it happens only when the build was told it may (`--transcribe`,
after the member approved the figure at Gate 2). Without that permission a
caption-less video is recorded, never silently dropped.

Rolling captions are collapsed by `captions.py` before anything is written —
raw auto-subs inflate a transcript three to four times over.

Stdlib only, plus yt-dlp where a video is actually being fetched.
"""
import json
import os
import sys
import tempfile

import captions as caption_text
import cli
import transcribe
from raw_store import Manifest, RawStore, Record, log_manifest
from scaffold import log_event

SOURCE_FORMAT = "youtube"

#: Where the arm remembers what it already pulled. Dot-prefixed and outside the
#: contract's folders, so lint walks past it and `raw/` stays pure material.
ARCHIVE_RELPATH = os.path.join(".ingest", "youtube-archive.txt")

#: Seconds between requests. The rights stance promises visible, conservative
#: limits, and the prototype found residential-IP throttling starts in the low
#: thousands of videos a day.
SLEEP_REQUESTS = 1.0

INSTALL_HINT = "pip install yt-dlp"


class Video(object):
    """One video, as everything downstream needs it."""

    def __init__(self, video_id, title="", url="", channel="", duration=0, published=""):
        self.video_id = video_id
        self.title = title or video_id
        self.url = url or "https://www.youtube.com/watch?v=" + video_id
        self.channel = channel
        self.duration = duration
        self.published = published


class Archive(object):
    """The video ids this brain already holds."""

    def __init__(self, brain):
        self.path = archive_path(brain)
        self.ids = set()
        if os.path.isfile(self.path):
            with open(self.path, "r", encoding="utf-8") as handle:
                self.ids = {line.strip() for line in handle if line.strip()}

    def has(self, video_id):
        return video_id in self.ids

    def add(self, video_id):
        self.ids.add(video_id)

    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write("".join(video_id + "\n" for video_id in sorted(self.ids)))
        return self.path


def archive_path(brain):
    return os.path.join(os.path.abspath(os.path.expanduser(brain)), ARCHIVE_RELPATH)


def ingest(targets, brain, limit=None, transcribe_missing=False,
           engine=transcribe.DEFAULT_ENGINE, downloader=None, transcriber=None):
    """Ingest YouTube `targets` — channels, playlists, videos or searches."""
    downloader = downloader or YtDlp()
    transcriber = transcriber or _engine_transcriber(engine)
    store = RawStore(brain)
    manifest = Manifest(store.brain)
    archive = Archive(store.brain)

    for target in targets:
        _ingest_target(target, store, manifest, archive, downloader, transcriber,
                       limit, transcribe_missing, engine)

    archive.save()
    _log_update_note(store.brain, downloader)
    log_manifest(store.brain, manifest, "youtube")
    return manifest


def _ingest_target(target, store, manifest, archive, downloader, transcriber,
                   limit, transcribe_missing, engine):
    try:
        videos = downloader.videos(target, limit=limit)
    except ImportError as failure:
        return manifest.add(Record(target, "failed", source_format=SOURCE_FORMAT,
                                   reason="{} — {}".format(failure, INSTALL_HINT)))
    except Exception as failure:
        return manifest.add(Record(target, "failed", source_format=SOURCE_FORMAT,
                                   reason="could not list {}: {}".format(target, failure)))

    if not videos:
        return manifest.add(Record(target, "failed", source_format=SOURCE_FORMAT,
                                   reason="no videos found — check the channel, "
                                          "playlist or search term"))
    for video in videos:
        _ingest_video(video, store, manifest, archive, downloader, transcriber,
                      transcribe_missing, engine)


def _ingest_video(video, store, manifest, archive, downloader, transcriber,
                  transcribe_missing, engine):
    if archive.has(video.video_id):
        return manifest.add(Record(video.url, "duplicate", source_format=SOURCE_FORMAT,
                                   reason="already ingested — in the brain's archive"))
    try:
        text = caption_text.clean(downloader.captions(video), "vtt")
    except Exception as failure:            # one dead video never stops a corpus
        return manifest.add(Record(video.url, "failed", source_format=SOURCE_FORMAT,
                                   reason="captions unavailable: {}".format(failure)))

    transcript = "captions"
    if caption_text.is_empty(text):
        if not transcribe_missing:
            return manifest.add(Record(
                video.url, "empty", source_format=SOURCE_FORMAT,
                reason="no usable captions (throttled, or none published) — re-run "
                       "this arm with --transcribe to send it to the transcription "
                       "engine instead"))
        text, transcript, failure = _transcribe(video, downloader, transcriber, engine)
        if failure:
            return manifest.add(Record(video.url, "failed", source_format=SOURCE_FORMAT,
                                       reason=failure))
        if caption_text.is_empty(text):
            return manifest.add(Record(video.url, "empty", source_format=SOURCE_FORMAT,
                                       reason="transcription returned almost nothing"))

    already = store.duplicate_of(text)
    if already:
        archive.add(video.video_id)
        return manifest.add(Record(video.url, "duplicate", source_format=SOURCE_FORMAT,
                                   reason="same text as {}".format(already)))

    raw = store.add(text, video.title, source=video.url, source_format=SOURCE_FORMAT,
                    title=video.title, author=video.channel,
                    published=video.published, duration=video.duration,
                    transcript=transcript)
    archive.add(video.video_id)
    return manifest.add(Record(video.url, "ok", raw=raw, words=len(text.split()),
                               source_format=SOURCE_FORMAT))


def _transcribe(video, downloader, transcriber, engine):
    """Pull the audio and send it to the engine. Returns `(text, label, failure)`."""
    try:
        with tempfile.TemporaryDirectory(prefix="brain-audio-") as directory:
            audio = downloader.audio(video, directory)
            return transcriber(audio), engine, ""
    except Exception as failure:
        return "", engine, "transcription failed: {}".format(failure)


def _engine_transcriber(engine):
    def run(path):
        return transcribe.transcribe(path, engine=engine)
    return run


def _log_update_note(brain, downloader):
    note = getattr(downloader, "update_note", "")
    if note and os.path.isfile(os.path.join(brain, "log.md")):
        log_event(brain, "youtube: " + note)


def self_update(module, updater=None):
    """Keep yt-dlp current, and never let trying to stop the arm.

    A pinned yt-dlp is the single likeliest cause of a caption-less run, so this
    is attempted on every start. Pip installs cannot self-update — that is not a
    failure, it is a fact worth writing into `log.md` next to the version, so a
    build that comes back empty has the first thing to check already recorded.
    """
    version = getattr(getattr(module, "version", None), "__version__", "unknown")
    updater = updater or _builtin_updater(module)
    if updater is None:
        return ("yt-dlp {} — no self-update on this install; run `pip install -U "
                "yt-dlp` if extraction starts coming back empty".format(version))
    try:
        return "yt-dlp {} — {}".format(version, "updated" if updater() else "up to date")
    except Exception as failure:
        return ("yt-dlp {} — self-update failed ({}); run `pip install -U yt-dlp` "
                "if extraction starts coming back empty".format(version, failure))


def _builtin_updater(module):
    """yt-dlp's own updater, where the install has one."""
    updater = getattr(getattr(module, "update", None), "Updater", None)
    if updater is None:
        return None

    def run():
        with module.YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
            return bool(updater(ydl).update())
    return run


class YtDlp(object):
    """yt-dlp, held as a library and imported on first use.

    Kept behind this class so the arm can be tested end to end without yt-dlp,
    a network or a cookie jar, and so every yt-dlp option the prototype settled
    on lives in one readable place.
    """

    def __init__(self, sleep_requests=SLEEP_REQUESTS, cookies_from_browser=None):
        self.sleep_requests = sleep_requests
        self.cookies_from_browser = cookies_from_browser or os.environ.get(
            "YT_COOKIES_FROM_BROWSER")
        self.update_note = ""
        self._module = None

    def module(self):
        if self._module is None:
            import yt_dlp                   # noqa: E402 — optional, per-arm dependency
            self._module = yt_dlp
            self.update_note = self_update(yt_dlp)
        return self._module

    def videos(self, target, limit=None):
        """Every video behind a channel, playlist, video URL or search phrase."""
        query = target if "://" in target else "ytsearch{}:{}".format(limit or 20, target)
        options = self._options(extract_flat="in_playlist")
        with self.module().YoutubeDL(options) as ydl:
            info = ydl.extract_info(query, download=False)
        entries = info.get("entries") if isinstance(info, dict) else None
        rows = entries if entries is not None else [info]
        videos = [self._video(row, info) for row in rows if row]
        return videos[:limit] if limit else videos

    def captions(self, video):
        """The video's caption track as raw VTT — published first, auto second."""
        with tempfile.TemporaryDirectory(prefix="brain-captions-") as directory:
            options = self._options(
                skip_download=True, writesubtitles=True, writeautomaticsub=True,
                subtitleslangs=["en.*", "en"], subtitlesformat="vtt",
                ignore_no_formats_error=True,
                outtmpl=os.path.join(directory, "%(id)s.%(ext)s"))
            with self.module().YoutubeDL(options) as ydl:
                ydl.download([video.url])
            tracks = sorted(name for name in os.listdir(directory) if name.endswith(".vtt"))
            if not tracks:
                return ""
            with open(os.path.join(directory, tracks[0]), encoding="utf-8",
                      errors="replace") as handle:
                return handle.read()

    def audio(self, video, directory):
        """The video's audio on disk, for the transcription fallback."""
        options = self._options(format="bestaudio/best",
                                outtmpl=os.path.join(directory, "%(id)s.%(ext)s"))
        with self.module().YoutubeDL(options) as ydl:
            ydl.download([video.url])
        files = sorted(os.listdir(directory))
        if not files:
            raise RuntimeError("no audio came back for " + video.url)
        return os.path.join(directory, files[0])

    def _options(self, **extra):
        options = {"quiet": True, "no_warnings": True, "noprogress": True,
                   "sleep_requests": self.sleep_requests}
        if self.cookies_from_browser:
            options["cookiesfrombrowser"] = (self.cookies_from_browser,)
        options.update(extra)
        return options

    @staticmethod
    def _video(row, info):
        video_id = row.get("id") or ""
        return Video(video_id=video_id, title=row.get("title") or video_id,
                     url=row.get("webpage_url") or row.get("url")
                         or "https://www.youtube.com/watch?v=" + video_id,
                     channel=row.get("channel") or row.get("uploader")
                             or (info or {}).get("channel") or "",
                     duration=row.get("duration") or 0,
                     published=row.get("upload_date") or "")


# --- cli -------------------------------------------------------------------

USAGE = ("usage: ingest_youtube.py <url-or-search> [...] --into <brain-dir>\n"
         "                         [--limit <n>] [--transcribe] [--engine <engine>]"
         " [--json]\n")


def main(argv):
    try:
        targets, options = cli.scan(
            argv, options={"--into": None, "--limit": None, "--transcribe": False,
                           "--engine": transcribe.DEFAULT_ENGINE, "--json": False},
            flags=("--transcribe", "--json"))
        limit = int(options["--limit"]) if options["--limit"] else None
        transcribe.engine_for(options["--engine"])
    except (cli.UsageError, ValueError) as failure:
        sys.stderr.write("ingest_youtube.py: {}\n{}".format(failure, USAGE))
        return 2

    if not targets or not options["--into"]:
        sys.stderr.write(USAGE)
        return 2

    manifest = ingest(targets, options["--into"], limit=limit,
                      transcribe_missing=options["--transcribe"],
                      engine=options["--engine"])
    print(json.dumps(manifest.as_dict(), indent=2)
          if options["--json"] else manifest.summary())
    if manifest.whole_corpus_failed:
        sys.stderr.write("ingest_youtube.py: no transcript could be read — stop and "
                         "talk to the member rather than building an empty brain\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
