<template>
  <div class="workbench-wrapper">
    <header class="workbench-header">
      <div class="header-left">
        <button class="btn btn-sm btn-outline-secondary me-3 border-0 text-white" @click="isLeftOpen = !isLeftOpen" title="패널 토글">
          <i class="bi" :class="isLeftOpen ? 'bi-layout-sidebar-inset' : 'bi-layout-sidebar'"></i>
        </button>
        <i class="bi bi-layout-text-sidebar-reverse me-2"></i>
        <input type="text" v-model="surveyTitle" class="survey-title-input" placeholder="조사표 제목">
        <div class="vr mx-3 bg-white opacity-25"></div>
        <button class="btn btn-sm btn-outline-warning text-white" @click="addAgMappingTable">
          <i class="bi bi-grid-3x3 me-1"></i> 테이블 생성
        </button>
      </div>
      <div class="header-right d-flex gap-2 align-items-center">
        
        <button class="btn btn-sm btn-light px-3 shadow-sm d-inline-flex align-items-center justify-content-center fixed-height-btn" 
                @click="openPreview">
          <i class="bi bi-eye me-2"></i>미리보기
        </button>
        
        <button class="btn btn-sm btn-primary px-3 shadow-sm d-inline-flex align-items-center justify-content-center fixed-height-btn" 
                @click="handleSave(false)" title="현재 버전에 덮어쓰기">
          <i class="bi bi-save me-2"></i>저장
        </button>
        
        <button class="btn btn-sm btn-success px-3 shadow-sm d-inline-flex align-items-center justify-content-center fixed-height-btn" 
                @click="handleSave(true)" title="새로운 버전으로 저장">
          <i class="bi bi-file-earmark-plus me-2"></i>새 버전 저장
        </button>

        <button class="btn btn-sm btn-danger px-3 shadow-sm d-inline-flex align-items-center justify-content-center fixed-height-btn" 
                @click="closeModal">
          <i class="bi bi-x-lg me-2"></i>닫기
        </button>
        
        <button class="btn btn-sm btn-outline-secondary border-0 text-white d-inline-flex align-items-center justify-content-center fixed-height-btn" 
                style="width: 36px;" 
                @click="isRightOpen = !isRightOpen">
          <i class="bi fs-5" :class="isRightOpen ? 'bi-layout-sidebar-inset-reverse' : 'bi-layout-sidebar-reverse'"></i>
        </button>
      </div>
    </header>

    <div class="workbench-body">
      <aside class="sidebar-left shadow-sm" :class="{ 'closed': !isLeftOpen }">
        <div class="sidebar-header bg-success bg-opacity-10 border-bottom d-flex justify-content-between align-items-center">
          <h5 class="m-0 fw-bold text-success text-truncate" v-if="isLeftOpen"><i class="bi bi-list-check me-2"></i>조사 항목</h5>
          <i class="bi bi-list-check fs-4 text-success mx-auto" v-else></i>
        </div>
        <div class="sidebar-content p-3" v-show="isLeftOpen">
          <draggable :list="questionPool" :group="{ name: 'questions', pull: 'clone', put: false }" :clone="cloneQuestion" :move="checkMove" item-key="id" :sort="false" draggable=".pool-item:not(.used-item)">
            <template #item="{ element }">
              <div class="pool-item shadow-sm border" :class="{ 'used-item': isItemUsed(element.id) }" @click="scrollToCanvasItem(element.id)">
                <div class="d-flex align-items-center">
                  <i :class="[getIconByType(element.type), element.type === 'table' ? 'text-primary' : 'text-success']" class="me-2 fs-5"></i>
                  <span class="text-truncate fw-medium small">{{ element.label }}</span>
                </div>
                <div class="pool-id-badge">{{ element.id }}</div>
                <i v-if="isItemUsed(element.id)" class="bi bi-check-circle-fill text-success used-badge"></i>
              </div>
            </template>
          </draggable>
        </div>
      </aside>

      <main class="design-canvas" id="canvas-scroll-area">
        <DesignCanvas v-model="designItems" :selectedId="selectedId" @select="selectItem" @remove="removeItem" />
      </main>

      <aside class="sidebar-right shadow-sm" :class="{ 'closed': !isRightOpen }">
        <div class="sidebar-header bg-primary bg-opacity-10 border-bottom d-flex justify-content-between align-items-center">
          <h5 class="m-0 fw-bold text-primary text-truncate" v-if="isRightOpen"><i class="bi bi-gear-fill me-2"></i>속성 설정</h5>
          <i class="bi bi-gear-fill fs-4 text-primary mx-auto" v-else></i>
        </div>
        <div v-if="isRightOpen">
          <div v-if="selectedItem" class="sidebar-content p-3 overflow-auto">
            <div class="property-group mb-4">
              <label class="form-label fw-bold text-dark">질문 문구 수정</label>
              <textarea v-model="selectedItem.label" class="form-control form-control-sm border-2" rows="3"></textarea>
            </div>
            
            <div v-if="selectedItem.type === 'table'" class="property-group mb-4 p-3 bg-white border border-primary-subtle rounded shadow-sm">
              <label class="form-label fw-bold text-primary border-bottom pb-2 w-100">테이블 헤더 수정</label>
              <div class="row g-2 mt-2">
                <div v-for="sub in (selectedItem.subItems || [])" :key="sub.id" class="col-12">
                  <div class="input-group input-group-sm">
                    <span class="input-group-text small" style="width: 75px;">{{ sub.id }}</span>
                    <input type="text" v-model="sub.label" class="form-control">
                  </div>
                </div>
              </div>
            </div>

            <div v-if="selectedItem.tableType === 'fixed'" class="property-group mb-4 p-3 bg-white border border-danger-subtle rounded">
              <label class="form-label fw-bold text-danger border-bottom pb-2 w-100">표측(행 라벨) 입력</label>
              <textarea :value="Array.isArray(selectedItem.rowLabels) ? selectedItem.rowLabels.join(', ') : selectedItem.rowLabels" @change="e => selectedItem.rowLabels = e.target.value.split(',').map(s=>s.trim()).filter(s=>s)" class="form-control form-control-sm" rows="5"></textarea>
            </div>
            
            <div v-if="selectedItem.type === 'mapping-table'" class="property-group mb-4 p-3 bg-white border rounded">
               <label class="form-label fw-bold text-dark">엑셀형 Grid 크기</label>
               <div class="row g-2">
                 <div class="col-6"><label class="small text-muted">행(Row)</label><input type="number" v-model.number="selectedItem.rowCount" class="form-control form-control-sm"></div>
                 <div class="col-6"><label class="small text-muted">열(Col)</label><input type="number" v-model.number="selectedItem.colCount" class="form-control form-control-sm"></div>
               </div>
            </div>
          </div>
          <div v-else class="h-100 d-flex flex-column align-items-center justify-content-center text-muted opacity-50 p-4">
            <i class="bi bi-cursor-fill display-4 mb-3"></i>
            <p class="text-center">수정할 문항을 선택하세요</p>
          </div>
        </div>
      </aside>
    </div>

    <div v-if="isPreviewOpen" class="preview-overlay" @click.self="isPreviewOpen = false">
      <div class="preview-modal">
        <div class="preview-header bg-dark text-white p-2 d-flex justify-content-between align-items-center">
          <h6 class="m-0 fw-bold ps-2"><i class="bi bi-eye me-2"></i>실시간 미리보기</h6>
          <button class="btn-close btn-close-white" @click="isPreviewOpen = false"></button>
        </div>
        <div class="preview-body p-0">
          <SurveyCollector :is-preview="true" :initial-data="previewData" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import draggable from 'vuedraggable';
