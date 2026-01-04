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
        <button v-if="!isPreview" class="btn btn-success fw-bold px-4 shadow-sm" @click="saveAllData(false)">
          <i class="bi bi-cloud-arrow-up me-1"></i>최종 저장
        </button>
        <button v-if="!isPreview" class="btn btn-outline-light" @click="closeModal">닫기</button>
      </div>
    </header>

    <div class="container py-4" style="max-width: 1000px;">
      
      <div v-if="savedWarnings.length > 0" class="alert alert-warning border-warning shadow-sm mb-4 animate__animated animate__fadeIn">
        <div class="d-flex align-items-center mb-2">
          <i class="bi bi-exclamation-triangle-fill me-2 fs-5"></i>
          <h6 class="mb-0 fw-bold">⚠️ 저장된 경고 사항 ({{ savedWarnings.length }}건)</h6>
        </div>
        <ul class="list-unstyled mb-0">
          <li v-for="(warning, idx) in savedWarnings" :key="idx" 
              class="mb-2 p-2 bg-white rounded border border-warning-subtle cursor-pointer hover-effect"
              @click="focusToWarningCell(warning)"
              title="클릭하여 이동">
            <div class="d-flex align-items-start">
              <i class="bi bi-arrow-right-circle-fill text-warning me-2 mt-1"></i>
              <div class="flex-grow-1">
                <strong class="text-dark">{{ warning.message || `규칙 위반 (조건: ${warning.condition})` }}</strong>
                <small class="d-block text-muted mt-1" v-if="warning.condition">Condition: {{ warning.condition }}</small>
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
        <div v-for="(q, qIdx) in currentForm.design_data" :key="q.id" class="card border-0 shadow-sm mb-4" :id="'card-' + q.id">
          <div class="card-body p-4">
            <div class="d-flex mb-3 align-items-center">
              <span class="badge bg-primary me-2 align-self-start mt-1">Q{{ qIdx + 1 }}</span>
              <h5 class="fw-bold mb-0 text-dark" style="line-height: 1.5;">{{ q.label }}</h5>
            </div>

            <div class="ps-4">
              <div v-if="['text', 'number'].includes(q.type)">
                <input :type="q.type" class="form-control bg-light" 
                       v-model="answers[currentForm.ver_form_id][q.id]" 
                       :id="'input-' + q.id"
                       :placeholder="q.label + ' 입력'">
              </div>

              <div v-else-if="q.type === 'radio'" class="d-flex flex-wrap gap-3 mt-2" :id="'group-' + q.id">
                <div v-for="opt in ensureArray(q.options)" :key="opt" class="form-check">
                  <input class="form-check-input" type="radio" :name="currentForm.ver_form_id + q.id" :value="opt" 
                         v-model="answers[currentForm.ver_form_id][q.id]" :id="q.id+opt">
                  <label class="form-check-label cursor-pointer" :for="q.id+opt">{{ opt }}</label>
                </div>
              </div>

              <div v-else-if="q.type === 'checkbox'" class="d-flex flex-wrap gap-3 mt-2" :id="'group-' + q.id">
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
                                 :id="'input-' + getMappedItemId(q, r, c)"
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
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue';

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

// 배열 보장 헬퍼
const ensureArray = (val) => {
  if (!val) return [];
  if (Array.isArray(val)) return val;
  return String(val).split(',').map(s => s.trim()).filter(s => s !== '');
};

const isCellMapped = (q, r, c) => q.cells && q.cells[`${r}-${c}`];
const getMappedItemId = (q, r, c) => q.cells[`${r}-${c}`].id;
const getMappedItemLabel = (q, r, c) => q.cells[`${r}-${c}`].label;

// 데이터 로드
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
          // 유연형
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

// 이벤트 리스너
const handleInitEvent = (event) => loadSurveyData(event.detail);

onMounted(() => {
  if (props.initialData) loadSurveyData(props.initialData);
  window.addEventListener('init-survey-collector', handleInitEvent);
});

onUnmounted(() => window.removeEventListener('init-survey-collector', handleInitEvent));

watch(() => props.initialData, (newVal) => {
  if (newVal) loadSurveyData(newVal);
}, { deep: true });

window.addEventListener('init-survey-collector', (e) => {
    if(e.detail && e.detail.degreeId) {
        window.surveyDegreeId = e.detail.degreeId;
    }
});

