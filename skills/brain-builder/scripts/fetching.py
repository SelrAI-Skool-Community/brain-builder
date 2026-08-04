#!/usr/bin/env python3
"""Every network read the kit makes, at one visible and conservative rate.

The rights stance promises "visible, conservative rate limits on anything that
fetches from the network" (docs/rights.md), and a promise spread across three
arms is a promise one of them will quietly break. So the arms do not call
`urllib` — they hold a `Fetcher`, which sleeps between requests, identifies
itself, and hands back bytes plus the content type the server declared.

It is also the seam the tests hold. Every arm takes its fetcher as an argument,
so the whole pipeline runs against fixture bytes with no network at all.

Stdlib only.
"""
import os
import time
import urllib.error
import urllib.request

#: Says what it is. The kit fetches at personal scale and does not pretend to
#: be a browser.
USER_AGENT = "brain-builder/1.0 (personal knowledge brain; local, non-commercial)"

#: Seconds between requests. Conservative on purpose — a build is not in a hurry.
DEFAULT_DELAY = 1.5

DEFAULT_TIMEOUT = 30


class FetchError(Exception):
    """A URL that could not be read. One dead link never stops a corpus."""


class Response(object):
    """What came back: the bytes, what the server called them, where it ended up."""

    def __init__(self, body, content_type="", url=""):
        self.body = body
        self.content_type = content_type
        self.url = url

    @property
    def text(self):
        return self.body.decode("utf-8", "replace")


class Fetcher(object):
    """A rate-limited reader. Callable, so an arm can be handed a stub instead."""

    def __init__(self, delay=DEFAULT_DELAY, timeout=DEFAULT_TIMEOUT,
                 opener=None, sleeper=time.sleep):
        self.delay = delay
        self.timeout = timeout
        self.opener = opener or urllib.request.urlopen
        self.sleeper = sleeper
        self.requests = 0

    def __call__(self, url):
        """Read `url`, having waited out the rate limit since the last read."""
        if self.requests and self.delay:
            self.sleeper(self.delay)
        self.requests += 1
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with self.opener(request, timeout=self.timeout) as response:
                return Response(response.read(),
                                response.headers.get("Content-Type", ""),
                                getattr(response, "url", url))
        except (urllib.error.URLError, OSError, ValueError) as failure:
            raise FetchError("could not fetch {}: {}".format(url, failure))

    def download(self, url, directory, filename="media"):
        """Read `url` into a file under `directory` and return the path.

        Audio enclosures are too big to hold in memory next to everything else a
        build is doing, and the transcription engine wants a file anyway.
        """
        response = self(url)
        path = os.path.join(directory, filename)
        with open(path, "wb") as handle:
            handle.write(response.body)
        return path
