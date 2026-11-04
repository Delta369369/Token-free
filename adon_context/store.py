"""Canonical local SQLite store, with explicit project isolation and immutable provenance."""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_DB = Path.home() / ".adon-context" / "context.sqlite3"
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,119}$")


def validate_id(value: str, what: str = "identifier") -> str:
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        raise ValueError(f"Invalid {what}: use 1-120 characters [A-Za-z0-9_.:-], starting alphanumeric")
    return value


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def canonical_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def json_load(path: str):
    p = Path(path).expanduser()
    return json.loads(p.read_text(encoding="utf-8"))


class ManagedConnection(sqlite3.Connection):
    """Commit/rollback on context exit AND release OS file handles.

    sqlite3.Connection.__exit__ manages transactions but does not close the
    connection. Windows therefore keeps temporary SQLite databases locked
    when a with-block exits unless close() is called explicitly.
    """

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


def connect(db: str | Path = DEFAULT_DB) -> sqlite3.Connection:
    path = Path(db).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        path.parent.chmod(0o700)
    c = sqlite3.connect(path, timeout=15, factory=ManagedConnection)
    try:
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys=ON")
        c.execute("PRAGMA busy_timeout=10000")
        c.execute("PRAGMA journal_mode=WAL")
        c.executescript("""
    CREATE TABLE IF NOT EXISTS projects (
      id TEXT PRIMARY KEY, created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS events (
      id TEXT PRIMARY KEY, project TEXT NOT NULL, session_id TEXT,
      kind TEXT NOT NULL, title TEXT NOT NULL, body TEXT NOT NULL,
      source_refs TEXT NOT NULL, occurred_at TEXT NOT NULL,
      created_at TEXT NOT NULL, record_sha256 TEXT NOT NULL,
      FOREIGN KEY(project) REFERENCES projects(id)
    );
    CREATE INDEX IF NOT EXISTS idx_events_project_date ON events(project,created_at);
    CREATE TABLE IF NOT EXISTS constraints_state (
      project TEXT NOT NULL, key TEXT NOT NULL, revision INTEGER NOT NULL,
      status TEXT NOT NULL, text TEXT NOT NULL, source_ref TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      PRIMARY KEY(project,key), FOREIGN KEY(project) REFERENCES projects(id)
    );
    CREATE TABLE IF NOT EXISTS constraint_history (
      id TEXT PRIMARY KEY, project TEXT NOT NULL, key TEXT NOT NULL,
      revision INTEGER NOT NULL, status TEXT NOT NULL, text TEXT NOT NULL,
      source_ref TEXT NOT NULL, changed_at TEXT NOT NULL, sha256 TEXT NOT NULL,
      FOREIGN KEY(project) REFERENCES projects(id)
    );
    CREATE TABLE IF NOT EXISTS sources (
      id TEXT PRIMARY KEY, project TEXT NOT NULL, path TEXT NOT NULL,
      file_sha256 TEXT, size_bytes INTEGER, note TEXT NOT NULL,
      registered_at TEXT NOT NULL, FOREIGN KEY(project) REFERENCES projects(id)
    );
    CREATE INDEX IF NOT EXISTS idx_sources_project ON sources(project);
    CREATE TABLE IF NOT EXISTS checkpoints (
      id TEXT PRIMARY KEY, project TEXT NOT NULL, session_id TEXT NOT NULL,
      objective TEXT NOT NULL, done TEXT NOT NULL, decisions TEXT NOT NULL,
      pending TEXT NOT NULL, next_action TEXT NOT NULL, git_commit TEXT,
      source_refs TEXT NOT NULL, event_ids TEXT NOT NULL, created_at TEXT NOT NULL,
      record_sha256 TEXT NOT NULL, FOREIGN KEY(project) REFERENCES projects(id)
    );
    CREATE INDEX IF NOT EXISTS idx_checkpoints_project ON checkpoints(project,created_at);
    CREATE TABLE IF NOT EXISTS usage (
      id TEXT PRIMARY KEY, project TEXT NOT NULL, task_id TEXT NOT NULL,
      run_id TEXT NOT NULL, provider TEXT NOT NULL, model TEXT NOT NULL,
      module TEXT NOT NULL, input_uncached INTEGER NOT NULL,
      cache_read INTEGER NOT NULL, cache_write INTEGER NOT NULL,
      output_tokens INTEGER NOT NULL, billed_usd REAL,
      elapsed_ms INTEGER, quality_pass INTEGER, retries INTEGER NOT NULL,
      created_at TEXT NOT NULL, source TEXT NOT NULL,
      FOREIGN KEY(project) REFERENCES projects(id)
    );
    CREATE INDEX IF NOT EXISTS idx_usage_project_task ON usage(project,task_id,run_id);
    CREATE TABLE IF NOT EXISTS graph_outbox (
      id TEXT PRIMARY KEY, project TEXT NOT NULL, event_id TEXT NOT NULL,
      status TEXT NOT NULL, enqueued_at TEXT NOT NULL,
      FOREIGN KEY(project) REFERENCES projects(id),
      FOREIGN KEY(event_id) REFERENCES events(id),
      UNIQUE(project,event_id)
    );
        """)
        if os.name != "nt":
            path.chmod(0o600)
        return c
    except BaseException:
        c.close()
        raise


