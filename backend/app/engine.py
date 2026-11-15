from __future__ import annotations
from ipaddress import ip_address, ip_network
from collections import defaultdict, deque
from typing import Any
import math

def iface_ip(device: dict, iface_name: str | None = None):
    for iface in device.get("interfaces", []):
        if iface_name is None or iface.get("name") == iface_name:
            try:
                return str(ip_address(iface.get("ip", ""))), int(iface.get("prefix", 24)), iface
            except Exception:
                continue
    return None, None, None

def validate_topology(topology: dict) -> list[dict]:
    errors, seen = [], {}
    for d in topology.get("devices", []):
        for i in d.get("interfaces", []):
            ip = i.get("ip")
            if not ip:
                continue
            try:
                addr = ip_address(ip)
                if addr.version != 4: raise ValueError()
                prefix = int(i.get("prefix", 24))
                if not 0 <= prefix <= 32: raise ValueError()
                if ip in seen:
                    errors.append({"code":"duplicate_ip","device":d["id"],"message":f"{ip} is also configured on {seen[ip]}."})
                seen[ip] = d["id"]
            except Exception:
                errors.append({"code":"invalid_ip","device":d["id"],"message":f"Invalid IPv4 interface configuration: {ip}/{i.get('prefix',24)}."})
    ids = {d["id"] for d in topology.get("devices", [])}
    for link in topology.get("links", []):
        if link.get("source") not in ids or link.get("target") not in ids:
            errors.append({"code":"invalid_link","message":f"Link {link.get('id')} references an unknown device."})
    return errors

