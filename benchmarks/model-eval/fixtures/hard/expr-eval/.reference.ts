export function evaluate(expr: string): number {
  let i=0; const s=expr.replace(/\s+/g,"");
  function parseExpr(): number { let v=parseTerm(); while(s[i]==="+"||s[i]==="-"){ const op=s[i++]; const t=parseTerm(); v=op==="+"?v+t:v-t; } return v; }
  function parseTerm(): number { let v=parseFactor(); while(s[i]==="*"||s[i]==="/"){ const op=s[i++]; const f=parseFactor(); v=op==="*"?v*f:v/f; } return v; }
  function parseFactor(): number { if(s[i]==="-"){ i++; return -parseFactor(); } if(s[i]==="("){ i++; const v=parseExpr(); i++; return v; } let j=i; while(j<s.length&&/[0-9.]/.test(s[j])) j++; const n=parseFloat(s.slice(i,j)); i=j; return n; }
  return parseExpr();
}
