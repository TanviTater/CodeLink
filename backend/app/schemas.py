from typing import Any, Literal
from pydantic import BaseModel, Field, ConfigDict

class Device(BaseModel):
    id: str
    type: Literal["pc", "router", "switch", "server"]
    name: str
    x: float = 100
    y: float = 100
    interfaces: list[dict[str, Any]] = Field(default_factory=list)
    routes: list[dict[str, Any]] = Field(default_factory=list)
    services: dict[str, Any] = Field(default_factory=dict)
    firewall: list[dict[str, Any]] = Field(default_factory=list)

class Link(BaseModel):
    id: str
    source: str
    target: str
    sourceInterface: str = "eth0"
    targetInterface: str = "eth0"
    enabled: bool = True
    delayMs: float = 2
    lossPercent: float = 0

class Topology(BaseModel):
    devices: list[Device] = Field(default_factory=list)
    links: list[Link] = Field(default_factory=list)

class ProjectCreate(BaseModel):
    name: str = "Untitled network"
    topology: Topology

class ProjectUpdate(BaseModel):
    name: str | None = None
    topology: Topology | None = None

class SimulationRequest(BaseModel):
    protocol: Literal["ping", "traceroute", "tcp", "udp", "dns", "http", "smtp"]
    source: str
    destination: str
    destinationPort: int | None = None
    sourcePort: int = 49152
    hostname: str | None = None
    path: str = "/"
    count: int = 4
    ttl: int = 8
    initialSeq: int = 1000
    serverResponse: str | None = None

class ImportRequest(BaseModel):
    name: str = "Imported network"
    topology: Topology
