from app.engine import Simulator, sample_topology, validate_topology

def test_sample_topology_valid():
    assert validate_topology(sample_topology()) == []

def test_tcp_handshake_uses_sequence_numbers():
    result=Simulator(sample_topology()).run({"protocol":"tcp","source":"pc1","destination":"server1","destinationPort":80,"initialSeq":4294967295})
    assert result["delivered"] is True
    syn=next(e for e in result["events"] if e["type"]=="tcp_syn")
    ack=next(e for e in result["events"] if e["type"]=="tcp_ack")
    assert syn["sequence"] == 4294967295
    assert ack["sequence"] == 0

def test_missing_link_fails_with_evidence():
    topology=sample_topology()
    topology["links"][2]["enabled"]=False
    result=Simulator(topology).run({"protocol":"tcp","source":"pc1","destination":"server1","destinationPort":80})
    assert not result["delivered"]
    assert any(d["category"]=="LINK_DOWN" for d in result["diagnostics"])

def test_udp_closed_port_is_not_tcp_rst():
    result=Simulator(sample_topology()).run({"protocol":"udp","source":"pc1","destination":"server1","destinationPort":9999})
    assert not result["delivered"]
    assert any(e["type"]=="icmp_port_unreachable" for e in result["events"])
    assert not any(e["type"]=="tcp_rst" for e in result["events"])

def test_dns_and_http():
    topo=sample_topology()
    dns=Simulator(topo).run({"protocol":"dns","source":"pc1","destination":"server1","hostname":"app.netsim.local"})
    assert dns["resolvedAddress"]=="10.0.1.10"
    http=Simulator(topo).run({"protocol":"http","source":"pc1","destination":"server1","path":"/"})
    assert http["metrics"]["status"]==200


def test_ping_records_route_and_metrics():
    result=Simulator(sample_topology()).run({"protocol":"ping","source":"pc1","destination":"server1","count":3})
    assert result["delivered"] is True
    assert result["path"] == ["pc1","sw1","r1","r2","server1"]
    assert result["metrics"]["sent"] == 3
    assert result["metrics"]["received"] == 3

def test_smtp_recipient_rejection_is_application_level():
    result=Simulator(sample_topology()).run({"protocol":"smtp","source":"pc1","destination":"server1","destinationPort":25,"serverResponse":"nobody@example.edu"})
    assert result["delivered"] is False
    assert result["reason"] == "SMTP recipient rejected by application"
    assert any(e["type"] == "smtp_reply" and e.get("code") == "550" for e in result["events"])
