<template>
  <div class="collector-container bg-light min-vh-100">
    <header class="collector-header text-white p-3 shadow-sm sticky-top d-flex justify-content-between align-items-center"
            :class="isPreview ? 'bg-secondary' : 'bg-primary'">
      <div>
        <h5 class="mb-0 fw-bold">
          <i class="bi" :class="isPreview ? 'bi-eye-fill' : 'bi-pencil-fill'"></i>
          {{ isPreview ? ' [미리보기 모드] 저장되지 않습니다.' : ' 조사 데이터 입력' }}
        </h5>
        <small class="opacity-75" v-if="respondentId && !isPreview">대상 ID: {{ respondentId }}</small>
      </div>
      <div class="d-flex gap-2">
        <button v-if="!isPreview" class="btn btn-success fw-bold px-4 shadow-sm" @click="saveAllData">
          <i class="bi bi-cloud-arrow-up me-1"></i>최종 저장
        </button>
        <button v-if="!isPreview" class="btn btn-outline-light" @click="closeModal">닫기</button>
      </div>
    </header>

    <div class="container py-4" style="max-width: 1000px;">
      <!-- WARNING 리스트 표시 -->
      <div v-if="savedWarnings.length > 0" class="alert alert-warning border-warning shadow-sm mb-4">
        <div class="d-flex align-items-center mb-2">
          <i class="bi bi-exclamation-triangle-fill me-2 fs-5"></i>
          <h6 class="mb-0 fw-bold">⚠️ 저장된 경고 사항 ({{ savedWarnings.length }}건)</h6>
        </div>
        <ul class="list-unstyled mb-0">
          <li v-for="(warning, idx) in savedWarnings" :key="idx" 
              class="mb-2 p-2 bg-white rounded border border-warning-subtle cursor-pointer"
              @click="focusToWarningCell(warning)"
              style="cursor: pointer; transition: all 0.2s;"
              @mouseenter="$event.currentTarget.style.backgroundColor = '#fff3cd'"
              @mouseleave="$event.currentTarget.style.backgroundColor = 'white'">
            <div class="d-flex align-items-start">
              <i class="bi bi-arrow-right-circle-fill text-warning me-2 mt-1"></i>
              <div class="flex-grow-1">
                <strong class="text-dark">{{ warning.message || `규칙 ${warning.rule_id}` }}</strong>
                <small class="d-block text-muted mt-1">{{ warning.condition }}</small>
              </div>
            </div>
          </li>
        </ul>
      </div>

      <ul class="nav nav-pills mb-4 bg-white p-2 rounded shadow-sm" v-if="surveyForms.length > 1">
        <li v-for="(form, fIdx) in surveyForms" :key="form.ver_form_id" class="nav-item">
          <button class="nav-link" :class="{ active: activeFormIdx === fIdx }" @click="activeFormIdx = fIdx">
            {{ form.form_name }}
          </button>
        </li>
      </ul>

      <div v-if="currentForm" class="survey-page animate__animated animate__fadeIn">
        <div v-for="(q, qIdx) in currentForm.design_data" :key="q.id" class="card border-0 shadow-sm mb-4">
          <div class="card-body p-4">
            <div class="d-flex mb-3 align-items-center">
              <span class="badge bg-primary me-2 align-self-start mt-1">Q{{ qIdx + 1 }}</span>
              <h5 class="fw-bold mb-0 text-dark" style="line-height: 1.5;">{{ q.label }}</h5>
            </div>

            <div class="ps-4">
              <div v-if="['text', 'number'].includes(q.type)">
                <input :type="q.type" class="form-control bg-light" 
                       v-model="answers[currentForm.ver_form_id][q.id]" 
                       :placeholder="q.label + ' 입력'">
              </div>

              <div v-else-if="q.type === 'radio'" class="d-flex flex-wrap gap-3 mt-2">
                <div v-for="opt in ensureArray(q.options)" :key="opt" class="form-check">
                  <input class="form-check-input" type="radio" :name="currentForm.ver_form_id + q.id" :value="opt" 
                         v-model="answers[currentForm.ver_form_id][q.id]" :id="q.id+opt">
                  <label class="form-check-label cursor-pointer" :for="q.id+opt">{{ opt }}</label>
                </div>
              </div>

              <div v-else-if="q.type === 'checkbox'" class="d-flex flex-wrap gap-3 mt-2">
                <div v-for="opt in ensureArray(q.options)" :key="opt" class="form-check">
                  <input class="form-check-input" type="checkbox" :value="opt" 
                         v-model="answers[currentForm.ver_form_id][q.id]" :id="q.id+opt">
                  <label class="form-check-label cursor-pointer" :for="q.id+opt">{{ opt }}</label>
                </div>
              </div>

              <div v-else-if="q.type === 'table' || q.type === 'mapping-table'" class="table-responsive bg-white rounded border p-3" :data-table-id="q.id">
                
                <table v-if="q.type === 'mapping-table'" class="table table-bordered align-middle text-center small mb-0">
                  <tbody>
                    <tr v-for="r in (q.rowCount || 3)" :key="r">
                      <td v-for="c in (q.colCount || 3)" :key="c" style="min-width: 80px; height: 45px;" class="p-1">
                        <div v-if="isCellMapped(q, r, c)">
                          <input type="text" class="form-control form-control-sm text-center bg-warning-subtle fw-bold border-warning"
                                 v-model="answers[currentForm.ver_form_id][getMappedItemId(q, r, c)]"
                                 :placeholder="getMappedItemLabel(q, r, c)">
                        </div>
                        <div v-else-if="q.cellTexts && q.cellTexts[`${r}-${c}`]" class="fw-bold text-secondary bg-light h-100 d-flex align-items-center justify-content-center">
                          {{ q.cellTexts[`${r}-${c}`] }}
                        </div>
                        <div v-else class="text-muted bg-light h-100">-</div>
                      </td>
                    </tr>
                  </tbody>
                </table>

                <div v-else>
                  <table class="table table-bordered align-middle text-center small mb-0">
                    <thead class="table-light">
                      <tr>
                        <th v-if="q.tableType === 'fixed'" style="width: 150px;" class="bg-light">항목(표측)</th>
                        <th v-else style="width: 50px;">No.</th>
                        <th v-for="sub in (q.subItems || [])" :key="sub.id">{{ sub.label }}</th>
                        
                        <th v-if="q.tableType !== 'fixed'" style="width: 50px;">삭제</th>
                      </tr>
                    </thead>
                    <tbody>
                      <template v-if="q.tableType === 'fixed'">
                        <tr v-for="(rowLabel, rIdx) in ensureArray(q.rowLabels)" :key="rIdx">
                          <td class="bg-light fw-bold text-start ps-3">{{ rowLabel }}</td>
                          <td v-for="sub in (q.subItems || [])" :key="sub.id">
                            <input type="text" class="form-control form-control-sm border-0 text-center" 
                                   v-model="answers[currentForm.ver_form_id][q.id][rIdx][sub.id]"
                                   :data-table-id="q.id"
                                   :data-row-index="rIdx"
                                   :data-col-id="sub.id">
                          </td>
                        </tr>
                      </template>

                      <template v-else>
                        <tr v-for="(row, rIdx) in answers[currentForm.ver_form_id][q.id]" :key="rIdx">
                          <td>{{ rIdx + 1 }}</td>
                          <td v-for="sub in (q.subItems || [])" :key="sub.id">
                            <input type="text" class="form-control form-control-sm border-0 text-center" 
                                   v-model="row[sub.id]"
                                   :data-table-id="q.id"
                                   :data-row-index="rIdx"
                                   :data-col-id="sub.id">
                          </td>
                          <td>
                            <button class="btn btn-sm btn-outline-danger border-0 py-0" @click="removeFlexibleRow(q.id, rIdx)">
                              <i class="bi bi-x-lg"></i>
                            </button>
                          </td>
                        </tr>
                        <tr v-if="!answers[currentForm.ver_form_id][q.id] || answers[currentForm.ver_form_id][q.id].length === 0">
                          <td :colspan="(q.subItems || []).length + 2" class="text-center text-muted py-3">
                            입력된 데이터가 없습니다. 아래 버튼을 눌러 행을 추가하세요.
                          </td>
                        </tr>
                      </template>
                    </tbody>
                    
                    <tfoot v-if="q.tableType !== 'fixed'">
                      <tr>
                        <td :colspan="(q.subItems || []).length + 2" class="p-2 bg-light">
                          <button class="btn btn-sm btn-outline-primary w-100 dashed-border fw-bold" @click="addFlexibleRow(q.id, q.subItems)">
                            <i class="bi bi-plus-circle me-1"></i> 행 추가하기
                          </button>
                        </td>
                      </tr>
                    </tfoot>
                  </table>
                </div>

              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';

