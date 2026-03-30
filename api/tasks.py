"""
tasks.py — Gestionnaire de tâches asynchrones
==============================================

POURQUOI ?
Le scoring d'une offre prend ~5-10s (appel API Claude).
Scorer 10 offres = 50-100s. On ne peut pas bloquer une
requête HTTP aussi longtemps (timeout navigateur, mauvaise UX).

SOLUTION : pattern "fire and forget" avec polling.
1. Le frontend POST /score/batch → reçoit un task_id en 200ms
2. Le backend lance le travail en BackgroundTask
3. Le frontend poll GET /tasks/{task_id} toutes les 2s
4. Quand status="done", le frontend récupère le résultat

LIMITATION :
Le store est en mémoire → perdu au redémarrage du serveur.
Pour de la production, on utiliserait Celery + Redis.
Pour ce projet, c'est suffisant.
"""

import uuid
import threading
from datetime import datetime
from typing import Any, Optional

from api.schemas import TaskStatus


class Task:
    """Une tâche asynchrone avec son état."""

    def __init__(self, task_type: str):
        self.id = str(uuid.uuid4())[:8]  # ID court et lisible
        self.type = task_type
        self.status = TaskStatus.PENDING
        self.progress: Optional[str] = None
        self.result: Optional[dict] = None
        self.error: Optional[str] = None
        self.created_at = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "task_id": self.id,
            "status": self.status.value,
            "progress": self.progress,
            "result": self.result,
            "error": self.error,
        }


class TaskManager:
    """
    Store de tâches en mémoire, thread-safe.

    Usage :
        task = task_manager.create("scoring")
        # ... dans un thread/BackgroundTask :
        task_manager.update(task.id, status="running", progress="2/5")
        task_manager.complete(task.id, result={...})
    """

    def __init__(self, max_tasks: int = 100):
        self._tasks: dict[str, Task] = {}
        self._lock = threading.Lock()
        self._max_tasks = max_tasks

    def create(self, task_type: str) -> Task:
        """Crée une nouvelle tâche et retourne son objet."""
        task = Task(task_type)
        with self._lock:
            # Nettoyage si trop de tâches stockées
            if len(self._tasks) >= self._max_tasks:
                self._cleanup()
            self._tasks[task.id] = task
        return task

    def get(self, task_id: str) -> Optional[Task]:
        """Récupère une tâche par son ID."""
        return self._tasks.get(task_id)

    def update(
        self,
        task_id: str,
        status: Optional[TaskStatus] = None,
        progress: Optional[str] = None,
    ):
        """Met à jour le statut/progression d'une tâche."""
        task = self._tasks.get(task_id)
        if task:
            with self._lock:
                if status:
                    task.status = status
                if progress is not None:
                    task.progress = progress

    def complete(self, task_id: str, result: dict):
        """Marque une tâche comme terminée avec son résultat."""
        task = self._tasks.get(task_id)
        if task:
            with self._lock:
                task.status = TaskStatus.DONE
                task.result = result

    def fail(self, task_id: str, error: str):
        """Marque une tâche comme échouée."""
        task = self._tasks.get(task_id)
        if task:
            with self._lock:
                task.status = TaskStatus.ERROR
                task.error = error

    def _cleanup(self):
        """Supprime les tâches terminées les plus anciennes."""
        terminées = [
            (tid, t) for tid, t in self._tasks.items()
            if t.status in (TaskStatus.DONE, TaskStatus.ERROR)
        ]
        terminées.sort(key=lambda x: x[1].created_at)
        # Supprimer la moitié des tâches terminées
        for tid, _ in terminées[:len(terminées) // 2]:
            del self._tasks[tid]


# Singleton — partagé entre toutes les routes
task_manager = TaskManager()