def ensure_project(c, project: str):
    validate_id(project, "project")
    c.execute("INSERT OR IGNORE INTO projects VALUES (?,?)", (project, utcnow()))


def add_event(c, project, kind, title, body, session_id=None, source_refs=None, graph=False):
    ensure_project(c, project)
    if kind not in {"decision", "verified", "observation", "hypothesis", "change", "error", "note"}:
        raise ValueError("Unsupported event kind")
    if not isinstance(title, str) or not title.strip() or len(title) > 400:
        raise ValueError("Event title must be nonempty and <= 400 characters")
    if not isinstance(body, str) or not body.strip() or len(body) > 40000:
        raise ValueError("Event body must be nonempty and <= 40000 characters")
    if session_id: validate_id(session_id, "session")
    refs = source_refs or []
    if not isinstance(refs, list) or any(not isinstance(x, str) or len(x)>250 for x in refs):
        raise ValueError("source_refs must be string array")
    for ref in refs:
        # Unknown external document IDs are permitted, but local src IDs must exist in project.
        if ref.startswith("src:"):
            sid = ref[4:]
            if not c.execute("SELECT 1 FROM sources WHERE project=? AND id=?", (project, sid)).fetchone():
                raise ValueError(f"Unknown project source reference: {ref}")
    eid, now = str(uuid.uuid4()), utcnow()
    signature = {"project":project,"kind":kind,"title":title,"body":body,"session_id":session_id,"source_refs":refs,"created_at":now}
    digest = sha256_text(canonical_json(signature))
    c.execute("INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?,?)", (eid,project,session_id,kind,title,body,canonical_json(refs),now,now,digest))
    if graph:
        c.execute("INSERT INTO graph_outbox VALUES (?,?,?,?,?)", (str(uuid.uuid4()),project,eid,"pending",now))
    return {"id":eid,"project":project,"sha256":digest,"queued_for_graphiti":graph}


def set_constraint(c, project, key, text, source_ref, status):
    ensure_project(c,project); validate_id(key, "constraint key")
    if status not in ("active", "revoked"):
        raise ValueError("status must be active/revoked")
    if not isinstance(text,str) or not text.strip() or len(text)>10000:
        raise ValueError("constraint text must be 1-10000 characters")
    if not isinstance(source_ref,str) or not source_ref.strip():
        raise ValueError("source reference required for constraint")
    prev=c.execute("SELECT revision FROM constraints_state WHERE project=? AND key=?",(project,key)).fetchone()
    rev=(prev[0] if prev else 0)+1
    now=utcnow()
    signature={"project":project,"key":key,"revision":rev,"text":text,"source_ref":source_ref,"status":status,"changed_at":now}
    sha=sha256_text(canonical_json(signature))
    c.execute("INSERT INTO constraint_history VALUES (?,?,?,?,?,?,?,?,?)",(str(uuid.uuid4()),project,key,rev,status,text,source_ref,now,sha))
    c.execute("INSERT INTO constraints_state VALUES (?,?,?,?,?,?,?) ON CONFLICT(project,key) DO UPDATE SET revision=excluded.revision,status=excluded.status,text=excluded.text,source_ref=excluded.source_ref,updated_at=excluded.updated_at",(project,key,rev,status,text,source_ref,now))
    return {"key":key,"revision":rev,"status":status,"sha256":sha}


