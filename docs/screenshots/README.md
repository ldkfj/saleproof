# Screenshot evidence status

The superseded pre-correction screenshots were removed from the public release
boundary. Git history preserves them for local audit continuity, but they must
not be cited as current release evidence.

After the corrected pair is deployed and recorded in
`deployments/README.md`, the current release evidence was generated into
`docs/screenshots/current/`. The harness first verified the explicit release
addresses and chain truth, all DOM assertions passed, and the seven screenshots
were visually reviewed. `06-write-pending.png` and `07-write-final.png` show the
same real snapshot transaction progressing from validator consensus to
`FINALIZED + SUCCESS`, with observation count `5 -> 6` without reload.
