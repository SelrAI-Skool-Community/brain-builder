---
kind: business
summary: A wiki organised by entity and process — offers, clients, pricing, how-we-do-X — answered as an advisor from outside the business, with a date attached to anything that moves.
stance: advisor
overlays: [standing]
wiki_organised_by: entity and process
---

# Business — blueprint

A brain that holds **one organisation's own facts**: what it sells, at what
price, to whom, and how it actually does the work. The stance is advisor —
Claude speaks as itself, from **outside the business**, about a business it knows
well: "you offer X", "the business charges Y", never "we".

That distance is deliberate. A brain that says "we" starts making commitments on
the organisation's behalf, and the whole value of this kind is that its numbers
are checkable rather than spoken for.

This file is a **skeleton, not an example**. Nothing here gets copied into a
brain verbatim — read it, then build the shape it describes out of the material
actually ingested. If a section below does not fit the corpus, the corpus wins.

## When to suggest this shape

Suggest business when the corpus is an organisation's **own** material — proposals,
price sheets, SOPs, client folders, contracts, onboarding docs, internal wikis —
and the member wants to ask it what things cost, who a client is, or how the
recurring work runs. Signals: "what do we charge for", "our process for", "which
clients are on", a drive folder that is the business's operating paperwork.

Suggest subject when the material is knowledge about a field rather than one
organisation's own facts, and persona when the member wants a named individual's
voice. One blueprint per brain; multi-kind behaviour is stacking at attach time.

## Wiki taxonomy — organised by entity and process

Not by concept. Pages are the **things the business has** and the **things the
business does**:

- **Offers** — one page per offer or product: what it is, what it includes, what
  it costs, who it is for, where the edges are.
- **Clients** — one page per client or account: engagement, scope, status,
  history. See the confidentiality rules below before this section is written.
- **Pricing** — the rates, tiers, discount rules and the conditions attached to
  them. Usually the fastest-moving page in the brain.
- **How-we-do-X** — one page per recurring process, written as the process runs:
  the steps, who does them, what they depend on, what usually goes wrong.
- **The business itself** — positioning, team, tools, anything asked about by
  name.

Shape rules that differ from a concept wiki:

- **Name pages the way the business names things.** Its own vocabulary for its
  own offers, not a tidied-up synonym. The router matches questions against these
  names, and members ask using the words on their own invoices.
- **One entity per page.** Two clients on one page is the shape that leaks one
  client's terms into an answer about the other.
- **Processes get their own pages, not a paragraph inside an offer.** The same
  process usually serves several offers.

## `standing/` — the optional overlay

`standing/` holds **standing facts and policies**: the things that are true
across every answer rather than about one entity. Terms of business, what the
organisation will and will not take on, approval thresholds, tone and claims
rules for outward-facing work, the legal entity's own details.

Its contract differs from `persona/` in one way that matters:

- **`standing/` is unfenced.** It is routed exactly like `wiki/` pages, linked
  from `index.md`, and loaded when relevant — not loaded whole on every question
  the way a persona overlay is.
- Standing policies **bind outward-facing work**, and they outrank subject-brain
  guidance when brains are stacked. A subject brain's best-practice advice does
  not override the organisation's own stated policy; the conflict gets surfaced.
- Use it only when a fact genuinely spans the whole business. A policy about one
  offer belongs on that offer's page.

## Freshness — the frontmatter that keeps this kind honest

A business corpus goes stale faster than anything else the kit builds, so pages
carry freshness fields and they are filled in, not decorated:

- `as_of:` — an ISO date (`YYYY-MM-DD`). When this page's facts were true. Take
  it from the source document's own date, never from the build date.
- `volatility: fast | slow | stable` — how fast this page rots. Prices, capacity,
  rates, current client status and anything in negotiation are `fast`. Positioning
  and process are usually `slow`. Registered details and history are `stable`.
