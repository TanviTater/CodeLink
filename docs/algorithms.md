# Algorithms

## IPv4 connected-network lookup
For each active adjacent link, inspect the neighbor interface's IPv4 network using its CIDR prefix. A destination address contained by that network is directly reachable through that neighbor.

## Longest-prefix match
For router routes matching the destination, sort by descending prefix length, then ascending metric, then next-hop address for deterministic ties. The first route wins.

## Forwarding
Each hop checks loop visitation, TTL, firewall rules, direct adjacency or a router route, next-hop reachability, interface status and link status. The engine emits an event for each decision.

## Diagnostics
The diagnostic registry maps concrete failure event types to a category, event ID evidence and a suggested repair. A recommendation is not a verified repair; verification requires a later successful run.
