# 多人協作與公開資料分享指南（Human & AI Guide）

本文件說明如何在本倉庫中**協作維護開放資料目錄**，以及如何將**自己公開的資料集或第三方開放資料平臺**寫成結構化 YAML，讓**人類開發者好維護**、同時讓 **AI Agent 能精準判讀並直接呼叫取數**。

> **給 AI Agent 的提示**：當使用者要求「幫我把某個公開資料／API 加進這個目錄」時，請先閱讀本指南與 [欄位規格書 (schema-spec.md)](schema-spec.md)，實際探測端點與欄位後再撰寫 `sources/<provider-id>.yaml`，切勿憑空臆測欄位或網址。

---

## 一、 核心設計原則

1. **一來源一檔案（避免協作衝突）**
   - 每個公開資料平臺、部會機關或個人資料發布專案，各自在 `sources/` 目錄下維護獨立檔案：`sources/<provider-id>.yaml`。
   - 檔名（不含副檔名）**必須與檔案內的 `provider.id` 完全一致**（例如 `sources/my-opendata.yaml` 內 `provider.id: "my-opendata"`）。
2. **禁止手動修改自動編譯區**
   - 根目錄的 `llms.txt` 與 `dist/full-catalog.json` 是由 `scripts/build_index.py` 自動彙整生成的索引，發 PR 時**只需修改 `sources/*.yaml`**（或本地跑腳本測試，CI 也會在合併後自動更新）。
3. **為 AI 而寫的語意描述（AI-First Metadata）**
   - 僅列出網址與欄位名稱不足以讓 AI 正確使用資料。每個資料集都應清楚回答三個問題：**何時該用它？有哪些參數與認證限制？回傳資料有哪些格式陷阱？**

---

## 二、 適用場景：誰可以分享資料？

