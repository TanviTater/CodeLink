# Architecture

```mermaid
flowchart LR
  UI[React + React Flow] --> API[FastAPI REST API]
  API --> DB[(SQLite / SQLAlchemy)]
  API --> SIM[Deterministic Simulator]
  SIM --> NET[IPv4 forwarding and routing]
  SIM --> PROTO[TCP / ICMP / UDP / DNS / HTTP / SMTP]
  SIM --> DIAG[Evidence-based diagnostics]
  SIM --> EVENTS[Ordered event log]
  EVENTS --> UI
```

The backend owns topology validation, protocol execution, forwarding decisions, metrics and diagnostic findings. The browser renders returned events and does not decide packet outcomes.