class Simulator:
    def __init__(self, topology: dict):
        self.topology = topology
        self.devices = {d["id"]: d for d in topology.get("devices", [])}
        self.events: list[dict] = []
        self.packets: list[dict] = []
        self.clock = 0.0
        self._seq = 0

    def event(self, kind: str, **kw):
        self._seq += 1
        ev = {"id": f"e{self._seq}", "timeMs": round(self.clock, 3), "type": kind, **kw}
        self.events.append(ev)
        return ev

    def _links(self, device_id):
        return [l for l in self.topology.get("links", []) if (l["source"] == device_id or l["target"] == device_id)]

    def _neighbor(self, link, current):
        return link["target"] if link["source"] == current else link["source"]

    def _interface_up(self, device_id, link, current):
        d = self.devices[current]
        name = link.get("sourceInterface") if link["source"] == current else link.get("targetInterface")
        iface = next((x for x in d.get("interfaces", []) if x.get("name") == name), None)
        return iface is None or iface.get("up", True)

    def _ip_of(self, device_id):
        ip, _, _ = iface_ip(self.devices[device_id])
        return ip

    def _connected_neighbor(self, current, target_ip):
        # Resolve an on-link target through transparent Layer-2 switches.
        # Return the first physical hop so every bridge traversal is still logged.
        try:
            target = ip_address(target_ip)
        except Exception:
            return None
        queue = deque([(current, None, {current})])
        while queue:
            node_id, first_link, visited = queue.popleft()
            for link in self._links(node_id):
                if not self._interface_up(node_id, link, node_id):
                    continue
                other = self._neighbor(link, node_id)
                if other in visited:
                    continue
                hop_link = first_link or link
                candidate = self.devices[other]
                for iface in candidate.get("interfaces", []):
                    try:
                        net = ip_network(f'{iface["ip"]}/{iface.get("prefix",24)}', strict=False)
                        if target in net:
                            return other if node_id == current else self._neighbor(hop_link, current), hop_link
                    except Exception:
                        pass
                # Only switches are transparent transit devices; routers must route.
                if candidate.get("type") == "switch":
                    queue.append((other, hop_link, visited | {other}))
        return None

    def _route_next(self, router, target_ip):
        routes = router.get("routes", [])
        matches = []
        for route in routes:
            try:
                net = ip_network(f'{route["network"]}/{route["prefix"]}', strict=False)
                if ip_address(target_ip) in net:
                    matches.append((net.prefixlen, route))
            except Exception: continue
        if not matches: return None
        matches.sort(key=lambda x: (-x[0], int(x[1].get("metric", 0)), x[1].get("nextHop", "")))
        return matches[0][1]

    def _firewall_denied(self, device, src_ip, dst_ip, protocol, dst_port):
        for rule in sorted(device.get("firewall", []), key=lambda r: int(r.get("priority", 100))):
            if rule.get("sourceIp") not in (None, "", "*", src_ip): continue
            if rule.get("destinationIp") not in (None, "", "*", dst_ip): continue
            if rule.get("protocol") not in (None, "", "*", protocol): continue
            if rule.get("destinationPort") not in (None, "", "*", dst_port): continue
            return rule.get("action", "allow").lower() == "deny"
        return False

    def forward(self, source: str, destination: str, protocol="ICMP", dst_port=None, ttl=16):
        if source not in self.devices or destination not in self.devices:
            self.event("packet_dropped", reason="Unknown source or destination device")
            return {"delivered": False, "reason":"Unknown source or destination device", "path":[]}
        src_ip, _, src_iface = iface_ip(self.devices[source])
        dst_ip, _, dst_iface = iface_ip(self.devices[destination])
        if not src_ip or not dst_ip:
            self.event("packet_dropped", device=source, reason="Source or destination has no valid IPv4 address")
            return {"delivered":False,"reason":"Missing or invalid IP configuration","path":[]}
        packet_id = f"p{len(self.packets)+1}"
        packet = {"id":packet_id,"source":src_ip,"destination":dst_ip,"protocol":protocol,"destinationPort":dst_port,"ttl":ttl}
        self.packets.append(packet)
        self.event("packet_created", packetId=packet_id, device=source, source=src_ip, destination=dst_ip, protocol=protocol, packet=packet.copy())
        current, path, visited, incoming_link = source, [source], set(), None
        while current != destination:
            if current in visited:
                self.event("packet_dropped", packetId=packet_id, device=current, reason="Routing loop detected")
                return {"delivered":False,"reason":"Routing loop detected","path":path}
            visited.add(current)
            if ttl <= 0:
                self.event("ttl_expired", packetId=packet_id, device=current, reason="TTL expired")
                return {"delivered":False,"reason":"TTL expired","path":path}
            ttl -= 1
            dev = self.devices[current]
            if self._firewall_denied(dev, src_ip, dst_ip, protocol, dst_port):
                self.event("firewall_denied", packetId=packet_id, device=current, reason="Firewall rule denied traffic", protocol=protocol, destinationPort=dst_port)
                return {"delivered":False,"reason":f"Firewall denied traffic at {dev['name']}","path":path}
            direct = self._connected_neighbor(current, dst_ip)
            next_id, chosen_link = None, None
            if dev["type"] == "switch":
                # Layer-2 bridge: forward out the eligible port other than the ingress port.
                candidates = [l for l in self._links(current) if l.get("enabled", True) and l.get("id") != (incoming_link or {}).get("id") and self._interface_up(current, l, current)]
                if candidates:
                    chosen_link = sorted(candidates, key=lambda l: l["id"])[0]
                    next_id = self._neighbor(chosen_link, current)
            elif direct:
                next_id, chosen_link = direct
            elif dev["type"] == "router":
                route = self._route_next(dev, dst_ip)
                if not route:
                    self.event("route_unavailable", packetId=packet_id, device=current, reason="No matching route (longest-prefix lookup)")
                    return {"delivered":False,"reason":f"No route to {dst_ip} at {dev['name']}","path":path}
                hop = route.get("nextHop")
                try: hop_ip = str(ip_address(hop))
                except Exception:
                    self.event("route_unavailable", packetId=packet_id, device=current, reason="Route has invalid next hop")
                    return {"delivered":False,"reason":"Invalid route next hop","path":path}
                neighbor = self._connected_neighbor(current, hop_ip)
                if not neighbor:
                    self.event("next_hop_unreachable", packetId=packet_id, device=current, reason=f"Next hop {hop_ip} is unreachable")
                    return {"delivered":False,"reason":f"Next hop {hop_ip} is unreachable","path":path}
                next_id, chosen_link = neighbor
            else:
                gateway = next((i.get("gateway") for i in dev.get("interfaces", []) if i.get("gateway")), None)
                if gateway:
                    neighbor = self._connected_neighbor(current, gateway)
                    if neighbor: next_id, chosen_link = neighbor
                if not next_id:
                    self.event("route_unavailable", packetId=packet_id, device=current, reason="Destination is remote and no usable default gateway exists")
                    return {"delivered":False,"reason":f"No usable default gateway at {dev['name']}","path":path}
            if not self._interface_up(current, chosen_link, current):
                self.event("interface_down", packetId=packet_id, device=current, reason="Outgoing interface is down")
                return {"delivered":False,"reason":f"Outgoing interface down at {dev['name']}","path":path}
            if not chosen_link.get("enabled", True):
                self.event("link_down", packetId=packet_id, device=current, linkId=chosen_link["id"], reason="Link is disabled")
                return {"delivered":False,"reason":f"Link {chosen_link['id']} is down","path":path}
            if float(chosen_link.get("lossPercent", 0)) >= 100:
                self.event("packet_dropped", packetId=packet_id, device=current, linkId=chosen_link["id"], reason="Deterministic link loss is 100%")
                return {"delivered":False,"reason":"Packet lost on link","path":path}
            self.clock += max(0, float(chosen_link.get("delayMs", 2)))
            self.event("packet_forwarded", packetId=packet_id, device=current, nextHop=next_id, linkId=chosen_link["id"], protocol=protocol, ttl=ttl)
            incoming_link = chosen_link
            current = next_id
            path.append(current)
        target = self.devices[destination]
        if self._firewall_denied(target, src_ip, dst_ip, protocol, dst_port):
            self.event("firewall_denied", packetId=packet_id, device=destination, reason="Destination firewall denied traffic", protocol=protocol, destinationPort=dst_port)
            return {"delivered":False,"reason":f"Firewall denied traffic at {target['name']}","path":path}
        self.event("packet_delivered", packetId=packet_id, device=destination, source=src_ip, destination=dst_ip, protocol=protocol)
        return {"delivered":True,"reason":None,"path":path,"packetId":packet_id}

    def run(self, req: dict):
        protocol = req["protocol"]
        src, dst = req["source"], req["destination"]
        dst_port = req.get("destinationPort")
        result = {"protocol":protocol,"source":src,"destination":dst,"delivered":False,"path":[],"events":self.events,"packets":self.packets,"metrics":{}}
        if src not in self.devices or dst not in self.devices:
            self.event("packet_dropped", reason="Unknown endpoint")
            result["reason"] = "Unknown endpoint"
            return self.finish(result)
        server = self.devices[dst]
        services = server.get("services", {})
        if protocol == "tcp":
            port = int(dst_port or 80)
            is_open = port in services.get("tcpPorts", [80, 443, 25]) or str(port) in services.get("tcpPorts", [])
            if not is_open:
                f = self.forward(src, dst, "TCP", port)
                if f["delivered"]:
                    self.event("tcp_rst", packetId=f.get("packetId"), device=dst, flags=["RST","ACK"], reason="Destination TCP port is closed")
                    result.update(delivered=False, reason="Connection refused: TCP port is closed", path=f["path"])
                else: result.update(reason=f["reason"],path=f["path"])
            else:
                base = int(req.get("initialSeq", 1000)) & 0xffffffff
                server_seq = (base * 7 + 91) & 0xffffffff
                f1 = self.forward(src,dst,"TCP",port)
                if f1["delivered"]:
                    self.event("tcp_syn", packetId=f1["packetId"], device=src, flags=["SYN"], sequence=base, acknowledgement=0, sourcePort=req.get("sourcePort",49152), destinationPort=port, state="SYN-SENT")
                    self.event("tcp_syn_ack", packetId=f1["packetId"], device=dst, flags=["SYN","ACK"], sequence=server_seq, acknowledgement=(base+1)&0xffffffff, state="SYN-RECEIVED")
                    self.event("tcp_ack", packetId=f1["packetId"], device=src, flags=["ACK"], sequence=(base+1)&0xffffffff, acknowledgement=(server_seq+1)&0xffffffff, state="ESTABLISHED")
                    result.update(delivered=True,reason=None,path=f1["path"],metrics={"handshakePackets":3,"clientInitialSeq":base,"serverInitialSeq":server_seq})
                else: result.update(reason=f1["reason"],path=f1["path"])
        elif protocol == "ping":
            count = max(1,min(20,int(req.get("count",4))))
            rtts=[]
            successful_path=[]
            for n in range(count):
                start=self.clock
                f=self.forward(src,dst,"ICMP",None,req.get("ttl",16))
                if f["delivered"]:
                    successful_path = f.get("path", [])
                    self.event("icmp_echo_request",packetId=f["packetId"],device=src,sequence=n+1)
                    self.clock += 1
                    self.event("icmp_echo_reply",packetId=f["packetId"],device=dst,sequence=n+1)
                    rtts.append(round(self.clock-start,3))
            result.update(delivered=len(rtts)>0,reason=None if rtts else (self.events[-1].get("reason") or "Request timed out"),path=successful_path)
            result["metrics"]={"sent":count,"received":len(rtts),"lost":count-len(rtts),"lossPercent":round((count-len(rtts))*100/count,1),"rttMin":min(rtts) if rtts else None,"rttMax":max(rtts) if rtts else None,"rttAvg":round(sum(rtts)/len(rtts),3) if rtts else None}
        elif protocol == "traceroute":
            max_ttl=max(1,min(32,int(req.get("ttl",8))))
            last=[]
            for hop in range(1,max_ttl+1):
                f=self.forward(src,dst,"ICMP",None,hop)
                last=f.get("path",[])
                if f["delivered"]:
                    self.event("traceroute_reached",device=dst,hop=hop)
                    result.update(delivered=True,path=last,reason=None)
                    break
                if f["reason"] == "TTL expired":
                    self.event("icmp_time_exceeded",device=last[-1] if last else src,hop=hop)
                else:
                    result.update(reason=f["reason"],path=last); break
            else: result.update(reason="Maximum hop limit reached",path=last)
            result["metrics"]={"hops":len(last),"maxTtl":max_ttl}
        elif protocol == "udp":
            port=int(dst_port or 53)
            f=self.forward(src,dst,"UDP",port)
            opened=port in services.get("udpPorts", [53,123]) or str(port) in services.get("udpPorts", [])
            if f["delivered"] and opened:
                self.event("udp_datagram_received",packetId=f["packetId"],device=dst,sourcePort=req.get("sourcePort",49152),destinationPort=port)
                result.update(delivered=True,path=f["path"])
            elif f["delivered"]:
                self.event("icmp_port_unreachable",packetId=f["packetId"],device=dst,destinationPort=port)
                result.update(reason=f"UDP port {port} is closed",path=f["path"])
            else: result.update(reason=f["reason"],path=f["path"])
        elif protocol == "dns":
            hostname=req.get("hostname") or req.get("destination")
            dns_records=services.get("dnsRecords",{})
            dns_ip=services.get("dnsServerDevice",dst)
            f=self.forward(src,dns_ip,"UDP",53)
            if not f["delivered"]: result.update(reason=f["reason"],path=f["path"])
            elif hostname in dns_records:
                self.event("dns_query",device=src,hostname=hostname,recordType="A")
                self.event("dns_response",device=dns_ip,hostname=hostname,address=dns_records[hostname],rcode="NOERROR")
                result.update(delivered=True,path=f["path"],resolvedAddress=dns_records[hostname])
            else:
                self.event("dns_response",device=dns_ip,hostname=hostname,rcode="NXDOMAIN")
                result.update(reason=f"NXDOMAIN: no A record for {hostname}",path=f["path"])
        elif protocol == "http":
            port=int(dst_port or 80)
            tcp_req={**req,"protocol":"tcp","destinationPort":port}
            tcp=self.run(tcp_req)
            # Preserve handshake events generated by the same simulator.
            if not tcp["delivered"]:
                result.update(reason=tcp.get("reason"),path=tcp.get("path"))
            else:
                route=services.get("httpRoutes",{})
                path=req.get("path","/")
                status=int(route.get(path,{}).get("status",404))
                self.event("http_request",device=src,method="GET",path=path,host=req.get("hostname") or self._ip_of(dst))
                self.event("http_response",device=dst,status=status,reason="OK" if status==200 else ("Service Unavailable" if status==503 else "Not Found"))
                result.update(delivered=status==200,reason=None if status==200 else f"HTTP {status}",path=tcp.get("path"),metrics={"status":status,"path":path})
        elif protocol == "smtp":
            port=int(dst_port or 25)
            tcp=self.run({**req,"protocol":"tcp","destinationPort":port})
            if not tcp["delivered"]: result.update(reason=tcp.get("reason"),path=tcp.get("path"))
            else:
                recipient=req.get("serverResponse") or "student@example.edu"
                accepted=recipient in services.get("acceptedRecipients",["student@example.edu"])
                transcript=[("220","Service ready"),("250","EHLO accepted"),("250","MAIL FROM accepted"),("250" if accepted else "550","RCPT TO "+("accepted" if accepted else "rejected")),("354","Start mail input") if accepted else ("","DATA not sent"),("250","Message accepted") if accepted else ("","Message not accepted"),("221","Closing connection")]
                for code,msg in transcript:
                    if code:self.event("smtp_reply",device=dst,code=code,message=msg)
                result.update(delivered=accepted,reason=None if accepted else "SMTP recipient rejected by application",path=tcp.get("path"),transcript=[{"code":c,"message":m} for c,m in transcript if c])
        return self.finish(result)

    def finish(self,result):
        result["events"]=self.events
        result["packets"]=self.packets
        result["metrics"]=result.get("metrics") or {}
        result["status"]="success" if result.get("delivered") else "failed"
        result["elapsedMs"]=round(self.clock,3)
        result["diagnostics"]=diagnose(result,self.topology)
        return result

