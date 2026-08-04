#!/usr/bin/env python3
"""Ingest YouTube transcripts into a brain's `raw/` (spec.md §6, video arm).

    python3 ingest_youtube.py <url-or-search> [...] --into <brain-dir>
                              [--limit N] [--transcribe] [--engine <engine>] [--json]
    python3 ingest_youtube.py --estimate <url-or-search> [...] [--limit N]

Ported from the seed brain's prototype, which is where every awkward decision
here was paid for once already.

**Cookies and a JS runtime, then plainer, then anonymous.** YouTube's bot check
wants browser cookies and its caption formats want the challenge solver, so
captions are tried against three recipes in turn (`CAPTION_RECIPES`). Anonymous
is last rather than first because a machine with a browser profile is the good
environment for this, and a machine without one still works.

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
import rights
import transcribe
from raw_store import Manifest, RawStore, Record, log_manifest, report
from scaffold import log_event

SOURCE_FORMAT = "youtube"

#: The only hosts this arm fetches. yt-dlp ships extractors for TikTok,
#: Instagram, Vimeo, X and Facebook, so without this guard the deferred list
#: (spec.md §6) would be enforced by nothing but the model's good manners — and
#: a Spotify URL would reach the generic extractor, which is a rights failure
#: rather than a scope one. A bare search term has no host and is always fine.
YOUTUBE_HOSTS = ("youtube.com", "youtu.be", "youtube-nocookie.com")

#: Where the arm remembers what it already pulled. Dot-prefixed and outside the
#: contract's folders, so lint walks past it and `raw/` stays pure material.
ARCHIVE_RELPATH = os.path.join(".ingest", "youtube-archive.txt")

#: Seconds between requests. The rights stance promises visible, conservative
#: limits, and the prototype found residential-IP throttling starts in the low
#: thousands of videos a day.
SLEEP_REQUESTS = 1.0

INSTALL_HINT = "pip install yt-dlp"

#: The prototype's finding, kept: YouTube's bot check wants browser cookies, and
#: exposing caption formats wants a JS runtime with the challenge solver. Each
#: recipe is tried in turn and the anonymous one is last, so a video that needs
#: none of it still works on a machine with no browser profile at all.
CAPTION_RECIPES = (
    {"cookies": True, "js": True},
    {"cookies": True, "js": False},
    {"cookies": False, "js": False},
)

#: Which browser's cookies, when a recipe wants them. `none` opts out entirely.
DEFAULT_COOKIE_BROWSER = "chrome"

#: English caption tracks, best first. Alphabetical order would prefer `en-US`
#: to `en`, which is not a preference anyone holds.
LANGUAGE_PREFERENCE = ("en", "en-orig", "en-US", "en-GB")


class Video(object):
    """One video, as everything downstream needs it."""

    def __init__(self, video_id, title="", url="", channel="", duration=0, published=""):
        self.video_id = video_id
        self.title = title or video_id
        self.url = url or "https://www.youtube.com/watch?v=" + video_id
        self.channel = channel
        self.duration = duration
        self.published = published


class Run(object):
    """One invocation's collaborators, so the per-video path takes two arguments.

    They travelled together as seven parameters through three functions, which
    is a type asking to be born.
    """

    def __init__(self, store, manifest, archive, downloader, transcriber,
                 transcribe_missing, engine):
        self.store = store
        self.manifest = manifest
        self.archive = archive
        self.downloader = downloader
        self.transcriber = transcriber
        self.transcribe_missing = transcribe_missing
        self.engine = engine

    def record(self, video, outcome, reason):
        """One video's outcome, named the way a member would recognise it."""
        if video.title and video.title != video.video_id:
            reason = "“{}”: {}".format(video.title, reason)
        return self.manifest.add(Record(video.url, outcome,
                                        source_format=SOURCE_FORMAT, reason=reason))


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
    store = RawStore(brain)
    run = Run(store=store, manifest=Manifest(store.brain), archive=Archive(store.brain),
              downloader=downloader,
              transcriber=transcriber or transcribe.transcriber_for(engine),
              transcribe_missing=transcribe_missing, engine=transcribe.engine_for(engine))

    for target in targets:
        _ingest_target(target, run, limit)

    run.archive.save()
    _log_update_note(store.brain, downloader)
    log_manifest(store.brain, run.manifest, "youtube")
    return run.manifest


def estimate(targets, limit=None, engine=transcribe.DEFAULT_ENGINE, downloader=None):
    """The ceiling on what transcribing this YouTube corpus could cost.

    A feed advertises which episodes ship a transcript; YouTube does not — the
    only way to know whether a video has usable captions is to ask for them,
    which is the fetch itself. So Gate 2 gets the worst case, said as the worst
    case, and the arm still tries captions first on every video.
    """
    downloader = downloader or YtDlp()
    durations, unpriced = [], []
    for target in targets:
        refusal = target_refusal(target)
        if refusal:                         # never fetched, so never priced
            unpriced.append("{} ({})".format(target, refusal))
            continue
        try:
            videos = downloader.videos(target, limit=limit)
        except Exception as failure:
            unpriced.append("{} ({})".format(target, failure))
            continue
        durations.extend(video.duration for video in videos)
    return transcribe.Quote(transcribe.estimate(durations, engine=engine),
                            unpriced=unpriced, ceiling=True)