def active_constraints(c,project):
    validate_id(project,"project")
    return [dict(x) for x in c.execute("SELECT key,revision,text,source_ref FROM constraints_state WHERE project=? AND status='active' ORDER BY key",(project,))]


def register_source(c, project, path, note="", hash_file=False):
    ensure_project(c,project)
    p=Path(path).expanduser().resolve()
    digest=None;size=None
    if hash_file:
        if not p.is_file(): raise FileNotFoundError(f"Source file does not exist: {p}")
        h=hashlib.sha256()
        with p.open("rb") as f:
            for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
        digest=h.hexdigest();size=p.stat().st_size
    sid=str(uuid.uuid4())
    c.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?)",(sid,project,str(p),digest,size,note,utcnow()))
    return {"id":sid,"path":str(p),"sha256":digest,"hashed":hash_file}


def verify_source(c, project, source_id):
    """Compare a registered file's current bytes with its optional stored digest."""
    validate_id(project, "project")
    row=c.execute("SELECT path,file_sha256 FROM sources WHERE project=? AND id=?",(project,source_id)).fetchone()
    if not row:
        raise ValueError("Source not found in project")
    if row["file_sha256"] is None:
        return {"id":source_id,"status":"unhashed","path":row["path"],"expected_sha256":None,"actual_sha256":None}
    p=Path(row["path"])
    if not p.is_file():
        return {"id":source_id,"status":"missing","path":row["path"],"expected_sha256":row["file_sha256"],"actual_sha256":None}
    h=hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
    actual=h.hexdigest()
    return {"id":source_id,"status":"verified" if actual==row["file_sha256"] else "changed","path":row["path"],"expected_sha256":row["file_sha256"],"actual_sha256":actual}


def create_checkpoint(c, obj):
    for key in ("project","session_id","objective","next_action"):
        if not isinstance(obj.get(key),str) or not obj[key].strip():raise ValueError(f"Missing {key}")
    project=validate_id(obj["project"],"project");session=validate_id(obj["session_id"],"session")
    ensure_project(c,project)
    for key in ("done","decisions","pending","source_refs","event_ids"):
        val=obj.get(key,[])
        if not isinstance(val,list) or not all(isinstance(x,str) and len(x)<=1000 for x in val):
            raise ValueError(f"{key} must be an array of strings <= 1000 chars each")
    for eid in obj.get("event_ids",[]):
        if not c.execute("SELECT 1 FROM events WHERE project=? AND id=?",(project,eid)).fetchone():
            raise ValueError(f"Event outside project or not found: {eid}")
    for ref in obj.get("source_refs",[]):
        if ref.startswith("src:") and not c.execute("SELECT 1 FROM sources WHERE project=? AND id=?",(project,ref[4:])).fetchone():
            raise ValueError(f"Source outside project or not found: {ref}")
    signature={"project":project,"session_id":session,"objective":obj["objective"],
               "done":obj.get("done",[]),"decisions":obj.get("decisions",[]),"pending":obj.get("pending",[]),
               "next_action":obj["next_action"],"git_commit":obj.get("git_commit"),
               "source_refs":obj.get("source_refs",[]),"event_ids":obj.get("event_ids",[])}
    digest=sha256_text(canonical_json(signature)); now=utcnow();cid=str(uuid.uuid4())
    c.execute("INSERT INTO checkpoints VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",(cid,project,session, obj["objective"], canonical_json(obj.get("done",[])),canonical_json(obj.get("decisions",[])),canonical_json(obj.get("pending",[])),obj["next_action"],obj.get("git_commit"),canonical_json(obj.get("source_refs",[])),canonical_json(obj.get("event_ids",[])),now,digest))
    return {"id":cid,"project":project,"session_id":session,"sha256":digest,"created_at":now}


def latest_checkpoint(c,project):
    validate_id(project,"project")
    row=c.execute("SELECT * FROM checkpoints WHERE project=? ORDER BY created_at DESC,rowid DESC LIMIT 1",(project,)).fetchone()
    return dict(row) if row else None


def checkpoint_dict(row):
    if row is None:return None
    result=dict(row)
    for k in ("done","decisions","pending","source_refs","event_ids"):
        result[k]=json.loads(result[k])
    return result


