import { ref } from 'vue'
import { triggerCompletion } from '../api'
import type { TargetEntity, CompletionResult, QualityCheck } from '../api/types'

export function useCompletion() {
  const completing = ref(false)
  const result = ref<CompletionResult | null>(null)
  const qualityCheck = ref<QualityCheck | null>(null)
  const error = ref<string | null>(null)

  async function triggerComplete(target: TargetEntity) {
    completing.value = true
    error.value = null
    result.value = null
    qualityCheck.value = null
    try {
      const res = await triggerCompletion(target)
      result.value = res.completion_result
      qualityCheck.value = res.quality_check
    } catch (e: any) {
      error.value = e.message || '补全失败'
      throw e
    } finally {
      completing.value = false
    }
  }

  function clearResult() {
    result.value = null
    qualityCheck.value = null
    error.value = null
  }

  return { completing, result, qualityCheck, error, triggerComplete, clearResult }
}
