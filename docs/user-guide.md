# NetSim Studio User Guide

## Start
1. Start the backend and frontend using the README instructions.
2. Open `http://localhost:5173`.
3. Open Network Lab and choose **Load sample topology**.
4. Click **Save topology** before running simulations.

## Build a topology
1. Add PCs, switches, routers, and servers from the toolbar.
2. Drag devices into position.
3. Connect node handles to create links.
4. Select each device and set its IPv4 address, prefix, gateway, and interface status.
5. On routers, configure static routes as JSON objects with `network`, `prefix`, `nextHop`, and `metric`.
6. On servers, configure listening ports and application service maps.
7. Save, then run ping to test reachability.

## Protocol Simulator
Choose a protocol card to open its walkthrough. Step through the animation to understand the conceptual exchange. Select **Run against topology** to execute the actual backend simulation. The result shows the recorded event timeline, packet records, and diagnostics.

## Troubleshooting
Create a controlled failure by disabling a link or setting an interface Down. Save and run ping or TCP. Open Troubleshooting Lab and read the diagnosis and evidence event IDs. Repair one variable, save, and rerun the same test. A successful new run verifies that test.

## Simulation packet details
Run a simulation first. Open Simulation packet details and select a packet row. The field panel explains source, destination, protocol, destination port, and TTL. Use the Event timeline to see the packet's progress.

## Challenge Lab
Open a challenge card to read its objective and instructions. Investigate the matching network property, repair it in Network Lab, save, run a fresh successful test, then click **Verify latest run**. The current backend verifier checks only for a recent successful run; it does not validate the exact challenge repair.
