# Protocol model and scope

- TCP: educational three-way handshake with configurable client initial sequence, deterministic server initial sequence, 32-bit wraparound and closed-port RST event.
- ICMP: echo request/reply and TTL-expired traceroute probes.
- UDP: connectionless delivery to configured listeners; closed ports produce ICMP Port Unreachable.
- DNS: simulated A-record lookup over the modeled UDP path, with NOERROR and NXDOMAIN.
- HTTP: simulated TCP setup followed by GET and configurable route response.
- SMTP: simulated TCP setup followed by a deterministic command/reply transcript and recipient policy.

The simulator is not a standards-complete implementation. It abstracts ARP, Ethernet framing, TCP reliability/congestion control, DNS wire encoding and SMTP message serialization.
