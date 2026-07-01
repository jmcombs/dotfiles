export function topoSort(n: number, edges: [number, number][]): number[] | null {
  const adj: number[][]=Array.from({length:n},()=>[]); const indeg=new Array(n).fill(0);
  for(const [a,b] of edges){ adj[a].push(b); indeg[b]++; }
  const q:number[]=[]; for(let i=0;i<n;i++) if(indeg[i]===0) q.push(i);
  const out:number[]=[];
  while(q.length){ const u=q.shift()!; out.push(u); for(const v of adj[u]){ if(--indeg[v]===0) q.push(v); } }
  return out.length===n?out:null;
}