| 分享情境 | 建議 `provider.id` 命名範例 | 建議資料提供方式 (`endpoint` / `download_url`) | 參考範例 |
| :--- | :--- | :--- | :--- |
| **個人／社群整理的公開靜態資料**（如 GitHub Raw、Gist、GitHub Pages、靜態 CSV/JSON 空間） | `community-<topic>` 或 `<project-id>` | 使用 `download_url` 填寫完整公開下載連結 | [範例 1](examples.md#範例-1個人或社群分享的靜態公開資料csv--json) |
| **自建或部會的免 OAuth API**（公開 GET 或僅需 Query/Header API Key） | `tw-<agency>` 或 `<service-name>` | 填寫 `provider.base_url` + 各資料集相對 `endpoint` | [範例 2](examples.md#範例-2需要-api-key-的開放資料-api) |
| **需要 OAuth2 與動態路徑參數的平臺** | `tw-tdx` 等標準 kebab-case | 使用 `endpoint` 搭配 `{Param}` 與 `sample_url` | [範例 3](examples.md#範例-3含路徑參數與-oauth2-認證的進階-api) |

---

## 三、 五步驟完成新增或更新

### Step 1：複製範本並命名檔案

從範本複製建立新的來源檔案（檔名須全小寫 `kebab-case`，僅含英數字與連字號 `-`）：

```bash
cp docs/templates/source-template.yaml sources/<provider-id>.yaml
```

> 若是**補充既有平臺的資料集**，請直接編輯對應的 `sources/<provider-id>.yaml`，並跳到 Step 3 後記得更新版號（Step 4）。

### Step 2：實際驗證端點與欄位（不可憑空想像）

撰寫前請務必親自用 `curl`、瀏覽器或 Python 實測該網址：
- 確認網址實際回傳 `HTTP 200`（或需認證端點正確回傳 `401/403`）。
- 確認實際回傳的欄位鍵名（Key Name）、大小寫與資料格式（例如日期是 `YYYY-MM-DD` 還是民國年 `YYYMMDD`、檔案編碼是 `UTF-8`、`UTF-8-SIG` 還是 `BIG5`）。
- 若網址中含有動態路徑參數（如 `/City/{City}`），請挑選一個確定有資料的測試值填寫在 `sample_url` 中，方便 CI 自動探測存活。

### Step 3：寫出讓 AI 一讀就懂的 `ai_usage_guide`

`ai_usage_guide` 是 AI Agent 決定「**要不要選這份資料、怎麼呼才不會錯**」的關鍵欄位。請採用以下結構撰寫：

1. **觸發情境（When to use）**：列舉使用者可能會問的自然語言問題或關鍵需求。
2. **查詢前置步驟（Prerequisites）**：是否需要先查另一張表取得代碼（例如先查站點表取得 `StationID`），或需先呼叫 Metadata API 取得最新年度連結。
3. **實務陷阱（Domain Gotchas）**：編碼（`BIG5` / `UTF-8-SIG`）、異體字（「臺」vs「台」）、特殊狀態碼（如 `是否放假: "2"` 才代表放假）、負數意義、千分位逗號或大型檔案串流提醒。

#### Good vs. Bad 對照

- **Bad（資訊不足，AI 容易用錯）**：
  ```yaml
  ai_usage_guide: "提供台灣假日資料。"
  ```
- **Good（明確觸發條件 + 關鍵防呆）**：
  ```yaml
  ai_usage_guide: >
    當使用者詢問臺灣「國定假日、連假日期、補班日、某天是否上班放假」時優先查詢。
    注意：「是否放假」欄位值為 "0"（上班）與 "2"（放假），並非 0 與 1；
    年度檔案網址每年會異動，建議先查詢 /api/v2/rest/dataset/14718 取得最新年度 CSV。
  ```

### Step 4：更新版本與異動紀錄（多人協作必填）

每次新增或修改 `sources/<provider-id>.yaml` 時，請遵循以下規則（`pr-check.yml` 會在發 PR 時自動檢查）：

1. 遞增頂層 `catalog_version`（遵循語意化版本 `MAJOR.MINOR.PATCH`）：
   - `PATCH`（如 `1.0.0` → `1.0.1`）：修正錯字、補充欄位說明或修復失效網址。
   - `MINOR`（如 `1.0.0` → `1.1.0`）：新增資料集或新增重要參數。
   - `MAJOR`（如 `1.0.0` → `2.0.0`）：平臺 API 重大改版導致既有端點或欄位結構不相容。
2. 更新 `last_updated` 為目前 ISO 8601 時間（含時區，例如 `2026-11-26T15:30:00+08:00`）。
3. 在 `changelog` 陣列的**最上方（第一筆）**新增對應紀錄，且 `changelog[0].version` 必須等於 `catalog_version`。

### Step 5：本地驗證與發送 Pull Request

提交前請執行驗證與索引建置腳本（建議先安裝 `pip install -r requirements.txt`）：

```bash
# 1. 檢查 Schema、版本同步、隱私規則與所有即時網址是否存活
python scripts/validate.py --check-urls

# 2. 重新編譯 llms.txt 與 dist/full-catalog.json（確認可正常建置）
python scripts/build_index.py
```

確認輸出顯示 `All checks passed successfully.` 後即可提交 Commit 與發起 Pull Request。

---

## 四、 公開倉庫資安與隱私紅線（Zero-PII Policy）

本倉庫為公開 GitHub 儲存庫，**任何檔案皆嚴禁出現私人或機敏資訊**。`scripts/validate.py` 與 GitHub Actions CI 會自動掃描並阻擋以下內容：

- **禁止真實金鑰與憑證**：絕對不可寫入 API Key、Client Secret、Bearer Token、JWT 或密碼。
  - **正確做法**：在 `provider.auth.env_vars` 僅寫「建議的環境變數名稱」（如 `MY_API_KEY`），並在 `how_to_get` 寫明申請流程。
- **禁止個人聯絡資訊**：不可寫入個人 Email、手機號碼、或政府資料原始 JSON 附帶的承辦人姓名與分機。
  - **正確做法**：`maintainer` 請填寫 GitHub Handle（如 `@your-handle`）或團隊名稱（如 `OpenData Contributors`）。
- **禁止本機環境路徑**：不可在文件、註解或範例中出現 `/home/<user>/...`、`C:\Users\<user>\...` 等本機絕對路徑。

---

## 五、 延伸閱讀

- [YAML 欄位完整規格書 (schema-spec.md)](schema-spec.md)：所有欄位名稱、型別、Regex 與合法值完整對照表。
- [實戰範例集 (examples.md)](examples.md)：包含靜態公開檔案、API Key 服務、OAuth2 與路徑參數三種情境的完整可改寫範例。
- [空白標準範本 (source-template.yaml)](templates/source-template.yaml)：可直接複製改寫的 YAML 骨架。
