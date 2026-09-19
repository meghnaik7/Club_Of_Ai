"""
Dependency & Critical Path Guardrails (24, 25):
- Prevents circular task dependencies (DAG cycle check)
- Detects prerequisite date conflicts (e.g. prerequisite due after dependent)
- Protects critical path calculations from LLM hallucination by computing deterministically
"""
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict, deque
from sqlalchemy.orm import Session

from app.models.task import Task, TaskDependency

class DependencyCycleError(ValueError):
    """Raised when a dependency would form a cycle in the task graph."""
    pass

class DependencyConflictError(ValueError):
    """Raised when dependency dates or constraints are impossible."""
    pass

DependencyError = DependencyConflictError
CycleDetectedError = DependencyCycleError

class DependencyGuard:
    @classmethod
    def validate_dependency_link(cls, db: Session, task_id: int, depends_on_id: int) -> bool:
        if task_id == depends_on_id:
            raise DependencyError(f"Self-dependency detected: Task {task_id} cannot depend on itself.")
        
        t1 = db.query(Task).filter(Task.id == task_id).first()
        t2 = db.query(Task).filter(Task.id == depends_on_id).first()
        if not t1:
            raise DependencyError(f"Task {task_id} not found.")
        if not t2:
            raise DependencyError(f"Prerequisite task {depends_on_id} not found.")
        return True

    @classmethod
    def detect_cycles(cls, graph: Dict[int, List[int]]) -> None:
        """Topological sort cycle detection."""
        in_degree = {u: 0 for u in graph}
        for u in graph:
            for v in graph[u]:
                in_degree[v] = in_degree.get(v, 0) + 1
        
        queue = deque([u for u, deg in in_degree.items() if deg == 0])
        visited_count = 0
        while queue:
            node = queue.popleft()
            visited_count += 1
            for neighbor in graph.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        if visited_count < len(in_degree):
            raise CycleDetectedError("Circular dependency cycle detected in task graph.")

    @classmethod
    def check_cycle_addition(
        cls,
        existing_dependencies: List[Tuple[int, int]], # list of (prerequisite_task_id, dependent_task_id)

        new_prerequisite_id: int,
        new_dependent_id: int
    ) -> bool:
        """
        Guardrail 24: Verifies adding edge (new_prerequisite_id -> new_dependent_id) creates NO cycle.
        If new_dependent_id can reach new_prerequisite_id through existing edges, then adding
        new_prerequisite_id -> new_dependent_id would complete a cycle.
        """
        if new_prerequisite_id == new_dependent_id:
            raise DependencyCycleError(
                f"Self-dependency detected: Task {new_prerequisite_id} cannot depend on itself."
            )

        # Build adjacency graph: prerequisite -> list of dependents
        graph = defaultdict(list)
        for prereq, dep in existing_dependencies:
            graph[prereq].append(dep)

        # BFS from new_dependent_id to see if we can reach new_prerequisite_id
        visited = set()
        queue = deque([new_dependent_id])

        while queue:
            current = queue.popleft()
            if current == new_prerequisite_id:
                raise DependencyCycleError(
                    f"Circular dependency cycle detected! Adding dependency ({new_prerequisite_id} -> {new_dependent_id}) "
                    f"creates an invalid cycle in the task graph."
                )
            if current not in visited:
                visited.add(current)
                for neighbor in graph[current]:
                    if neighbor not in visited:
                        queue.append(neighbor)

        return True

    @classmethod
    def validate_dependency_dates(
        cls,
        prereq_due_date: Optional[str],
        dep_due_date: Optional[str],
        prereq_id: int,
        dep_id: int
    ) -> None:
        """
        Ensures prerequisite task is not scheduled to complete AFTER the dependent task.
        """
        from app.guardrails.date_guard import DateGuard
        p_due = DateGuard.parse_datetime(prereq_due_date)
        d_due = DateGuard.parse_datetime(dep_due_date)

        if p_due and d_due:
            if p_due > d_due:
                raise DependencyConflictError(
                    f"Dependency scheduling conflict: Prerequisite Task #{prereq_id} is due on {p_due.date()}, "
                    f"which is after Dependent Task #{dep_id} due on {d_due.date()}."
                )

    @classmethod
    def compute_deterministic_critical_path(
        cls,
        tasks: List[Dict], # list of task dicts: id, duration_days, prerequisites
    ) -> Dict[str, any]:
        """
        Guardrail 25: Critical Path Guardrail.
        Deterministic CPM (Critical Path Method) implementation.
        Never allows LLM to guess or fabricate critical path.
        """
        task_map = {t["id"]: t for t in tasks}
        durations = {t["id"]: max(1, t.get("duration_days", 1)) for t in tasks}
        
        # Build DAG
        adj = defaultdict(list)
        in_degree = {t["id"]: 0 for t in tasks}
        prereqs = {t["id"]: t.get("prerequisites", []) for t in tasks}

        for t_id, p_list in prereqs.items():
            for p in p_list:
                if p in in_degree:
                    adj[p].append(t_id)
                    in_degree[t_id] += 1

        # Topological sort (Kahn's algorithm)
        zero_in = deque([t_id for t_id, deg in in_degree.items() if deg == 0])
        topo_order = []
        while zero_in:
            node = zero_in.popleft()
            topo_order.append(node)
            for nxt in adj[node]:
                in_degree[nxt] -= 1
                if in_degree[nxt] == 0:
                    zero_in.append(nxt)

        if len(topo_order) < len(tasks):
            raise DependencyCycleError("Cannot compute critical path: Circular dependencies exist in task list.")

        # Forward pass: Early Start (ES) and Early Finish (EF)
        es = {t_id: 0 for t_id in topo_order}
        ef = {t_id: durations[t_id] for t_id in topo_order}

        for node in topo_order:
            for nxt in adj[node]:
                if ef[node] > es[nxt]:
                    es[nxt] = ef[node]
                    ef[nxt] = es[nxt] + durations[nxt]

        max_project_days = max(ef.values()) if ef else 0

        # Backward pass: Late Finish (LF) and Late Start (LS)
        lf = {t_id: max_project_days for t_id in topo_order}
        ls = {t_id: max_project_days - durations[t_id] for t_id in topo_order}

        # Reverse topological order
        for node in reversed(topo_order):
            for nxt in adj[node]:
                if ls[nxt] < lf[node]:
                    lf[node] = ls[nxt]
                    ls[node] = lf[node] - durations[node]

        # Slack and Critical Path
        slack = {t_id: ls[t_id] - es[t_id] for t_id in topo_order}
        critical_tasks = [t_id for t_id in topo_order if slack[t_id] == 0]

        return {
            "total_project_days": max_project_days,
            "critical_path_task_ids": critical_tasks,
            "slacks": slack,
            "early_finish": ef,
            "late_finish": lf
        }
