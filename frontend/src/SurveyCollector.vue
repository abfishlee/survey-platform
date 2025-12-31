<template>
  <div class="collector-container bg-light min-vh-100">
    <header class="collector-header bg-primary text-white p-3 shadow-sm sticky-top d-flex justify-content-between align-items-center">
      <div>
        <h5 class="mb-0 fw-bold"><i class="bi bi-pencil-fill me-2"></i>조사 데이터 입력</h5>
        <small class="opacity-75" v-if="respondentId">대상 ID: {{ respondentId }}</small>
      </div>
      <div class="d-flex gap-2">
        <button class="btn btn-success fw-bold px-4" @click="saveAllData">
          <i class="bi bi-cloud-arrow-up me-1"></i>최종 저장
        </button>
        <button class="btn btn-outline-light" @click="closeModal">닫기</button>
      </div>
    </header>

    <div class="container py-4">
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
            <div class="d-flex mb-3">
              <span class="badge bg-primary me-2 align-self-start mt-1">Q{{ qIdx + 1 }}</span>
              <h5 class="fw-bold mb-0 text-dark">{{ q.label }}</h5>
            </div>

            <div class="ps-4">
              <input v-if="q.type === 'text' || q.type === 'number'" 
                     :type="q.type" class="form-control" 
                     v-model="answers[currentForm.ver_form_id][q.id]"
                     :placeholder="q.label + ' 입력'">

              <div v-else-if="q.type === 'radio'" class="d-flex flex-wrap gap-4 mt-2">
                <div v-for="opt in ensureArray(q.options)" :key="opt" class="form-check">
                  <input class="form-check-input" type="radio" :name="q.id" :value="opt" 
                         v-model="answers[currentForm.ver_form_id][q.id]" :id="q.id+opt">
                  <label class="form-check-label cursor-pointer" :for="q.id+opt">{{ opt }}</label>
                </div>
              </div>

              <div v-else-if="q.type === 'checkbox'" class="d-flex flex-wrap gap-4 mt-2">
                <div v-for="opt in ensureArray(q.options)" :key="opt" class="form-check">
                  <input class="form-check-input" type="checkbox" :value="opt" 
                         v-model="answers[currentForm.ver_form_id][q.id]" :id="q.id+opt">
                  <label class="form-check-label cursor-pointer" :for="q.id+opt">{{ opt }}</label>
                </div>
              </div>

              <div v-else-if="q.type === 'table'" class="table-responsive border rounded bg-white p-3 shadow-sm">
                <table class="table table-bordered align-middle">
                  <thead class="table-light text-center">
                    <tr>
                      <th v-if="q.useRowHeaders" style="width: 150px;" class="bg-warning-subtle small fw-bold">항목(표측)</th>
                      <th v-else style="width: 50px;" class="small fw-bold">#</th>
                      <th v-for="col in ensureArray(q.columns)" :key="col" class="small fw-bold">{{ col }}</th>
                      <th v-if="!q.useRowHeaders" style="width: 50px;"></th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(row, rIdx) in answers[currentForm.ver_form_id][q.id]" :key="rIdx">
                      <td v-if="q.useRowHeaders" class="text-center bg-light fw-bold small text-secondary">
                        {{ ensureArray(q.rowLabels)[rIdx] }}
                      </td>
                      <td v-else class="text-center small text-muted">{{ rIdx + 1 }}</td>
                      
                      <td v-for="col in ensureArray(q.columns)" :key="col">
                        <input type="text" v-model="row[col]" class="form-control form-control-sm border-0 shadow-none text-center">
                      </td>
                      
                      <td v-if="!q.useRowHeaders" class="text-center">
                        <button class="btn btn-link text-danger p-0" @click="removeTableRow(q.id, rIdx)">
                          <i class="bi bi-x-circle"></i>
                        </button>
                      </td>
                    </tr>
                  </tbody>
                </table>
                <button v-if="!q.useRowHeaders" class="btn btn-sm btn-outline-primary mt-2" @click="addTableRow(q.id, q.columns)">
                  <i class="bi bi-plus"></i> 행 추가
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';

// --- 상태 관리 ---
const dataId = ref(null);
const respondentId = ref('');
const surveyForms = ref([]);
const activeFormIdx = ref(0);
const answers = ref({}); // 구조: { "버전ID": { "문항ID": "값" } }

const currentForm = computed(() => surveyForms.value[activeFormIdx.value]);

// 유틸리티: 문자열을 배열로 변환
const ensureArray = (val) => {
  if (!val) return [];
  if (Array.isArray(val)) return val;
  return val.split(',').map(s => s.trim()).filter(s => s !== '');
};

// --- Django에서 보낸 데이터 수신 ---
const handleInit = (event) => {
  const { dataId: id, respondentId: rid, forms } = event.detail;
  dataId.value = id;
  respondentId.value = rid;
  surveyForms.value = forms;

  // 답변 데이터 구조 초기화 (기존 저장값 있으면 로드)
  forms.forEach(form => {
    const formAns = {};
    form.design_data.forEach(q => {
      const saved = form.saved_values ? form.saved_values[q.id] : null;
      
      if (q.type === 'table') {
        if (q.useRowHeaders) {
          // 표측형: 표측 라벨 개수만큼 행 생성
          formAns[q.id] = saved || ensureArray(q.rowLabels).map(() => ({}));
        } else {
          // 일반형: 최소 1행 생성
          formAns[q.id] = saved || [{}];
        }
      } else if (q.type === 'checkbox') {
        formAns[q.id] = saved || [];
      } else {
        formAns[q.id] = saved || '';
      }
    });
    answers.value[form.ver_form_id] = formAns;
  });
};

onMounted(() => { window.addEventListener('init-survey-collector', handleInit); });

// 테이블 행 관리
const addTableRow = (qId, columns) => {
  const rowObj = {};
  ensureArray(columns).forEach(c => rowObj[c] = '');
  answers.value[currentForm.value.ver_form_id][qId].push(rowObj);
};
const removeTableRow = (qId, idx) => {
  answers.value[currentForm.value.ver_form_id][qId].splice(idx, 1);
};

// 최종 저장
const saveAllData = async () => {
  if (!confirm("입력한 내용을 모두 저장하시겠습니까?")) return;
  
  try {
    const response = await fetch(`/data/${dataId.value}/save-survey/`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json', 
        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || '' 
      },
      body: JSON.stringify({ answers: answers.value })
    });
    const result = await response.json();
    if (response.ok) {
      alert("데이터가 성공적으로 저장되었습니다.");
      location.reload();
    } else {
      alert("저장 실패: " + result.message);
    }
  } catch (e) {
    alert("서버 통신 중 오류가 발생했습니다.");
  }
};

const closeModal = () => { if(confirm("종료하시겠습니까? 입력 중인 데이터는 사라질 수 있습니다.")) location.reload(); };
</script>

<style scoped>
.collector-header { z-index: 1050; }
.card { border-radius: 12px; transition: transform 0.2s; }
.cursor-pointer { cursor: pointer; }
.nav-pills .nav-link { color: #555; font-weight: 500; }
.nav-pills .nav-link.active { background-color: #0d6efd; color: white; }
.table th { font-size: 0.8rem; letter-spacing: -0.5px; }
</style>