<template>
  <div class="workbench-wrapper">
    <header class="workbench-header">
      <div class="header-left">
        <i class="bi bi-layout-text-sidebar-reverse me-2"></i>
        <input type="text" v-model="surveyTitle" class="survey-title-input" placeholder="조사표 제목을 입력하세요">
      </div>

      <div class="header-right d-flex gap-2">
        <button class="btn btn-sm btn-outline-light me-2" @click="openPreview">
          <i class="bi bi-eye"></i> 미리보기
        </button>
        <button class="btn btn-sm btn-primary" :disabled="!currentVersionId" @click="handleSave(false)">
          <i class="bi bi-save me-1"></i> 현재 버전에 저장
        </button>
        <button class="btn btn-sm btn-success" @click="handleSave(true)">
          <i class="bi bi-plus-circle me-1"></i> 신규 버전 저장
        </button>
        <div class="vr mx-1" style="background-color: white; opacity: 0.5;"></div>
        <button class="btn btn-sm btn-danger" @click="closeModal">
          <i class="bi bi-x-lg"></i> 닫기
        </button>
      </div>
    </header>

    <div class="workbench-body">
      <aside class="sidebar-left">
        <div class="section-title">문항 항목 (Pool)</div>
        <draggable
          :list="questionPool"
          :group="{ name: 'questions', pull: 'clone', put: false }"
          :clone="cloneQuestion"
          item-key="type"
          class="pool-list"
        >
          <template #item="{ element }">
            <div class="pool-item">
              <i :class="getIconByType(element.type)" class="me-2 text-primary"></i>
              {{ element.label }}
            </div>
          </template>
        </draggable>
      </aside>

      <main class="design-canvas">
        <div class="canvas-list-wrapper">
          <draggable v-model="designItems" group="questions" item-key="id" class="canvas-list" ghost-class="ghost-item" handle=".drag-handle">
            <template #item="{ element, index }">
              <div class="canvas-item" :class="{ active: selectedId === element.id, 'border-danger': element.hasError }" @click="selectItem(element)">
                <div class="drag-handle"><i class="bi bi-grip-vertical"></i></div>
                <div class="item-number">Q{{ index + 1 }}</div>
                <div class="item-content">
                  <div class="item-label">
                    <i :class="getIconByType(element.type)" class="me-1 small text-muted"></i>
                    {{ element.label }}
                    <span v-if="element.hasError" class="badge bg-danger ms-2" style="font-size: 10px;">설정 오류</span>
                  </div>
                  
                  <div class="item-preview">
                    <input v-if="element.type === 'text' || element.type === 'number'" 
                           type="text" class="form-control form-control-sm w-50" disabled 
                           :placeholder="element.type === 'number' ? '숫자만 입력 가능' : '주관식 입력란'">
                    
                    <div v-else-if="element.type === 'radio' || element.type === 'checkbox'" class="d-flex flex-wrap gap-3">
                      <label v-for="(opt, oIdx) in ensureArray(element.options)" :key="oIdx" class="small text-secondary">
                        <input :type="element.type" disabled> {{ opt }}
                      </label>
                    </div>

                    <div v-else-if="element.type === 'table'" class="table-preview-container">
                      <table class="table table-sm table-bordered mb-0 bg-light small shadow-sm">
                        <thead>
                          <tr class="table-secondary text-center">
                            <th v-if="element.useRowHeaders" class="bg-warning-subtle" style="width: 100px;">항목</th>
                            <th v-for="col in ensureArray(element.columns)" :key="col">{{ col }}</th>
                          </tr>
                        </thead>
                        <tbody>
                          <template v-if="element.useRowHeaders">
                            <tr v-for="row in ensureArray(element.rowLabels)" :key="row">
                              <td class="bg-light fw-bold text-center">{{ row }}</td>
                              <td v-for="col in ensureArray(element.columns)" :key="col" class="bg-white"></td>
                            </tr>
                          </template>
                          <template v-else>
                            <tr v-for="n in 2" :key="n">
                              <td v-for="col in ensureArray(element.columns)" :key="col" class="bg-white" style="height: 25px;"></td>
                            </tr>
                          </template>
                        </tbody>
                      </table>
                      <div class="text-end mt-1" v-if="!element.useRowHeaders">
                        <small class="text-primary">+ 행 추가 버튼 활성화</small>
                      </div>
                    </div>
                  </div>
                </div>
                <button class="btn-delete" @click.stop="removeItem(index)"><i class="bi bi-trash3"></i></button>
              </div>
            </template>
            
            <template #header>
              <div v-if="designItems.length === 0" class="empty-canvas-msg-inner">
                <i class="bi bi-plus-circle display-4 mb-3"></i>
                <p>좌측 항목을 이 영역으로 드래그하여<br>조사표를 구성하세요.</p>
              </div>
            </template>
          </draggable>
        </div>
      </main>

      <aside class="sidebar-right">
        <div class="section-title">문항 상세 속성</div>
        <div v-if="selectedItem" class="property-form">
          <div class="mb-3">
            <label class="form-label small fw-bold">질문 내용</label>
            <textarea v-model="selectedItem.label" class="form-control form-control-sm" rows="2" @input="validateCurrentItem"></textarea>
          </div>

          <div v-if="selectedItem.type === 'radio' || selectedItem.type === 'checkbox'" class="mb-3">
            <label class="form-label small fw-bold">옵션 설정 (콤마로 구분)</label>
            <textarea 
              :value="Array.isArray(selectedItem.options) ? selectedItem.options.join(', ') : selectedItem.options"
              @input="e => { updateList(selectedItem, 'options', e.target.value); validateCurrentItem(); }"
              class="form-control form-control-sm" placeholder="예: 매우만족, 보통, 불만족" rows="3"></textarea>
          </div>

          <div v-if="selectedItem.type === 'table'" class="table-property-group border-top pt-3">
            <div class="mb-3">
              <label class="form-label small fw-bold text-primary">열(Header) 설정 (콤마 구분)</label>
              <textarea 
                :value="Array.isArray(selectedItem.columns) ? selectedItem.columns.join(', ') : selectedItem.columns"
                @input="e => { updateList(selectedItem, 'columns', e.target.value); validateCurrentItem(); }"
                class="form-control form-control-sm" placeholder="예: 이름, 나이, 연락처" rows="2"></textarea>
            </div>

            <div class="form-check form-switch mb-3">
              <input class="form-check-input" type="checkbox" v-model="selectedItem.useRowHeaders" id="useRowHeaderCheck" @change="validateCurrentItem">
              <label class="form-check-label small fw-bold" for="useRowHeaderCheck">표측(행 머리글) 사용</label>
            </div>

            <div v-if="selectedItem.useRowHeaders" class="mb-3">
              <label class="form-label small fw-bold text-primary">표측(왼쪽 질의) 입력 (콤마 구분)</label>
              <textarea 
                :value="Array.isArray(selectedItem.rowLabels) ? selectedItem.rowLabels.join(', ') : selectedItem.rowLabels"
                @input="e => { updateList(selectedItem, 'rowLabels', e.target.value); validateCurrentItem(); }"
                class="form-control form-control-sm" placeholder="예: 가구주, 배우자, 자녀1" rows="3"></textarea>
            </div>
          </div>

          <div v-if="selectedItem.hasError" class="alert alert-danger py-2 small">
            <i class="bi bi-exclamation-triangle-fill me-2"></i> {{ selectedItem.errorMsg }}
          </div>
        </div>
        <div v-else class="empty-property-msg">
          <i class="bi bi-pencil-square mb-2"></i>
          <p>문항을 선택하면 속성을 수정할 수 있습니다.</p>
        </div>
      </aside>
    </div>

    <div v-if="isPreviewOpen" class="preview-overlay" @click.self="closePreview">
      <div class="preview-content card shadow-lg">
        <div class="card-header bg-dark text-white d-flex justify-content-between align-items-center">
          <h5 class="mb-0"><i class="bi bi-eye"></i> 조사표 미리보기</h5>
          <button class="btn-close btn-close-white" @click="closePreview"></button>
        </div>
        <div class="card-body overflow-auto p-5 bg-light">
          <div class="preview-paper shadow-sm mx-auto">
            <h3 class="text-center mb-5 fw-bold text-primary">{{ surveyTitle }}</h3>
            <div v-for="(item, idx) in designItems" :key="item.id" class="preview-item mb-5 pb-5 border-bottom">
              <div class="fw-bold mb-3 fs-5">{{ idx + 1 }}. {{ item.label }}</div>
              
              <div v-if="item.type === 'text' || item.type === 'number'" class="ps-3">
                <input :type="item.type === 'number' ? 'number' : 'text'" class="form-control" :placeholder="item.label + ' 입력'">
              </div>
              
              <div v-else-if="item.type === 'radio' || item.type === 'checkbox'" class="ps-3">
                <div v-for="opt in ensureArray(item.options)" :key="opt" class="form-check form-check-inline me-4">
                  <input :type="item.type" :name="'q'+item.id" class="form-check-input" :id="item.id+opt">
                  <label class="form-check-label" :for="item.id+opt">{{ opt }}</label>
                </div>
              </div>

              <div v-else-if="item.type === 'table'" class="ps-3">
                <div class="table-responsive">
                  <table class="table table-bordered align-middle shadow-sm">
                    <thead class="table-light text-center">
                      <tr>
                        <th v-if="!item.useRowHeaders" style="width: 50px;">#</th>
                        <th v-if="item.useRowHeaders" class="bg-warning-subtle" style="width: 140px;">항목</th>
                        <th v-for="col in ensureArray(item.columns)" :key="col">{{ col }}</th>
                        <th v-if="!item.useRowHeaders" style="width: 60px;">삭제</th>
                      </tr>
                    </thead>
                    <tbody>
                      <template v-if="item.useRowHeaders">
                        <tr v-for="row in ensureArray(item.rowLabels)" :key="row">
                          <td class="bg-light fw-bold text-center">{{ row }}</td>
                          <td v-for="col in ensureArray(item.columns)" :key="col">
                            <input type="text" class="form-control form-control-sm border-0 shadow-none">
                          </td>
                        </tr>
                      </template>
                      <template v-else>
                        <tr>
                          <td class="text-center">1</td>
                          <td v-for="col in ensureArray(item.columns)" :key="col">
                            <input type="text" class="form-control form-control-sm border-0 shadow-none">
                          </td>
                          <td class="text-center"><button class="btn btn-link text-danger p-0"><i class="bi bi-x-circle"></i></button></td>
                        </tr>
                      </template>
                    </tbody>
                  </table>
                  <button v-if="!item.useRowHeaders" class="btn btn-sm btn-outline-primary mt-2"><i class="bi bi-plus"></i> 행 추가</button>
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
import { ref, onMounted, onUnmounted } from 'vue';
import draggable from 'vuedraggable';

