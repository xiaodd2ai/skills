---
name: check-x-visibility
description: Diagnose suspected X/Twitter visibility restrictions (shadowban、影子封禁、账号被限流、搜索封禁、帖子搜不到、回复折叠、推荐曝光暴跌) using observer checks, account reports and post analytics. Use when asked to check a specific handle or interpret evidence about its reach.
---

# Check X account visibility

Start with the handle or status URL already supplied. Perform the available read-only checks before requesting more evidence. Record the date, timezone, viewer state, URL and observed result. Keep account-specific material out of the skill repository.

## Establish the viewer first

Every result depends on who is looking, so identify the browser session before testing: guest, signed in as the owner, signed in as a follower, or signed in as an unrelated account. Open the X home page and read which account, if any, is logged in. Check whether that account follows the target.

A guest session reaches only part of the interface. On 2026-11-26 a guest could open a public profile's Posts tab and a post's direct link. Search and the profile's Replies tab redirected to login, and a post page showed a partial thread behind "See all the replies". X changes these gates, so confirm them in the current session and record what was blocked.

Run every check the current viewer supports. An independent signed-in non-follower is the strongest observer for search, suggestions and replies. When only a guest session exists, finish the guest checks, then ask once for that observer's screenshots of the remaining surfaces. The owner's own results have limited value as an independent observation.

## Check what another person can see

| Surface | Test | Interpretation |
| --- | --- | --- |
| Public profile and posts (guest or signed in) | Open the profile. Identify recent public originals by timestamp, skip the pinned item, and open their direct links. Record any platform notice verbatim. | A visible post establishes reachability for that viewer. Record protected accounts, deleted posts, regional notices and login prompts separately. |
| Latest search (signed in) | Search `from:HANDLE` in Latest. Compare against known recent, publicly reachable originals. Try a distinctive phrase from a missing post and a known indexed post from another public account as a control in the same session. | Multiple missing examples with a working control warrant an independent observer or later retest. Note indexing delay and search filters. A login redirect or broken control leaves this test inconclusive. |
| Account suggestions (signed in) | In global search, try the full handle, then remove its last character. Observe autocomplete before submitting. Compare with a control handle and record the viewer's relationship to the account. | One missing suggestion is a weak signal. Record full-handle People results separately from autocomplete. |
| Replies (signed in for the full thread) | Use an existing reply **by the target to someone else**. Check its permalink and parent thread from the same viewer. Record whether it appears by default, after expanding replies, under a spam notice, in author-hidden replies, or only by direct link. | Ranking, author moderation and partial guest threads can produce different outcomes. If the page asks for login to see all replies, the missing reply is unverified. Look for a repeated pattern across unrelated parent threads. |

Use existing posts throughout.

## Interpret platform evidence

Read the owner's X notices or supplied **Under the Hood** report. Record its actual start and end dates, the account or post affected, the displayed label, days observed, and the effect X describes. A historical entry confirms the reported period. Establish current status separately.

The report runs behind the calendar. It covers one calendar month and switches to the previous month about 10 days after that month ends, so a restriction that began in the current month cannot appear yet. An empty report, a report that has not reached the period in question, ineligibility, and lack of access are four different results. Quote an appeal route only when the relevant notice or label provides one.

When a report names a label, or the question is which rule produces an effect or how long it lasts, read [references/source-mappings.md](references/source-mappings.md). It holds the eligibility thresholds, label effects and configured lifetimes checked against a pinned revision of the published algorithm source.

## Compare distribution

Use owner analytics when available. Compare the last 28 **complete** days with the preceding 28 in the same timezone. State both date ranges and identify whether the export measures impressions accrued during the period or lifetime impressions for posts published in it. Group originals, replies and quotes separately. For lifetime metrics, compare at similar post ages where possible and disclose uneven observation time.

For comparable groups show post count, median impressions per post, and the absolute and percentage change (percentage undefined for a zero baseline). Check weekly medians and outliers before claiming a sustained decline. If the export is only daily totals, report that trend and ask for per-post rows before drawing a per-post conclusion. Record major shifts in posting volume, content mix or paid exposure.

Use explicit For You source data when available. Non-follower reach is a proxy that also includes other surfaces. Total likes alone cannot identify follower engagement. Stable engagement alongside falling impressions can motivate an investigation but cannot establish enforcement. Third-party app access and API quota belong to a separate account-access investigation.

## Deliver the finding

Lead with the strongest supported conclusion for the named account, then give one row per requested surface:

| Surface | Viewer | Checked at | Evidence | Result |
| --- | --- | --- | --- | --- |

Each result takes one of four labels. Use **platform-confirmed restriction** only for an explicit notice or a matching account report with a stated visibility effect, limited to its object, surface and period. Use **observed anomaly** for a reproducible discrepancy with working controls, **no anomaly observed in this sample** for successful checks, and **insufficient evidence** for blocked, ambiguous or untested checks. A trend can confirm declining exposure while the cause remains unknown.

If evidence is incomplete, name the single most useful missing item, such as the parent thread, a dated notice, or a per-post export. Account changes, appeals and public test posts require a separate request.

The check is complete when every requested surface has a row with an observed result or a named gap, and the conclusion states the viewer, the date and the scope it applies to.