def diagnose(result: dict, topology: dict):
    findings=[]
    for ev in result.get("events",[]):
        reason=ev.get("reason","")
        category=None; fix=None
        if ev["type"]=="link_down":
            category="LINK_DOWN"; fix="Re-enable the failed link in the topology editor."
        elif ev["type"]=="interface_down":
            category="INTERFACE_DOWN"; fix="Enable the outgoing interface."
        elif ev["type"]=="firewall_denied":
            category="FIREWALL_DENIAL"; fix="Review the matching firewall rule and allow the required protocol/port."
        elif ev["type"]=="route_unavailable":
            category="MISSING_ROUTE_OR_GATEWAY"; fix="Configure a default gateway on the host or a matching static route on the router."
        elif ev["type"]=="next_hop_unreachable":
            category="UNREACHABLE_NEXT_HOP"; fix="Verify the next-hop address and that it is on a directly connected subnet."
        elif ev["type"]=="ttl_expired":
            category="TTL_EXPIRED"; fix="Inspect routing for a loop or excessive hop count."
        elif ev["type"]=="tcp_rst":
            category="TCP_PORT_CLOSED"; fix="Start the TCP service or configure the destination port as listening."
        elif ev["type"]=="icmp_port_unreachable":
            category="UDP_PORT_CLOSED"; fix="Configure a UDP listener on the destination port."
        elif ev["type"]=="dns_response" and ev.get("rcode")=="NXDOMAIN":
            category="DNS_RECORD_MISSING"; fix="Add the correct A record to the simulated DNS service."
        if category and not any(x["category"]==category for x in findings):
            findings.append({"id":f"d{len(findings)+1}","category":category,"device":ev.get("device"),"explanation":reason or ev.get("message") or category.replace("_"," ").lower(),"evidenceEventIds":[ev["id"]],"recommendedFix":fix,"confidence":"high","verified":False})
    if result.get("status")=="failed" and not findings:
        last=next((e for e in reversed(result.get("events",[])) if e["type"] in ("packet_dropped","route_unavailable","firewall_denied")),None)
        if last:
            findings.append({"id":"d1","category":"NETWORK_FAILURE","device":last.get("device"),"explanation":last.get("reason","The simulation did not complete."),"evidenceEventIds":[last["id"]],"recommendedFix":"Inspect the last forwarding event and verify endpoint configuration, route and link status.","confidence":"medium","verified":False})
    return findings

