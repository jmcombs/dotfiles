#!/usr/bin/env python3
"""Compute the full honest metric set from a llama-humaneval result JSON.
Usage: mlx_metrics.py <result.json> [<result.json> ...]
Reports: model, lang, n, pass/fail/timeout, clean pass@1, median tok/s,
aggregate tok/s, median+max completion tokens, cap-hits (>=8192)."""
import json, sys, statistics, os

def analyze(f):
    d = json.load(open(f))
    rows = d['results']['results']
    model = rows[0]['provider']['id'].split(':')[-1]
    lang = 'ts' if os.path.basename(f).startswith('ts') else 'py'
    npass=nfail=nto=cap=0
    tps=[]; toks=[]; agg_tok=0; agg_ms=0
    for s in rows:
        fr=s.get('failureReason',0)
        comp=(s.get('tokenUsage') or {}).get('completion',0)
        ms=s.get('latencyMs',0)
        if fr==2: nto+=1
        elif s.get('success'): npass+=1
        else: nfail+=1
        if comp>=8192: cap+=1
        if fr!=2 and comp>0 and ms>0:
            tps.append(comp/(ms/1000)); toks.append(comp)
            agg_tok+=comp; agg_ms+=ms
    p1=npass/(npass+nfail)*100 if (npass+nfail) else 0
    med=statistics.median(tps) if tps else 0
    agg=agg_tok/(agg_ms/1000) if agg_ms else 0
    return dict(model=model,lang=lang,n=len(rows),npass=npass,nfail=nfail,nto=nto,
                cap=cap,p1=p1,med=med,agg=agg,
                medtok=statistics.median(toks) if toks else 0,
                maxtok=max(toks) if toks else 0,
                walls=agg_ms/1000)

if __name__=='__main__':
    print(f"{'model':<30}{'lang':<5}{'n':>4}{'pass':>5}{'fail':>5}{'to':>4}{'cap':>4}{'pass@1':>8}{'medTPS':>8}{'aggTPS':>8}{'medTok':>8}{'maxTok':>8}{'wall_s':>9}")
    print('-'*107)
    for f in sys.argv[1:]:
        r=analyze(f)
        print(f"{r['model']:<30}{r['lang']:<5}{r['n']:>4}{r['npass']:>5}{r['nfail']:>5}{r['nto']:>4}{r['cap']:>4}{r['p1']:>7.1f}%{r['med']:>8.1f}{r['agg']:>8.1f}{r['medtok']:>8.0f}{r['maxtok']:>8.0f}{r['walls']:>9.0f}")