const props = defineProps({
  isPreview: { type: Boolean, default: false },
  initialData: { type: Object, default: null } 
});

const dataId = ref(null);
const respondentId = ref('');
const surveyForms = ref([]);
const activeFormIdx = ref(0);
const answers = ref({});
const savedWarnings = ref([]); 

const currentForm = computed(() => surveyForms.value[activeFormIdx.value]);

const ensureArray = (val) => {
  if (!val) return [];
  if (Array.isArray(val)) return val;
  return String(val).split(',').map(s => s.trim()).filter(s => s !== '');
};

const isCellMapped = (q, r, c) => q.cells && q.cells[`${r}-${c}`];
const getMappedItemId = (q, r, c) => q.cells[`${r}-${c}`].id;
const getMappedItemLabel = (q, r, c) => q.cells[`${r}-${c}`].label;

const loadSurveyData = (data) => {
  if (!data) return;
  const { dataId: id, respondentId: rid, forms, saved_warnings } = data;
  dataId.value = id;
  respondentId.value = rid;
  surveyForms.value = forms;
  savedWarnings.value = saved_warnings || [];

  forms.forEach(form => {
    if (!answers.value[form.ver_form_id]) answers.value[form.ver_form_id] = {};
    form.design_data.forEach(q => {
      const savedVal = form.saved_values ? form.saved_values[q.id] : null;
      if (q.type === 'table') {
        if (q.tableType === 'fixed') {
          const rowCount = ensureArray(q.rowLabels).length;
          const subItems = q.subItems || [];
          answers.value[form.ver_form_id][q.id] = savedVal || Array.from({ length: rowCount }, () => {
            const row = {};
            subItems.forEach(sub => row[sub.id] = '');
            return row;
          });
        } else {
          // 유연형 초기화: 저장된 값이 없으면 1행 생성 (빈 배열로 시작하고 싶으면 [] 로 변경 가능)
          const subItems = q.subItems || [];
          answers.value[form.ver_form_id][q.id] = savedVal || [
             subItems.reduce((acc, sub) => ({ ...acc, [sub.id]: '' }), {})
          ];
        }
      } else if (q.type === 'mapping-table') {
        if (q.cells) {
          Object.values(q.cells).forEach(cellItem => {
            if (!answers.value[form.ver_form_id][cellItem.id]) {
              answers.value[form.ver_form_id][cellItem.id] = (form.saved_values && form.saved_values[cellItem.id]) || '';
            }
          });
        }
      } else if (q.type === 'checkbox') {
        answers.value[form.ver_form_id][q.id] = savedVal || [];
      } else {
        answers.value[form.ver_form_id][q.id] = savedVal || '';
      }
    });
  });
};

