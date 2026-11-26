# Open Data Catalog（開放資料目錄）

**Data Catalog as Code（程式碼化的開放資料目錄）** —— 以獨立 YAML 檔案分散維護各政府與公開資料平臺規格，透過 JSON Schema 驗證與自動化索引編譯，同時兼顧**人類協作易讀性**與 **AI Agent 兩階段精準檢索**。

---

## 已收錄資料平臺

| 來源代碼 (`provider.id`) | 平臺名稱 | 官方網址 | 認證機制 | 來源定義檔 |
| :--- | :--- | :--- | :--- | :--- |
| `tw-data-gov` | 政府資料開放平臺 | https://data.gov.tw/ | 免認證公開存取 | [`sources/tw-data-gov.yaml`](sources/tw-data-gov.yaml) |
| `tw-moenv` | 環境部環境資料開放平臺 | https://data.moenv.gov.tw/ | API Key Query Parameter (`api_key`) | [`sources/tw-moenv.yaml`](sources/tw-moenv.yaml) |
| `tw-tdx` | 交通部 TDX 運輸資料流通服務平臺 | https://tdx.transportdata.tw/ | OAuth 2.0 Bearer Token（含低頻訪客額度） | [`sources/tw-tdx.yaml`](sources/tw-tdx.yaml) |

---

## 專案架構設計

本專案採用「**核心規範 + 獨立來源檔 + 自動編譯索引**」三層架構，避免多人或跨部會擴充時產生合併衝突，並防止單一檔案過大耗盡 AI Token：

```text
opendata-catalog/
├── README.md                   # 專案說明與貢獻指南（給人類閱讀）
├── AGENTS.md                   # AI Agent 檢索規則、認證串接與維護手冊（給 AI 閱讀）
├── llms.txt                    # 自動生成的輕量級總目錄（第一階段 AI 導航入口）
├── requirements.txt            # 維運與驗證腳本 Python 套件依賴
├── docs/                       # 多人協作與資料分享教學文件（人類 & AI 雙用）
│   ├── contributing-guide.md   # 協作流程、ai_usage_guide 寫法與零私密資訊規範
│   ├── schema-spec.md          # YAML 欄位完整規格書
│   ├── examples.md             # 靜態檔案、API Key、OAuth2 實戰範例集
│   └── templates/
│       └── source-template.yaml # 可直接複製改寫的空白來源範本
├── schemas/
│   └── catalog.schema.json     # JSON Schema (Draft 2020-12) 欄位與型別驗證規範
├── sources/                    # 【核心維護區】每個開放資料平臺/機關獨立一份 YAML
│   ├── tw-data-gov.yaml        # 政府資料開放平臺 (data.gov.tw)
│   ├── tw-moenv.yaml           # 環境部環境資料開放平臺 (data.moenv.gov.tw)
│   └── tw-tdx.yaml             # 交通部 TDX 運輸資料流通服務平臺 (tdx.transportdata.tw)
├── dist/                       # 【自動編譯區】由 scripts/build_index.py 產出，勿手動編輯
│   └── full-catalog.json       # 合併所有來源之單一結構化 JSON 索引
├── scripts/
│   ├── validate.py             # Schema 驗證、版號檢查、隱私/機敏掃描與即時 URL 存活測試
│   └── build_index.py          # 讀取 sources/*.yaml 自動編譯 llms.txt 與 full-catalog.json
└── .github/
    └── workflows/
        ├── pr-check.yml        # PR 自動檢查格式、版號同步、隱私規則與單元測試
        ├── auto-build.yml      # 合併至 main 時自動重新編譯索引並寫回倉庫
        └── health-check.yml    # 每週定期巡檢開放資料端點，失效時自動建立 Issue
```

---

## 如何串接給 AI Agent 或應用程式使用

1. **AI Agent 兩階段檢索（省 Token、高準確率）**
   - **Stage 1**：讓 AI 先讀取 [`llms.txt`](llms.txt) 與 [`AGENTS.md`](AGENTS.md)，快速判斷問題對應哪一個資料平臺。
   - **Stage 2**：只讀取對應的 `sources/<id>.yaml`，取得精確 API 路徑、OData 參數、欄位定義與實務注意事項（如「臺／台」字差異、民國年格式、狀態碼定義）。
2. **本機開發工具（Claude Code / Cursor / Antigravity / MCP）**
   - 將本倉庫 `git clone` 至本機並作為工作區或掛載 Filesystem MCP Server，AI 即可依 `AGENTS.md` 指引自主導航與串接資料。
3. **應用程式直接讀取**
   - 系統或資料管線可直接讀取 [`dist/full-catalog.json`](dist/full-catalog.json)，一次取得所有平臺與已展開 `resolved_endpoint` 的完整 JSON 結構。

---

## 本地開發與驗證流程

### 1. 安裝環境依賴

建議使用 Python 3.10+ 虛擬環境（`venv` 或 `conda`）：

```bash
pip install -r requirements.txt
```

### 2. 執行驗證與索引編譯

```bash
# 執行 JSON Schema 驗證、版號同步檢查與隱私/機敏資訊掃描
python scripts/validate.py

# 額外對所有資料集發送輕量 HTTP 請求測試端點是否存活
python scripts/validate.py --check-urls

# 重新編譯 llms.txt 與 dist/full-catalog.json
python scripts/build_index.py

# 檢查索引檔是否與 sources/*.yaml 完全同步（CI 模式）
python scripts/build_index.py --check
```

---

## 貢獻指南與資安隱私規範

歡迎透過 Pull Request 新增更多開放資料平臺（例如環境部、中央氣象署、各縣市政府開放資料平臺等）或分享個人／社群整理的公開資料集：

完整步驟與規格請參閱協作文件：
- [多人協作與公開資料分享指南 (`docs/contributing-guide.md`)](docs/contributing-guide.md)
- [YAML 欄位完整規格書 (`docs/schema-spec.md`)](docs/schema-spec.md)
- [實戰範例集 (`docs/examples.md`)](docs/examples.md) 與 [空白範本 (`docs/templates/source-template.yaml`)](docs/templates/source-template.yaml)

重點原則摘要：

1. **新增或修改來源**：於 `sources/` 建立 `<provider-id>.yaml`（檔名須與 `provider.id` 一致），並填妥 `ai_usage_guide`、`sample_url` 與 `fields` 欄位說明。
2. **更新版本紀錄**：每次異動既有來源檔時，請同步遞增 `catalog_version`、更新 `last_updated` 並於 `changelog` 頂端補上變更摘要。
3. **公開倉庫零私密資訊原則**：
   - **嚴禁提交任何私人或機敏資訊**，包含但不限於 API Key、Client ID / Client Secret、Bearer Token、個人信箱、電話號碼（含機關承辦人個人聯絡方式）及本機檔案路徑。
   - 需要認證之平臺請僅於 `provider.auth.env_vars` 標註環境變數名稱（如 `TDX_CLIENT_ID`），`scripts/validate.py` 會在本地與 CI 自動攔截可疑機敏字串。

---

## 授權條款

本倉庫之目錄程式碼、Schema 與工具腳本採用 [MIT License](LICENSE) 授權；各開放資料集本身之著作權與使用規範，請依各來源檔案內 `provider.license` 所載之政府資料開放授權條款或原提供機關規範辦理（使用時請依規定顯名標示資料來源）。
