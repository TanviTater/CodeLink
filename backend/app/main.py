
import json
import csv
import io

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import Project, SimulationRun
from .schemas import (
    ProjectCreate,
    ProjectUpdate,
    SimulationRequest,
    ImportRequest,
)
from .engine import Simulator, validate_topology, CHALLENGES


Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="NetSim Studio API",
    version="1.0.0",
    description="Deterministic educational network protocol simulator.",
)

# CORS configuration: allow local development and deployed frontend

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://code-link-j19bdnqgh-tanvi9.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



def project_out(p):
    return {
        "id": p.id,
        "name": p.name,
        "topology": json.loads(p.topology_json),
        "createdAt": p.created_at.isoformat(),
        "updatedAt": p.updated_at.isoformat(),
    }


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "NetSim Studio API"}


@app.get("/api/projects")
def list_projects(db: Session = Depends(get_db)):
    return [
        project_out(p)
        for p in db.query(Project).order_by(Project.updated_at.desc()).all()
    ]


@app.post("/api/projects")
def create_project(body: ProjectCreate, db: Session = Depends(get_db)):
    data = body.topology.model_dump()
    errors = validate_topology(data)

    if errors:
        raise HTTPException(422, detail=errors)

    p = Project(
        name=body.name,
        topology_json=json.dumps(data),
    )

    db.add(p)
    db.commit()
    db.refresh(p)

    return project_out(p)


@app.get("/api/projects/{project_id}")
def get_project(project_id: int, db: Session = Depends(get_db)):
    p = db.get(Project, project_id)

    if not p:
        raise HTTPException(404, "Project not found")

    return project_out(p)


@app.put("/api/projects/{project_id}")
def update_project(
    project_id: int,
    body: ProjectUpdate,
    db: Session = Depends(get_db),
):
    p = db.get(Project, project_id)

    if not p:
        raise HTTPException(404, "Project not found")

    if body.name is not None:
        p.name = body.name

    if body.topology is not None:
        data = body.topology.model_dump()
        errors = validate_topology(data)

        if errors:
            raise HTTPException(422, detail=errors)

        p.topology_json = json.dumps(data)

    db.commit()
    db.refresh(p)

    return project_out(p)


@app.delete("/api/projects/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    p = db.get(Project, project_id)

    if not p:
        raise HTTPException(404, "Project not found")

    db.delete(p)
    db.commit()

    return {"deleted": True}


@app.post("/api/projects/{project_id}/simulate")
def simulate(
    project_id: int,
    body: SimulationRequest,
    db: Session = Depends(get_db),
):
    p = db.get(Project, project_id)

    if not p:
        raise HTTPException(404, "Project not found")

    snapshot = json.loads(p.topology_json)
    result = Simulator(snapshot).run(body.model_dump())

    run = SimulationRun(
        project_id=project_id,
        protocol=body.protocol,
        status=result["status"],
        source=body.source,
        destination=body.destination,
        config_snapshot=json.dumps(snapshot),
        result_json=json.dumps(result),
    )

    db.add(run)
    db.commit()
    db.refresh(run)

    result["runId"] = run.id

    return result


@app.get("/api/runs")
def list_runs(
    project_id: int | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(SimulationRun)

    if project_id:
        q = q.filter(SimulationRun.project_id == project_id)

    return [
        {
            "id": r.id,
            "projectId": r.project_id,
            "protocol": r.protocol,
            "status": r.status,
            "source": r.source,
            "destination": r.destination,
            "createdAt": r.created_at.isoformat(),
        }
        for r in q.order_by(SimulationRun.created_at.desc()).limit(200).all()
    ]


@app.get("/api/runs/{run_id}")
def get_run(run_id: int, db: Session = Depends(get_db)):
    r = db.get(SimulationRun, run_id)

    if not r:
        raise HTTPException(404, "Run not found")

    data = json.loads(r.result_json)
    data["runId"] = r.id

    return data


@app.get("/api/runs/{run_id}/diagnostics")
def run_diagnostics(run_id: int, db: Session = Depends(get_db)):
    r = db.get(SimulationRun, run_id)

    if not r:
        raise HTTPException(404, "Run not found")

    return json.loads(r.result_json).get("diagnostics", [])


@app.get("/api/projects/{project_id}/export")
def export_project(project_id: int, db: Session = Depends(get_db)):
    p = db.get(Project, project_id)

    if not p:
        raise HTTPException(404, "Project not found")

    return {
        "format": "netsim-project-v1",
        "name": p.name,
        "topology": json.loads(p.topology_json),
    }


@app.post("/api/projects/import")
def import_project(body: ImportRequest, db: Session = Depends(get_db)):
    data = body.topology.model_dump()
    errors = validate_topology(data)

    if errors:
        raise HTTPException(422, detail=errors)

    p = Project(
        name=body.name,
        topology_json=json.dumps(data),
    )

    db.add(p)
    db.commit()
    db.refresh(p)

    return project_out(p)


@app.get("/api/challenges")
def challenges():
    return CHALLENGES


@app.post("/api/challenges/{challenge_id}/check")
def check_challenge(
    challenge_id: str,
    project_id: int,
    db: Session = Depends(get_db),
):
    if challenge_id not in {c["id"] for c in CHALLENGES}:
        raise HTTPException(404, "Challenge not found")

    p = db.get(Project, project_id)

    if not p:
        raise HTTPException(404, "Project not found")

    # Completion is based on a fresh successful simulation.
    recent = (
        db.query(SimulationRun)
        .filter_by(project_id=project_id)
        .order_by(SimulationRun.created_at.desc())
        .first()
    )

    verified = bool(recent and recent.status == "success")

    return {
        "challengeId": challenge_id,
        "verified": verified,
        "score": 80 if verified else 0,
        "message": (
            "A successful fresh simulation was found."
            if verified
            else "Run a test after repairing the topology; "
                 "no successful verification run exists."
        ),
    }


@app.get("/api/analytics")
def analytics(db: Session = Depends(get_db)):
    runs = db.query(SimulationRun).all()
    success = sum(r.status == "success" for r in runs)

    return {
        "projects": db.query(Project).count(),
        "runs": len(runs),
        "successful": success,
        "failed": len(runs) - success,
        "successRate": round(success * 100 / len(runs), 1) if runs else 0,
        "protocols": {
            protocol: sum(r.protocol == protocol for r in runs)
            for protocol in [
                "ping",
                "traceroute",
                "tcp",
                "udp",
                "dns",
                "http",
                "smtp",
            ]
        },
    }


@app.get("/api/runs/{run_id}/packets.csv")
def packets_csv(run_id: int, db: Session = Depends(get_db)):
    r = db.get(SimulationRun, run_id)

    if not r:
        raise HTTPException(404, "Run not found")

    packets = json.loads(r.result_json).get("packets", [])

    out = io.StringIO()

    writer = csv.DictWriter(
        out,
        fieldnames=[
            "id",
            "source",
            "destination",
            "protocol",
            "destinationPort",
            "ttl",
        ],
    )

    writer.writeheader()
    writer.writerows(packets)

    return StreamingResponse(
        iter([out.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": (
                f"attachment; filename=run-{run_id}-packets.csv"
            )
        },
    )
