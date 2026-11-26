# YAML 欄位完整規格書（Catalog Schema Specification）

本文件對應 [`schemas/catalog.schema.json`](../schemas/catalog.schema.json)（Schema Version `1.0` / JSON Schema Draft 2020-12）與 [`scripts/validate.py`](../scripts/validate.py) 的所有語法與語意驗證規則，供**人類貢獻者**與 **AI Agent** 精準查閱。

> 所有物件皆設定 `additionalProperties: false`，表示**不可自行發明未定義的欄位名稱**，否則驗證將會失敗。

---

## 一、 檔案命名與頂層結構（Root Object）

- **檔案位置**：`sources/<provider-id>.yaml`（僅接受 `.yaml` 或 `.yml`，推薦統一用 `.yaml`）
- **核心對齊規則**：`檔名主體 == provider.id`（例如 `sources/my-city-bus.yaml` 內的 `provider.id` 必須是 `"my-city-bus"`）。

| 欄位名稱 | 型別 | 必填 | 格式／限制 | 說明 |
| :--- | :--- | :---: | :--- | :--- |
| `catalog_version` | `string` | 是 | `^\d+\.\d+\.\d+$` | 本 YAML 目錄文件的語意化版號（如 `"1.0.0"`）。 |
| `schema_version` | `string` | 是 | 固定值 `"1.0"` | 對應的 Schema 版本。 |
| `last_updated` | `string` | 是 | ISO 8601 含時區 | 例：`"2026-11-26T12:00:00+08:00"` 或 `"2026-11-26T04:00:00Z"`。 |
| `maintainer` | `string` | 是 | 非空字串 | 公開維護者識別（如 GitHub `@handle` 或社群名稱），**勿填 Email 或真實個資**。 |
| `changelog` | `array` | 是 | 至少 1 筆 | 版本異動紀錄陣列（見下方結構）；**第 0 筆的 `version` 必須等於 `catalog_version`**。 |
| `provider` | `object` | 是 | 物件 | 資料提供方共用設定（見第二節）。 |
| `datasets` | `array` | 是 | 至少 1 筆 | 收錄的資料集清單（見第三節）。 |

### `changelog[]` 子欄位

| 欄位名稱 | 型別 | 必填 | 格式／限制 | 說明 |
| :--- | :--- | :---: | :--- | :--- |
| `version` | `string` | 是 | `^\d+\.\d+\.\d+$` | 該次修改後的目錄版號。 |
| `date` | `string` | 是 | `YYYY-MM-DD` | 更新日期。 |
| `note` | `string` | 是 | 非空字串 | 本次新增、修正或棄用資料集的簡要說明。 |

---

## 二、 資料提供方設定（`provider`）

| 欄位名稱 | 型別 | 必填 | 格式／限制 | 說明 |
| :--- | :--- | :---: | :--- | :--- |
| `id` | `string` | 是 | `^[a-z0-9]+(-[a-z0-9]+)*$` | 全小寫 `kebab-case` 唯一識別碼，須與 YAML 檔名完全一致。 |
| `name` | `string` | 是 | 非空字串 | 平臺或資料提供專案的正式顯示名稱。 |
| `summary` | `string` | 是 | 長度 10–200 字元 | **一句話摘要**，會自動編譯進 `llms.txt` 作為 AI 第一階段檢索依據。 |
| `organization` | `string` | 否 | 非空字串 | 主管機關、團隊或發布組織名稱。 |
| `homepage` | `string` | 是 | `^https?://` | 平臺首頁或資料發布專案首頁（`--check-urls` 會檢查存活）。 |
| `docs_url` | `string` | 否 | `^https?://` | OpenAPI / Swagger 或使用說明文件網址。 |
| `base_url` | `string` | 否* | `^https?://[^/]+(/.*)?$` | API 共用根網址（**不可加結尾 `/`**）。若任何資料集使用 `endpoint`，則此欄必填。 |
| `license` | `string` | 是 | 非空字串 | 授權條款名稱（如 `政府資料開放授權條款-第1版`、`CC BY 4.0`、`MIT`）。 |
| `license_url` | `string` | 否 | `^https?://` | 授權條款全文連結。 |
| `rate_limit` | `string` | 否 | 字串 | 流量限制與快取建議說明。 |
| `auth` | `object` | 是 | 物件 | 存取認證規格（見下方結構）。 |

