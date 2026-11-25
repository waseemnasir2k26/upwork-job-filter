# upwork-job-filter

A small, inspectable filter for agency owners and freelancers who want to say no to weak Upwork jobs quickly, score the few that remain, and prepare one honest proposal draft that a human reads and sends.

## Who it is for

Small agency owners and freelancers with clearly defined service lanes who want a repeatable review process instead of reading every post.

## What it does

- `filter.py`: applies the kill rules to a saved job list and shows the rule that failed for each rejected job.
- `score.py`: scores survivors out of 100 (hire rate 25, budget 25, fit 25, competition 15, freshness 10). Pass mark 65.
- `mask.py`: makes a table with no client names, titles, links or ids, safe for screen recordings.
- `proposal-prompt.md`: a prompt for a 120 to 180 word proposal draft with honesty rules.
- `sample-jobs.json`: SYNTHETIC jobs for trying it out.

## What it will not do

- Scrape Upwork pages or automate a browser to collect jobs.
- Submit, message or save anything on Upwork. It never sends a proposal.
- Guarantee jobs, clients, income or wins.
- Invent client proof, portfolio examples or numbers.
- Bypass Upwork policies or account controls.

## The kill rules

Reject if any is true (only on a stated value; a missing value is flagged for manual review, never guessed):

- Client country not in US, Canada, Australia, UK, Germany, Singapore.
- Payment not verified.
- Client hire rate under 40%.
- Client total spend under $500.
- Posted more than 96 hours ago.
- More than 20 proposals (Upwork gives a band; the upper end is used).
- Fixed budget under $200, or hourly ceiling under $25.

No budget stated is not a reason to reject.

## The scoring model

Hire rate 25, budget 25, fit with your real services 25, competition 15, freshness 10. Pass at 65. If hire rate is not in your data, a spend-based proxy gives at most 12 of 25 and says so. A score ranks jobs; it is not a chance of winning.

## Use it in five steps

1. Connect Claude Code to the official Upwork connector you have access to.
2. Fetch jobs in your own service lanes (read-only searches) and save the JSON.
3. `python filter.py jobs.json --now 2026-11-19T15:33:00Z` to apply the kill rules.
4. `python score.py jobs.json` to score; `python mask.py jobs.json --out out` for a shareable table.
5. Fill the three blocks in `proposal-prompt.md`, draft in Claude Code, review it yourself, and press send yourself.

## Privacy

Raw pulls contain client names and spend. Keep them in a private folder, never commit them, never show them on screen. Use `mask.py` output instead.

## Limitations

- The search result carries only an opening snippet; re-open the job before you spend Connects.
- A proposals band like "20 to 50" is treated as 50 (pessimistic). Change `proposals_upper` in `filter.py` if you disagree.
- Your market will differ: edit the constants at the top of `filter.py` and `score.py`, and write down why.

## Adapt it

Change thresholds in `filter.py`, lane keywords and weights in `score.py`. Run `python -m unittest discover -s tests` after every change.

## Built by SkynetLabs

This filter is the one we run on our own Upwork pipeline at [SkynetLabs](https://skynetjoe.com/?utm_source=github&utm_medium=readme&utm_campaign=upwork-job-filter), an AI automation agency (n8n workflows, AI voice agents, WhatsApp bots, AEO and SEO). Built by [Waseem Nasir](https://www.waseemnasir.com/?utm_source=github&utm_medium=readme&utm_campaign=upwork-job-filter).

Related free tools: [upwork-mcp-toolkit](https://github.com/waseemnasir2k26/upwork-mcp-toolkit) and [upwork-job-radar](https://github.com/waseemnasir2k26/upwork-job-radar).

MIT licence.