def target_refusal(target):
    """Why this arm will not fetch `target`, or `None`.

    Two different refusals, deliberately worded differently: a DRM'd host is the
    rights stance (docs/rights.md) and never has a way in, while another video
    platform is simply not in v1 and might be later. Both are named, neither is
    worked around, and a bare search term is neither.
    """
    if "://" not in (target or ""):
        return None
    drm = rights.refusal_for_url(target)
    if drm:
        return drm
    host = rights.host_of(target)
    if any(host == allowed or host.endswith("." + allowed) for allowed in YOUTUBE_HOSTS):
        return None
    return ("{} is not a v1 source — this arm reads YouTube. Instagram, TikTok, "
            "Vimeo, X, Facebook and LinkedIn are deferred; an export, a download "
            "or the show's RSS feed is the way in today.".format(host or target))


def _ingest_target(target, run, limit):
    refusal = target_refusal(target)
    if refusal:                             # refused before a single request goes out
        return run.manifest.add(Record(target, "unsupported",
                                       source_format=SOURCE_FORMAT, reason=refusal))
    try:
        videos = run.downloader.videos(target, limit=limit)
    except ImportError as failure:
        return run.manifest.add(Record(target, "failed", source_format=SOURCE_FORMAT,
                                       reason="{} — {}".format(failure, INSTALL_HINT)))
    except Exception as failure:
        return run.manifest.add(Record(
            target, "failed", source_format=SOURCE_FORMAT,
            reason="could not list {}: {}".format(target, failure)))

    if not videos:
        return run.manifest.add(Record(
            target, "failed", source_format=SOURCE_FORMAT,
            reason="no videos found — check the channel, playlist or search term"))
    for video in videos:
        _ingest_video(video, run)


def _ingest_video(video, run):
    if run.archive.has(video.video_id):
        return run.record(video, "duplicate",
                          "already ingested — in the brain's archive")
    try:
        text = caption_text.clean(run.downloader.captions(video), "vtt")
    except Exception as failure:            # one dead video never stops a corpus
        return run.record(video, "failed",
                          "captions unavailable: {}".format(failure))

    provenance = {"transcript": "captions"}
    if caption_text.is_empty(text):
        if not run.transcribe_missing:
            return run.record(
                video, "empty",
                "no usable captions (throttled, or none published) — re-run this "
                "arm with --transcribe to send it to the transcription engine instead")
        text, failure = _transcribe(video, run)
        if failure:
            return run.record(video, "failed", failure)
        if caption_text.is_empty(text):
            return run.record(video, "empty", "transcription returned almost nothing")
        provenance = {"transcript": run.engine.name, "caution": run.engine.caution}

    already = run.store.duplicate_of(text)
    if already:
        run.archive.add(video.video_id)
        return run.record(video, "duplicate", "same text as {}".format(already))

    landed = run.store.land(run.manifest, text, video.title, video.url, SOURCE_FORMAT,
                            title=video.title, author=video.channel,
                            published=video.published, duration=video.duration,
                            **provenance)
    if landed.outcome == "ok":
        run.archive.add(video.video_id)
    return landed


