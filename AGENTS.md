# AGENTS.md — AI Agent 檢索與維護操作手冊

本倉庫採用 **Data Catalog as Code（程式碼化的開放資料目錄）** 架構，將各開放資料平臺與機關之 API 端點、下載連結、認證機制與欄位定義標準化為獨立 YAML 檔案。所有進入本倉庫執行**資料查詢**或**目錄維護**的 AI Agent，請務必遵循以下規範。

---

## 一、 兩階段漸進式導航（Progressive Retrieval）

為避免一次載入全部 YAML 耗盡 Context Window 並降低檢索精準度，請嚴格執行兩階段讀取：

1. **第一階段：讀取根目錄 [`llms.txt`](llms.txt)**
   - `llms.txt` 僅數十行，列出所有已收錄平臺的一句話摘要、資料集數量、認證需求與對應 YAML 路徑。
   - 根據使用者問題快速鎖定目標來源檔案（例如：空氣品質、碳足跡與水質鎖定 `sources/tw-moenv.yaml`；交通時刻與即時路況鎖定 `sources/tw-tdx.yaml`；國定假日、統編稅籍、上市股價或跨部會資料探索鎖定 `sources/tw-data-gov.yaml`）。
2. **第二階段：精準讀取目標 `sources/<provider-id>.yaml`**
   - 只讀取與任務相關的單一或少數 YAML 檔。
   - 仔細閱讀該資料集的 `ai_usage_guide`、`parameters`、`encoding` 與 `fields` 後再組裝 HTTP 請求或資料解析程式。

> 若需要由外部系統透過程式碼一次載入全部結構化索引，請直接讀取自動編譯產物 [`dist/full-catalog.json`](dist/full-catalog.json)，切勿手動修改 `dist/` 或 `llms.txt`。

---

## 二、 API 呼叫與資料解析關鍵規則

### 1. 端點網址組裝規則
- **相對路徑 (`endpoint`)**：將 `provider.base_url`（去除結尾 `/`）加上 `dataset.endpoint`。若路徑含 `{Param}` 佔位符（如 `/v2/Bus/EstimatedTimeOfArrival/City/{City}`），請對照 `parameters` 中 `in: "path"` 的說明與 `example` 替換。
- **直接下載 (`download_url`)**：直接使用完整網址發送請求，無須拼接 `base_url`。

### 2. 認證與金鑰安全（Authentication）
- 若 `provider.auth.required` 為 `false`：可直接發送 HTTP `GET` 請求（建議附帶清楚的 `User-Agent` 並遵守 `rate_limit`）。
- 若 `provider.auth.required` 為 `true`：
  - 依 `provider.auth.env_vars` 指定的環境變數名稱向執行環境讀取憑證（例如 `TDX_CLIENT_ID`、`TDX_CLIENT_SECRET`）。
  - **OAuth2 Client Credentials（如 TDX 平臺）**：先對 `provider.auth.token_url` 發送 `POST`（`Content-Type: application/x-www-form-urlencoded`，內含 `grant_type=client_credentials`、`client_id`、`client_secret`）取得 `access_token` 並於本地快取，再於資料請求標頭帶入 `Authorization: Bearer <access_token>`。
  - 若環境中未設定所需金鑰，請先向使用者說明申請方式（參考 `provider.auth.how_to_get`）或評估是否符合低頻訪客模式限制，切勿猜測或硬編碼任何金鑰。

### 3. 臺灣開放資料常見實務陷阱（Domain Gotchas）
- **正體異體字（「臺」與「台」）**：臺灣政府機關與臺鐵站名、縣市名多採用正體「**臺**」（如 `臺北市`、`臺中市`、`臺南市`、`臺東縣`），但部分商業或高鐵站名可能使用「**台**」（如高鐵 `台北`、`台中`）。撰寫過濾條件前請先查閱該資料集的 `fields` 與 `parameters` 說明。
- **民國紀年轉換**：財稅、證交所、健保等資料常使用民國年（如 `1151126` 代表 `115 + 1911 = 2026` 年 `11` 月 `26` 日；`0950315` 代表 `2006-03-15`）。解析日期前務必確認 `fields[].format`。
- **檔案編碼與大型檔案處理**：
  - 注意 `dataset.encoding`（常見 `UTF-8`、含 BOM 的 `UTF-8-SIG`、以及舊系統如全字庫索引的 `BIG5`）。
  - 針對全站總目錄匯出或全國稅籍壓縮檔（數十至數百 MB），必須使用 Python 串流或分塊讀取過濾，禁止將原始巨型檔案直接輸出至對話視窗。
- **動態資源連結查詢（`data.gov.tw`）**：許多按年度上架的政府資料集（如辦公日曆表、健保申報量）每年會新增不同下載網址。可優先呼叫 `https://data.gov.tw/api/v2/rest/dataset/{datasetId}` 動態取得 `result.distribution` 內最新年度的 `resourceDownloadUrl`。

---

## 三、 目錄維護與安全規範（給維護本倉庫的 AI Agent）

當受託新增開放資料網站或修改 `sources/*.yaml` 時，請先閱讀 [多人協作與公開資料分享指南](docs/contributing-guide.md) 與 [YAML 欄位完整規格書](docs/schema-spec.md)（範本可參考 [空白範本](docs/templates/source-template.yaml) 與 [實戰範例集](docs/examples.md)），並嚴格遵守以下鐵律：

1. **嚴禁寫入任何私人或機敏資訊（Public Repo Zero-PII Policy）**
   - 本倉庫為公開儲存庫，**絕對不可**在任何檔案中出現：API Key、Client Secret、Access Token、個人真實姓名與私人信箱、手機電話號碼、機關承辦人個人聯絡電話/信箱、本機絕對路徑、或本機專屬環境名稱。
2. **一來源一檔案原則**
   - 每個資料平臺或部會獨立維護於 `sources/<provider-id>.yaml`，檔名必須與 `provider.id` 完全一致（kebab-case，如 `tw-tdx.yaml`、`tw-data-gov.yaml`）。
3. **真實端點驗證**
   - 新增任何資料集前，請實際探測 API 或網頁確認端點存活（HTTP 200）且欄位名稱與真實回傳一致，切勿憑空臆測路徑或欄位名稱。
4. **版號同步與自動化編譯**
   - 每次修改 `sources/*.yaml` 時，必須同步遞增 `catalog_version`（語意化版本）、更新 `last_updated`（ISO 8601）並在 `changelog` 最上方新增紀錄。
   - 提交前依序執行：
     ```bash
     python scripts/validate.py --check-urls
     python scripts/build_index.py
     ```
   - 確認 Schema 驗證、隱私掃描、端點存活檢查全數通過，且 `llms.txt` 與 `dist/full-catalog.json` 已同步更新。
