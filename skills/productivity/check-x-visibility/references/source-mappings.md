# Source mappings for label reports

These mappings come from the published X algorithm source, [xai-org/x-algorithm](https://github.com/xai-org/x-algorithm), at revision [`269340ce2eb8ca785bafa4f2c17a2e8b752bccd3`](https://github.com/xai-org/x-algorithm/tree/269340ce2eb8ca785bafa4f2c17a2e8b752bccd3). They were last checked on 2026-11-26.

Use a local checkout of that repository when one exists and record its Git revision. Otherwise read the pinned revision online. When the revision differs from the one above, reopen the relevant file before quoting anything below. The published rule files state that some production thresholds are replaced with mock values, so treat configured numbers as the shape of a rule and rely on the account's own report for what applied.

## Under the Hood report

File: `under-the-hood/strato/columns/underTheHoodReport.User.strato`

- Eligibility requires an account older than 365 days (`minimumAccountAge`) and at least 10 eligible posts in the prior month (`minimumEligiblePosts`).
- The report uses calendar-month buckets in UTC. `reportMonthBucket` selects the previous calendar month once 10 days have passed since its last day (`minDaysAfterMonthEnd`), and the month before that until then. It never selects the current month.
- The selected month is also capped by the latest month that has data, so the displayed period can be older than the calendar rule alone suggests.

Use the period and eligibility checks displayed for the account under review. An ineligible account and an eligible account with no labels are different findings.

## Account label: SpamHighRecall

- Effect: `under-the-hood/strato/lib/underTheHoodLabels.strato` describes it as "The account's posts are hidden from recommendations to non-followers."
- Writers: `abuse-enforcement-service/service-lib/rules/enforcement_user.yaml` has several rules that add this label. The rule for the input score label `llm_slop_user` writes it with a 7-day TTL (`ttl_msec: 604800000`). Other rules write the same label with a 7-day TTL, a 30-day TTL, or no TTL.

A report showing `SpamHighRecall` therefore cannot identify which classifier fired or which lifetime applies.

## Post label: RiskyHighVizReply

- Writer: in `abuse-enforcement-service/service-lib/rules/enforcement_post.yaml`, the rule for `llm_slop_post` writes `RiskyHighVizReply` on that post with a 30-day TTL (`ttl_msec: 2592000000`).
- Consumer: `visibility-filtering/rules/tweet_rules.rs` defines `RISKY_HIGH_VIZ_REPLY_OON_DROP_UNSPECIFIED`, which drops the post for non-followers. At this revision `visibility-filtering/rules/levels.rs` includes that rule only in the notification levels for mentions, replies and media tags.

For a claim about any specific surface, trace the label through `levels.rs` and the applicable rule at the revision in use.

## Limits of a source reading

A TTL measures the configured lifetime of one label write. Account-wide reach, whether the rule fired for this account, and a recovery date each need separate evidence from the account's notices, report or analytics.
