#!/usr/bin/env python3
"""Ingest podcasts into a brain's `raw/` (spec.md §6, Apple Podcasts + RSS arm).

    python3 ingest_podcast.py <apple-url|itunes-id|rss-url|"show name"> [...]
                              --into <brain-dir> [--limit N] [--transcribe]
                              [--engine <engine>] [--delay 1.5] [--json]
    python3 ingest_podcast.py --estimate <show> [...]

Two subsystems feed one transcription fallback: yt-dlp handles anything
video-shaped, and this handles anything feed-shaped. They are separate because
the resolution problem is different — Apple Podcasts is a *directory*, not a
host. Nothing is fetched from Apple; an Apple URL yields an `id`, the iTunes
Lookup API turns that `id` into the publisher's own `feedUrl`, and everything
after that is ordinary RSS from the publisher.

**The transcript is often already there.** `<podcast:transcript>` is a real and
growing tag, and an episode that ships one costs nothing to ingest. So the
ordering is publisher transcript → transcription fallback → fail loudly, and
`--estimate` prices only the episodes that would actually need the engine.

**Spotify resolves to RSS or it does not resolve.** The player is DRM'd and the
kit never touches it (docs/rights.md). A Spotify-exclusive show has no feed to
find, and that is a dead end stated plainly rather than a workaround to hunt —
an episode with no audio and no transcript comes back as a named failure.

Stdlib only: `ElementTree` reads RSS, and the network sits behind `fetching`.
"""
import json
import os
import re
import sys
import tempfile
import xml.etree.ElementTree as ElementTree
from urllib.parse import quote_plus

import captions as caption_text
import cli
import rights
import transcribe
from fetching import DEFAULT_DELAY, FetchError, Fetcher
from raw_store import Manifest, RawStore, Record, log_manifest, report

SOURCE_FORMAT = "podcast"

LOOKUP_URL = "https://itunes.apple.com/lookup?id={}&entity=podcast"
SEARCH_URL = "https://itunes.apple.com/search?media=podcast&limit=1&term={}"

#: Transcript formats, richest first. A format not on this list is not chosen —
#: a PDF "transcript" is not one this kit can read.
TRANSCRIPT_PREFERENCE = ("vtt", "json", "srt", "html", "text")

_ITUNES = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"
_PODCAST = "{https://podcastindex.org/namespace/1.0}"
_APPLE_ID = re.compile(r"/id(\d+)")


class ResolveError(Exception):
    """The show could not be turned into a feed. Never a silent skip."""


class Episode(object):
    """One item in a feed, and the two ways its words might be got."""

    def __init__(self, title="", guid="", published="", duration=0, page_url="",
                 enclosure_url="", transcripts=None, feed_url=""):
        self.title = title
        self.guid = guid
        self.published = published
        self.duration = duration
        self.page_url = page_url
        self.enclosure_url = enclosure_url
        self.transcripts = transcripts or []
        self.feed_url = feed_url

    @property
    def source(self):
        """What the `raw/` page is attributed to: the episode's own page.

        Falls back through everything the feed might have given it and ends at
        the feed itself, because a chunk with nothing to attribute it to is a
        chunk the rights stance will not let into `raw/` at all.
        """
        return (self.page_url or self.enclosure_url or self.guid or self.title
                or self.feed_url)


class Run(object):
    """One invocation's collaborators, so the per-episode path stays readable."""

    def __init__(self, store, manifest, fetcher, transcriber, transcribe_missing, engine):
        self.store = store
        self.manifest = manifest
        self.fetcher = fetcher
        self.transcriber = transcriber
        self.transcribe_missing = transcribe_missing
        self.engine = engine

    def record(self, episode, outcome, reason):
        """One episode's outcome, named the way a member would recognise it.

        The `source` stays the URL — that is the attribution — but the log line
        leads with the episode title, because "ep2.mp3" tells nobody which
        episode of which show came back without words.
        """
        if episode.title:
            reason = "“{}”: {}".format(episode.title, reason)
        return self.manifest.add(Record(episode.source, outcome,
                                        source_format=SOURCE_FORMAT, reason=reason))


class Feed(object):
    """A show: what it is called, who makes it, and what is in it."""

    def __init__(self, title="", author="", url="", episodes=None):
        self.title = title
        self.author = author
        self.url = url
        self.episodes = episodes or []