const currentSurveyId = ref(null);
const surveyTitle = ref('조사표 설계 작업대');
const currentVersionId = ref(null);
const questionPool = ref([]);
const designItems = ref([]);
const selectedId = ref(null);
const selectedItem = ref(null);
const isPreviewOpen = ref(false);

const getIconByType = (type) => {
  const map = {
    'text': 'bi bi-fonts', 'number': 'bi bi-hash',
    'radio': 'bi bi-ui-checks-grid', 'checkbox': 'bi bi-check-all',
    'table': 'bi bi-table' // 테이블 전용 아이콘
  };
  return map[type] || 'bi bi-question-square';
};

const ensureArray = (options) => {
  if (!options) return [];
  if (Array.isArray(options)) return options;
  return options.split(',').map(s => s.trim()).filter(s => s !== '');
};

// 범용 리스트 업데이트 (콤마 문자열 -> 배열)
const updateList = (item, field, val) => {
  item[field] = val.split(',').map(s => s.trim()).filter(s => s !== '');
};

const validateCurrentItem = () => {
  if (!selectedItem.value) return;
  const item = selectedItem.value;
  item.hasError = false;
  item.errorMsg = "";

  if (!item.label || item.label.trim() === "") {
    item.hasError = true;
    item.errorMsg = "질문 내용은 필수입니다.";
  } else if ((item.type === 'radio' || item.type === 'checkbox') && ensureArray(item.options).length === 0) {
    item.hasError = true;
    item.errorMsg = "객관식 옵션을 최소 하나 이상 입력하세요.";
  } else if (item.type === 'table') {
    if (ensureArray(item.columns).length === 0) {
      item.hasError = true;
      item.errorMsg = "테이블의 열(Header) 정보를 입력하세요.";
    } else if (item.useRowHeaders && ensureArray(item.rowLabels).length === 0) {
      item.hasError = true;
      item.errorMsg = "표측을 사용할 경우 행(Row) 라벨 정보를 입력하세요.";
    }
  }
};

