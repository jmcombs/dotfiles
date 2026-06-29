export function mergeIntervals(intervals: [number, number][]): [number, number][] {
  if (intervals.length === 0) return [];
  const s = [...intervals].sort((a,b)=>a[0]-b[0]);
  const out: [number,number][] = [s[0].slice() as [number,number]];
  for (let i=1;i<s.length;i++){ const cur=out[out.length-1]; if (s[i][0]<=cur[1]) cur[1]=Math.max(cur[1],s[i][1]); else out.push(s[i].slice() as [number,number]); }
  return out;
}
