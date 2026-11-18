"""
올팍 시트뷰 — 공공데이터 내려받기·확인 스크립트

[준비]
  pip install requests pandas
  같은 폴더에 keys.json 을 만들고 API 키를 넣는다 (GitHub에 올리지 말 것):
    {"입출차": "키", "연계": "키", "공연": "키", "유실물": "키"}
  아래 CONFIG 의 url 칸에 각 데이터 상세 페이지의 '요청주소'를 붙여 넣는다.

[사용법]
  python kspo_check.py test 공연              응답 구조와 컬럼 이름 확인 (1페이지만)
  python kspo_check.py fetch 입출차           전체 내려받기 (끊겨도 다시 실행하면 이어받기)
  python kspo_check.py merge 입출차           받은 페이지를 data/입출차.csv 하나로 합치기
  python kspo_check.py cols 입출차            합친 CSV의 컬럼 이름과 앞부분 보기

  python kspo_check.py check4 --date 날짜컬럼 --venue 공연장컬럼
  python kspo_check.py check5 --in 입차컬럼 --out 출차컬럼 --zone 주차구역컬럼
  python kspo_check.py check6 --date 날짜컬럼 --hour 시간컬럼 --count 차량대수컬럼 --in 입차컬럼 --out 출차컬럼
  (컬럼 이름은 cols 명령으로 확인한 실제 이름을 넣는다)
"""
import sys, os, json, time, glob, argparse
import xml.etree.ElementTree as ET
import requests
import pandas as pd

CONFIG = {
    "입출차": {"url": "https://api.kcisa.kr/openapi/API_CPM_008/request", "rows": 1000},   # 15159093
    "연계":   {"url": "https://api.kcisa.kr/openapi/API_CPM_009/request", "rows": 10000},   # 15164822
    "공연":   {"url": "https://api.kcisa.kr/openapi/service/rest/meta/KSCperf", "rows": 100},    # 3037877
    "유실물": {"url": "https://api.kcisa.kr/openapi/service/rest/meta/KSClost", "rows": 100},    # 15038496
}
EXTRA = {"keyword": ""}   # api.kcisa.kr 안내: 조회조건이 있으면 빈 값이라도 keyword= 를 붙여 호출
DAILY_LIMIT = 990          # 개발계정 일 1,000회 제한에서 여유분을 뺀 값
CONG_ZONES = ["P1A", "P1B", "P2", "P4", "P5", "P6", "P7", "P8", "P9", "P10", "P11"]  # 혼잡도 데이터의 주차구역


def key(name):
    if os.environ.get(f"KEY_{name}"):
        return os.environ[f"KEY_{name}"]
    with open("keys.json", encoding="utf-8") as f:
        return json.load(f)[name]


def call(name, page):
    c = CONFIG[name]
    if not c["url"]:
        sys.exit(f"CONFIG['{name}']['url'] 에 요청주소를 넣어 주세요.")
    p = {"serviceKey": key(name), "pageNo": page, "numOfRows": c["rows"], **EXTRA, **c.get("params", {})}
    r = requests.get(c["url"], params=p, timeout=180)
    r.encoding = r.apparent_encoding
    return r


def parse(text):
    """JSON 또는 XML 응답에서 item 목록과 totalCount를 꺼낸다."""
    try:
        d = json.loads(text)
        body = d.get("response", d).get("body", d.get("response", d))
        items = body.get("items", [])
        if isinstance(items, dict):
            items = items.get("item", [])
        if isinstance(items, dict):
            items = [items]
        return items, int(body.get("totalCount", 0) or 0)
    except (ValueError, AttributeError):
        root = ET.fromstring(text)
        items = [{ch.tag: ch.text for ch in it} for it in root.iter("item")]
        tc = root.find(".//totalCount")
        return items, int(tc.text) if tc is not None and tc.text else 0


def cmd_test(name):
    r = call(name, 1)
    print("HTTP", r.status_code)
    print(r.text[:1500])
    try:
        items, total = parse(r.text)
        print(f"\n전체 {total}건, 이번 페이지 {len(items)}건")
        if items:
            print("컬럼:", list(items[0].keys()))
            if total:
                print(f"필요한 호출 수: 약 {-(-total // CONFIG[name]['rows'])}회")
    except Exception as e:
        print("\n파싱 실패 — 위 원문을 보고 EXTRA 의 type 값을 바꿔 보세요:", e)


def cmd_fetch(name):
    d = f"pages/{name}"
    os.makedirs(d, exist_ok=True)
    page = len(glob.glob(f"{d}/*.txt")) + 1
    print(f"{page}페이지부터 시작")
    calls = 0
    while calls < DAILY_LIMIT:
        try:
            r = call(name, page); calls += 1
        except requests.exceptions.RequestException as e:
            print(f"{page}페이지 연결 오류, 20초 후 재시도:", e); time.sleep(20); continue
        if r.status_code in (429, 500, 502, 503, 504):
            print(f"{page}페이지 서버 응답 {r.status_code}, 30초 기다렸다 재시도"); time.sleep(30); continue
        items, total = parse(r.text) if r.status_code == 200 else ([], 0)
        if r.status_code != 200 or not items:
            print(f"중단: {page}페이지 (HTTP {r.status_code})", r.text[:200])
            break
        with open(f"{d}/{page:05d}.txt", "w", encoding="utf-8") as f:
            f.write(r.text)
        print(f"{page}페이지 완료 / 전체 약 {-(-total // CONFIG[name]['rows'])}페이지")
        if page * CONFIG[name]["rows"] >= total > 0:
            print("전부 받았습니다."); break
        page += 1
        time.sleep(5)