// 행 추가/삭제
const addFlexibleRow = (qId, subItems) => {
  const newRow = {};
  (subItems || []).forEach(sub => newRow[sub.id] = '');
  if (!answers.value[currentForm.value.ver_form_id][qId]) {
    answers.value[currentForm.value.ver_form_id][qId] = [];
  }
  answers.value[currentForm.value.ver_form_id][qId].push(newRow);
};

const removeFlexibleRow = (qId, idx) => {
  const rows = answers.value[currentForm.value.ver_form_id][qId];
  if (rows && rows.length > 0) {
    rows.splice(idx, 1);
  }
};

// 저장 로직
const saveAllData = async (forceSave = false) => {
  if (props.isPreview) return;
  if (!forceSave && !confirm("입력한 모든 데이터를 저장하시겠습니까?")) return;
  
  try {
    let url = `/data/${dataId.value}/save-survey/`;
    if (window.surveyDegreeId) {
        url += `?degree_id=${window.surveyDegreeId}`;
    }

    const response = await fetch(url, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json', 
        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || '' 
      },
      body: JSON.stringify({ answers: answers.value, force_save: forceSave })
    });
    
    const result = await response.json();
    
    if (response.ok) {
      if (result.status === 'warning' && result.warnings && result.warnings.length > 0) {
        const warningMsg = "⚠️ 경고가 있습니다:\n\n" + result.warnings.join('\n') + "\n\n경고를 무시하고 저장하시겠습니까?";
        if (confirm(warningMsg)) {
          saveAllData(true);
        }
        return;
      }
      
      if (result.warnings && result.warnings.length > 0) {
        alert("⚠️ 경고: " + result.warnings.join('\n') + "\n\n저장되었습니다.");
      } else {
        alert("성공적으로 저장되었습니다.");
      }
      location.reload();
    } else {
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
    console.error(e);
    alert("서버 통신 중 오류가 발생했습니다.");
  }
};

const closeModal = () => { 
  if (props.isPreview) return; 
  if(confirm("종료하시겠습니까?")) location.reload(); 
};

/* ----------------------------------------------------
   [하이라이트 헬퍼 함수]
   ---------------------------------------------------- */
const highlightElement = (element, container = null) => {
    if(!element) return;
    
    // 1. 스크롤
    element.scrollIntoView({ behavior: 'smooth', block: 'center' });
    
    // 2. 포커스
    element.focus();
    if(element.select && element.type !== 'radio' && element.type !== 'checkbox') {
        element.select();
    }

    // 3. 스타일 적용
    const originalTransition = element.style.transition;
    const originalBg = element.style.backgroundColor;
    const originalShadow = element.style.boxShadow;
    const originalBorder = element.style.border;

    element.style.transition = 'all 0.3s ease';
    element.style.backgroundColor = '#fff3cd'; // 연한 노랑
    element.style.boxShadow = '0 0 0 4px rgba(255, 193, 7, 0.4)'; // 반짝임 효과
    element.style.border = '2px solid #ffc107';

    if(container) {
        container.style.transition = 'background-color 0.3s';
        container.style.backgroundColor = '#fff3cd';
    }

    // 4. 복구
    setTimeout(() => {
        element.style.backgroundColor = originalBg;
        element.style.boxShadow = originalShadow;
        element.style.border = originalBorder;
        element.style.transition = originalTransition;
        if(container) container.style.backgroundColor = '';
    }, 2000);
};

/* ----------------------------------------------------
   [핵심 수정] 내검 이동 (로직 단순화 & 강력해짐)
   ---------------------------------------------------- */