import DesignCanvas from './canvas/DesignCanvas.vue';
import SurveyCollector from './SurveyCollector.vue';

const surveyTitle = ref('신규 조사표 설계');
const currentSurveyId = ref(null);
const currentVersionId = ref(null);
const questionPool = ref([]);
const designItems = ref([]);
const selectedId = ref(null);
const selectedItem = ref(null);
const isPreviewOpen = ref(false);
const isLeftOpen = ref(true);
const isRightOpen = ref(true);
const previewData = ref(null);

const getIconByType = (type) => {
  const map = { 'text': 'bi bi-fonts', 'number': 'bi bi-hash', 'radio': 'bi bi-ui-checks-grid', 'checkbox': 'bi bi-check-all', 'table': 'bi bi-table', 'mapping-table': 'bi bi-grid-3x3' };
  return map[type] || 'bi bi-question-square';
};

const cloneQuestion = (origin) => {
  const clone = JSON.parse(JSON.stringify(origin));
  clone.id = origin.id + '_' + Date.now();
  clone.originId = origin.id; 
  if (clone.type === 'table') {
    clone.subItems = clone.subItems || [];
    clone.rowLabels = clone.rowLabels || [];
  }
  return clone;
};

// [수정] 매핑 테이블 내부의 셀까지 확인하여 사용 여부 판단
const isItemUsed = (originId) => {
  return designItems.value.some(item => {
    if (item.originId === originId || item.id === originId) return true;
    if (item.type === 'mapping-table' && item.cells) {
      return Object.values(item.cells).some(c => c.originId === originId || c.id === originId);
    }
    return false;
  });
};

