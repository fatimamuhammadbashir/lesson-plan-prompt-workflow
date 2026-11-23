import { useCallback, useEffect, useState } from 'react'
import { api, ApiError } from '../api'
import type { Meta } from '../types'

export function useMeta() {
  const [meta, setMeta] = useState<Meta | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const reload = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setMeta(await api.meta())
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? cause.message
          : 'Could not load the curriculum. Start the API with python app.py serve.',
      )
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void reload()
  }, [reload])

  return { meta, loading, error, reload }
}
