export function parseCSV(text: string): string[][] {
  const rows: string[][]=[]; let row: string[]=[]; let field=""; let inq=false; let i=0;
  while(i<text.length){ const c=text[i];
    if(inq){ if(c==='"'){ if(text[i+1]==='"'){ field+='"'; i+=2; continue; } inq=false; i++; continue; } field+=c; i++; continue; }
    if(c==='"'){ inq=true; i++; continue; }
    if(c===","){ row.push(field); field=""; i++; continue; }
    if(c==="\n"){ row.push(field); rows.push(row); row=[]; field=""; i++; continue; }
    field+=c; i++;
  }
  row.push(field); rows.push(row); return rows;
}