const handleInitEvent = (event) => {
  const { surveyId, surveyName, initialData, versionId, questionPool: receivedPool } = event.detail;
  currentSurveyId.value = surveyId;
  surveyTitle.value = surveyName || '조사표 설계';
  currentVersionId.value = versionId || null;
  questionPool.value = receivedPool || [];
  
  if (initialData) {
    const parsed = typeof initialData === 'string' ? JSON.parse(initialData) : initialData;
    designItems.value = parsed.map(item => ({
      ...item,
      options: ensureArray(item.options),
      columns: ensureArray(item.columns || []),
      rowLabels: ensureArray(item.rowLabels || []),
      useRowHeaders: item.useRowHeaders || false,
      hasError: false
    }));
  }
};

onMounted(() => { window.addEventListener('init-survey-editor', handleInitEvent); });
onUnmounted(() => { window.removeEventListener('init-survey-editor', handleInitEvent); });

const cloneQuestion = (origin) => {
  return {
    ...JSON.parse(JSON.stringify(origin)),
    id: 'q_' + Date.now(),
    options: ensureArray(origin.options),
    columns: ensureArray(origin.columns || []),
    rowLabels: ensureArray(origin.rowLabels || []),
    useRowHeaders: origin.useRowHeaders || false,
    hasError: false
  };
};

