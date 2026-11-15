# CodeLink — Interactive Network Protocol Simulator & Troubleshooting Lab

A local, deterministic educational network simulator built with React + TypeScript + Vite and FastAPI + SQLAlchemy + SQLite.

## What is implemented
- Editable React Flow topology with hosts, routers, switches and servers.
- Backend-owned IPv4/subnet validation, routing-table longest-prefix match, hop-by-hop forwarding, TTL and link/interface checks.
- Deterministic event log used for packet inspection, timeline and diagnostics.
- TCP three-way handshake (configurable sequence numbers, ACK arithmetic, closed-port refusal, firewall drops).
- ICMP-style ping, traceroute, UDP, DNS A lookup, HTTP GET over a simulated TCP handshake, and a simplified SMTP transaction.
- Evidence-linked troubleshooting, repair suggestions, saved projects, immutable simulation runs, JSON import/export, CSV packet export.
- Ten challenge definitions, API documentation, backend tests and architecture notes.

## Important simulation boundaries
This is an educational discrete-event abstraction, not a full Ethernet/IP implementation. It does not open sockets, capture real traffic, access the Internet, or send email. ARP is abstracted as a per-hop neighbor-resolution event. Switches learn source MACs and flood unknown/broadcast frames. Link delay is simulated in milliseconds. The current implementation intentionally models one packet flow per experiment.

## Requirements
- Python 3.10+
- Node.js 18+
- npm

## Run locally

Terminal 1:
```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Terminal 2:
```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. API docs: http://localhost:8000/docs.

## Tests
```bash
cd backend
pytest -q
```

## Default workflow
1. Open Network Lab and load the sample topology.
2. Select a source host and destination.
3. Run Ping, TCP, UDP, DNS, HTTP or SMTP.
4. Inspect the event timeline and packet table.
5. Use Troubleshooting to review event-backed findings.
6. Save the project or export its JSON.

## API overview
- `GET /api/health`
- `GET/POST /api/projects`
- `GET/PUT/DELETE /api/projects/{id}`
- `POST /api/projects/{id}/simulate`
- `GET /api/runs`, `GET /api/runs/{id}`, `GET /api/runs/{id}/diagnostics`
- `POST /api/projects/import`, `GET /api/projects/{id}/export`
- `GET /api/challenges`, `POST /api/challenges/{id}/check`
- `GET /api/analytics`

The backend is the source of truth for validation, routing, simulation, events, metrics and diagnoses.

## Verification and scope
See `docs/verification-and-limitations.md` for the tests actually executed and the remaining gaps against the full specification.


## Updated learning workflows

- Documentation cards are clickable and open standalone guides in new browser tabs under `frontend/public/docs/`.
- Protocol Simulator cards open a dedicated walkthrough modal. Use Previous/Next to step through the conceptual animation, then run the backend simulation against a saved topology.
- Network Lab includes a short workflow strip and a full Network Design Manual.
- Troubleshooting Lab explains how to introduce a fault, run a test, map evidence IDs to events, repair one setting, and verify.
- Packet/event inspection explains packet rows and lets you select a packet to inspect each field.
- Challenge cards open an instruction brief. The challenge verifier remains intentionally limited: it checks for a recent successful run, not a challenge-specific repair.


## Beginner topology workflow

Use Load working sample to see the recommended PC → Switch → Router → Router → Server layout. To build your own, add devices, then use Connect two devices to create a link without dragging. NetSim assigns ports automatically (PC/server eth0, switch p1/p2…, router eth0/eth1). The Connections & port status list is the reliable place to enable or disable any link.

## Troubleshooting exercise

Open Troubleshooting Lab and choose Load faulty exercise. The Edge Router–Core Router link is intentionally disabled. In Network Lab, enable that link, save, and run Ping or TCP. Return to Troubleshooting Lab to see the result.


## CodeLink beginner-first interface update
The Network Lab now opens with a beginner-friendly network view:
- Devices appear as clear selectable cards with plain-language descriptions.
- The existing dropdown-based connection builder remains the recommended way to create links.
- Selecting a device shows its address and interface readiness at a glance.
- The React Flow topology canvas and detailed configuration panel remain available under **Open advanced topology editor**.
- The underlying FastAPI simulator, saved projects, protocol walkthroughs, troubleshooting exercise, challenge area, history, export and documentation are retained.

The simplified view is a usability layer over the existing simulator, not a replacement for the network model. Existing simulator scope and challenge-verification limitations still apply as documented above.
