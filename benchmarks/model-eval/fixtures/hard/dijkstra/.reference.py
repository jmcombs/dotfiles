import heapq
def shortest_path(n, edges, start, end):
    adj = [[] for _ in range(n)]
    for a,b,w in edges: adj[a].append((b,w)); adj[b].append((a,w))
    dist = [float("inf")]*n; dist[start]=0
    pq=[(0,start)]
    while pq:
        d,u=heapq.heappop(pq)
        if d>dist[u]: continue
        if u==end: return d
        for v,w in adj[u]:
            if d+w<dist[v]: dist[v]=d+w; heapq.heappush(pq,(d+w,v))
    return dist[end] if dist[end]!=float("inf") else -1
