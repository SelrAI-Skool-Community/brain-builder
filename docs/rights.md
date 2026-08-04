# Content rights

The stance this kit is built to. Plain English, not legal advice.

## Rules the kit follows

- **Never ships content.** The kit never bundles, seeds, or distributes copyrighted material or pre-built brains. Every brain is built by you, on your machine, from sources you supply.
- **Brains stay local by default.** The privacy story is the legal story: personal use of lawfully acquired material on your own machine is the strong position.
- **No DRM removal, ever.** Circumventing DRM (Kindle, Audible, and the like) is a separate offence with no personal-use safe harbour. The kit will not touch DRM-protected files.
- **No paywall bypass.** Paywalled pages are quarantined, not worked around. A truncated extraction is parked in the brain's `quarantine/` folder, named in `log.md`, and never distilled into the wiki — `raw/` never sees it.
- **Everything is attributed.** Every chunk in a brain carries its source: URL, video id, or file path, plus the date it was ingested.
- **Visible, conservative rate limits** on anything that fetches from the network.
- **Never a lecture.** All of the above is enforced in the ingestion arms rather than asked about. The kit states a refusal once, in a line, when it happens; it never nags mid-run and never asks you to confirm you have read this page.

## YouTube

Pulling transcripts is against YouTube's Terms of Service (section 5.B). The kit does not claim otherwise. In practice it is tolerated at personal scale on public, unauthenticated endpoints. The kit's position: personal use, respectful rate limits, and no republication or redistribution of transcripts. The official Captions API (your own key) is the sanctioned path and the kit supports it.

## Books and documents

The load-bearing line from Bartz v. Anthropic: lawfully acquired sources plus transformative personal use leaned fair use; pirated libraries did not. The strong position, and the only one the kit supports: you parse books you bought, on your own machine, without sharing and without bulk verbatim regeneration.

## Podcasts and audio

Podcasts are published to be fetched: the kit resolves a show to the publisher's own RSS feed and reads it, preferring the `<podcast:transcript>` the publisher already ships. Where there is none, the audio enclosure is transcribed once, on your machine's behalf, and the transcript stays in your brain like any other chunk.

Spotify is the line. The kit resolves *to* RSS or it does not resolve at all: it never touches the DRM'd player, and a Spotify-exclusive show has no feed, which is a dead end the kit states rather than a lock it picks. Audible is the same answer for the same reason.

## Persona brains

A persona brain is built from a person's published public work for your own use. It stays on your machine like every other brain. Do not redistribute one.
