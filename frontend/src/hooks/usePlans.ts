import { useCallback, useEffect, useState } from 'react'
import { api, ApiError } from '../api'
import type { PlanSummary } from '../types'

export function usePlans() {
  const [plans, setPlans] = useState<PlanSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const reload = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const response = await api.listPlans()
      setPlans(response.plans)
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? cause.message
          : 'Could not load lesson plans. Start the API with python app.py serve.',
      )
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void reload()
  }, [reload])

  return { plans, loading, error, reload }
}