const selectItem = (item) => {
  selectedId.value = item.id;
  selectedItem.value = item;
};

const removeItem = (index) => {
  if (confirm('이 문항을 삭제할까요?')) {
    designItems.value.splice(index, 1);
    selectedItem.value = null;
    selectedId.value = null;
  }
};

const openPreview = () => { isPreviewOpen.value = true; };
const closePreview = () => { isPreviewOpen.value = false; };

const handleSave = async (isNew) => {
  if (designItems.value.length === 0) return alert('설계된 문항이 없습니다.');

  let errorCount = 0;
  designItems.value.forEach(item => {
    // 모든 항목 강제 검증 로직 실행
    if (!item.label || item.label.trim() === "" || 
       ((item.type === 'radio' || item.type === 'checkbox') && ensureArray(item.options).length === 0) ||
       (item.type === 'table' && (ensureArray(item.columns).length === 0 || (item.useRowHeaders && ensureArray(item.rowLabels).length === 0)))) {
      item.hasError = true;
      errorCount++;
    }
  });

  if (errorCount > 0) {
    alert(`설정에 오류가 있는 문항이 ${errorCount}건 있습니다. 확인해 주세요.`);
    return;
  }

  const mode = isNew ? "신규 버전" : "현재 버전";
  if (!confirm(`${mode}으로 저장하시겠습니까?`)) return;

  try {
    const response = await fetch(`/questionnaire/${currentSurveyId.value}/save/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || '' },
      body: JSON.stringify({
        design_data: designItems.value,
        version_id: isNew ? null : currentVersionId.value,
        is_new_version: isNew
      })
    });
    const result = await response.json();
    if (response.ok) {
      alert(result.message);
      currentVersionId.value = result.version_id;
      window.dispatchEvent(new CustomEvent('version-saved', { detail: { q_id: currentSurveyId.value } }));
    }
  } catch (e) { alert("서버 통신 오류"); }
};

const closeModal = () => { if (confirm('작업을 종료하시겠습니까?')) location.reload(); };
</script>

<style scoped>
.workbench-wrapper { display: flex; flex-direction: column; height: 100vh; background: #f1f3f5; font-family: 'Pretendard', sans-serif; }
.workbench-header { height: 50px; background: #212529; color: white; display: flex; justify-content: space-between; align-items: center; padding: 0 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
.survey-title-input { background: transparent; border: none; border-bottom: 1px solid #495057; color: #fff; font-weight: bold; width: 300px; padding: 2px 5px; }
.workbench-body { display: flex; flex: 1; overflow: hidden; }
.sidebar-left, .sidebar-right { width: 300px; background: #fff; border: 1px solid #dee2e6; padding: 20px; overflow-y: auto; }

/* 캔버스 및 안내 문구 */
.design-canvas { flex: 1; background: #dee2e6; padding: 30px; overflow-y: auto; display: flex; justify-content: center; }
.canvas-list-wrapper { width: 100%; max-width: 850px; min-height: 100%; }
.canvas-list { min-height: 100%; background: #fff; border-radius: 8px; padding: 35px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); position: relative; }
.empty-canvas-msg-inner { position: absolute; top: 45%; left: 50%; transform: translate(-50%, -50%); color: #adb5bd; text-align: center; width: 100%; }

/* 문항 아이템 디자인 */
.canvas-item { display: flex; align-items: flex-start; padding: 20px; border: 1px solid #f1f3f5; margin-bottom: 18px; border-radius: 10px; position: relative; cursor: pointer; background: white; transition: all 0.2s; }
.canvas-item:hover { border-color: #dee2e6; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
.canvas-item.active { border-color: #0d6efd; background: #f8faff; box-shadow: 0 0 0 2px rgba(13, 110, 253, 0.15); }
.canvas-item.border-danger { border: 2px solid #dc3545 !important; }

/* 테이블 컨테이너 */
.table-preview-container { margin-top: 12px; border: 1px dashed #dee2e6; padding: 8px; border-radius: 6px; background: #fafafa; }

/* 미리보기 스타일 */
.preview-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.75); z-index: 2000; display: flex; align-items: center; justify-content: center; }
.preview-content { width: 95%; height: 92%; max-width: 1100px; display: flex; flex-direction: column; border: none; }
.preview-paper { background: white; padding: 60px 80px; min-height: 100%; width: 100%; max-width: 900px; }

.section-title { font-size: 0.88rem; font-weight: 700; color: #444; margin-bottom: 18px; border-left: 4px solid #0d6efd; padding-left: 12px; }
.pool-item { padding: 12px 15px; background: #f8f9fa; border: 1px solid #e9ecef; margin-bottom: 10px; border-radius: 8px; cursor: grab; font-size: 0.88rem; font-weight: 500; }
.pool-item:hover { background: #fff; border-color: #0d6efd; color: #0d6efd; }
.drag-handle { cursor: grab; color: #ccc; margin-right: 15px; font-size: 1.2rem; }
.item-number { background: #0d6efd; color: white; width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: bold; margin-right: 15px; }
.item-content { flex: 1; }
.item-label { font-size: 1rem; color: #333; }
.btn-delete { background: none; border: none; color: #ced4da; position: absolute; right: 15px; top: 15px; transition: color 0.2s; }
.btn-delete:hover { color: #dc3545; }
.ghost-item { opacity: 0.4; background: #e7f5ff !important; border: 2px dashed #339af0 !important; }
</style>