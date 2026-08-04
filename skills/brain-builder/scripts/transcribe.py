#!/usr/bin/env python3
"""The transcription fallback, and the one cost line the member ever sees.

    python3 transcribe.py --estimate <duration> [<duration> …] [--engine <engine>]
    python3 transcribe.py <audio-file> [--engine <engine>] [--json]
    python3 transcribe.py --engines

Two subsystems feed one fallback (spec.md §6): yt-dlp for anything video-shaped
and the RSS resolver for podcasts. Both come here when the publisher shipped no
transcript, and both come here for the same reason — a source with no words in
it is not a source, and the alternative to transcribing it is failing loudly.

**Cost surfaces once, at Gate 2.** `estimate()` renders the line the member
approves before a single second is billed, and nothing after that gate mentions
money again. Arms only transcribe when the build was told it may.

**Engines.** ElevenLabs Scribe v2 at $0.22/hr is the default and the only one
whose output is quotable: 2.2 % WER, diarization built in, ten-hour files in one
call. Groq's turbo Whisper is an eighth of the price and is documented, not
default — Whisper-family engines invent fluent sentences during silences on
long-form audio, which is survivable for rough indexing and poison for a
verbatim persona corpus. Anything transcribed by it is marked, so a page built
on it can never quietly become a quotation.

The API key rides in an environment variable (`ELEVENLABS_API_KEY`), is never
written to disk, and never reaches a `raw/` page. A missing key is a loud
failure naming the variable, not a silent skip.

Stdlib only, and the network call sits behind a `poster` seam so the arms can be
tested end to end with no key and no connection.
"""
import json
import mimetypes
import os
import re
import sys
import urllib.request
import uuid

import cli


class Engine(object):
    """One transcription engine: what it costs, what it is called, what to trust."""

    def __init__(self, name, label, price_per_hour, url, model_id, key_env,
                 auth_header, caution=""):
        self.name = name
        self.label = label
        self.price_per_hour = price_per_hour
        self.url = url
        self.model_id = model_id
        self.key_env = key_env
        self.auth_header = auth_header
        self.caution = caution

    def headers(self, key):
        return {self.auth_header[0]: self.auth_header[1].format(key=key)}


#: The engines on offer. Whisper-family models are absent on purpose.
ENGINES = {
    "scribe-v2": Engine(
        name="scribe-v2", label="ElevenLabs Scribe v2", price_per_hour=0.22,
        url="https://api.elevenlabs.io/v1/speech-to-text", model_id="scribe_v2",
        key_env="ELEVENLABS_API_KEY", auth_header=("xi-api-key", "{key}")),
    "groq": Engine(
        name="groq", label="Groq whisper-large-v3-turbo", price_per_hour=0.04,
        url="https://api.groq.com/openai/v1/audio/transcriptions",
        model_id="whisper-large-v3-turbo", key_env="GROQ_API_KEY",
        auth_header=("Authorization", "Bearer {key}"),
        caution="rough indexing only, never quote it"),
}

DEFAULT_ENGINE = "scribe-v2"

_CLOCK = re.compile(r"^\d{1,3}(:[0-5]?\d){1,2}$")


class TranscriptionError(Exception):
    """The fallback could not produce words. Always loud, never a silent skip."""


class Estimate(object):
    """What transcribing this build would cost, in the shape Gate 2 states it."""

    def __init__(self, engine, seconds, items):
        self.engine = engine
        self.seconds = seconds
        self.items = items

    @property
    def hours(self):
        return round(self.seconds / 3600.0, 2)

    @property
    def cost(self):
        return round(self.seconds / 3600.0 * self.engine.price_per_hour, 2)

    def line(self):
        """The Gate 2 sentence. Said even when it is free, because that is the
        line that stops a surprise on the arms that do transcribe."""
        if not self.seconds:
            return "Transcription — none, $0."
        caution = " ({})".format(self.engine.caution) if self.engine.caution else ""
        return ("Transcription — {items} source{plural}, {hours:g} hours via {label}"
                "{caution}, about ${cost:.2f} one-off at ${rate:.2f}/hr.").format(
                    items=self.items, plural="" if self.items == 1 else "s",
                    hours=self.hours, label=self.engine.label, caution=caution,
                    cost=self.cost, rate=self.engine.price_per_hour)

    def as_dict(self):
        return {"engine": self.engine.name, "items": self.items,
                "hours": self.hours, "cost": self.cost, "line": self.line()}


def engine_for(name):
    """The engine called `name`, or a refusal naming the ones that exist."""
    try:
        return ENGINES[name or DEFAULT_ENGINE]
    except KeyError:
        raise ValueError("unknown transcription engine {!r} — choose from {}".format(
            name, ", ".join(sorted(ENGINES))))


