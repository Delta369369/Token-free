"""Deterministic, advisory-only context and routing policies. No auto-restarts or API calls."""
from __future__ import annotations


def context_decision(observed: dict) -> dict:
    """Decision is advisory; platform-native compaction takes precedence if imminent."""
    ctx = observed.get("context_tokens")
    window = observed.get("context_window")
    recent_cache = observed.get("cache_hit_percent")
    stage_complete = bool(observed.get("stage_complete", False))
    goal_change = bool(observed.get("goal_change", False))
    if ctx is None or window is None or window <= 0 or ctx < 0 or ctx > window:
        return {"action":"measure", "reason":"Context window and current token count required", "automatic":False}
    fraction=ctx/window
    if stage_complete or goal_change:
        return {"action":"checkpoint", "reason":"Natural boundary; preserve state and choose next session manually", "automatic":False}
    if fraction >= 0.88:
        return {"action":"compact", "reason":"Context nearing window; honor native platform limits", "automatic":False}
    if fraction >= 0.72 and (recent_cache is None or recent_cache < 60):
        return {"action":"checkpoint", "reason":"Large context and limited cache reuse; estimate re-entry cost", "automatic":False}
    return {"action":"continue", "reason":"No verified economic reason to reset context", "automatic":False}


def model_route(task: dict) -> dict:
    """Router returns a class of tool/model, never a fabricated concrete model ID."""
    if task.get("contains_restricted_data") and not task.get("external_processing_authorized"):
        return {"route":"local_only","reason":"External transmission not authorized","automatic":False}
    kind=task.get("kind","general")
    high=bool(task.get("critical")) or kind in {"legal_analysis","security_change","cross_module_refactor","evidence_exhaustive"}
    if kind in {"file_hash","exact_lookup","filter","format_validation","arithmetic"}:
        return {"route":"deterministic_local","reason":"No LLM necessary for this task class","automatic":False}
    if high:
        return {"route":"validated_high_capability","reason":"Critical work requires verified quality and source checks","automatic":False}
    if kind in {"labeling","formatting","simple_extraction"}:
        return {"route":"validated_economy_model","reason":"Economical model allowed only after task-specific quality testing","automatic":False}
    return {"route":"standard_validated_model","reason":"Default route; benchmark can justify downgrade","automatic":False}


def benchmark(data: dict) -> dict:
    """Compare paired, verified tasks; never present unknown cost as zero."""
    runs=data.get("runs")
    if not isinstance(runs,list):raise ValueError("runs must be an array")
    pairs={}
    token_fields=("input_uncached","cache_read","cache_write","output_tokens")
    for r in runs:
        task=r.get("task_id");variant=r.get("variant")
        if not isinstance(task,str) or not task or variant not in ("baseline","optimized"):
            raise ValueError("task_id and variant baseline/optimized required")
        for k in token_fields:
            val=r.get(k,0)
            if not isinstance(val,int) or isinstance(val,bool) or val<0:
                raise ValueError(f"Invalid token field: {k}")
        if r.get("quality_pass") not in (True,False):raise ValueError("Explicit quality_pass required")
        if variant in pairs.setdefault(task,{}):raise ValueError(f"Duplicate {task} / {variant}")
        pairs[task][variant]=r
    completed=[v for v in pairs.values() if set(v)=={"baseline","optimized"}]
    if not completed:raise ValueError("No paired tasks")
    def total(x):return sum(x.get(k,0) for k in token_fields)
    baseline_tokens=sum(total(p["baseline"]) for p in completed)
    optimized_tokens=sum(total(p["optimized"]) for p in completed)
    def dollars(variant):
        vals=[p[variant].get("billed_usd") for p in completed]
        if any(v is None for v in vals):return None
        if any(not isinstance(v,(int,float)) or v<0 for v in vals):raise ValueError("Invalid billed_usd")
        return round(sum(vals),6)
    base_usd=dollars("baseline");opt_usd=dollars("optimized")
    baseline_success=sum(p["baseline"]["quality_pass"] for p in completed)
    optimized_success=sum(p["optimized"]["quality_pass"] for p in completed)
    accepted=[p for p in completed if p["baseline"]["quality_pass"] and p["optimized"]["quality_pass"]]
    return {
       "paired_tasks":len(completed),"quality_pass_baseline":baseline_success,"quality_pass_optimized":optimized_success,
       "quality_pass_both":len(accepted), "all_runs_pass_quality":len(accepted)==len(completed),
       "baseline_total_tokens":baseline_tokens,"optimized_total_tokens":optimized_tokens,
       "token_reduction_percent":round(100*(baseline_tokens-optimized_tokens)/baseline_tokens,2) if baseline_tokens else None,
       "baseline_billed_usd":base_usd,"optimized_billed_usd":opt_usd,
       "usd_reduction_percent":round(100*(base_usd-opt_usd)/base_usd,2) if base_usd and opt_usd is not None else None,
       "accepted_task_token_savings_percent":round(100*(sum(total(p['baseline']) for p in accepted)-sum(total(p['optimized']) for p in accepted))/sum(total(p['baseline']) for p in accepted),2) if sum(total(p['baseline']) for p in accepted) else None,
       "caution":"Paired simulation or measured usage: check source field. Cached tokens count as tokens; dollar costs are separately supplied, not inferred. Regression invalidates a savings claim."
    }
