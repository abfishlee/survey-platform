<template>
  <div class="canvas-wrapper">
    <draggable 
      v-model="list" 
      group="questions" 
      item-key="id" 
      class="canvas-list" 
      :class="{ 'is-empty': !list || list.length === 0 }"
      handle=".drag-handle"
      animation="200"
    >
      <template #header>
        <div v-if="!list || list.length === 0" class="empty-canvas">
          <i class="bi bi-plus-circle display-1 text-muted opacity-25 mb-4"></i>
          <h5 class="text-muted fw-bold text-center">항목을 이곳으로 드래그하여 조사표를 구성하세요</h5>
        </div>
      </template>

      <template #item="{ element, index }">
        <div 
          v-if="element" 
          :id="'q-' + element.id"
          class="canvas-item shadow-sm" 
          :class="{ active: selectedId === element.id }" 
          @click="selectItem(element)"
        >
          <div class="d-flex justify-content-between align-items-center mb-3 border-bottom pb-2">
            <div class="d-flex align-items-center">
              <div class="drag-handle me-3" title="드래그하여 순서 변경"><i class="bi bi-grip-vertical fs-5 text-muted"></i></div>
              <div class="badge bg-primary me-2 px-3">Q{{ index + 1 }}</div>
              <div class="fw-bold text-dark fs-6">{{ element.label }}</div>
            </div>
            <button class="btn btn-sm btn-link text-danger p-0 ms-2" @click.stop="removeItem(index)"><i class="bi bi-trash3-fill"></i></button>
          </div>
          
          <div class="ps-4">
            <div v-if="['text', 'number', 'radio', 'checkbox'].includes(element.type)">
               <input v-if="['text', 'number'].includes(element.type)" class="form-control form-control-sm bg-light" disabled :placeholder="element.label + ' 입력'">
               <div v-else class="d-flex flex-wrap gap-2 mt-2">
                 <div v-for="opt in ensureArray(element.options)" :key="opt" class="form-check form-check-inline">
                   <input :type="element.type" class="form-check-input" disabled checked>
                   <label class="form-check-label">{{ opt }}</label>
                 </div>
                 <div v-if="ensureArray(element.options).length === 0" class="text-muted small">옵션이 없습니다. (속성창에서 추가)</div>
               </div>
            </div>

            <div v-else-if="element.type === 'table' || element.type === 'mapping-table'">
              <div class="table-render-zone rounded border overflow-hidden shadow-sm">
                <AgMappingTable v-if="element.type === 'table'" :item="element" />
                <ExcelMappingTable v-else :item="element" />
              </div>
              <div v-if="element.tableType === 'flexible'" class="mt-2 text-end">
                <span class="badge bg-info bg-opacity-10 text-info border border-info x-small px-2 py-1">
                  <i class="bi bi-info-circle me-1"></i> 유연형: 미리보기 및 수집 화면에서 [행 추가/삭제] 버튼 활성화
                </span>
              </div>
            </div>
          </div>
        </div>
      </template>
    </draggable>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import draggable from 'vuedraggable';
import AgMappingTable from './AgMappingTable.vue';
import ExcelMappingTable from './ExcelMappingTable.vue';

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  selectedId: [String, Number]
});
const emit = defineEmits(['update:modelValue', 'select', 'remove']);

const list = computed({
  get: () => props.modelValue || [],
  set: (val) => emit('update:modelValue', val)
});

const ensureArray = (data) => {
  if (!data) return [];
  if (Array.isArray(data)) return data;
  return String(data).split(',').map(s => s.trim()).filter(s => s !== '');
};

const selectItem = (item) => emit('select', item);
const removeItem = (index) => emit('remove', index);
</script>

<style scoped>
.canvas-wrapper { width: 100%; max-width: 100%; margin: 0; padding: 0 20px 100px 20px; box-sizing: border-box; }
.canvas-list { min-height: 850px; background: white; padding: 40px; border-radius: 12px; border: 1px solid #e2e8f0; width: 100%; box-sizing: border-box; }
.empty-canvas { height: 600px; display: flex; flex-direction: column; align-items: center; justify-content: center; }
.canvas-item { border: 1px solid #f1f5f9; padding: 25px; border-radius: 12px; cursor: pointer; transition: all 0.2s ease; margin-bottom: 25px; background: #fff; }
.canvas-item:hover { border-color: #3b82f6; box-shadow: 0 10px 30px rgba(59, 130, 246, 0.08) !important; }
.canvas-item.active { border: 2px solid #3b82f6; background-color: #f8fbff; }
.table-render-zone { width: 100%; }
.drag-handle { cursor: grab; color: #cbd5e0; }
.drag-handle:hover { color: #64748b; }
.x-small { font-size: 0.65rem; }
</style>