def sample_topology():
    return {
      "devices":[
        {"id":"pc1","type":"pc","name":"Client PC","x":80,"y":180,"interfaces":[{"name":"eth0","ip":"192.168.10.10","prefix":24,"gateway":"192.168.10.1","mac":"02:00:00:00:10:10","up":True}],"routes":[],"services":{},"firewall":[]},
        {"id":"sw1","type":"switch","name":"Access Switch","x":300,"y":180,"interfaces":[{"name":"p1","up":True},{"name":"p2","up":True}],"routes":[],"services":{},"firewall":[]},
        {"id":"r1","type":"router","name":"Edge Router","x":520,"y":180,"interfaces":[{"name":"eth0","ip":"192.168.10.1","prefix":24,"up":True},{"name":"eth1","ip":"10.0.0.1","prefix":24,"up":True}],"routes":[{"network":"10.0.1.0","prefix":24,"nextHop":"10.0.0.2","metric":10}],"services":{},"firewall":[]},
        {"id":"r2","type":"router","name":"Core Router","x":740,"y":180,"interfaces":[{"name":"eth0","ip":"10.0.0.2","prefix":24,"up":True},{"name":"eth1","ip":"10.0.1.1","prefix":24,"up":True}],"routes":[{"network":"192.168.10.0","prefix":24,"nextHop":"10.0.0.1","metric":10}],"services":{},"firewall":[]},
        {"id":"server1","type":"server","name":"Application Server","x":960,"y":180,"interfaces":[{"name":"eth0","ip":"10.0.1.10","prefix":24,"gateway":"10.0.1.1","up":True}],"routes":[],"services":{"tcpPorts":[80,25,443],"udpPorts":[53,123],"dnsRecords":{"app.netsim.local":"10.0.1.10"},"httpRoutes":{"/":{"status":200},"/health":{"status":200}},"acceptedRecipients":["student@example.edu"]},"firewall":[]}
      ],
      "links":[
        {"id":"l1","source":"pc1","target":"sw1","sourceInterface":"eth0","targetInterface":"p1","enabled":True,"delayMs":1,"lossPercent":0},
        {"id":"l2","source":"sw1","target":"r1","sourceInterface":"p2","targetInterface":"eth0","enabled":True,"delayMs":1,"lossPercent":0},
        {"id":"l3","source":"r1","target":"r2","sourceInterface":"eth1","targetInterface":"eth0","enabled":True,"delayMs":5,"lossPercent":0},
        {"id":"l4","source":"r2","target":"server1","sourceInterface":"eth1","targetInterface":"eth0","enabled":True,"delayMs":2,"lossPercent":0}
      ]
    }