const checkMove = (evt) => {
  if (isItemUsed(evt.draggedContext.element.id)) return false;
  return true;
};

// [수정] 매핑 테이블 내부 항목일 경우 부모 테이블로 스크롤
const scrollToCanvasItem = (originId) => {
  if (!isItemUsed(originId)) return;
  
  const targetItem = designItems.value.find(item => {
    if (item.originId === originId || item.id === originId) return true;
    if (item.type === 'mapping-table' && item.cells) {
      return Object.values(item.cells).some(c => c.originId === originId || c.id === originId);
    }
    return false;
  });

  if (targetItem) {
    selectedId.value = targetItem.id;
    selectedItem.value = targetItem;
    if (!isRightOpen.value) isRightOpen.value = true;
    setTimeout(() => {
      const el = document.getElementById(`q-${targetItem.id}`);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        el.classList.add('highlight-effect');
        setTimeout(() => el.classList.remove('highlight-effect'), 1500);
      }
    }, 100);
  }
};

const addAgMappingTable = () => {
  designItems.value.push({
    id: 'map_' + Date.now(),
    label: '신규 엑셀형 매핑 테이블',
    type: 'mapping-table',
    tableType: 'mapping',
    rowCount: 5,
    colCount: 4,
    cells: {},
    cellTexts: {},
    hasError: false
  });
};

const selectItem = (item) => {
  selectedId.value = item.id;
  selectedItem.value = item;
  if (!isRightOpen.value) isRightOpen.value = true;
};

const removeItem = (index) => {
  if (confirm('삭제하시겠습니까?')) {
    designItems.value.splice(index, 1);
    selectedItem.value = null;
    selectedId.value = null;
  }
};

const openPreview = () => {
  previewData.value = {
    dataId: null,
    respondentId: 'PREVIEW_TEST',
    forms: [{
      ver_form_id: 'preview_v1',
      form_name: surveyTitle.value,
      design_data: JSON.parse(JSON.stringify(designItems.value))
    }]
  };
  isPreviewOpen.value = true;
};

const handleInitEvent = (event) => {
  const { surveyId, surveyName, initialData, versionId, questionPool: pool } = event.detail;
  currentSurveyId.value = surveyId;
  surveyTitle.value = surveyName || '조사표 설계';
  currentVersionId.value = versionId;
  questionPool.value = pool || [];
  if (initialData) {
    const data = typeof initialData === 'string' ? JSON.parse(initialData) : initialData;
    designItems.value = (data || []).map(item => ({ ...item, subItems: item.subItems || [], rowLabels: item.rowLabels || [] }));
  }
};

onMounted(() => window.addEventListener('init-survey-editor', handleInitEvent));
onUnmounted(() => window.removeEventListener('init-survey-editor', handleInitEvent));