def verify_checkpoint(row):
    """Validate stored checkpoint payload; tolerate v1.0.1 hashes of omitted empty arrays."""
    cp=checkpoint_dict(row)
    if cp is None:return False
    keys=("project","session_id","objective","done","decisions","pending","next_action","git_commit","source_refs","event_ids")
    signature={k:cp[k] for k in keys}
    if sha256_text(canonical_json(signature))==cp["record_sha256"]:return True
    # v1.0.1 originally hashed omitted list fields as null while storing them as [].
    empty_lists=[k for k in ("done","decisions","pending","source_refs","event_ids") if cp[k]==[]]
    for mask in range(1,1<<len(empty_lists)):
        legacy=dict(signature)
        for i,key in enumerate(empty_lists):
            if mask & (1<<i):legacy[key]=None
        if sha256_text(canonical_json(legacy))==cp["record_sha256"]:return True
    return False


def search(c,project,query,limit=10):
    validate_id(project,"project");limit=max(1,min(int(limit),100))
    terms=[t.casefold() for t in (query or "").split() if t][:15]
    rows=c.execute("SELECT id,session_id,kind,title,body,created_at,source_refs,record_sha256 FROM events WHERE project=? ORDER BY created_at DESC,rowid DESC LIMIT 10000",(project,)).fetchall()
    results=[]
    for r in rows:
        item=dict(r);contents=(item["title"]+" "+item["body"]).casefold()
        score=sum(contents.count(t) for t in terms)
        if terms and score<=0:continue
        item["score"]=score
        # Search gives excerpts by default; show-event can fetch full content.
        item["body_excerpt"]=item.pop("body")[:400]
        item["source_refs"]=json.loads(item["source_refs"])
        results.append(item)
    results.sort(key=lambda x:(x["score"],x["created_at"]),reverse=True)
    return results[:limit]


def usage_add(c,obj):
    for key in ("project","task_id","run_id"):
        validate_id(obj.get(key),key)
    project=obj["project"];ensure_project(c,project)
    for key in ("provider","model","module"):
        if not isinstance(obj.get(key),str) or not obj[key].strip() or len(obj[key])>100:
            raise ValueError(f"Missing or invalid {key}")
    for key in ("input_uncached","cache_read","cache_write","output_tokens","retries"):
        val=obj.get(key,0)
        if not isinstance(val,int) or isinstance(val,bool) or val<0:
            raise ValueError(f"{key} must be nonnegative integer")
    quality=obj.get("quality_pass")
    if quality is not None and not isinstance(quality,bool):raise ValueError("quality_pass must be true/false/null")
    price=obj.get("billed_usd")
    if price is not None and (not isinstance(price,(int,float)) or isinstance(price,bool) or price<0 or price==float("inf") or price!=price):
        raise ValueError("billed_usd must be a finite nonnegative number or null")
    elapsed=obj.get("elapsed_ms")
    if elapsed is not None and (not isinstance(elapsed,int) or elapsed<0):raise ValueError("elapsed_ms must be >= 0 or null")
    rid=str(uuid.uuid4())
    c.execute("INSERT INTO usage VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(rid,project,obj["task_id"],obj["run_id"],obj["provider"],obj["model"],obj["module"],obj.get("input_uncached",0),obj.get("cache_read",0),obj.get("cache_write",0),obj.get("output_tokens",0),float(price) if price is not None else None,elapsed, None if quality is None else int(quality),obj.get("retries",0),utcnow(),obj.get("source","provider")))
    return {"id":rid,"task_id":obj["task_id"],"run_id":obj["run_id"]}


def project_usage(c,project):
    validate_id(project,"project")
    row=c.execute("SELECT COUNT(*) calls, SUM(input_uncached) input_uncached, SUM(cache_read) cache_read, SUM(cache_write) cache_write, SUM(output_tokens) output_tokens, SUM(CASE WHEN billed_usd IS NOT NULL THEN billed_usd ELSE 0 END) recorded_usd, SUM(CASE WHEN billed_usd IS NULL THEN 1 ELSE 0 END) unknown_cost_calls, SUM(retries) retries FROM usage WHERE project=?",(project,)).fetchone()
    return dict(row)