CHALLENGES = [
 {"id":"gateway","title":"Repair the missing gateway","difficulty":"Beginner","objective":"Restore host connectivity to a remote subnet.","fault":"Remove the client default gateway."},
 {"id":"route","title":"Add a missing static route","difficulty":"Intermediate","objective":"Restore routing between two routed networks.","fault":"Remove the edge router route to the server subnet."},
 {"id":"subnet","title":"Correct the subnet mask","difficulty":"Beginner","objective":"Identify an incorrect prefix length.","fault":"Change the client prefix to /16."},
 {"id":"link","title":"Restore a failed link","difficulty":"Beginner","objective":"Find and re-enable a disabled path link.","fault":"Disable the router-to-router link."},
 {"id":"firewall","title":"Find the firewall block","difficulty":"Intermediate","objective":"Permit the required TCP service.","fault":"Add a deny rule for TCP destination port 80."},
 {"id":"udp","title":"Diagnose a closed UDP port","difficulty":"Beginner","objective":"Enable a UDP listener.","fault":"Remove UDP port 53 from the server listeners."},
 {"id":"dns","title":"Fix the DNS record","difficulty":"Intermediate","objective":"Correct an A record.","fault":"Remove app.netsim.local from DNS records."},
 {"id":"http","title":"Resolve and request a web page","difficulty":"Intermediate","objective":"Use DNS then retrieve a configured HTTP route.","fault":"Remove the / route from the HTTP service."},
 {"id":"smtp","title":"Diagnose recipient rejection","difficulty":"Intermediate","objective":"Distinguish application rejection from network failure.","fault":"Remove student@example.edu from accepted recipients."},
 {"id":"loop","title":"Break the routing loop","difficulty":"Advanced","objective":"Detect a forwarding loop and repair routing.","fault":"Configure reciprocal incorrect next-hop routes."}
]
