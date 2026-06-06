<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { MessagePlugin } from 'tdesign-vue-next'
import { getConfig, updateConfig, getConfigDefaults } from '../api'
import type { PipelineConfig } from '../api/types'

const config = reactive<PipelineConfig>({
  thresholds: { auto_approve: 0.80, pending_review: 0.60 },
  models: { default: 'qwen-plus', auto_select: true, table_rich_threshold: 5 },
  retrieval: { milvus_top_k: 20, es_keyword_top_k: 20, es_siblings_top_k: 5, rrf_k: 60, rrf_top_n: 15, sample_boost: true },
  rules: {
    required_fields: { enabled: true },
    display_name_no_code: { enabled: true },
    description_not_copy_name: { enabled: true },
    sensitive_level_valid: { enabled: true },
    tag_no_duplicates: { enabled: true },
    business_domain_valid: { enabled: true },
    table_name_consistency: { enabled: true },
  },
})

const loading = ref(false)
const saving = ref(false)
const dirty = ref(false)

const modelOptions = [
  { label: 'qwen-plus', value: 'qwen-plus' },
  { label: 'qwen-max', value: 'qwen-max' },
  { label: 'qwen-turbo', value: 'qwen-turbo' },
]

const ruleMeta: Record<string, { label: string; severity: string; desc: string }> = {
  required_fields: { label: 'required_fields', severity: 'CRITICAL', desc: 'display_name 和 description 任一缺失直接拒绝' },
  display_name_no_code: { label: 'display_name_no_code', severity: 'WARNING', desc: '中文名不应包含大段英文字符' },
  description_not_copy_name: { label: 'description_not_copy_name', severity: 'WARNING', desc: '描述不应与中文名完全一致' },
  sensitive_level_valid: { label: 'sensitive_level_valid', severity: 'WARNING', desc: '敏感级别必须在 L1–L4 范围内' },
  tag_no_duplicates: { label: 'tag_no_duplicates', severity: 'INFO', desc: '标签列表不应包含重复项' },
  business_domain_valid: { label: 'business_domain_valid', severity: 'INFO', desc: '业务域名字符长度合理' },
  table_name_consistency: { label: 'table_name_consistency', severity: 'WARNING', desc: '中文名不应与英文表名完全相同' },
}

function severityTheme(severity: string): 'danger' | 'warning' | 'default' {
  if (severity === 'CRITICAL') return 'danger'
  if (severity === 'WARNING') return 'warning'
  return 'default'
}

function markDirty() { dirty.value = true }

onMounted(async () => {
  loading.value = true
  try {
    const res = await getConfig()
    if (res.success && res.data) {
      Object.assign(config, res.data)
    }
  } catch { /* use defaults */ }
  finally { loading.value = false }
})

async function handleSave() {
  saving.value = true
  try {
    const partial: Partial<PipelineConfig> = {
      thresholds: { ...config.thresholds },
      models: { ...config.models },
      retrieval: { ...config.retrieval },
      rules: { ...config.rules },
    }
    await updateConfig(partial)
    dirty.value = false
    MessagePlugin.success('配置已保存')
  } catch {
    MessagePlugin.error('保存失败')
  } finally { saving.value = false }
}

async function handleReset() {
  try {
    const res = await getConfigDefaults()
    if (res.success && res.data) {
      Object.assign(config, res.data)
      dirty.value = false
      MessagePlugin.success('已恢复默认配置')
    }
  } catch {
    MessagePlugin.error('恢复默认失败')
  }
}
</script>

