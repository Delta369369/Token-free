"""ADON Context Efficiency Core command-line interface."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

from .store import (DEFAULT_DB,connect,ensure_project,add_event,set_constraint,active_constraints,
                    register_source,create_checkpoint,latest_checkpoint,checkpoint_dict,search,usage_add,project_usage,json_load)
from .render import render_checkpoint
from .policy import benchmark,context_decision,model_route


def emit(obj):print(json.dumps(obj,ensure_ascii=False,indent=2))

def main(argv=None):
    p=argparse.ArgumentParser(prog="adon-context",description="ADON Context Efficiency Core v1.0.1 (local, offline-first)")
    p.add_argument("--db",default=str(DEFAULT_DB),help="SQLite file; default ~/.adon-context/context.sqlite3")
    sub=p.add_subparsers(dest="cmd",required=True)
    a=sub.add_parser("init");a.add_argument("--project",required=True)
    a=sub.add_parser("event-add");a.add_argument("--project",required=True);a.add_argument("--kind",required=True,choices=["decision","verified","observation","hypothesis","change","error","note"]);a.add_argument("--title",required=True);a.add_argument("--body",required=True);a.add_argument("--session");a.add_argument("--source-ref",action="append",default=[]);a.add_argument("--queue-graphiti",action="store_true")
    a=sub.add_parser("constraint-set");a.add_argument("--project",required=True);a.add_argument("--key",required=True);a.add_argument("--text",required=True);a.add_argument("--source-ref",required=True);a.add_argument("--status",choices=["active","revoked"],default="active")
    a=sub.add_parser("constraints");a.add_argument("--project",required=True)
    a=sub.add_parser("source-add");a.add_argument("--project",required=True);a.add_argument("--path",required=True);a.add_argument("--note",default="");a.add_argument("--hash-file",action="store_true")
    a=sub.add_parser("source-verify");a.add_argument("--project",required=True);a.add_argument("--id",required=True)
    a=sub.add_parser("checkpoint-save");a.add_argument("--file",required=True)
    a=sub.add_parser("checkpoint-show");a.add_argument("--project",required=True)
    a=sub.add_parser("restore");a.add_argument("--project",required=True);a.add_argument("--out");a.add_argument("--max-chars",type=int,default=8500)
    a=sub.add_parser("search");a.add_argument("--project",required=True);a.add_argument("--query",default="");a.add_argument("--limit",type=int,default=10)
    a=sub.add_parser("event-show");a.add_argument("--project",required=True);a.add_argument("--id",required=True)
    a=sub.add_parser("usage-add");a.add_argument("--file",required=True)
    a=sub.add_parser("usage-stats");a.add_argument("--project",required=True)
    a=sub.add_parser("benchmark");a.add_argument("--file",required=True)
    a=sub.add_parser("policy-context");a.add_argument("--file",required=True)
    a=sub.add_parser("policy-route");a.add_argument("--file",required=True)
    a=sub.add_parser("graphiti-pending");a.add_argument("--project",required=True)
    args=p.parse_args(argv)
    try:
        if args.cmd in {"benchmark","policy-context","policy-route"}:
            data=json_load(args.file)
            emit({"benchmark":benchmark,"policy-context":context_decision,"policy-route":model_route}[args.cmd](data));return 0
        with connect(args.db) as c:
            if args.cmd=="init":ensure_project(c,args.project);emit({"project":args.project,"db":str(Path(args.db).expanduser())})
            elif args.cmd=="event-add":emit(add_event(c,args.project,args.kind,args.title,args.body,args.session,args.source_ref,args.queue_graphiti))
            elif args.cmd=="constraint-set":emit(set_constraint(c,args.project,args.key,args.text,args.source_ref,args.status))
            elif args.cmd=="constraints":emit(active_constraints(c,args.project))
            elif args.cmd=="source-add":emit(register_source(c,args.project,args.path,args.note,args.hash_file))
            elif args.cmd=="source-verify":
                from .store import verify_source
                result=verify_source(c,args.project,args.id);emit(result)
                if result["status"]!="verified":return 2
            elif args.cmd=="checkpoint-save":emit(create_checkpoint(c,json_load(args.file)))
            elif args.cmd=="checkpoint-show":emit(checkpoint_dict(latest_checkpoint(c,args.project)))
            elif args.cmd=="restore":
                text=render_checkpoint(c,latest_checkpoint(c,args.project),args.max_chars)
                if args.out:
                    target=Path(args.out).expanduser()
                    target.parent.mkdir(parents=True,exist_ok=True)
                    target.write_text(text,encoding="utf-8")
                    emit({"written":str(target),"characters":len(text),"token_estimate_chars_over_4":round(len(text)/4)})
                else:print(text,end="")
            elif args.cmd=="search":emit(search(c,args.project,args.query,args.limit))
            elif args.cmd=="event-show":
                row=c.execute("SELECT * FROM events WHERE project=? AND id=?",(args.project,args.id)).fetchone()
                if not row:raise ValueError("Event not found in project")
                v=dict(row);v["source_refs"]=json.loads(v["source_refs"]);emit(v)
            elif args.cmd=="usage-add":emit(usage_add(c,json_load(args.file)))
            elif args.cmd=="usage-stats":emit(project_usage(c,args.project))
            elif args.cmd=="graphiti-pending":
                from .store import validate_id
                validate_id(args.project,"project")
                emit([dict(r) for r in c.execute("SELECT o.id,o.event_id,o.status,e.kind,e.title,e.body,e.source_refs,e.created_at FROM graph_outbox o JOIN events e ON o.event_id=e.id AND o.project=e.project WHERE o.project=? AND o.status='pending' ORDER BY o.enqueued_at",(args.project,))])
        return 0
    except (ValueError,KeyError,FileNotFoundError,json.JSONDecodeError,PermissionError) as exc:
        print("ERROR:",exc,file=sys.stderr);return 2

if __name__=="__main__":sys.exit(main())
