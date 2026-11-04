import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class TestCLI(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="adon context ");self.addCleanup(self.temp.cleanup)
        self.db=Path(self.temp.name)/"project.db"

    def run_cli(self,*args,expected=0):
        p=subprocess.run([sys.executable,"-m","adon_context","--db",str(self.db),*args],cwd=ROOT,capture_output=True,text=True,timeout=15)
        self.assertEqual(p.returncode,expected,p.stdout+"\n"+p.stderr)
        return p.stdout

    def test_round_trip_and_search(self):
        self.run_cli("init","--project","adon-ai")
        self.run_cli("constraint-set","--project","adon-ai","--key","source-integrity","--text","Do not drop citations","--source-ref","decision:source-1")
        event=json.loads(self.run_cli("event-add","--project","adon-ai","--kind","decision","--title","Source integrity","--body","Keep every citation","--session","s-test"))
        results=json.loads(self.run_cli("search","--project","adon-ai","--query","citation"))
        self.assertEqual(results[0]['id'],event['id'])
        cp={"project":"adon-ai","session_id":"s-test","objective":"Finish implementation","next_action":"Run tests","done":["Checked CLI"],"decisions":["Keep cited source"],"pending":[],"source_refs":["decision:source-1"],"event_ids":[event['id']]}
        cpfile=Path(self.temp.name)/"cp.json";cpfile.write_text(json.dumps(cp))
        self.run_cli("checkpoint-save","--file",str(cpfile))
        output=Path(self.temp.name)/"CHECKPOINT.md"
        self.run_cli("restore","--project","adon-ai","--out",str(output))
        text=output.read_text()
        self.assertIn("Do not drop citations",text)
        self.assertIn(event['id'],text)
        self.assertIn("Run tests",text)
        self.assertEqual(json.loads(self.run_cli("search","--project","other","--query","citation")),[])

    def test_synthetic_benchmark(self):
        stdout=self.run_cli("benchmark","--file",str(ROOT/"examples"/"benchmark.synthetic.json"))
        result=json.loads(stdout)
        self.assertEqual(result['paired_tasks'],2)
        self.assertTrue(result['all_runs_pass_quality'])

    def test_full_offline_workflow_across_processes(self):
        self.run_cli("init","--project","adon-local")
        event=json.loads(self.run_cli("event-add","--project","adon-local","--kind","decision","--title","Offline decision","--body","Keep the source and its digest","--session","session-full","--queue-graphiti"))
        constraint=json.loads(self.run_cli("constraint-set","--project","adon-local","--key","retain-source","--text","Keep source references","--source-ref","decision:001"))
        self.assertEqual(constraint['revision'],1)
        self.assertEqual(len(json.loads(self.run_cli("constraints","--project","adon-local"))),1)
        source=Path(self.temp.name)/"source files"/"file with spaces.txt";source.parent.mkdir();source.write_text("original bytes",encoding="utf-8")
        registered=json.loads(self.run_cli("source-add","--project","adon-local","--path",str(source),"--hash-file"))
        self.assertEqual(json.loads(self.run_cli("source-verify","--project","adon-local","--id",registered['id']))['status'],'verified')
        cp={"project":"adon-local","session_id":"session-full","objective":"Validate local workflow","next_action":"Review results","done":["Event persisted"],"decisions":["Offline only"],"pending":["None"],"source_refs":["src:"+registered['id']],"event_ids":[event['id']]}
        cpfile=Path(self.temp.name)/"checkpoint with spaces.json";cpfile.write_text(json.dumps(cp),encoding="utf-8")
        self.run_cli("checkpoint-save","--file",str(cpfile))
        saved=json.loads(self.run_cli("checkpoint-show","--project","adon-local"))
        self.assertEqual(saved['event_ids'],[event['id']])
        restored=Path(self.temp.name)/"restored checkpoint.md"
        self.run_cli("restore","--project","adon-local","--out",str(restored))
        self.assertIn("Keep source references",restored.read_text(encoding="utf-8"))
        self.assertEqual(json.loads(self.run_cli("search","--project","adon-local","--query","digest"))[0]['id'],event['id'])
        self.assertEqual(json.loads(self.run_cli("event-show","--project","adon-local","--id",event['id']))['id'],event['id'])
        self.assertEqual(json.loads(self.run_cli("search","--project","another-project","--query","digest")),[])
        self.run_cli("event-show","--project","another-project","--id",event['id'],expected=2)
        usage={"project":"adon-local","task_id":"task-1","run_id":"run-1","provider":"synthetic","model":"synthetic","module":"handoff","input_uncached":100,"cache_read":5,"output_tokens":20,"quality_pass":True}
        usagefile=Path(self.temp.name)/"usage.json";usagefile.write_text(json.dumps(usage),encoding="utf-8")
        self.run_cli("usage-add","--file",str(usagefile))
        self.assertEqual(json.loads(self.run_cli("usage-stats","--project","adon-local"))['unknown_cost_calls'],1)
        benchmarkfile=Path(self.temp.name)/"benchmark.json";benchmarkfile.write_text(json.dumps({"runs":[{"task_id":"synthetic-1","variant":"baseline","input_uncached":100,"quality_pass":True},{"task_id":"synthetic-1","variant":"optimized","input_uncached":50,"quality_pass":True}]}),encoding="utf-8")
        self.assertEqual(json.loads(self.run_cli("benchmark","--file",str(benchmarkfile)))['paired_tasks'],1)
        contextfile=Path(self.temp.name)/"context.json";contextfile.write_text(json.dumps({"context_tokens":90,"context_window":100}),encoding="utf-8")
        self.assertEqual(json.loads(self.run_cli("policy-context","--file",str(contextfile)))['action'],'compact')
        routefile=Path(self.temp.name)/"route.json";routefile.write_text(json.dumps({"kind":"file_hash"}),encoding="utf-8")
        self.assertEqual(json.loads(self.run_cli("policy-route","--file",str(routefile)))['route'],'deterministic_local')
        self.assertEqual(len(json.loads(self.run_cli("graphiti-pending","--project","adon-local"))),1)
        source.write_text("altered bytes",encoding="utf-8")
        self.run_cli("source-verify","--project","adon-local","--id",registered['id'],expected=2)

if __name__=='__main__':unittest.main()
