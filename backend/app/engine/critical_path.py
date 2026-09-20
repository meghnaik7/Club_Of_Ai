from sqlalchemy.orm import Session
from typing import List, Dict, Any, Set
from app.models.task import Task, TaskStatus

def calculate_critical_path(db: Session, event_id: int) -> Dict[str, Any]:
    """
    Calculate the critical path for tasks in an event.
    For simplicity in this phase, we identify tasks that have no slack (e.g., they block other tasks and have approaching due dates).
    A full CPM would require duration estimation on each task. Here we use dependencies and due dates.
    """
    tasks = db.query(Task).filter(Task.event_id == event_id, Task.status != TaskStatus.DONE).all()
    
    if not tasks:
        return {"critical_path": [], "message": "No active tasks found for event."}

    # Build adjacency list
    adj: Dict[int, List[int]] = {t.id: [] for t in tasks}
    in_degree: Dict[int, int] = {t.id: 0 for t in tasks}
    
    for t in tasks:
        # tasks this task blocks (t is prerequisite)
        for dep in t.dependencies_in:
            if dep.dependent_task_id in adj:
                adj[t.id].append(dep.dependent_task_id)
                in_degree[dep.dependent_task_id] += 1

    # If there are no task dependencies, no critical path exists
    has_dependencies = any(len(edges) > 0 for edges in adj.values())
    if not has_dependencies:
        return {
            "critical_path_length": 0,
            "critical_path": [],
            "critical_task_ids": [],
            "critical_tasks": [],
            "message": "No task dependencies defined for this event."
        }

    # Find longest path (critical path) treating each task as weight 1, or weighted by priority/due date
    # Here we just do a simple longest path in DAG
    topo_order = []
    zero_in = [tid for tid, deg in in_degree.items() if deg == 0]
    
    # Simple topological sort
    temp_in = in_degree.copy()
    queue = zero_in.copy()
    while queue:
        curr = queue.pop(0)
        topo_order.append(curr)
        for nxt in adj[curr]:
            temp_in[nxt] -= 1
            if temp_in[nxt] == 0:
                queue.append(nxt)
                
    if len(topo_order) != len(tasks):
        return {"error": "Cycle detected in task dependencies"}
        
    # Longest path dynamic programming
    dist = {t.id: 1 for t in tasks}
    parent = {t.id: None for t in tasks}
    
    for u in topo_order:
        for v in adj[u]:
            if dist[u] + 1 > dist[v]:
                dist[v] = dist[u] + 1
                parent[v] = u
                
    if not dist:
        return {"critical_path": []}
        
    # find max dist
    max_node = max(dist, key=dist.get)
    
    # backtrack
    path = []
    curr = max_node
    while curr is not None:
        path.append(curr)
        curr = parent[curr]
        
    path.reverse()
    
    critical_tasks = [t for t in tasks if t.id in path]
    # sort by path order
    critical_tasks.sort(key=lambda t: path.index(t.id))
    
    return {
        "critical_path_length": len(path),
        "critical_task_ids": path,
        "critical_tasks": [{"id": t.id, "title": t.title, "due_date": t.due_date} for t in critical_tasks]
    }
