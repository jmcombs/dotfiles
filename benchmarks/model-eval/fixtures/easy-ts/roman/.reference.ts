const M:[number,string][]=[[1000,"M"],[900,"CM"],[500,"D"],[400,"CD"],[100,"C"],[90,"XC"],[50,"L"],[40,"XL"],[10,"X"],[9,"IX"],[5,"V"],[4,"IV"],[1,"I"]];
export function toRoman(n:number):string{let r="";for(const [v,s] of M){while(n>=v){r+=s;n-=v;}}return r;}
export function fromRoman(s:string):number{let n=0,i=0;for(const [v,sym] of M){while(s.startsWith(sym,i)){n+=v;i+=sym.length;}}return n;}
