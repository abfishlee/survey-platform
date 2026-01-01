<template>
  <div class="card shadow-sm border-0">
    <div class="card-header bg-white py-3 d-flex justify-content-between align-items-center">
        <h5 class="mb-0 fw-bold text-secondary">
          <i class="bi bi-bar-chart-steps me-2"></i>자료 분석 설계
        </h5>
        <div>
            <a :href="`/survey/${surveyId}/analysis/list/`" class="btn btn-outline-secondary btn-sm fw-bold me-2">
                <i class="bi bi-list-ul me-1"></i>저장된 목록
            </a>

            <button class="btn btn-primary btn-sm fw-bold" @click="saveAnalysis">
                <i class="bi bi-save me-1"></i>분석 주제 저장
            </button>
        </div>
    </div>

    <div class="card-body p-0">
      <div id="custom-pivot-wrapper">
         <div ref="pivotContainer"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue';
import WebDataRocks from 'webdatarocks';
import 'webdatarocks/webdatarocks.css'; // 기본 CSS (깨짐 방지)
import koLocal from '@/ko.json';

const surveyId = window.SURVEY_ID_FROM_DJANGO;
const pivotContainer = ref(null);
let webdatarocksInstance = null;

// CSRF Token 가져오기 (Django POST 요청 필수)
const getCsrfToken = () => {
  return document.cookie.split('; ')
    .find(row => row.startsWith('csrftoken='))
    ?.split('=')[1];
};

// [기능] 분석 저장 함수
const saveAnalysis = async () => {
    // 1. WebDataRocks의 현재 상태(JSON) 추출
    const report = webdatarocksInstance.getReport();
    
    // 2. 제목 입력 받기
    const title = prompt("저장할 분석 주제의 제목을 입력하세요:", "새 분석 보고서");
    if (!title) return;

    try {
        // 3. 서버로 전송
        const response = await fetch(`/survey/${surveyId}/analysis/save/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({
                title: title,
                description: "관리자에 의해 생성됨",
                report: report // 여기가 핵심! 설정을 통째로 보냄
            })
        });

        const result = await response.json();
        if (result.status === 'success') {
            alert("성공적으로 저장되었습니다! 💾");
        } else {
            alert("저장 실패: " + result.message);
        }
    } catch (e) {
        console.error(e);
        alert("서버 통신 중 오류가 발생했습니다.");
    }
};

const getPivotConfig = (jsonData) => ({
  container: pivotContainer.value,
  toolbar: true,
  height: 750,
  width: "100%",
  
  // [추가] 툴바 커스터마이징: '저장(save)' 탭 제거하기
  beforetoolbarcreated: (toolbar) => {
    const tabs = toolbar.getTabs();
    toolbar.getTabs = function() {
        // id가 'wdr-tab-save'인 것만 빼고 리턴 (저장 버튼 숨김)
        return tabs.filter(tab => tab.id !== "wdr-tab-save");
    }
  },

  global: {
    localization: koLocal 
  },
  report: {
    dataSource: { data: jsonData },
    options: {
      grid: {
        type: "compact",
        showTotals: "yes",
        showGrandTotals: "yes" 
      }
    },
    slice: {
      rows: [{ uniqueName: "권역" }],
      columns: [{ uniqueName: "상태" }],
      measures: [{ uniqueName: "ID", aggregation: "count", caption: "응답자 수" }]
    }
  }
});

onMounted(async () => {
  try {
    const response = await fetch(`/survey/${surveyId}/pivot-data/`);
    const jsonData = await response.json();
    if (pivotContainer.value) {
      webdatarocksInstance = new WebDataRocks(getPivotConfig(jsonData));
    }
  } catch (e) {
    if (pivotContainer.value) webdatarocksInstance = new WebDataRocks(getPivotConfig([]));
  }
});

onBeforeUnmount(() => {
  if (webdatarocksInstance) webdatarocksInstance.dispose();
});
</script>

<style scoped>
/* 추가 스타일 없음 (순정 사용) */
</style>