export function convert(num: string, fromBase: number, toBase: number): string {
  let v=0; for(const ch of num.toLowerCase()){ v=v*fromBase+parseInt(ch,36); }
  if(v===0) return "0";
  let out=""; const digits="0123456789abcdefghijklmnopqrstuvwxyz";
  while(v>0){ out=digits[v%toBase]+out; v=Math.floor(v/toBase); }
  return out;
}