def cmd_merge(name):
    rows = []
    for fp in sorted(glob.glob(f"pages/{name}/*.txt")):
        with open(fp, encoding="utf-8") as f:
            rows += parse(f.read())[0]
    os.makedirs("data", exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(f"data/{name}.csv", index=False, encoding="utf-8-sig")
    print(f"data/{name}.csv 저장: {len(df)}행, 컬럼 {list(df.columns)}")


def load(name):
    return pd.read_csv(f"data/{name}.csv", low_memory=False)


def cmd_cols(name):
    df = load(name)
    print(df.dtypes); print(df.head(10).to_string())


def cmd_check4(a):
    df = load("연계")
    print("[공연장 값 목록]"); print(df[a.venue].value_counts(dropna=False).to_string())
    n = df.dropna(subset=[a.venue]).groupby(a.date)[a.venue].nunique()
    print(f"\n복수 공연일(같은 날 공연장 2곳 이상): {(n > 1).sum()}일 / 공연 있는 날 {len(n)}일")


def cmd_check5(a):
    df = load("입출차")
    ins, out = pd.to_datetime(df[a.in_], errors="coerce"), pd.to_datetime(df[a.out], errors="coerce")
    print(f"출차일시 결측: {out.isna().mean()*100:.2f}%  ({out.isna().sum()}건 / {len(df)}건)")
    dur = (out - ins).dt.total_seconds() / 3600
    print(f"주차 시간(시간) 분포:\n{dur.describe().to_string()}")
    print(f"24시간 초과: {(dur > 24).mean()*100:.2f}%")
    zones = df[a.zone].astype(str).value_counts()
    print("\n[주차구역 값]"); print(zones.to_string())
    miss = [z for z in CONG_ZONES if z not in zones.index]
    print("\n혼잡도 데이터 구역명과 일치:", "모두 일치" if not miss else f"없는 구역 {miss}")


def cmd_check6(a):
    lk = load("연계")
    dt = pd.to_datetime(lk[a.date].astype(str) + " " + lk[a.hour].astype(str).str.zfill(2) + ":00", errors="coerce")
    print(f"날짜+시간 변환 실패: {dt.isna().sum()}행 (0이 아니면 --hour 형식 확인)")
    print(f"날짜+시간 중복: {dt.duplicated().sum()}개")
    full = pd.date_range("2025-01-01", "2025-12-31 23:00", freq="h")
    print(f"2025년 중 빠진 시간대: {len(full.difference(dt.dropna()))}개 / {len(full)}개")
    print("\n[컬럼별 결측 수]"); print(lk.isna().sum().to_string())
    raw = load("입출차")
    ins, out = pd.to_datetime(raw[a.in_], errors="coerce"), pd.to_datetime(raw[a.out], errors="coerce")
    print("\n[차량 대수 = 입차? 점유?] 무작위 5개 시간대 비교")
    for h in dt.dropna().sample(5, random_state=1).sort_values():
        n_in = ((ins >= h) & (ins < h + pd.Timedelta(hours=1))).sum()
        n_occ = ((ins <= h) & ((out > h) | out.isna())).sum()
        v = lk.loc[dt == h, a.count].values
        print(f"{h}  연계값 {v}  |  원천 입차 {n_in}  |  원천 점유 {n_occ}")

def cmd_perf():
    df = load("공연")
    print(f"전체 {len(df)}건")
    for c in ["extent", "temporalCoverage", "spatial"]:
        filled = df[c].notna() & (df[c].astype(str).str.strip() != "")
        print(f"{c}: 값 있음 {filled.mean()*100:.1f}%")
    print("\n[temporalCoverage 예시 15개]"); print(df["temporalCoverage"].dropna().sample(15, random_state=1).to_string())
    print("\n[extent 예시 15개]"); print(df["extent"].dropna().sample(15, random_state=1).to_string())
    print("\n[spatial 상위 20]"); print(df["spatial"].value_counts().head(20).to_string())
    y25 = df[df["temporalCoverage"].astype(str).str.contains("2025")]
    print(f"\n2025년 공연(temporalCoverage에 2025 포함): {len(y25)}건")
    print(y25[["title", "temporalCoverage", "extent", "spatial"]].head(15).to_string())

def cmd_perf2():
    df = load("공연")
    for c in ["extent", "temporalCoverage", "spatial"]:
        real = ~df[c].astype(str).str.strip().isin(["", ".", "nan"])
        print(f"{c}: 실제 값 있음 {real.mean()*100:.1f}%")
    print("\n[regDate 연도별 건수]")
    print(pd.to_datetime(df["regDate"], errors="coerce").dt.year.value_counts().sort_index().to_string())
    print("\n[최근 등록 10건]")
    print(df.sort_values("regDate", ascending=False)[["regDate", "title", "temporalCoverage", "extent", "spatial"]].head(10).to_string())

def cmd_perf3():
    df = load("공연")
    yrs = df["title"].astype(str).str.extract(r"(20\d\d)")[0].dropna().astype(int)
    print("[제목에 적힌 연도별 건수]"); print(yrs.value_counts().sort_index().to_string())

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd"); ap.add_argument("name", nargs="?")
    for o in ["date", "venue", "zone", "out", "hour", "count"]:
        ap.add_argument(f"--{o}")
    ap.add_argument("--in", dest="in_")
    a = ap.parse_args()
    {"test": lambda: cmd_test(a.name), "fetch": lambda: cmd_fetch(a.name),
     "merge": lambda: cmd_merge(a.name), "cols": lambda: cmd_cols(a.name),
     "check4": lambda: cmd_check4(a), "check5": lambda: cmd_check5(a),
     "check6": lambda: cmd_check6(a), "perf": cmd_perf, "perf2": cmd_perf2, "perf3": cmd_perf3}[a.cmd]()