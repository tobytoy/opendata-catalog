# 實戰範例集（Catalog YAML Examples）

本文件提供三種最常見的開放資料分享情境範例。無論你是想把**自己整理的公開 CSV／JSON 分享給 AI Agent 使用**，或是**收錄政府／第三方開放資料 API**，都可以直接複製最接近的範例改寫。

> **注意**：以下範例中的網域（如 `example.org`）僅供格式教學參考；實際提交至 `sources/` 前，請務必填入真實可存取的網址，並執行 `python scripts/validate.py --check-urls` 驗證通過。

---

## 範例 1：個人或社群分享的靜態公開資料（CSV / JSON）

**適用場景**：你整理了一份公開資料（例如各縣市夜市清單、公開活動時程、開源基準資料集），放在 GitHub Raw、GitHub Pages、Gist 或靜態檔案空間，**沒有 API 伺服器，也不需要任何金鑰**，只要提供 `download_url` 即可讓 AI 下載解析。

**檔案路徑**：`sources/community-taiwan-datasets.yaml`（`provider.id` 須為 `"community-taiwan-datasets"`）

```yaml
catalog_version: "1.0.0"
schema_version: "1.0"
last_updated: "2026-11-26T12:00:00+08:00"
maintainer: "@community-maintainer"
changelog:
  - version: "1.0.0"
    date: "2026-11-26"
    note: "初始建立社群維護之公開靜態資料目錄，收錄臺灣節慶市集與縣市代碼對照表"

provider:
  id: "community-taiwan-datasets"
  name: "社群整理臺灣公開基礎資料集"
  summary: "由開源社群整理並託管於公開靜態空間的臺灣行政區代碼、節慶與常用對照 CSV/JSON 資料"
  organization: "OpenData Community"
  homepage: "https://example.org/community-taiwan-datasets"
  license: "CC BY 4.0"
  license_url: "https://creativecommons.org/licenses/by/4.0/"
  rate_limit: "靜態檔案無速率限制，建議讀取後於本地暫存"
  auth:
    required: false
    type: "None"
    how_to_get: "公開靜態檔案，免申請即可直接透過 HTTP GET 下載"

datasets:
  - id: "tw_county_codes"
    name: "臺灣縣市與英文代碼對照表"
    category: "共通對照"
    publisher: "OpenData Community"
    source_page: "https://example.org/community-taiwan-datasets/county-codes"
    ai_usage_guide: >
      當需要將使用者輸入的中文縣市名稱（含「臺」與「台」異體字，如「台北市」或「臺北市」）
      轉換為政府 API 常用之英文代碼（如 Taipei、NewTaipei）或內政部標準行政區代碼時使用。
      檔案含 UTF-8 BOM（UTF-8-SIG），使用 Python csv 模組讀取時請指定 encoding="utf-8-sig"。
    tags: ["縣市代碼", "行政區", "對照表", "臺與台轉換"]
    format: "CSV"
    encoding: "UTF-8-SIG"
    method: "GET"
    update_frequency: "行政區異動時更新"
    download_url: "https://example.org/community-taiwan-datasets/data/tw_county_codes.csv"
    sample_url: "https://example.org/community-taiwan-datasets/data/tw_county_codes.csv"
    fields:
      - name: "county_name_zh"
        type: "string"
        description: "正體中文縣市名稱（統一使用「臺」，如臺北市、臺中市）"
      - name: "county_name_alt"
        type: "string"
        description: "常見異體寫法（如台北市、台中市）"
      - name: "tdx_city_code"
        type: "string"
        description: "交通部 TDX 平臺使用之英文縣市代碼（如 Taipei、NewTaipei）"
      - name: "iso_3166_2"
        type: "string"
        description: "ISO 3166-2:TW 區域代碼（如 TW-TPE）"
```

### 為什麼這樣寫 AI 會好用？
1. **`encoding: "UTF-8-SIG"`**：提醒 Python 讀取 CSV 時避開 BOM 字元導致第一欄鍵名變成 `\ufeffcounty_name_zh`。
2. **`ai_usage_guide` 講明橋接用途**：AI 一看就知道這份表是用來做「中文縣市名 ↔ `tdx_city_code`」的翻譯橋樑。

---

## 範例 2：需要 API Key 的開放資料 API

**適用場景**：資料平臺提供統一的 `base_url`，底下的多個資料集透過相對 `endpoint` 查詢，且需要在 Query String 或 HTTP Header 帶入免費申請的 API Key。

**檔案路徑**：`sources/example-env-api.yaml`

