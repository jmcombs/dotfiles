export function flatten(arr: any[]): number[] {
  const out: number[]=[];
  for(const x of arr){ if(Array.isArray(x)) out.push(...flatten(x)); else out.push(x); }
  return out;
}
