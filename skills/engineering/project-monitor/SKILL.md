---
name: project-monitor
description: Use when the user asks to monitor a particular project's open-source upstreams or comparable products, run its update digest, or set up recurring project update notifications (监控这个项目、技术栈更新、同类产品新功能).
---

# Project monitor

Answer two questions for the maintainer: what changed in software this project uses, and what can users now do in comparable products? Honor requests for either track alone.

## Select the project and operation

- Use the named repository or service, otherwise the current Git project. In a workspace of independent repositories, ask which project if the request leaves it ambiguous. Use the requested revision, the repository's documented integration branch, or its remote default branch. Read files at that revision without switching the user's checkout. Record the commit and local timezone.
- “Run once” or “what changed today?” means collect and report now. “Set up daily monitoring” means build the inventory and configure a recurring check. A request for both gets both. “List what we monitor” needs only the inventory.
- Reuse the project's existing inventory, history, and scheduler entry when available, including monitors created before this skill. For a new monitor, keep its files outside the checkout in a user-local state directory keyed by repository identity **and** service path. Record the location in the recurring task so a fresh chat can resume. Keep internal repository URLs, paths, manifests and credentials out of external search queries.

## Build and refresh the inventory

1. Read the project's own instructions and product overview. Identify its users and their recurring workflows. Inspect the actual manifests and lockfiles for all relevant modules and ecosystems. Record package name, resolved version (or declared range if unresolved), component role, and evidence path. Keep build/test tools and optional adapters identifiable.
2. Look beyond packages. Inspect fork remotes and sync markers, vendored licenses and provenance, ports documented in source, shipped skills, container build stages and globally installed tools, deployment profiles, plugins, and remote service adapters. Record the imported commit or image tag where available. A sample configuration or optional adapter establishes support; production use needs separate evidence.
3. Resolve each public upstream through its publisher, package metadata, or attribution. Keep registry feeds for packages with unavailable repositories. Group requests by repository, retaining **all package identities** so a monorepo's unrelated releases stay out of the digest. Refresh the inventory when the project revision changes.
4. Use the user's named comparables, or select a small set that serves the same audience and workflow. Record why each belongs and its official release log, blog, or repository. An upstream can also be a product comparator; report the same event once.

## Run a check

- Fix one cutoff at the start. For “today” use midnight in the user's timezone; for a first recurring run without a specified window, look back 72 hours and label earlier dates separately. For ongoing checks use each source's last successful cutoff with a small overlap. Preserve older gaps outside today's report for later backfill.
- Check official releases and registry publications, including applicable advisories. Compare affected ranges with locked versions. For forks and ports also inspect relevant default-branch merges since the checkpoint and compare with the local sync marker and implementation. Distinguish merged, released, and already incorporated changes.
- Use the source's pagination contract (including cursor or next-link pagination), check timestamps and package names, and mark previews, drafts, and withdrawn releases accurately; omit drafts from release counts. When access fails, use a verified alternate source and keep the failed source pending. Use the user's preferred browser for product research. Read the dated original announcement and distinguish availability, staged rollout, preview, and customer case study.
- Report the check window and coverage. Lead with material changes. For a dependency, give the locked and released versions, affected local behavior and a concrete compatibility check. For a product, describe what its user can now do and the comparable workflow here. Link each item to the official evidence. Group routine patches and prereleases. A manual run returns a result even on a quiet day.
- Persist successful cutoffs, source failures, inventory revision and reported event identities per project. Deduplicate release ID/package/version/channel, merged SHA, advisory ID, or canonical article and feature. Keep release promotions and substantive availability changes visible. Advance a source only after its window was fully read and the results saved. Use atomic writes and serialize overlapping manual and scheduled updates to the same state.

## Configure recurring checks

Use the host's supported automation tool when recurring monitoring is requested. Find an existing monitor by project identity, then create or update just that project's entry. Retain the requested schedule, timezone and destination; if none exist, default to daily at 09:00 local time in the requesting chat and state that choice. Put the project location, branch policy, state location, sources, timezone and a **run-once** invocation of this skill in the recurring prompt. Check the returned schedule and enabled status. If persistent scheduling is unavailable, deliver the usable manual invocation and explain what still needs scheduling. A quiet scheduled run should surface only material changes or a failure that needs attention.
