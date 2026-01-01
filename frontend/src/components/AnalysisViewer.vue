<template>
  <div class="card shadow-sm border-0">
    <div class="card-header bg-white py-3">
        <h5 class="mb-0 fw-bold text-primary">
            <i class="bi bi-bar-chart-fill me-2"></i>{{ analysisTitle }}
        </h5>
    </div>
    <div class="card-body p-0">
      <div id="viewer-pivot-wrapper">
         <div ref="pivotContainer"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue';
import WebDataRocks from 'webdatarocks';
import 'webdatarocks/webdatarocks.css'; // 기본 스타일
import koLocal from '@/ko.json'; // 한글화

// HTML에서 전역 변수로 넘겨준 ID 받기
const analysisId = window.ANALYSIS_ID_FROM_DJANGO;
const analysisTitle = ref("분석 리포트 로딩 중...");
const pivotContainer = ref(null);
let webdatarocksInstance = null;

onMounted(async () => {
  try {
    // 1. 서버에서 저장된 설정(JSON) 가져오기
    const res = await fetch(`/survey/analysis/${analysisId}/json/`);
    const data = await res.json();

    if (data.status === 'success') {
        analysisTitle.value = data.title;
        const savedReport = data.report_config;

        // 2. WebDataRocks 초기화 (저장된 설정 주입)
        if (pivotContainer.value) {
            webdatarocksInstance = new WebDataRocks({
                container: pivotContainer.value,
                toolbar: true, // 툴바는 보여주되 저장 기능은 뺄 예정
                height: 750,
                width: "100%",
                global: { localization: koLocal },
                
                // [핵심] 저장된 리포트 설정을 그대로 넣습니다!
                report: savedReport,
                
                // 뷰어 전용 옵션 (저장 버튼 숨기기 등)
                beforetoolbarcreated: (toolbar) => {
                    const tabs = toolbar.getTabs();
                    toolbar.getTabs = function() {
                        // 저장, 연결, 열기 등 수정 관련 버튼 숨기기
                        return tabs.filter(tab => 
                            tab.id !== "wdr-tab-save" && 
                            tab.id !== "wdr-tab-connect" &&
                            tab.id !== "wdr-tab-open"
                        );
                    }
                }
            });
        }
    } else {
        alert("데이터를 불러오지 못했습니다.");
    }
  } catch (e) {
    console.error(e);
    alert("서버 오류가 발생했습니다.");
  }
});

onBeforeUnmount(() => {
  if (webdatarocksInstance) webdatarocksInstance.dispose();
});
</script>

<style>
/* 뷰어용 스타일 (AnalysisPivot.vue와 동일하게 유지하거나 수정 가능) */
#viewer-pivot-wrapper #wdr-component {
  font-family: 'Pretendard', sans-serif !important;
  font-size: 13px !important;
  background: white !important;
}
/* ... 필요하다면 이전에 만든 CSS 스타일을 여기에 붙여넣으세요 ... */
</style>