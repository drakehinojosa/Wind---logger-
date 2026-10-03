# Protocol v1.1 Prospective Logger — Specification for Audit

1. SCHEMA
log/entries.jsonl (one line per game, written once, at or after D and before kickoff; append-only, SHA-256 hash-chained):
event_id, lg, home, away, ref_id, K (canonical kickoff), D, anchor_snap, status, ticket {book, rank, total, under_price, over_price, quote_last_update, odds_snap}, venue_id, venue, forecast_run, forecast {gfs|hrrr: mph, grid_lat, grid_lon, url_first}, qualified, logged_at, prev_hash.
Status values: LOGGED; X not on reference schedule / out of scope; X1 not listed at K-36h; X4 kickoff changed >5 min by D; M2 no hierarchy book quoted at D; EXCL covered / Hawai'i / outside specified HRRR coverage; EXCL forecast (file missing or Last-Modified after D); ERROR (missed capture, unknown venue, finalized after kickoff).
log/grades.jsonl (hash-chained): event_id, lg, K, date_et, status (GRADED/VOID), line, price, final_total, result, units.
looks/<LG>_<N>.json: stats and decision at each milestone.

2. QUALIFICATION LOGIC (frozen/rules.json)
NFL: GFS and HRRR mean speed both >= 10.0 and < 20.0 mph. NCAAF: both >= 15.0 mph. FBS-involved reference games only. Venues from the frozen venue table (195 venues); unknown venue = logged ERROR, excluded. Ticket = first book in the frozen 2026 league hierarchy (from 2025 coverage, >=90%, alphabetical tie-break) with a matched Over/Under pair in the latest capture at or before D.
2026 hierarchies: NFL betmgm, draftkings, fanatics, fanduel, betonlineag, lowvig, mybookieag, williamhill_us, betus, bovada. NCAAF draftkings, fanduel, williamhill_us, betrivers, bovada, betonlineag, betus.

3. TIMESTAMP / LEAKAGE CONTROLS
Runs every 5 min. Anchor: latest events listing captured in [listed commence-36h-15min, commence-36h]; K = that listed commence. D capture: latest events and totals snapshot in [D-15min, D]; quotes with last_update after the capture are dropped. Forecast run = latest 00Z/12Z at or before D-6h; every file's AWS Last-Modified <= D. The entry is written once D passes; an entry finalized at or after kickoff is marked ERROR. Missed captures are logged as ERROR, never backfilled. Games already inside 36h when the logger starts are logged as ERROR (no backfill). The logger never reads scores.

4. MILESTONE / LOOK LOGIC
Per league, looks only when graded non-void qualified games reach 150 / 300 / 450 / 600, using exactly the first N by kickoff. No statistics are computed between looks. Looks stop after PROMOTION GATE PASSED or KILL.

5. PROMOTION
z = mean unit return / CR1 SE clustered by kickoff date (US Eastern), the frozen convention, verified to reproduce the accepted historical values (NFL 0.1803 / 0.0659; NCAAF 0.1870 / 0.1136). PROMOTION GATE PASSED if z >= 2.24 at a look: prospective testing stops for that league, files and code are frozen, and the full report returns for independent audit. It does NOT authorize betting. Historical 2021-2025 results are never mixed in.

6. KILL RULES
Look 150: KILL if z <= -1.28. Looks 300 and 450: KILL if mean return <= 0. Look 600: KILL unless the promotion gate passed. After any terminal decision the league's logging stops.

7. APPEND-ONLY / SEALING
Each record carries the SHA-256 hash of the previous line; the grader and the look calculator verify the chain and refuse to run if it is broken. Hosted in a GitHub repository; every run is a timestamped commit, so git history is an independent audit trail. The grader runs daily, grades only LOGGED qualified entries 48h+ after kickoff from the frozen score sources (nflverse; cfbfastR), marks VOID after 30 days without an official final, and prints counts only.

8. INTEGRITY CHECKS
Chain verification on every grade and look run. One entry per event (state flag). Entries written before kickoff (else ERROR). Statistic reproduces the accepted historical values. Tested: live run (68 games already inside 36h correctly logged as ERROR, 0 credits); simulated-clock run (anchor, D capture, ticket, ESPN venue match, covered-venue exclusion; 1 credit); forecast function on a past date (both systems returned, Last-Modified check passed). Not yet exercised live end to end: a qualifying outdoor game at D (first real one after hosting).

KNOWN LIMITATIONS
- Accrual is slow: historically about 37 qualifying NFL games per season (184 over 5 seasons) and about 17 NCAAF (85 over 5). The first look (150) is roughly 4 NFL seasons and roughly 9 NCAAF seasons away.
- Live odds cost 1 credit per sport per run during D windows (about 1,000-1,500 credits/month in season), so the free 500-credit tier is not enough.
- GitHub Actions scheduling can be delayed; the 15-minute capture window with 5-minute runs gives about three chances per capture; a window with no capture is logged as ERROR and is never widened.
