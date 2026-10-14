# v1.1 production audit log (append-only; new entries are added below, existing entries are never edited)

## 2026-10-14 — Implementation correction: ESPN venue lookup (independently audited; approved subject to verification)
- Defect: espn_venue() matched Odds API team names to ESPN displayName by exact string; NCAAF naming differences returned no venue → "ERROR unknown venue".
- Correction: NCAAF names normalized on both sides with the frozen v1.1 cfb_name() rules; exact set match of the two teams; fails closed (unresolvable name, zero or multiple matching ESPN events, or missing venue id → no venue). NFL unchanged. Classified as an implementation correction; v1.1 substantive rules unchanged; no new protocol version.
- logger.py SHA-256: original 033a8f1ef6abc1f26dbe1d8d0bb00d3018e449f3b06263e906612739f54c262c → patched 6c4ded9047fd40bdc2c2c66cc4459d64dd757d17f5945831d3e6ff0d7f462407. No other file changed.
- Implementation-caused exclusions (permanently retained as ERROR; not reconstructed, backfilled, overwritten or reclassified; original records, timestamps and hash-chain entries preserved). Reported separately from ordinary eligibility exclusions:
  - 57ad14afc7db1843fd56f5971dadb058  Southern Miss @ Troy  K 2026-10-07T00:00:00Z
  - b274da111dc9826f36e5fa238998dd69  Sam Houston @ Liberty  K 2026-10-08T23:00:00Z
  - 23614f055733537fb79ab73e68040eca  Wyoming @ San José State  K 2026-10-10T01:00:00Z
  - 310dd8851a99203930a45881b0156d36  Old Dominion @ App State  K 2026-10-10T17:00:00Z
  - 43dda5e509a9619bee41f752a2c25fa7  Miami (OH) @ UMass  K 2026-10-10T18:00:00Z
  - 837b4ddbdcd5e8e3a68a7c954208ff40  Louisiana @ Louisiana Tech  K 2026-10-10T23:30:00Z
  - 7dd6e0d9f2657c834974c28b286ff58d  Hawai'i @ Arizona State  K 2026-10-11T02:30:00Z
  - 2bbbf3488a5d57c9c13ae578bad17a9d  Western Kentucky @ Sam Houston  K 2026-10-15T00:00:00Z
- Not a defect: Ball State @ Northwestern resolves to venue 11823 (new Ryan Field), outside the frozen venue table; remains ERROR per frozen rule. Venue additions require a separately versioned prospective protocol.
- Deployment timestamp: (recorded in the next entry at deployment)
