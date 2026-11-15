# Verification status and known limitations

## Executed in the build environment
- Python `compileall` on backend application and tests: passed.
- Backend Pytest suite: 7 passed.
- FastAPI smoke test: health endpoint, challenge listing, project creation, TCP simulation and project deletion returned successful responses.
- Sample TCP simulation traversed `pc1 -> sw1 -> r1 -> r2 -> server1`.

## Not verified in this environment
- Frontend production build and browser screenshots: npm dependency installation did not complete in the available execution window, so a Vite/TypeScript build could not be run here.
- Responsive browser behavior and Playwright tests have not been executed.

## Deliberate scope gaps versus the full project brief
This delivered version is a functional baseline, not a claim that every item in the 1,445-line specification is complete. In particular:
- TCP retransmission timers, timeout recovery, full connection teardown and a complete TCP state machine are not implemented.
- Ping/traceroute are educational abstractions; reverse-path ICMP delivery and realistic router-only TTL decrement are simplified.
- Ethernet/ARP is abstracted; MAC learning tables and full switch flooding behavior are not yet implemented.
- Firewall rules currently support ordered matching of source/destination IP, protocol and destination port, but not every possible rule dimension.
- Challenge scenarios are catalogued and a basic fresh-success check exists; isolated challenge copies, fault setup, persistent scoring, hints and penalties need further implementation.
- There is no complete configuration-diff engine, repair-application workflow, or verified repair ledger yet.
- Browser E2E tests and the complete academic report/diagrams remain follow-up work.

Do not present these unimplemented areas as completed in a university demonstration. The code and documentation distinguish the implemented simulation abstractions from real network behavior.
