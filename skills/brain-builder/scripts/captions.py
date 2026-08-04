#!/usr/bin/env python3
"""Turn a publisher's caption or transcript file into prose.

Both transcript-carrying arms land here — YouTube captions and the
`<podcast:transcript>` a feed advertises — because both arrive as the same
problem in different wrappers: timing markup around text that repeats itself.

The repetition is the point. YouTube auto-captions roll: each cue restates the
tail of the one before it so the on-screen line can grow word by word. Pasted
together naively, a transcript comes out three to four times longer than the
words actually spoken (spec.md §6, measured in the prototype) — and a corpus
that lies about its own size feeds a wiki that lies about how much it saw.

`join_cues` fixes that by treating each cue as a continuation: whatever the cue
already shares with the tail of what has been kept is overlap, not new speech.
Trimming needs an overlap of two words or a cue already wholly present, so a
sentence that merely happens to start with the word the last one ended on
survives intact.

Stdlib only — everything here is string work.
"""
import json
import re
from html.parser import HTMLParser

#: Below this, a "transcript" is a stub: a throttled fetch, a captions track
#: that exists but holds nothing, or a placeholder. The prototype's threshold.
MIN_TRANSCRIPT_CHARS = 200

_MIME_FORMATS = {
    "text/vtt": "vtt", "application/vtt": "vtt",
    "application/x-subrip": "srt", "text/srt": "srt", "application/srt": "srt",
    "application/json": "json", "application/x-json": "json",
    "text/html": "html", "application/xhtml+xml": "html",
    "text/plain": "text",
}

_TIMESTAMP = re.compile(r"-->")
_CUE_INDEX = re.compile(r"^\d+$")
_CUE_HEADER = re.compile(r"^(WEBVTT|Kind:|Language:|NOTE|STYLE|REGION)")
_TAG = re.compile(r"<[^>]+>")
_SOUND_EFFECT = re.compile(r"\[[^\]]*\]")
_WORD = re.compile(r"[^\w']+")
_WHITESPACE = re.compile(r"\s+")

#: Comparing more tail than this buys nothing and costs time on long transcripts.
_MAX_OVERLAP = 40


def clean(text, fmt="text"):
    """The prose inside a transcript of `fmt`, rolling repetition collapsed."""
    if fmt == "json":
        return _from_json(text)
    if fmt == "html":
        return _collapse(_from_html(text))
    if fmt in ("vtt", "srt"):
        return join_cues(parse_cues(text))
    return _collapse(text)


def known_format(mime_type, url=""):
    """The format a transcript declares, or `None` when nothing recognises it.

    Feeds declare `application/octet-stream` often enough that the extension has
    to be the fallback. `None` is the useful answer for a caller choosing
    *between* transcripts — a PDF transcript is not one this kit can read, and
    guessing "text" at it would fill a page with binary.
    """
    declared = (mime_type or "").split(";")[0].strip().lower()
    if declared in _MIME_FORMATS:
        return _MIME_FORMATS[declared]
    extension = url.split("?")[0].split("#")[0].rsplit(".", 1)[-1].lower()
    if extension in ("vtt", "srt", "json", "html", "htm"):
        return "html" if extension == "htm" else extension
    return None


def format_for(mime_type, url=""):
    """What a `<podcast:transcript>` actually is; plain text when nothing says."""
    return known_format(mime_type, url) or "text"


def parse_cues(text):
    """Every cue's words, with timing, numbering and markup taken off."""
    cues = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or _TIMESTAMP.search(stripped) or _CUE_INDEX.match(stripped):
            continue
        if _CUE_HEADER.match(stripped):
            continue
        stripped = _SOUND_EFFECT.sub(" ", _TAG.sub("", stripped)).strip()
        if stripped:
            cues.append(_collapse(stripped))
    return cues


def join_cues(cues):
    """Concatenate cues, dropping what each one restates of the one before it.

    Overlap is measured on normalised words — case and punctuation off — so that
    a cue re-typed with a comma still reads as the repetition it is.
    """
    kept, normalised = [], []
    for cue in cues:
        words = cue.split()
        if not words:
            continue
        shape = [_normalise(word) for word in words]
        overlap = _overlap(normalised, shape)
        if overlap == len(words):
            continue                        # the whole cue is already in the text
        if overlap < 2:
            overlap = 0                     # one shared word is a coincidence
        kept.extend(words[overlap:])
        normalised.extend(shape[overlap:])
    return " ".join(kept)


def is_empty(text, min_chars=MIN_TRANSCRIPT_CHARS):
    """Whether a fetched transcript is a stub rather than a transcript.

    Deliberately blunt and deliberately loud: a throttled YouTube fetch returns
    a caption file with almost nothing in it, and the one outcome the spec rules
    out is treating that as a source that simply had little to say. A genuinely
    tiny source trips this too, and being told so is the right answer.
    """
    return len(_collapse(text or "")) < min_chars


def _overlap(tail, head):
    """The longest run that ends `tail` and starts `head`."""
    limit = min(len(tail), len(head), _MAX_OVERLAP)
    for size in range(limit, 0, -1):
        if tail[-size:] == head[:size]:
            return size
    return 0


def _normalise(word):
    return _WORD.sub("", word.lower())


def _collapse(text):
    return _WHITESPACE.sub(" ", text or "").strip()


def _from_json(text):
    """A Podcast Index JSON transcript: `{"segments": [{"body": …}]}`."""
    try:
        payload = json.loads(text)
    except ValueError:
        return _collapse(text)
    segments = payload.get("segments") if isinstance(payload, dict) else payload
    if not isinstance(segments, list):
        return _collapse(text)
    bodies = [str(segment.get("body") or segment.get("text") or "")
              if isinstance(segment, dict) else str(segment)
              for segment in segments]
    return join_cues([_collapse(body) for body in bodies if body.strip()])


class _TextOnly(HTMLParser):
    """The readable text of an HTML transcript page."""

    SKIP = ("script", "style", "head")

    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.chunks = []
        self.skipping = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skipping += 1

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skipping:
            self.skipping -= 1

    def handle_data(self, data):
        if not self.skipping and data.strip():
            self.chunks.append(data.strip())


def _from_html(text):
    parser = _TextOnly()
    parser.feed(text or "")
    parser.close()
    return " ".join(parser.chunks)
