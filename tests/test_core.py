import json
import hashlib
import tempfile
import unittest
from pathlib import Path

from adon_context.store import (connect, add_event, active_constraints, set_constraint,register_source,
                                create_checkpoint, latest_checkpoint, search, usage_add, project_usage,
                                verify_source, verify_checkpoint)
from adon_context.render import render_checkpoint
from adon_context.policy import benchmark, context_decision, model_route
from adon_context.store import canonical_json, sha256_text


class TestCore(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db=Path(self.tmp.name)/"hidden"/"state.sqlite3"

    def test_event_scoped(self):
        with connect(self.db) as c:
            a=add_event(c,"project-A","decision","A decision","Unique secret alpha", "session-one")
            add_event(c,"project-B","decision","B decision","Unique secret beta", "session-two")
            self.assertEqual(len(search(c,"project-A","alpha")),1)
            self.assertEqual(search(c,"project-B","alpha"),[])
            self.assertEqual(len(search(c,"project-A","")),1)
            self.assertIsNotNone(c.execute("SELECT record_sha256 FROM events WHERE id=?",(a['id'],)).fetchone())

    def test_constraint_revision(self):
        with connect(self.db) as c:
            a=set_constraint(c,"a","rule","must retain source","src:decision1","active")
            b=set_constraint(c,"a","rule","new rule","src:decision2","active")
            self.assertEqual((a['revision'],b['revision']),(1,2))
            self.assertEqual(len(active_constraints(c,"a")),1)
            set_constraint(c,"a","rule","revoked by operator","src:decision3","revoked")
            self.assertEqual(active_constraints(c,"a"),[])
            self.assertEqual(c.execute("SELECT COUNT(*) FROM constraint_history").fetchone()[0],3)

    def test_source_hash(self):
        f=Path(self.tmp.name)/"source files"/"source file.txt";f.parent.mkdir();f.write_text("original",encoding="utf-8")
        with connect(self.db) as c:
            a=register_source(c,"project-A",str(f),hash_file=True)
        self.assertEqual(a['sha256'],hashlib.sha256(b"original").hexdigest())
        with connect(self.db) as c:
            self.assertEqual(verify_source(c,"project-A",a['id'])['status'],'verified')
            f.write_text("changed",encoding="utf-8")
            self.assertEqual(verify_source(c,"project-A",a['id'])['status'],'changed')
            with self.assertRaisesRegex(ValueError,"not found in project"):
                verify_source(c,"project-B",a['id'])

    def test_checkpoint_and_restore(self):
        with connect(self.db) as c:
            src=register_source(c,"A",str(Path(self.tmp.name)/"x.txt"))
            evt=add_event(c,"A","verified","test","passed",source_refs=["src:"+src['id']])
            set_constraint(c,"A","never-drop","cite sources","policy:1","active")
            cp={"project":"A","session_id":"s1","objective":"Continue work","next_action":"Check code","done":["Test passed"],"decisions":[],"pending":[],"source_refs":["src:"+src['id']],"event_ids":[evt['id']]}
            res=create_checkpoint(c,cp)
            self.assertTrue(res['sha256'])
            raw=latest_checkpoint(c,"A")
            self.assertTrue(verify_checkpoint(raw))
            text=render_checkpoint(c,raw)
            self.assertIn("cite sources",text)
            self.assertIn(evt['id'],text)
            self.assertIn("Check code",text)
            with self.assertRaises(ValueError):render_checkpoint(c,latest_checkpoint(c,"A"),max_chars=200)

    def test_checkpoint_tampering_is_rejected(self):
        with connect(self.db) as c:
            create_checkpoint(c,{"project":"A","session_id":"s1","objective":"Original","next_action":"Continue"})
            c.execute("UPDATE checkpoints SET objective='Tampered' WHERE project='A'")
            raw=latest_checkpoint(c,"A")
            self.assertFalse(verify_checkpoint(raw))
            with self.assertRaisesRegex(ValueError,"integrity check failed"):
                render_checkpoint(c,raw)

    def test_legacy_checkpoint_hash_with_omitted_lists_is_accepted(self):
        with connect(self.db) as c:
            create_checkpoint(c,{"project":"A","session_id":"s1","objective":"Original","next_action":"Continue"})
            raw=latest_checkpoint(c,"A")
            signature={"project":"A","session_id":"s1","objective":"Original","done":None,"decisions":None,
                       "pending":None,"next_action":"Continue","git_commit":None,"source_refs":None,"event_ids":None}
            c.execute("UPDATE checkpoints SET record_sha256=? WHERE id=?",(sha256_text(canonical_json(signature)),raw['id']))
            self.assertTrue(verify_checkpoint(latest_checkpoint(c,"A")))

    def test_checkpoint_crossproject_reference_rejected(self):
        with connect(self.db) as c:
            evt=add_event(c,"A","verified","first","text")
            bad={"project":"B","session_id":"s1","objective":"abc","next_action":"next","event_ids":[evt['id']]}
            with self.assertRaises(ValueError):create_checkpoint(c,bad)

    def test_graph_outbox_optin(self):
        with connect(self.db) as c:
            a=add_event(c,"A","decision","one","do something",graph=True)
            add_event(c,"A","note","two","no graph")
            self.assertTrue(a['queued_for_graphiti'])
            self.assertEqual(c.execute("SELECT COUNT(*) FROM graph_outbox").fetchone()[0],1)

    def test_usage_unknown_preserved(self):
        obj={"project":"A","task_id":"t1","run_id":"r1","provider":"openai","model":"test","module":"handoff","input_uncached":100,"cache_read":20,"output_tokens":10,"quality_pass":True}
        with connect(self.db) as c:
            usage_add(c,obj)
            totals=project_usage(c,"A")
            self.assertEqual(totals['unknown_cost_calls'],1)
            self.assertEqual(totals['cache_read'],20)
            self.assertEqual(totals['recorded_usd'],0)

    def test_benchmark(self):
        data={"runs":[{"task_id":"a","variant":"baseline","input_uncached":100,"output_tokens":50,"quality_pass":True,"billed_usd":2},
                      {"task_id":"a","variant":"optimized","input_uncached":40,"cache_read":20,"output_tokens":30,"quality_pass":True,"billed_usd":1}]}
        r=benchmark(data)
        self.assertEqual(r['paired_tasks'],1)
        self.assertEqual(r['token_reduction_percent'],40.0)
        self.assertEqual(r['usd_reduction_percent'],50.0)
        self.assertTrue(r['all_runs_pass_quality'])
        data['runs'][1]['quality_pass']=False
        self.assertFalse(benchmark(data)['all_runs_pass_quality'])

    def test_policies(self):
        self.assertEqual(context_decision({"context_tokens":90,"context_window":100})['action'],'compact')
        self.assertEqual(context_decision({"context_tokens":20,"context_window":100,"stage_complete":True})['action'],'checkpoint')
        self.assertEqual(model_route({"kind":"file_hash"})['route'],'deterministic_local')
        self.assertEqual(model_route({"kind":"legal_analysis","contains_restricted_data":True,"external_processing_authorized":False})['route'],'local_only')


if __name__=='__main__':unittest.main()