def estimate(durations, engine=DEFAULT_ENGINE):
    """What transcribing these durations would cost, for the plan gate."""
    seconds = [parse_duration(duration) for duration in durations]
    return Estimate(engine_for(engine), sum(seconds), len(seconds))


def parse_duration(value):
    """Seconds, from either a number of seconds or an `hh:mm:ss` clock.

    Feeds state `<itunes:duration>` both ways, and a feed that states something
    else entirely is worth zero to the estimate rather than worth an exception —
    one junk duration must not stop a build.
    """
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return max(0, int(value))
    text = str(value).strip()
    if _CLOCK.match(text):
        seconds = 0
        for part in text.split(":"):
            seconds = seconds * 60 + int(part)
        return seconds
    try:
        return max(0, int(float(text)))
    except ValueError:
        return 0


def transcribe(path, engine=DEFAULT_ENGINE, api_key=None, environ=None, poster=None):
    """The words in an audio file, or a loud failure explaining what is missing."""
    engine = engine_for(engine)
    environ = os.environ if environ is None else environ
    key = api_key or environ.get(engine.key_env) or ""
    if not key.strip():
        raise TranscriptionError(
            "no {} in the environment — {} needs a key to transcribe. Set it and "
            "re-run this arm; nothing else in the build depends on it.".format(
                engine.key_env, engine.label))

    poster = poster or post_audio
    try:
        payload = poster(engine.url, engine.headers(key), path, engine.model_id)
    except TranscriptionError:
        raise
    except Exception as failure:
        raise TranscriptionError("{} failed on {}: {}".format(
            engine.label, os.path.basename(path), failure))

    text = str((payload or {}).get("text") or "").strip()
    if not text:
        raise TranscriptionError("{} returned no words for {}".format(
            engine.label, os.path.basename(path)))
    return text


def post_audio(url, headers, path, model_id, timeout=1800):
    """Upload one audio file as multipart/form-data and read back the JSON.

    Written on `urllib` rather than a client library because the kit ships with
    zero install steps for anything but the ingestion readers themselves.
    """
    boundary = uuid.uuid4().hex
    with open(path, "rb") as handle:
        audio = handle.read()
    content_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
    body = b"".join([
        _part(boundary, 'name="model_id"', model_id.encode("utf-8")),
        _part(boundary, 'name="model"', model_id.encode("utf-8")),
        _part(boundary, 'name="file"; filename="{}"'.format(os.path.basename(path)),
              audio, content_type),
        "--{}--\r\n".format(boundary).encode("utf-8"),
    ])
    request = urllib.request.Request(url, data=body, headers=dict(
        headers, **{"Content-Type": "multipart/form-data; boundary=" + boundary}))
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8", "replace"))


def _part(boundary, disposition, payload, content_type=None):
    head = "--{}\r\nContent-Disposition: form-data; {}\r\n".format(boundary, disposition)
    if content_type:
        head += "Content-Type: {}\r\n".format(content_type)
    return head.encode("utf-8") + b"\r\n" + payload + b"\r\n"


# --- cli -------------------------------------------------------------------

USAGE = ("usage: transcribe.py --estimate <duration> [<duration> ...] [--engine <engine>]\n"
         "       transcribe.py <audio-file> [--engine <engine>] [--json]\n"
         "       transcribe.py --engines\n")


def main(argv):
    try:
        positional, options = cli.scan(
            argv, options={"--engine": DEFAULT_ENGINE, "--estimate": False,
                           "--engines": False, "--json": False},
            flags=("--estimate", "--engines", "--json"))
    except cli.UsageError as failure:
        sys.stderr.write("transcribe.py: {}\n{}".format(failure, USAGE))
        return 2

    try:
        engine = engine_for(options["--engine"])
    except ValueError as failure:
        sys.stderr.write("transcribe.py: {}\n{}".format(failure, USAGE))
        return 2

    if options["--engines"]:
        for name in sorted(ENGINES):
            offer = ENGINES[name]
            print("{}\t${:.2f}/hr\t{}{}".format(
                name, offer.price_per_hour, offer.label,
                " — " + offer.caution if offer.caution else ""))
        return 0

    if options["--estimate"]:
        quote = estimate(positional, engine=engine.name)
        print(json.dumps(quote.as_dict(), indent=2) if options["--json"] else quote.line())
        return 0

    if len(positional) != 1:
        sys.stderr.write(USAGE)
        return 2

    try:
        text = transcribe(positional[0], engine=engine.name)
    except TranscriptionError as failure:
        sys.stderr.write("transcribe.py: {}\n".format(failure))
        return 1
    print(json.dumps({"engine": engine.name, "text": text}, indent=2)
          if options["--json"] else text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