const handleSave = async (isNew) => {
  if(!confirm(isNew ? '새로운 버전으로 저장하시겠습니까?' : '현재 버전에 덮어쓰시겠습니까?')) return;
  try {
    const payload = { design_data: designItems.value, is_new_version: isNew, version_id: currentVersionId.value };
    const response = await fetch(`/questionnaire/${currentSurveyId.value}/save/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || '' },
      body: JSON.stringify(payload)
    });
    const resData = await response.json();
    if (response.ok) {
      alert(resData.message || '저장되었습니다.');
      if(resData.version_id) currentVersionId.value = resData.version_id;
    } else {
      alert('저장 실패: ' + (resData.message || '오류 발생'));
    }
  } catch (e) { alert('통신 오류: ' + e); }
};

const closeModal = () => { if(confirm('종료하시겠습니까?')) location.reload(); };
</script>

<style scoped>
/* (기존 CSS 동일) */
.workbench-wrapper { display: flex; flex-direction: column; height: 100vh; width: 100%; background: #f1f5f9; overflow: hidden; position: fixed; top: 0; left: 0; right: 0; bottom: 0; z-index: 1000; }
.workbench-header { height: 60px; background: #0f172a; padding: 0 25px; display: flex; justify-content: space-between; align-items: center; color: white; flex-shrink: 0; z-index: 100; }
.workbench-body { display: flex; flex: 1; width: 100%; overflow: hidden; }
.sidebar-left, .sidebar-right { transition: width 0.3s ease; background: #fff; flex-shrink: 0; display: flex; flex-direction: column; overflow: hidden; }
.sidebar-left { width: 300px; border-right: 1px solid #e2e8f0; }
.sidebar-right { width: 350px; border-left: 1px solid #e2e8f0; }
.sidebar-left.closed, .sidebar-right.closed { width: 60px; }
.closed .sidebar-header h5, .closed .sidebar-content { display: none; }
.sidebar-header { padding: 12px 15px; flex-shrink: 0; height: 50px; display: flex; align-items: center; }
.sidebar-content { flex: 1; overflow-y: auto; }
.design-canvas { flex: 1; min-width: 0; background: #cbd5e1; padding: 20px; overflow-y: auto; display: flex; justify-content: center; }
.pool-item { background: white; border: 1px solid #e2e8f0; border-radius: 8px; position: relative; cursor: grab; padding: 12px; margin-bottom: 12px; transition: all 0.2s; }
.pool-item:hover { border-color: #3b82f6; transform: translateX(5px); }
.pool-item.used-item { background-color: #f8f9fa; opacity: 0.6; cursor: pointer; border-color: #e9ecef; }
.pool-item.used-item:hover { transform: none; border-color: #e9ecef; }
.used-badge { position: absolute; right: 10px; top: 35%; font-size: 1.2rem; }
.pool-id-badge { position: absolute; top: -5px; right: 5px; font-size: 0.6rem; color: #94a3b8; background: #f8fafc; border: 1px solid #e2e8f0; padding: 0 4px; border-radius: 4px; }
.survey-title-input { background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); color: white; width: 350px; border-radius: 4px; padding: 5px 15px; outline: none; }
.preview-overlay { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(15, 23, 42, 0.75); z-index: 10000; display: flex; align-items: center; justify-content: center; backdrop-filter: blur(8px); }
.preview-modal { width: 95%; height: 95%; background: white; border-radius: 20px; overflow: hidden; display: flex; flex-direction: column; }
.preview-body { flex: 1; overflow-y: auto; background: #f1f5f9; padding: 0; }
:deep(.highlight-effect) { box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.5) !important; border-color: #3b82f6 !important; transition: all 0.3s ease; }
/* [수정] 버튼 높이 및 정렬 강제 통일 */
.fixed-height-btn {
  height: 36px !important;       /* 높이 고정 (36px) */
  line-height: 1 !important;     /* 글자 높이 정렬 */
  border: 1px solid transparent; /* 테두리 공간 확보 (색상은 transparent로 자동 처리) */
  vertical-align: middle;        /* 수직 정렬 */
}

/* btn-light 등 배경색이 있는 버튼의 테두리가 묻히지 않도록 미세 조정 */
.btn-light.fixed-height-btn {
  border-color: #dee2e6 !important;
}

</style>