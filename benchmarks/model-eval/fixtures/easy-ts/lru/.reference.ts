export class LRUCache<K,V>{cap:number;m=new Map<K,V>();constructor(c:number){this.cap=c;}
get(k:K):V|undefined{if(!this.m.has(k))return undefined;const v=this.m.get(k)!;this.m.delete(k);this.m.set(k,v);return v;}
put(k:K,v:V):void{if(this.m.has(k))this.m.delete(k);this.m.set(k,v);if(this.m.size>this.cap)this.m.delete(this.m.keys().next().value as K);}}