<template>
  <div class="config-page">
    <div class="page-header">
      <h1>参数配置</h1>
      <p class="page-subtitle">管理 Pipeline 各阶段的运行参数，修改后立即生效</p>
    </div>

    <div v-if="loading" class="loading-state">
      <t-loading text="加载配置中..." />
    </div>

    <template v-else>
      <!-- 分流阈值 -->
      <section class="config-section">
        <h2>分流阈值</h2>
        <p class="section-desc">控制补全结果自动采纳 / 待审核 / 拒绝的置信度门槛</p>
        <div class="threshold-row">
          <div class="threshold-item">
            <div class="threshold-head">
              <label>自动采纳阈值</label>
              <span class="threshold-value">{{ (config.thresholds.auto_approve * 100).toFixed(0) }}%</span>
            </div>
            <t-slider
              :model-value="config.thresholds.auto_approve"
              :min="0.5" :max="1.0" :step="0.05"
              :marks="{ 0.5: '0.5', 0.6: '0.6', 0.7: '0.7', 0.8: '0.8', 0.9: '0.9', 1.0: '1.0' }"
              @change="(v: number) => { config.thresholds.auto_approve = v; markDirty() }"
            />
            <p class="threshold-hint">置信度 >= 该值且无 WARNING 时自动采纳</p>
          </div>
          <div class="threshold-item">
            <div class="threshold-head">
              <label>待审核阈值</label>
              <span class="threshold-value">{{ (config.thresholds.pending_review * 100).toFixed(0) }}%</span>
            </div>
            <t-slider
              :model-value="config.thresholds.pending_review"
              :min="0.2" :max="0.7" :step="0.05"
              :marks="{ 0.2: '0.2', 0.3: '0.3', 0.4: '0.4', 0.5: '0.5', 0.6: '0.6', 0.7: '0.7' }"
              @change="(v: number) => { config.thresholds.pending_review = v; markDirty() }"
            />
            <p class="threshold-hint">置信度 < 该值或有关键违规时直接拒绝；介于两阈值之间待审核</p>
          </div>
        </div>
      </section>

      <!-- 模型选择 -->
      <section class="config-section">
        <h2>模型选择</h2>
        <p class="section-desc">配置 LLM 生成阶段的模型策略</p>
        <div class="form-grid">
          <div class="form-item">
            <label>默认模型</label>
            <div class="filter-select-wrap">
              <select
                :value="config.models.default"
                class="filter-select"
                :class="{ active: true }"
                @change="config.models.default = ($event.target as HTMLSelectElement).value; markDirty()"
              >
                <option v-for="opt in modelOptions" :key="opt.value" :value="opt.value">
                  {{ opt.label }}
                </option>
              </select>
            </div>
          </div>
          <div class="form-item">
            <label>自动模型升级</label>
            <t-switch
              :value="config.models.auto_select"
              @change="(v: boolean) => { config.models.auto_select = v; markDirty() }"
            />
            <p class="threshold-hint">表上下文丰富时自动升级到更强模型</p>
          </div>
          <div class="form-item">
            <label>升级阈值</label>
            <t-input-number
              :value="config.models.table_rich_threshold"
              :min="1" :max="20" :step="1"
              style="width: 100px"
              @change="(v: number) => { config.models.table_rich_threshold = v; markDirty() }"
            />
            <p class="threshold-hint">表兄弟字段描述数超过此值时触发升级</p>
          </div>
        </div>
      </section>

      <!-- 检索参数 -->
      <section class="config-section">
        <h2>检索参数</h2>
        <p class="section-desc">控制 Stage 1 双路检索 (Milvus + ES) 的行为</p>
        <div class="form-grid">
          <div class="form-item">
            <label>Milvus Top-K</label>
            <t-input-number :value="config.retrieval.milvus_top_k" :min="5" :max="100" style="width: 100px"
              @change="(v: number) => { config.retrieval.milvus_top_k = v; markDirty() }" />
          </div>
          <div class="form-item">
            <label>ES 关键词 Top-K</label>
            <t-input-number :value="config.retrieval.es_keyword_top_k" :min="5" :max="100" style="width: 100px"
              @change="(v: number) => { config.retrieval.es_keyword_top_k = v; markDirty() }" />
          </div>
          <div class="form-item">
            <label>ES 兄弟字段数</label>
            <t-input-number :value="config.retrieval.es_siblings_top_k" :min="1" :max="50" style="width: 100px"
              @change="(v: number) => { config.retrieval.es_siblings_top_k = v; markDirty() }" />
          </div>
          <div class="form-item">
            <label>RRF 常数 K</label>
            <t-input-number :value="config.retrieval.rrf_k" :min="10" :max="200" style="width: 100px"
              @change="(v: number) => { config.retrieval.rrf_k = v; markDirty() }" />
          </div>
          <div class="form-item">
            <label>RRF 最终数量</label>
            <t-input-number :value="config.retrieval.rrf_top_n" :min="5" :max="50" style="width: 100px"
              @change="(v: number) => { config.retrieval.rrf_top_n = v; markDirty() }" />
          </div>
          <div class="form-item">
            <label>样本实体置顶</label>
            <t-switch :value="config.retrieval.sample_boost"
              @change="(v: boolean) => { config.retrieval.sample_boost = v; markDirty() }" />
          </div>
        </div>
      </section>

      <!-- 质量规则 -->
      <section class="config-section">
        <h2>质量规则</h2>
        <p class="section-desc">启用或禁用各质量校验规则</p>
        <div class="rule-table-wrap">
          <t-table
            :data="Object.entries(config.rules).map(([key, val]) => ({ rule: key, ...ruleMeta[key], enabled: val.enabled }))"
            :columns="[
              { colKey: 'rule', title: '规则名', width: 220 },
              { colKey: 'severity', title: '级别', width: 100 },
              { colKey: 'desc', title: '说明', ellipsis: true },
              { colKey: 'enabled', title: '启用', width: 80 },
            ]"
            row-key="rule"
            size="small"
            hover
          >
            <template #severity="{ row }">
              <t-tag size="small" :theme="severityTheme(row.severity)" variant="light">
                {{ row.severity }}
              </t-tag>
            </template>
            <template #enabled="{ row }">
              <t-switch
                :value="row.enabled"
                size="small"
                @change="(v: boolean) => { config.rules[row.rule].enabled = v; markDirty() }"
              />
            </template>
          </t-table>
        </div>
      </section>

      <!-- 操作栏 -->
      <div class="config-actions">
        <t-button theme="default" variant="outline" @click="handleReset">恢复默认</t-button>
        <t-button theme="primary" :loading="saving" :disabled="!dirty" @click="handleSave">保存配置</t-button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.config-page {
  --color-bg: oklch(99% 0.002 240);
  --color-surface: oklch(100% 0 0);
  --color-fg: oklch(18% 0.012 250);
  --color-muted: oklch(54% 0.012 250);
  --color-border: oklch(92% 0.005 250);
  --color-accent: oklch(58% 0.18 255);
  --color-accent-soft: oklch(58% 0.18 255 / 0.08);
  --font-mono: 'JetBrains Mono', 'SF Mono', ui-monospace, Menlo, monospace;
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 16px;
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', system-ui, sans-serif;
  color: var(--color-fg);
}