const focusToWarningCell = async (warning) => {
  const condition = (warning.condition || '').toString();
  console.log("🔍 이동 시도:", condition);

  // 1. { } 안의 문자를 무조건 추출 (가장 중요한 ID)
  // 예: "{q1} == 0" -> "q1"
  // 예: "{table}[0][col]" -> "table"
  const mainIdMatch = condition.match(/\{([^}]+)\}/);
  
  if (!mainIdMatch) {
      // 괄호가 없을 경우(단순 ID) 전체를 ID로 가정해봄
      if (condition.trim().length > 0 && !condition.includes(' ')) {
          // 공백없는 짧은 문자열이면 ID로 간주
      } else {
          alert(`이동할 항목 ID를 찾을 수 없습니다.\n조건식: ${condition}`);
          return;
      }
  }

  const targetId = mainIdMatch ? mainIdMatch[1].trim() : condition.trim();
  
  // 2. 표(Table) 좌표 추가 추출 ([숫자][문자] 형태)
  let targetRow = -1;
  let targetCol = null;
  
  const rowColMatch = condition.match(/\]\[(\d+)\]\[([^\]]+)\]/); // [0][col]
  const colAllMatch = condition.match(/\]\[\*\]\[([^\]]+)\]/);    // [*][col]

  if (rowColMatch) {
      targetRow = parseInt(rowColMatch[1]);
      targetCol = rowColMatch[2].trim();
  } else if (colAllMatch) {
      targetCol = colAllMatch[1].trim();
      targetRow = -1; // 빈 행 탐색 필요
  }

  // 3. 설계 데이터에서 ID 찾기 (SystemID or UserID)
  let foundFormIdx = -1;
  let actualQuestionId = null;
  let questionType = null;
  let actualColId = null;

  for (let i = 0; i < surveyForms.value.length; i++) {
      const form = surveyForms.value[i];
      // ID 또는 OriginID 매칭 (대소문자 무시)
      const q = form.design_data.find(d => 
          d.id === targetId || d.originId === targetId ||
          (d.id && d.id.toUpperCase() === targetId.toUpperCase()) || 
          (d.originId && d.originId.toUpperCase() === targetId.toUpperCase())
      );

      if (q) {
          foundFormIdx = i;
          actualQuestionId = q.id;
          questionType = q.type;
          
          // 테이블 열 ID 매핑
          if (targetCol && q.subItems) {
              const sub = q.subItems.find(s => s.id === targetCol || s.label === targetCol);
              if (sub) actualColId = sub.id;
              else actualColId = targetCol;
          }
          break;
      }
  }

  if (!actualQuestionId) {
      alert(`화면에서 항목(${targetId})을 찾을 수 없습니다.`);
      return;
  }

  // 4. 탭 전환
  if (activeFormIdx.value !== foundFormIdx) {
      activeFormIdx.value = foundFormIdx;
  }
  await nextTick(); // 화면 렌더링 대기

  // 5. DOM 찾기 및 이동
  if (['table', 'mapping-table'].includes(questionType)) {
      // --- 테이블 ---
      if (actualColId) {
          // 셀 이동
          if (targetRow === -1) {
              // [*] 패턴이면 첫 번째 빈 값 찾기
              const currentData = answers.value[surveyForms.value[foundFormIdx].ver_form_id][actualQuestionId];
              if (Array.isArray(currentData)) {
                  targetRow = currentData.findIndex(row => !row[actualColId] || row[actualColId].toString().trim() === '');
                  if (targetRow === -1) targetRow = 0;
              } else targetRow = 0;
          }
          const selector = `input[data-table-id="${actualQuestionId}"][data-row-index="${targetRow}"][data-col-id="${actualColId}"]`;
          setTimeout(() => {
              const el = document.querySelector(selector);
              if(el) highlightElement(el, el.closest('td'));
              else highlightElement(document.getElementById('card-' + actualQuestionId)); // 실패시 카드 전체
          }, 100);
      } else {
          // 테이블 전체
          highlightElement(document.getElementById('card-' + actualQuestionId));
      }
  } else {
      // --- 일반 문항 ---
      setTimeout(() => {
          let el = document.getElementById('input-' + actualQuestionId);
          
          if (!el) {
              // Radio/Checkbox 찾기
              const verFormId = surveyForms.value[foundFormIdx].ver_form_id;
              el = document.querySelector(`input[name*="${actualQuestionId}"]`);
          }
          
          if (!el) {
              // 그룹 Div 찾기
              el = document.getElementById('group-' + actualQuestionId);
          }

          if (el) {
              const container = el.closest('.ps-4') || el.closest('.card-body');
              highlightElement(el, (el.type === 'radio' || el.type === 'checkbox') ? container : null);
          } else {
              // 최후의 수단: 카드 전체
              highlightElement(document.getElementById('card-' + actualQuestionId));
          }
      }, 100);
  }
};
</script>

<style scoped>
.collector-header { z-index: 1050; }
.card { border-radius: 12px; }
.cursor-pointer { cursor: pointer; }
.hover-effect:hover { background-color: #f8f9fa !important; border-color: #ffc107 !important; }
.nav-pills .nav-link { color: #6c757d; font-weight: 600; }
.nav-pills .nav-link.active { background-color: #0d6efd; color: white; }
.table th { font-size: 0.85rem; font-weight: 700; letter-spacing: -0.5px; }
.table-responsive { overflow-x: auto; }
.dashed-border { border: 2px dashed #dee2e6; transition: all 0.2s; }
.dashed-border:hover { 
  border-color: #0d6efd; 
  background-color: #e7f1ff; 
  color: #0d6efd !important; 
}
</style>