def ingest(targets, brain, limit=None, transcribe_missing=False,
           engine=transcribe.DEFAULT_ENGINE, fetcher=None, transcriber=None,
           delay=DEFAULT_DELAY):
    """Ingest podcast `targets` into `brain`'s `raw/`. Never raises."""
    fetcher = fetcher or Fetcher(delay=delay)
    store = RawStore(brain)
    run = Run(store=store, manifest=Manifest(store.brain), fetcher=fetcher,
              transcriber=transcriber or transcribe.transcriber_for(engine),
              transcribe_missing=transcribe_missing,
              engine=transcribe.engine_for(engine))

    for target in targets:
        feed = _load_feed(target, fetcher, run.manifest)
        if feed is None:
            continue
        for episode in (feed.episodes[:limit] if limit else feed.episodes):
            _ingest_episode(episode, feed, run)

    log_manifest(store.brain, run.manifest, "podcast")
    return run.manifest


def estimate(targets, fetcher=None, limit=None, engine=transcribe.DEFAULT_ENGINE,
             delay=DEFAULT_DELAY):
    """What Gate 2 quotes: the hours only the episodes with no transcript cost.

    An episode that ships a `<podcast:transcript>` is free, so pricing it would
    quote the member for work the build will not do. A published transcript that
    turns out to be dead does fall through to the engine at build time, and that
    is the one direction this estimate can be wrong in — under, never over.

    A show that cannot be resolved is named rather than dropped: quoting "$0"
    for a corpus that will fail at build time is the worst possible use of the
    one gate where cost is stated.
    """
    fetcher = fetcher or Fetcher(delay=delay)
    durations, unpriced = [], []
    for target in targets:
        try:
            feed = parse_feed(fetcher(resolve_feed(target, fetcher)).text)
        except (ResolveError, rights.RightsError, FetchError,
                ElementTree.ParseError) as failure:
            unpriced.append("{} ({})".format(target, failure))
            continue
        for episode in (feed.episodes[:limit] if limit else feed.episodes):
            if not pick_transcript(episode.transcripts) and episode.enclosure_url:
                durations.append(episode.duration)
    return transcribe.Quote(transcribe.estimate(durations, engine=engine),
                            unpriced=unpriced)


def resolve_feed(target, fetcher):
    """The publisher's RSS URL for a show, however the member named it."""
    refusal = rights.refusal_for_url(target)
    if refusal:
        raise rights.RightsError(refusal)

    apple_id = _APPLE_ID.search(target) if "podcasts.apple.com" in target else None
    if apple_id:
        return _from_directory(LOOKUP_URL.format(apple_id.group(1)), fetcher, target)
    if target.strip().isdigit():
        return _from_directory(LOOKUP_URL.format(target.strip()), fetcher, target)
    if "://" in target:
        return target
    return _from_directory(SEARCH_URL.format(quote_plus(target.strip())), fetcher, target)


def _from_directory(url, fetcher, target):
    try:
        payload = json.loads(fetcher(url).text)
    except (FetchError, ValueError) as failure:
        raise ResolveError("could not look {} up in the podcast directory: {}"
                           .format(target, failure))
    for result in payload.get("results") or []:
        if result.get("feedUrl"):
            return result["feedUrl"]
    raise ResolveError(
        "no RSS feed for {} in the podcast directory — a show with no feed is "
        "usually a platform exclusive, and there is no other way in".format(target))


def parse_feed(xml, url=""):
    """An RSS document as a `Feed`, `<podcast:transcript>` tags included."""
    root = ElementTree.fromstring(xml)
    channel = root.find("channel") if root.tag != "channel" else root
    if channel is None:
        raise ElementTree.ParseError("not an RSS feed")
    return Feed(title=_text(channel, "title"),
                author=_text(channel, _ITUNES + "author") or _text(channel, "managingEditor"),
                url=url,
                episodes=[_episode(item, url) for item in channel.findall("item")])


def _episode(item, feed_url=""):
    enclosure = item.find("enclosure")
    return Episode(
        title=_text(item, "title"), guid=_text(item, "guid"),
        published=_text(item, "pubDate"),
        duration=transcribe.parse_duration(_text(item, _ITUNES + "duration")),
        page_url=_text(item, "link"),
        enclosure_url=(enclosure.get("url") or "") if enclosure is not None else "",
        transcripts=[(node.get("url") or "", node.get("type") or "")
                     for node in item.findall(_PODCAST + "transcript")
                     if node.get("url")],
        feed_url=feed_url)


def pick_transcript(transcripts):
    """The best transcript the kit can actually read, or `None`."""
    ranked = []
    for url, mime in transcripts or []:
        fmt = caption_text.known_format(mime, url)
        if fmt in TRANSCRIPT_PREFERENCE:
            ranked.append((TRANSCRIPT_PREFERENCE.index(fmt), url, mime))
    if not ranked:
        return None
    ranked.sort(key=lambda row: row[0])
    return ranked[0][1], ranked[0][2]