.page-header { margin-bottom: 28px; }
.page-header h1 { font-size: 1.5rem; font-weight: 700; letter-spacing: -0.01em; margin: 0; }
.page-subtitle { font-size: 0.875rem; color: var(--color-muted); margin-top: 4px; }
.loading-state { display: flex; justify-content: center; padding: 64px 0; }

.config-section {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 24px;
  margin-bottom: 16px;
}
.config-section h2 { font-size: 1.125rem; font-weight: 700; margin: 0 0 4px; }
.section-desc { font-size: 0.875rem; color: var(--color-muted); margin: 0 0 24px; }

.threshold-row { display: flex; flex-direction: column; gap: 32px; }
.threshold-item label { font-weight: 500; font-size: 0.875rem; }
.threshold-head { display: flex; align-items: center; gap: 12px; }
.threshold-value { font-size: 1.25rem; font-weight: 700; color: var(--color-accent); font-family: var(--font-mono); font-variant-numeric: tabular-nums; }
.threshold-hint { font-size: 0.75rem; color: var(--color-muted); margin-top: 4px; }

.form-grid { display: flex; flex-wrap: wrap; gap: 20px 32px; }
.form-item { display: flex; align-items: center; gap: 10px; }
.form-item label { font-size: 0.875rem; font-weight: 500; white-space: nowrap; }

.filter-select-wrap { position: relative; display: flex; align-items: center; }
.filter-select {
  appearance: none; padding: 5px 28px 5px 10px; border-radius: 20px;
  border: 1px solid var(--color-border); font-size: 13px; font-weight: 500;
  cursor: pointer; background: transparent; color: var(--color-fg);
  font-family: inherit; transition: all 0.15s;
}
.filter-select:hover { border-color: var(--color-accent); }
.filter-select.active { background: var(--color-accent-soft); color: var(--color-accent); border-color: var(--color-accent); }
.filter-select-wrap::after {
  content: ''; position: absolute; right: 10px; top: 50%; transform: translateY(-50%);
  pointer-events: none; border-left: 4px solid transparent; border-right: 4px solid transparent;
  border-top: 5px solid currentColor;
}

.rule-table-wrap { margin-top: 8px; }
.config-actions { display: flex; justify-content: flex-end; gap: 12px; padding-top: 8px; }

:deep(.t-table) { font-size: 14px; font-variant-numeric: tabular-nums; }
:deep(.t-table th) { font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; color: var(--color-muted); }

@media (max-width: 768px) {
  .config-page { padding: 16px; }
  .form-grid { flex-direction: column; gap: 16px; }
}
</style>
