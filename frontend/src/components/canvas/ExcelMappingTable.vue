<template>
  <div class="excel-table-wrapper border rounded p-3 bg-white shadow-sm">
    <div class="mb-3 d-flex justify-content-between align-items-center border-bottom pb-2">
      <span class="badge bg-info text-dark">
        <i class="bi bi-grid-3x3-gap me-1"></i> [유형 3] 엑셀형 매핑 테이블
      </span>
      <small class="text-muted">빈 셀 클릭: 질의입력 / 항목 드래그: 매핑</small>
    </div>
    
    <div class="table-responsive">
      <table class="table table-bordered excel-style-table m-0">
        <tbody>
          <tr v-for="r in item.rowCount" :key="r">
            <td v-for="c in item.colCount" :key="c" class="excel-cell p-0 position-relative">
              <draggable 
                :list="getMappedItem(r, c)" 
                group="questions" 
                item-key="id" 
                class="cell-content-zone d-flex flex-column align-items-center justify-content-center"
                @add="(evt) => onDrop(evt, r, c)"
              >
                <template #item="{ element }">
                  <div class="mapped-badge badge bg-success shadow-sm" @click.stop="removeMap(r, c)">
                    <i class="bi bi-link-45deg me-1"></i>{{ element.id }}
                    <i class="bi bi-x-circle-fill ms-2 opacity-50"></i>
                  </div>
                </template>
                
                <template #header>
                  <div v-if="!hasMappedItem(r, c)" class="w-100 h-100">
                    <input 
                      v-model="item.cellTexts[`${r}-${c}`]"
                      class="excel-input border-0 w-100 h-100 text-center" 
                      placeholder="질의입력"
                    >
                  </div>
                </template>
              </draggable>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import draggable from 'vuedraggable';

const props = defineProps(['item']);

// 특정 셀에 매핑된 데이터가 있는지 확인 (v-for 바인딩용)
const getMappedItem = (r, c) => {
  const key = `${r}-${c}`;
  return props.item.cells[key] ? [props.item.cells[key]] : [];
};

// UI 제어용
const hasMappedItem = (r, c) => {
  return !!props.item.cells[`${r}-${c}`];
};

// 드래그 드롭 시 데이터 매핑
const onDrop = (evt, r, c) => {
  const key = `${r}-${c}`;
  // 원본 객체를 셀 데이터에 복사
  props.item.cells[key] = evt.item._underlying_vm_;
  // 매핑되면 입력된 텍스트는 비우거나 유지 (사용자 선택사항)
};

// 매핑 삭제
const removeMap = (r, c) => {
  const key = `${r}-${c}`;
  delete props.item.cells[key];
};
</script>

<style scoped>
.excel-style-table { border-collapse: collapse; table-layout: fixed; width: 100%; border: 2px solid #dee2e6; }
.excel-cell { border: 1px solid #dee2e6 !important; height: 50px; min-width: 120px; vertical-align: middle; background: #fff; }
.excel-cell:hover { background-color: #f1f8ff; }
.cell-content-zone { min-height: 50px; width: 100%; height: 100%; }
.excel-input { font-size: 0.8rem; outline: none; background: transparent; transition: background 0.2s; }
.excel-input:focus { background: #fffde7; }
.mapped-badge { font-size: 0.7rem; cursor: pointer; padding: 5px 8px; z-index: 10; }
.mapped-badge:hover { background-color: #157347 !important; }
</style>