### `provider.auth` 子欄位

| 欄位名稱 | 型別 | 必填 | 格式／限制 | 說明 |
| :--- | :--- | :---: | :--- | :--- |
| `required` | `boolean` | 是 | `true` / `false` | 存取資料集是否必須帶入憑證。 |
| `type` | `string` | 是 | 列舉值（見右） | 允許值：`None`、`API Key (Query Parameter)`、`API Key (Header)`、`Bearer Token`、`OAuth2 Client Credentials (Bearer Token)`。 |
| `token_url` | `string` | 否 | `^https?://` | 當 `type` 為 OAuth2 Client Credentials 時，換發 Token 的 POST 網址。 |
| `header_name` | `string` | 否 | 字串 | 帶入憑證的 HTTP Header 名稱（如 `Authorization` 或 `X-API-Key`）。 |
| `param_name` | `string` | 否 | 字串 | 當 `type` 為 Query Parameter 時的參數名稱（如 `api_key`）。 |
| `env_vars` | `array` | 否 | `^[A-Z][A-Z0-9_]*$` | 建議存放憑證的環境變數名稱清單（**只寫變數名稱，絕不寫入真實值**）。 |
| `how_to_get` | `string` | 否 | 字串 | 說明如何註冊或免費申請金鑰。 |
| `notes` | `string` | 否 | 字串 | 補充認證細節（如 Token 效期、快取策略、Header 格式）。 |

---

## 三、 資料集清單（`datasets[]`）

每個資料集至少須提供 `endpoint` 或 `download_url` 其中之一（`anyOf` 規則）。

| 欄位名稱 | 型別 | 必填 | 格式／限制 | 說明 |
| :--- | :--- | :---: | :--- | :--- |
| `id` | `string` | 是 | `^[a-z0-9_]+(-[a-z0-9_]+)*$` | 在同一份 YAML 內唯一的資料集代碼（建議小寫蛇形或短橫線）。 |
| `name` | `string` | 是 | 非空字串 | 資料集顯示名稱。 |
| `category` | `string` | 否 | 非空字串 | 主題分類（如 `公共資訊`、`軌道運輸`、`環境監測`）。 |
| `publisher` | `string` | 否 | 非空字串 | 實際提供機關或作者（適合匯聚型平臺或多人專案標註來源）。 |
| `source_page` | `string` | 否 | `^https?://` | 該資料集的介紹網頁連結。 |
| `ai_usage_guide` | `string` | 是 | 最少 10 字元 | **AI Agent 判讀核心**：說明使用時機、前置步驟與欄位/編碼陷阱。 |
| `tags` | `array` | 是 | 至少 1 個、不可重複 | 關鍵字標籤清單，幫助 AI 與人類搜尋比對。 |
| `format` | `string` | 是 | 列舉值（見右） | 允許值：`JSON`、`CSV`、`XML`、`ZIP`、`GeoJSON`、`JSON / CSV`、`CSV / ZIP`、`JSON / XML`。 |
| `encoding` | `string` | 否 | 字串 | 檔案字元編碼（如 `UTF-8`、`UTF-8-SIG`、`BIG5`）。 |
| `method` | `string` | 否 | `GET` / `POST` | HTTP 請求方法，預設為 `GET`。 |
| `update_frequency` | `string` | 是 | 非空字串 | 更新頻率（如 `每分鐘更新`、`每日更新`、`不定期更新`）。 |
| `endpoint` | `string` | 條件必填 | 必須以 `/` 開頭 | 相對 API 路徑（搭配 `provider.base_url` 組合）。支援 `{Param}` 佔位符。 |
| `download_url` | `string` | 條件必填 | `^https?://` | 完整直接下載網址或獨立檔案連結（無須拼接 `base_url`）。 |
| `sample_url` | `string` | 否 | `^https?://` | **建議填寫**：含具體測試參數的完整公開網址，供 `--check-urls` 與 CI 健康檢查探測使用。 |
| `parameters` | `array` | 否 | 物件陣列 | 請求參數定義（見下方結構）。 |
| `fields` | `array` | 是 | 至少 1 筆 | 回傳欄位或 CSV 欄位定義（見下方結構）。 |