def _load_feed(target, fetcher, manifest):
    try:
        url = resolve_feed(target, fetcher)
        return parse_feed(fetcher(url).text, url)
    except (ResolveError, rights.RightsError, FetchError) as failure:
        manifest.add(Record(target, "failed", source_format=SOURCE_FORMAT,
                            reason=str(failure)))
    except ElementTree.ParseError as failure:
        manifest.add(Record(target, "failed", source_format=SOURCE_FORMAT,
                            reason="{} is not a readable RSS feed: {}".format(target, failure)))
    return None


def _ingest_episode(episode, feed, run):
    text = _published_transcript(episode, run.fetcher)
    provenance = {"transcript": "publisher"}

    if not text and not episode.enclosure_url:
        return run.record(episode, "failed",
                          "no audio and no transcript in the feed — this reads as a "
                          "platform exclusive, and there is no other way in")

    if not text:
        if not run.transcribe_missing:
            return run.record(episode, "empty",
                              "no published transcript — re-run this arm with "
                              "--transcribe to send the audio to the transcription "
                              "engine instead")
        text, failure = _transcribe(episode, run)
        if failure:
            return run.record(episode, "failed", failure)
        provenance = {"transcript": run.engine.name, "caution": run.engine.caution}

    if caption_text.is_empty(text):
        return run.record(episode, "empty", "the transcript came back almost empty")

    already = run.store.duplicate_of(text)
    if already:
        return run.record(episode, "duplicate", "same text as {}".format(already))

    return run.store.land(run.manifest, text, episode.title or episode.guid,
                          episode.source, SOURCE_FORMAT, title=episode.title,
                          author=feed.author or feed.title,
                          published=episode.published, duration=episode.duration,
                          show=feed.title, **provenance)


def _published_transcript(episode, fetcher):
    """The publisher's own transcript, if there is one and it can be read.

    A transcript URL that 404s is not a failure — it is a reason to fall through
    to the next step in the ordering, which is exactly what the ordering is for.
    The feed's declared type wins; the server's `Content-Type` is the fallback,
    because feeds declare `application/octet-stream` at a real rate.
    """
    chosen = pick_transcript(episode.transcripts)
    if not chosen:
        return ""
    url, mime = chosen
    try:
        response = fetcher(url)
    except FetchError:
        return ""
    fmt = caption_text.known_format(mime, url) or caption_text.format_for(
        response.content_type, url)
    text = caption_text.clean(response.text, fmt)
    return "" if caption_text.is_empty(text) else text


def _transcribe(episode, run):
    """Pull the enclosure and send it to the engine. Returns `(text, failure)`."""
    try:
        with tempfile.TemporaryDirectory(prefix="brain-audio-") as directory:
            audio = run.fetcher.download(episode.enclosure_url, directory,
                                         _media_name(episode))
            return run.transcriber(audio), ""
    except Exception as failure:
        return "", "transcription failed: {}".format(failure)


def _media_name(episode):
    extension = os.path.splitext(episode.enclosure_url.split("?")[0])[1] or ".mp3"
    return "episode" + extension


def _text(node, tag):
    found = node.find(tag)
    return (found.text or "").strip() if found is not None and found.text else ""


# --- cli -------------------------------------------------------------------

USAGE = ("usage: ingest_podcast.py <apple-url|itunes-id|rss-url|\"show name\"> [...]\n"
         "                         --into <brain-dir> [--limit <n>] [--transcribe]\n"
         "                         [--engine <engine>] [--delay <seconds>] [--json]\n"
         "       ingest_podcast.py --estimate <show> [...] [--limit <n>]\n")


def main(argv):
    try:
        targets, options = cli.scan(
            argv, options={"--into": None, "--limit": None, "--transcribe": False,
                           "--estimate": False, "--engine": transcribe.DEFAULT_ENGINE,
                           "--delay": DEFAULT_DELAY, "--json": False},
            flags=("--transcribe", "--estimate", "--json"))
        limit = int(options["--limit"]) if options["--limit"] else None
        delay = float(options["--delay"])
        transcribe.engine_for(options["--engine"])
    except (cli.UsageError, ValueError) as failure:
        sys.stderr.write("ingest_podcast.py: {}\n{}".format(failure, USAGE))
        return 2

    if not targets:
        sys.stderr.write(USAGE)
        return 2

    if options["--estimate"]:
        quote = estimate(targets, limit=limit, engine=options["--engine"], delay=delay)
        print(json.dumps(quote.as_dict(), indent=2) if options["--json"] else quote.line())
        return 0

    if not options["--into"]:
        sys.stderr.write(USAGE)
        return 2

    return report(ingest(targets, options["--into"], limit=limit,
                         transcribe_missing=options["--transcribe"],
                         engine=options["--engine"], delay=delay),
                  "ingest_podcast.py", "no episode could be read",
                  as_json=options["--json"])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
