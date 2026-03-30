export default function TaskBar({ task }) {
  if (!task) return null
  const cls = task.status === 'done' ? 'done' : task.status === 'error' ? 'error' : ''
  return (
    <div className={`task-bar ${cls}`}>
      {task.status === 'running' || task.status === 'pending' ? (
        <div className="spinner" />
      ) : task.status === 'done' ? (
        <span>✅</span>
      ) : (
        <span>❌</span>
      )}
      <span className="progress-text">
        {task.status === 'done'
          ? `Terminé — ${task.result?.offres_scorees ?? task.result?.nombre_fichiers ?? 0} traité(s)`
          : task.status === 'error'
          ? `Erreur : ${task.error}`
          : task.progress || 'En attente...'}
      </span>
    </div>
  )
}