const handleInitEvent = (event) => loadSurveyData(event.detail);

onMounted(() => {
  if (props.initialData) loadSurveyData(props.initialData);
  window.addEventListener('init-survey-collector', handleInitEvent);
});

onUnmounted(() => window.removeEventListener('init-survey-collector', handleInitEvent));

watch(() => props.initialData, (newVal) => {
  if (newVal) loadSurveyData(newVal);
}, { deep: true });

// [행 추가]
const addFlexibleRow = (qId, subItems) => {
  const newRow = {};
  (subItems || []).forEach(sub => newRow[sub.id] = '');
  // 배열이 초기화되지 않았을 경우 대비
  if (!answers.value[currentForm.value.ver_form_id][qId]) {
    answers.value[currentForm.value.ver_form_id][qId] = [];
  }
  answers.value[currentForm.value.ver_form_id][qId].push(newRow);
};

// [행 삭제]
const removeFlexibleRow = (qId, idx) => {
  const rows = answers.value[currentForm.value.ver_form_id][qId];
  if (rows.length > 0) rows.splice(idx, 1);
};

const saveAllData = async (forceSave = false) => {
  if (props.isPreview) return;
  if (!forceSave && !confirm("입력한 모든 데이터를 저장하시겠습니까?")) return;
  try {
    const response = await fetch(`/data/${dataId.value}/save-survey/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || '' },
      body: JSON.stringify({ answers: answers.value, force_save: forceSave })
    });
    const result = await response.json();
    if (response.ok) {
      // WARNING 상태인 경우 (저장 전 확인)
      if (result.status === 'warning' && result.warnings && result.warnings.length > 0) {
        const warningMsg = "⚠️ 경고가 있습니다:\n\n" + result.warnings.join('\n') + "\n\n경고를 무시하고 저장하시겠습니까?";
        if (confirm(warningMsg)) {
          // 사용자가 확인하면 force_save=true로 다시 저장 요청
          saveAllData(true);
        }
        return;
      }
      
      // 저장 성공
      if (result.warnings && result.warnings.length > 0) {
        alert("⚠️ 경고: " + result.warnings.join('\n') + "\n\n저장되었습니다.");
      } else {
        alert("성공적으로 저장되었습니다.");
      }
      location.reload();
    } else {
      // 내검 규칙 위반 에러 처리
      if (result.errors && result.errors.length > 0) {
        let errorMsg = "❌ 내검 규칙 위반:\n\n" + result.errors.join('\n');
        if (result.warnings && result.warnings.length > 0) {
          errorMsg += "\n\n⚠️ 경고:\n" + result.warnings.join('\n');
        }
        alert(errorMsg);
      } else {
        alert("저장 실패: " + (result.message || '알 수 없는 오류'));
      }
    }
  } catch (e) {
    alert("서버 통신 중 오류가 발생했습니다.");
  }
};

const closeModal = () => { 
  if (props.isPreview) return; 
  if(confirm("종료하시겠습니까?")) location.reload(); 
};

// WARNING 셀로 포커스 및 이동
const focusToWarningCell = (warning) => {
  const condition = warning.condition || '';
  
  // 테이블 셀 참조 패턴: {table_id}[row][col]
  const tableCellMatch = condition.match(/\{(\w+)\}\[(\d+)\]\[(\w+)\]/);
  if (!tableCellMatch) {
    alert('일반 필드 포커스 기능은 아직 구현되지 않았습니다.');
    return;
  }
  
  const [, tableIdOrOrigin, rowIdx, colId] = tableCellMatch;
  const rowIndex = parseInt(rowIdx);
  
  // 해당 테이블 찾기 (originId 또는 실제 ID로 찾기)
  let targetForm = null;
  let targetQuestion = null;
  
  for (const form of surveyForms.value) {
    // originId 또는 실제 ID로 찾기
    targetQuestion = form.design_data.find(q => 
      q.id === tableIdOrOrigin || q.originId === tableIdOrOrigin
    );
    if (targetQuestion) {
      targetForm = form;
      break;
    }
  }
  
  if (!targetQuestion || targetQuestion.type !== 'table') {
    alert('해당 테이블을 찾을 수 없습니다.');
    return;
  }
  
  // 실제 테이블 ID 사용 (originId로 찾았을 경우)
  const actualTableId = targetQuestion.id;
  
  // 해당 조사표로 전환
  const formIdx = surveyForms.value.findIndex(f => f.ver_form_id === targetForm.ver_form_id);
  if (formIdx !== -1) {
    activeFormIdx.value = formIdx;
  }
  
  // DOM 업데이트 대기 후 스크롤 및 포커스
  setTimeout(() => {
    // 테이블 컨테이너 찾기 (실제 ID 사용)
    const tableContainer = document.querySelector(`[data-table-id="${actualTableId}"]`);
    if (!tableContainer) {
      alert('테이블을 찾을 수 없습니다.');
      return;
    }
    
    // 테이블 컨테이너로 스크롤
    tableContainer.scrollIntoView({ behavior: 'smooth', block: 'center' });
    
    setTimeout(() => {
      const table = tableContainer.querySelector('table');
      if (!table) {
        alert('테이블 요소를 찾을 수 없습니다.');
        return;
      }
      
      const rows = table.querySelectorAll('tbody tr');
      if (!rows[rowIndex]) {
        alert(`행 ${rowIndex + 1}을 찾을 수 없습니다.`);
        return;
      }
      
      // data 속성으로 직접 input 찾기 (실제 테이블 ID 사용)
      const input = table.querySelector(`input[data-table-id="${actualTableId}"][data-row-index="${rowIndex}"][data-col-id="${colId}"]`);
      
      console.log('[셀 포커스 디버깅]', {
        tableIdOrOrigin,
        actualTableId,
        rowIndex,
        colId,
        input,
        allInputs: Array.from(table.querySelectorAll('input')).map(inp => ({
          tableId: inp.getAttribute('data-table-id'),
          rowIndex: inp.getAttribute('data-row-index'),
          colId: inp.getAttribute('data-col-id')
        }))
      });
      
      if (!input) {
        console.error('입력 필드를 찾을 수 없음:', {
          tableIdOrOrigin,
          actualTableId,
          rowIndex,
          colId,
          searchSelector: `input[data-table-id="${actualTableId}"][data-row-index="${rowIndex}"][data-col-id="${colId}"]`
        });
        alert(`해당 셀을 찾을 수 없습니다. (테이블: ${tableIdOrOrigin}, 행: ${rowIndex + 1}, 열: ${colId})`);
        return;
      }
      
      // input의 부모 셀 찾기
      const targetCell = input.closest('td');
      if (!targetCell) {
        alert('셀 요소를 찾을 수 없습니다.');
        return;
      }
      
      // 셀로 스크롤
      targetCell.scrollIntoView({ behavior: 'smooth', block: 'center' });
      
      setTimeout(() => {
        input.focus();
        input.select(); // 텍스트 선택
        // 강조 표시
        input.style.border = '3px solid #ffc107';
        input.style.boxShadow = '0 0 15px rgba(255, 193, 7, 0.8)';
        input.style.backgroundColor = '#fff3cd';
        input.style.fontWeight = 'bold';
        
        // 셀 배경도 강조
        targetCell.style.backgroundColor = '#fff3cd';
        targetCell.style.transition = 'background-color 0.3s';
        
        // 2초 후 강조 제거
        setTimeout(() => {
          input.style.border = '';
          input.style.boxShadow = '';
          input.style.backgroundColor = '';
          input.style.fontWeight = '';
          targetCell.style.backgroundColor = '';
        }, 2000);
      }, 300);
    }, 300);
  }, 100);
};
</script>

<style scoped>
.collector-header { z-index: 1050; }
.card { border-radius: 12px; }
.cursor-pointer { cursor: pointer; }
.nav-pills .nav-link { color: #6c757d; font-weight: 600; }
.nav-pills .nav-link.active { background-color: #0d6efd; color: white; }
.table th { font-size: 0.85rem; font-weight: 700; letter-spacing: -0.5px; }
.table-responsive { overflow-x: auto; }
.dashed-border { border: 2px dashed #dee2e6; transition: all 0.2s; }
.dashed-border:hover { 
  border-color: #0d6efd; 
  background-color: #e7f1ff; /* 배경: 아주 연한 파란색 */
  color: #0d6efd !important; /* 글자: 파란색 강제 적용 (Bootstrap 덮어쓰기) */
}
</style>