```yaml
catalog_version: "1.0.0"
schema_version: "1.0"
last_updated: "2026-11-26T12:00:00+08:00"
maintainer: "@contributor-handle"
changelog:
  - version: "1.0.0"
    date: "2026-11-26"
    note: "新增環境監測開放 API 目錄，包含即時空氣品質測站與雨量資料集"

provider:
  id: "example-env-api"
  name: "範例環境感測開放資料平臺"
  summary: "提供空氣品質、PM2.5、紫外線與微氣候感測器即時觀測數據之 REST JSON API"
  organization: "環境感測示範計畫"
  homepage: "https://api.example.org/"
  docs_url: "https://api.example.org/swagger"
  base_url: "https://api.example.org/v2"
  license: "政府資料開放授權條款-第1版"
  rate_limit: "免費金鑰每日上限 5,000 次請求"
  auth:
    required: true
    type: "API Key (Query Parameter)"
    param_name: "api_key"
    env_vars:
      - "ENV_API_KEY"
    how_to_get: "至平臺官網註冊免費開發者帳號後，於個人控制台核發 API Key"
    notes: >
      呼叫時請從環境變數 ENV_API_KEY 讀取金鑰並帶入 Query Parameter (?api_key=...)，
      切勿將金鑰寫死於程式碼或提交至版本控制。

datasets:
  - id: "air_quality_latest"
    name: "即時空氣品質監測指標"
    category: "環境監測"
    ai_usage_guide: >
      當使用者詢問「現在某縣市空氣好不好、PM2.5 數值、AQI 等級」時查詢。
      注意縣市篩選須使用正體「臺」（如「臺北市」），且回傳數值欄位可能因測站維護而回傳字串 "-" 或空字串，
      轉型為浮點數前須先做空值防呆。
    tags: ["空氣品質", "AQI", "PM2.5", "即時監測"]
    format: "JSON"
    encoding: "UTF-8"
    method: "GET"
    update_frequency: "每小時更新"
    endpoint: "/air_quality_latest"
    sample_url: "https://api.example.org/v2/air_quality_latest?limit=1"
    parameters:
      - name: "county"
        in: "query"
        type: "string"
        required: false
        example: "臺北市"
        description: "篩選縣市名稱（須使用正體「臺」）"
      - name: "limit"
        in: "query"
        type: "integer"
        required: false
        default: 100
        example: 20
        description: "單次最大回傳筆數"
    fields:
      - name: "sitename"
        type: "string"
        description: "測站名稱（如：中山、板橋）"
      - name: "county"
        type: "string"
        description: "所在縣市名稱"
      - name: "aqi"
        type: "integer"
        unit: "指標值"
        description: "空氣品質指標（0-50 良好、51-100 普通、101-150 對敏感族群不健康）"
      - name: "pm25"
        type: "float"
        unit: "μg/m³"
        description: "細懸浮微粒小時濃度（維護時可能為 '-'）"
      - name: "publishtime"
        type: "datetime"
        format: "YYYY/MM/DD HH:mm:ss"
        description: "資料發布時間"
```

### 安全重點提醒
- `env_vars` 寫的是 `ENV_API_KEY`（變數名稱），**不是**真實金鑰字串。
- 如果在公開環境沒有設定金鑰，AI Agent 讀到 `auth.required: true` 與 `how_to_get` 後，會主動告訴使用者先申請並設定環境變數，而不會盲目撞牆。

---

## 範例 3：含路徑參數與 OAuth2 認證的進階 API

**適用場景**：RESTful 網址本身帶有路徑參數（如 `/City/{City}` 或 `/Station/{StationID}`），且使用 OAuth 2.0 `client_credentials` 換發短期 Bearer Token。

可參考倉庫內已實際驗證通過的真實範例：
- [`sources/tw-tdx.yaml`](../sources/tw-tdx.yaml)（涵蓋 OAuth2 Token 端點、路徑佔位符 `{City}` / `{OriginStationID}`、OData `$filter` 與巢狀欄位 `Stations[].StationName` 寫法）
- [`sources/tw-data-gov.yaml`](../sources/tw-data-gov.yaml)（涵蓋動態詮釋資料查詢 `/api/v2/rest/dataset/{datasetId}`、大型匯出檔案串流提醒與民國年日期格式說明）

### 路徑參數的關鍵規則回顧

```yaml
endpoint: "/v2/Bus/EstimatedTimeOfArrival/City/{City}"
sample_url: "https://tdx.transportdata.tw/api/basic/v2/Bus/EstimatedTimeOfArrival/City/Taipei?$top=1&$format=JSON"
parameters:
  - name: "City"          # 必須與 {City} 完全同名
    in: "path"            # 必須明確標示為 path
    type: "string"
    required: true
    example: "Taipei"     # 必須提供 example
    description: "縣市英文代碼（如 Taipei、NewTaipei、Taichung、Kaohsiung）"
```
