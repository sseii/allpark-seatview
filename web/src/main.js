// 화면 전환 뼈대. 각 화면은 담당자가 별도 파일(src/pages/*.js)로 만들어 연결한다.
const pages = {
  main: "공연 목록 (웹 담당)",
  seat: "3D 좌석 시야 뷰어 (3D 담당)",
  arrival: "권장 도착 시간대·주차장 혼잡 그래프 (분석 결과 JSON 연결)",
  barrierfree: "휠체어석 시야·검증 경로 지도",
  after: "출차 정체 예상·유실물 조회",
};

function render() {
  const key = location.hash.replace("#", "") || "main";
  document.getElementById("app").innerHTML =
    `<section><h2>${key}</h2><p>${pages[key] ?? "없는 화면"}</p></section>`;
}

window.addEventListener("hashchange", render);
render();