- `canonical:` — where the **live** truth lives, in a phrase a member can act on:
  the system, sheet or document that would be checked to confirm the number
  today. This is what makes a stale answer recoverable rather than merely wrong.

Every `fast` page needs an `as_of`, because the router answers fast facts with
their date attached in the same breath — the number stays exact and the date is
the honesty. A `fast` page without a date makes that impossible, and lint warns
about it — a warning, not an error, so it is on the build to fix it rather than
on the exit code to force it.

## Source-authority ranking — the kind's first job, at build time

**A business corpus contradicts itself.** The same price appears in a 2023
proposal, a 2025 rate card and a Slack export; two SOPs describe the same process
differently; a signed contract disagrees with the deck that sold it. Adjudicating
which documents to distrust is the first real work of a business build, and it
happens **before pages are written**, not while answering.

Rank the corpus once, up front:

1. **Rank sources by authority**, and write the ranking into `log.md` so it is
   inspectable. The usual ordering: signed and executed documents, then the
   system of record, then current published material, then internal drafts and
   decks, then chat and email. Recency breaks ties **within** a tier, never
   across one — a recent draft does not beat a signed contract.
2. **Distil from the highest-authority source** available for each fact, and
   record it in the page's `sources:` as usual.
3. **Flag every contradiction explicitly.** Where sources genuinely disagree on
   something that matters, the page says so in a line — what each source says,
   which one this page follows, and why — rather than silently picking one. A
   contradiction that survives adjudication is a `## Known gaps` entry too.
4. **Never average, never split the difference.** Two prices are not one price;
   pick the authoritative one and flag the other.

## Confidentiality

This material is the organisation's own, and the brain is **local-only**: it is
not published, not distributed, and not pasted anywhere it did not come from.

The rules that survive into the router, because they govern answers rather than
the build:

- **One client's details never reach another client's documents**, and never
  reach outward-facing drafts, unless the member asks for exactly that. Rates,
  terms, names and volumes are the usual leak.
- **Client pages are for internal answers.** Drafting anything the client of
  record will read means their page only, plus offers and standing policy.
- Aggregates leak too. "Most clients pay around X" is a client's rate wearing a
  disguise when there are four clients.

## Page shape

OKF frontmatter, then the answer the page exists to give:

- `type:` — required; the entity or process category in the business's own words.
- `title:` — what the business calls this thing.
- `sources:` — the `raw/` files behind it, highest-authority first.
- `as_of:` / `volatility:` / `canonical:` — as above, on anything that moves.

Numbers stay exact and keep their conditions — what the price includes, what
tier it is, what it depends on. A price stripped of its conditions is the
failure mode that turns this brain into a quoting mistake.

## index.md

One-liners carrying **the actual numbers and the actual names** — the offers, the
prices, the clients — because that is what routing runs on. Link `standing/`
pages here alongside `wiki/` pages; the standing overlay is routed, so it belongs
on the map.

`## Known gaps` is required, and for this kind it also carries **what is known to
be stale**: pages whose `as_of` is old, facts the corpus never settled, and
contradictions that survived adjudication.

## Write-back is routine here

This is the staleness-prone kind, so write-back is the normal case rather than
the exception. A price confirmed in conversation, a process described out loud, a
client status corrected — all of it files back into the wiki during the
conversation, with an `as_of` of the day it was confirmed and marked
derived-from-conversation. The alternative is a brain that quietly ages into
being wrong.

## Calibration

Ask it one of the member's own questions with a **checkable** answer — a price, a
client's current status, the steps of a process they know. The answer either
carries the right number with its date attached, or it does not. Record the
question and its expected answer in `log.md` alongside the authority ranking:
this kind goes stale, so the calibration is worth re-running, and one that was
never written down cannot be.

Ask a stale-fact question too: something the member knows has changed recently.
A brain that answers it with the old number *and its date* is working as
designed. One that answers with the old number and no date is not.
