<template>
  <div class="ag-table-container">
    <ag-grid-vue
      class="ag-theme-alpine"
      style="width: 100%; height: 320px;"
      theme="legacy"
      :columnDefs="columnDefs"
      :rowData="rowData"
      :defaultColDef="defaultColDef"
      @grid-ready="onGridReady"
    >
    </ag-grid-vue>

    <div v-if="item.tableType === 'flexible'" class="mt-2 d-flex gap-2 justify-content-end">
      <button class="btn btn-xs btn-outline-primary shadow-sm" @click="addRow">
        <i class="bi bi-plus-lg me-1"></i> 행 추가
      </button>
      <button class="btn btn-xs btn-outline-danger shadow-sm" @click="removeRow">
        <i class="bi bi-dash-lg me-1"></i> 행 삭제
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { AgGridVue } from "ag-grid-vue3";
import { ModuleRegistry, AllCommunityModule } from 'ag-grid-community';
ModuleRegistry.registerModules([ AllCommunityModule ]);

import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-alpine.css";

const props = defineProps(['item']);
const gridApi = ref(null);

const columnDefs = computed(() => {
  const cols = [];
  if (props.item.tableType === 'fixed') {
    cols.push({ headerName: '표측(질의)', field: 'rowLabel', width: 150, pinned: 'left', cellStyle: { background: '#f8f9fa', fontWeight: 'bold' } });
  } else {
    cols.push({ headerName: 'No.', valueGetter: "node.rowIndex + 1", width: 60, cellStyle: { textAlign: 'center' } });
  }
  (props.item.subItems || []).forEach((sub) => {
    cols.push({ headerName: sub.label, field: sub.id, flex: 1, minWidth: 100, cellClass: 'text-center' });
  });
  return cols;
});

const rowData = ref([]);

const onGridReady = (params) => {
  gridApi.value = params.api;
  syncRowData();
};

// 데이터 동기화 함수
const syncRowData = () => {
  if (props.item.tableType === 'fixed') {
    const labels = Array.isArray(props.item.rowLabels) ? props.item.rowLabels : String(props.item.rowLabels || '').split(',').map(s=>s.trim()).filter(s=>s);
    rowData.value = labels.map(label => ({ rowLabel: label }));
  } else {
    // 유연형은 저장된 데이터가 있으면 불러오고 없으면 빈 배열
    rowData.value = props.item.storedRows || [];
  }
};

// 표측 값 변경 감지 (고정형)
watch(() => props.item.rowLabels, () => {
  syncRowData();
}, { deep: true });

// [행 추가] - 부모 데이터에도 상태 저장
const addRow = () => {
  const newRow = {};
  rowData.value = [...rowData.value, newRow]; // 반응형 업데이트
  if(!props.item.storedRows) props.item.storedRows = [];
  props.item.storedRows.push(newRow); // 부모 데이터 저장
};

// [행 삭제]
const removeRow = () => {
  if (rowData.value.length > 0) {
    rowData.value = rowData.value.slice(0, -1);
    if(props.item.storedRows) props.item.storedRows.pop();
  }
};

const defaultColDef = { resizable: true, sortable: false };
</script>

<style scoped>
.ag-table-container { width: 100%; }
:deep(.ag-header-cell-label) { font-size: 0.85rem; justify-content: center; }
:deep(.ag-cell) { font-size: 0.85rem; }
</style>