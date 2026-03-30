import { useState, useEffect, useCallback } from 'react'

let _show = () => {}

export function useToast() {
  const [toast, setToast] = useState(null)

  useEffect(() => {
    _show = (msg, type = 'success') => {
      setToast({ msg, type })
      setTimeout(() => setToast(null), 3500)
    }
    return () => { _show = () => {} }
  }, [])

  return toast
}

export function showToast(msg, type = 'success') {
  _show(msg, type)
}

export function Toast({ toast }) {
  if (!toast) return null
  return <div className={`toast ${toast.type}`}>{toast.msg}</div>
}
