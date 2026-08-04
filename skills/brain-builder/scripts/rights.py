#!/usr/bin/env python3
"""The rights stance, enforced (docs/rights.md is the prose; this is the code).

Three rules the kit holds mechanically, because a rule that lives only in a doc
is a rule a build can talk itself past:

  refuse DRM             Kindle, Audible, encrypted EPUB/PDF, the Spotify
                         player. Circumventing DRM is a separate offence with no
                         personal-use safe harbour, so the kit does not try and
                         does not offer a way around it.
  quarantine paywalls    A paywalled page yields a teaser that reads like an
                         article and is not one. Silently distilled, it becomes
                         a confident wiki page built on 200 words of marketing.
                         It is parked, named in the log, and never ingested.
  attribute every chunk  Nothing reaches `raw/` without a source and a format.
                         `raw_store` calls this on the way in, so an arm cannot
                         write an anonymous page by forgetting to pass one.

And one rule about tone, which shows up here as an absence: these messages state
what happened and what would work instead. None of them asks the member to
confirm they have read anything, and none of them fires unprompted mid-build.

Stdlib only.
"""
import os
import re
import zipfile

#: File formats that exist to be DRM-wrapped. Refused on sight, unopened.
DRM_EXTENSIONS = {
    ".azw": "Kindle", ".azw3": "Kindle", ".azw4": "Kindle", ".kfx": "Kindle",
    ".aax": "Audible", ".aa": "Audible",
    ".acsm": "Adobe DRM", ".ibooks": "Apple Books DRM",
}

#: Hosts whose whole model is a DRM'd player. Never fetched; an alternative is
#: named instead, because for podcasts there almost always is one.
DRM_HOSTS = {
    "open.spotify.com": "Spotify's player is DRM-protected and the kit does not "
                        "touch it — point me at the show's RSS feed or its Apple "
                        "Podcasts link instead. A Spotify-exclusive show has no "
                        "feed, and that is a dead end rather than a workaround.",
    "play.spotify.com": "Spotify's player is DRM-protected and the kit does not "
                        "touch it — the show's RSS feed or Apple Podcasts link works.",
    "www.audible.com": "Audible files are DRM-protected and the kit does not touch "
                       "them. A podcast RSS feed or a purchased DRM-free file works.",
    "www.kindle.com": "Kindle files are DRM-protected and the kit does not touch "
                      "them. A DRM-free EPUB or PDF of the same book works.",
}

#: Wall language explicit enough to condemn an extraction whatever its length.
PAYWALL_MARKERS = (
    "subscribe to continue", "subscribe to read", "subscribe now to keep reading",
    "already a subscriber", "this article is for subscribers", "subscribers only",
    "to continue reading", "continue reading this article", "sign in to read",
    "log in to read", "register to continue", "create a free account to continue",
    "you have reached your article limit", "unlock this article",
    "become a member to read", "start your free trial to read",
    "this content is available to subscribers",
)

#: Softer signals, which only condemn an extraction that is also suspiciously short.
PAYWALL_HINTS = ("subscribe", "subscription", "sign in", "log in", "paywall",
                 "members only", "premium", "free trial")

#: Below this, a web extraction is teaser-shaped. Trafilatura returns full
#: articles well above it; walls return a fraction of one.
MIN_ARTICLE_WORDS = 180

#: Nothing lands in `raw/` without these.
REQUIRED_PROVENANCE = ("source", "source_format")

_HOST = re.compile(r"^[a-z]+://([^/]+)", re.IGNORECASE)


class RightsError(Exception):
    """Material the stance will not let through, with the reason to log."""


def refusal_for_file(path):
    """Why this file is refused, or `None` if the kit may open it."""
    extension = os.path.splitext(path)[1].lower()
    if extension in DRM_EXTENSIONS:
        return ("{} DRM — the kit does not open DRM-protected files. A DRM-free "
                "EPUB or PDF of the same title works.".format(DRM_EXTENSIONS[extension]))
    if extension == ".epub" and _epub_is_encrypted(path):
        return ("this EPUB is DRM-encrypted — the kit does not open it. A DRM-free "
                "copy of the same book works.")
    if extension == ".pdf" and _pdf_is_encrypted(path):
        return ("this PDF is DRM-encrypted or password-protected — the kit does not "
                "open it. An unprotected copy works.")
    return None


def refusal_for_url(url):
    """Why this URL is refused, or `None` if the kit may fetch it."""
    match = _HOST.match(url or "")
    host = (match.group(1) if match else "").lower().split(":")[0]
    return DRM_HOSTS.get(host)


def paywall_reason(text, url=""):
    """Why an extraction looks like a wall rather than an article, or `None`.

    An empty extraction is not a paywall — it is an empty extraction, and the
    arm has an outcome for that already.
    """
    body = (text or "").strip()
    if not body:
        return None
    lowered = re.sub(r"\s+", " ", body.lower())
    for marker in PAYWALL_MARKERS:
        if marker in lowered:
            return ("paywalled — the extraction carries a subscription wall "
                    "(“{}”), so it is quarantined rather than ingested".format(marker))
    words = len(body.split())
    if words < MIN_ARTICLE_WORDS:
        for hint in PAYWALL_HINTS:
            if hint in lowered:
                return ("paywalled — {} words with subscription language "
                        "(“{}”) reads as a teaser, not the article, so it is "
                        "quarantined rather than ingested".format(words, hint))
    return None


def attribution_gap(provenance):
    """Which attribution a page is missing, or `None` when it carries enough."""
    missing = [key for key in REQUIRED_PROVENANCE
               if not str(provenance.get(key) or "").strip()]
    if not missing:
        return None
    return ("no {} — every chunk in a brain says where it came from"
            .format(" or ".join(missing)))


def require_attribution(provenance):
    """Raise unless the page about to be written says where it came from."""
    gap = attribution_gap(provenance)
    if gap:
        raise RightsError(gap)


def _epub_is_encrypted(path):
    """Adobe and friends declare their encryption in the container itself."""
    try:
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
    except (zipfile.BadZipFile, OSError):
        return False                        # unreadable is the arm's problem, not this one
    return bool(names & {"META-INF/encryption.xml", "META-INF/rights.xml"})


def _pdf_is_encrypted(path):
    """An encrypted PDF names an `/Encrypt` dictionary in its trailer."""
    try:
        with open(path, "rb") as handle:
            head = handle.read(4096)
            handle.seek(0, os.SEEK_END)
            handle.seek(max(0, handle.tell() - 4096))
            tail = handle.read(4096)
    except OSError:
        return False
    return b"/Encrypt" in head or b"/Encrypt" in tail