def _transcribe(video, run):
    """Pull the audio and send it to the engine. Returns `(text, failure)`."""
    try:
        with tempfile.TemporaryDirectory(prefix="brain-audio-") as directory:
            return run.transcriber(run.downloader.audio(video, directory)), ""
    except Exception as failure:
        return "", "transcription failed: {}".format(failure)


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

    def __init__(self, sleep_requests=SLEEP_REQUESTS, cookies_from_browser=None,
                 environ=None):
        environ = os.environ if environ is None else environ
        self.sleep_requests = sleep_requests
        browser = (cookies_from_browser
                   or environ.get("YT_COOKIES_FROM_BROWSER")
                   or DEFAULT_COOKIE_BROWSER)
        self.cookies_from_browser = "" if browser.lower() == "none" else browser
        self.update_note = ""
        self._module = None

    def module(self):
        if self._module is None:
            import yt_dlp                   # noqa: E402 — optional, per-arm dependency
            self._module = yt_dlp
            self.update_note = self_update(yt_dlp)
        return self._module

    def videos(self, target, limit=None):
        """Every video behind a channel, playlist, video URL or search phrase.

        A channel URL does not resolve to videos: it resolves to the channel's
        *tabs* — Videos, Shorts, Live — each of which is itself a playlist. So
        the entries are flattened until what is left has a video id.
        """
        query = target if "://" in target else "ytsearch{}:{}".format(limit or 20, target)
        options = self._options(extract_flat="in_playlist")
        with self.module().YoutubeDL(options) as ydl:
            info = ydl.extract_info(query, download=False)
        videos = [self._video(row, info) for row in _flatten(info)]
        return videos[:limit] if limit else videos

    def captions(self, video):
        """The video's English caption track as raw VTT, or `""` if it has none.

        Tried against each recipe in turn (`CAPTION_RECIPES`): cookies and a JS
        runtime first, because that is what the bot check and the challenge
        solver want, then plain cookies, then anonymous. The prototype needed
        all three, and the machine this runs on is a member's own — which the
        research found is the good environment for exactly this.
        """
        for recipe in CAPTION_RECIPES:
            if recipe["cookies"] and not self.cookies_from_browser:
                continue                    # nothing to offer; the next recipe is lighter
            text = self._captions_once(video, recipe)
            if text:
                return text
        return ""

    def _captions_once(self, video, recipe):
        with tempfile.TemporaryDirectory(prefix="brain-captions-") as directory:
            options = self._options(
                skip_download=True, writesubtitles=True, writeautomaticsub=True,
                subtitleslangs=["en.*", "en"], subtitlesformat="vtt",
                ignore_no_formats_error=True, cookies=recipe["cookies"],
                outtmpl=os.path.join(directory, "%(id)s.%(ext)s"))
            if recipe["js"]:
                options["js_runtimes"] = ["node"]
                options["remote_components"] = ["ejs:github"]
            try:
                with self.module().YoutubeDL(options) as ydl:
                    ydl.download([video.url])
            except Exception:                # a recipe that fails is why there are three
                return ""
            track = _pick_track([name for name in os.listdir(directory)
                                 if name.endswith(".vtt")])
            if not track:
                return ""
            with open(os.path.join(directory, track), encoding="utf-8",
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

    def _options(self, cookies=True, **extra):
        options = {"quiet": True, "no_warnings": True, "noprogress": True,
                   "sleep_requests": self.sleep_requests}
        if cookies and self.cookies_from_browser:
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


def _flatten(info, depth=0):
    """Every video row inside an extract_info result, tabs and playlists opened.

    Bounded depth because the structure is (channel → tab → playlist → video) at
    worst, and an unbounded walk over someone's whole channel graph is not what
    "the last 40 videos" asked for.
    """
    if not isinstance(info, dict):
        return []
    entries = info.get("entries")
    if entries is None:
        return [info] if info.get("id") else []
    if depth >= 3:
        return []
    rows = []
    for entry in entries:
        if isinstance(entry, dict) and entry.get("_type") == "playlist":
            rows.extend(_flatten(entry, depth + 1))
        elif isinstance(entry, dict) and entry.get("id"):
            rows.append(entry)
    return rows


def _pick_track(names):
    """The best English caption file yt-dlp wrote, by language not by alphabet."""
    if not names:
        return None
    def rank(name):
        language = name.rsplit(".", 2)[-2] if name.count(".") >= 2 else ""
        return (LANGUAGE_PREFERENCE.index(language)
                if language in LANGUAGE_PREFERENCE else len(LANGUAGE_PREFERENCE),
                name)
    return sorted(names, key=rank)[0]


# --- cli -------------------------------------------------------------------

USAGE = ("usage: ingest_youtube.py <url-or-search> [...] --into <brain-dir>\n"
         "                         [--limit <n>] [--transcribe] [--engine <engine>]"
         " [--json]\n"
         "       ingest_youtube.py --estimate <url-or-search> [...] [--limit <n>]\n")


def main(argv):
    try:
        targets, options = cli.scan(
            argv, options={"--into": None, "--limit": None, "--transcribe": False,
                           "--estimate": False, "--engine": transcribe.DEFAULT_ENGINE,
                           "--json": False},
            flags=("--transcribe", "--estimate", "--json"))
        limit = int(options["--limit"]) if options["--limit"] else None
        transcribe.engine_for(options["--engine"])
    except (cli.UsageError, ValueError) as failure:
        sys.stderr.write("ingest_youtube.py: {}\n{}".format(failure, USAGE))
        return 2

    if not targets:
        sys.stderr.write(USAGE)
        return 2

    if options["--estimate"]:
        quote = estimate(targets, limit=limit, engine=options["--engine"])
        print(json.dumps(quote.as_dict(), indent=2) if options["--json"] else quote.line())
        return 0

    if not options["--into"]:
        sys.stderr.write(USAGE)
        return 2

    return report(ingest(targets, options["--into"], limit=limit,
                         transcribe_missing=options["--transcribe"],
                         engine=options["--engine"]),
                  "ingest_youtube.py", "no transcript could be read",
                  as_json=options["--json"])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