### `datasets[].parameters[]` 子欄位

> **重要語意規則**：只要 `endpoint` 中出現 `{ParamName}` 路徑佔位符，就**必須**在 `parameters` 中定義對應的 `name: "ParamName"` 且 `in: "path"`，並提供 `example`（或於資料集填寫 `sample_url`）。

| 欄位名稱 | 型別 | 必填 | 格式／限制 | 說明 |
| :--- | :--- | :---: | :--- | :--- |
| `name` | `string` | 是 | 非空字串 | 參數名稱（若為路徑參數須與 `{...}` 內完全一致）。 |
| `in` | `string` | 否 | `query` / `path` / `header` | 參數位置，預設為 `query`。 |
| `type` | `string` | 是 | `string` / `integer` / `number` / `boolean` | 參數資料型別。 |
| `required` | `boolean` | 是 | `true` / `false` | 是否為必填參數。 |
| `default` | `string\|int\|num\|bool` | 否 | — | 預設值。 |
| `example` | `string\|int\|num\|bool` | 否 | — | 合法範例值（強烈建議提供，特別是 `path` 參數）。 |
| `description` | `string` | 是 | 非空字串 | 參數用途、格式與允許值說明。 |

### `datasets[].fields[]` 子欄位

> 巢狀 JSON 欄位建議使用點號與中括號表達，例如 `Stations[].StationName` 或 `result.distribution`。

| 欄位名稱 | 型別 | 必填 | 格式／限制 | 說明 |
| :--- | :--- | :---: | :--- | :--- |
| `name` | `string` | 是 | 非空字串 | 原始欄位鍵名（必須與實際回傳完全一致，區分大小寫或中文全半形）。 |
| `type` | `string` | 是 | 列舉值（見右） | 允許值：`string`、`integer`、`float`、`number`、`boolean`、`date`、`datetime`、`object`、`array`。 |
| `unit` | `string` | 否 | 字串 | 數值單位（如 `秒`、`分鐘`、`km/h`、`TWD`、`μg/m³`）。 |
| `format` | `string` | 否 | 字串 | 日期／代碼格式說明（如 `YYYYMMDD`、`YYYMMDD (民國年)`、`ISO 8601`）。 |
| `description` | `string` | 是 | 非空字串 | 欄位含義、枚舉代碼對照表（如 `0=正常、1=未發車`）與清洗注意事項。 |

---

## 四、 自動驗證腳本檢查項目一覽

執行 `python scripts/validate.py` 時會依序檢查：

1. **JSON Schema 驗證**：型別、必填欄位、列舉值、Regex 格式與禁止額外未定義屬性。
2. **語意一致性檢查**：
   - 檔案主名 `== provider.id`，且全倉庫不重複。
   - `changelog[0].version == catalog_version`。
   - 同一檔案內 `datasets[].id` 不重複。
   - 若使用 `endpoint`，`provider.base_url` 必須存在。
   - `endpoint` 內所有 `{Placeholder}` 均在 `parameters` 宣告 `in: "path"` 並具備 `example` 或 `sample_url`。
3. **隱私與機敏資訊掃描**：檢查是否意外出現本機路徑、私鑰、Token、Email 或手機號碼。
4. **即時網址探測（加上 `--check-urls` 時）**：對 `provider.homepage` 與每個資料集（優先使用 `sample_url`，其次組合 `base_url + endpoint` 或 `download_url`）發送輕量 HTTP `HEAD`/`GET` 請求確認端點可達。
