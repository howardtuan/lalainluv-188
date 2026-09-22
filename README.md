# Lalainluv 拉拉熊日本代購

Django 5.2 + PostgreSQL，奶茶色前後台共用版型與 CSS。支援桌面、平板與手機；Docker 對外 Port **8080**。

## 功能

- 拉拉熊商品分類、搜尋、排序、庫存、商品多圖、訪客購物車及登入後合併。
- **不串接金流**：送出訂單即保存到管理後台，由管理員人工確認並聯繫付款、配送，不會自動扣款。
- 訂單保存會員信箱、收件人、電話、地址、備註、商品名稱／單價／數量、小計、運費、總金額、時間與狀態；後續商品改價不影響舊訂單。
- PostgreSQL transaction / row locks 保護庫存，防止超賣與重複下單。滿 NT$ 2,000 免運，否則運費 NT$ 60。
- Email／密碼會員必須完成 LINE 或 Google OAuth 綁定，才能使用會員、下單、許願等功能；綁定後也能直接社群登入同一帳號。
- 專用管理員帳密由 `.env` 同步，使用內建帳密登入，**不需要社群綁定**。
- 同風格管理介面：訂單、商品新增／編輯／上下架、庫存、多圖、分類、輪播、許願回覆、網站資訊。
- 輪播全部來自資料庫，**包括第一張**；可替換圖片、手機專用圖片、文字、連結、排序與啟用狀態。全部停用就不顯示輪播。
- 訂單狀態：待確認 → 已確認 → 已出貨 → 已完成；未出貨可取消，庫存只回補一次。管理員內部備註不會顯示給會員。

## 管理入口與帳密

- [網站](http://127.0.0.1:8080/)
- [管理員登入](http://127.0.0.1:8080/manage/login/)
- [管理後台](http://127.0.0.1:8080/manage/)
- 舊 `/admin/` 入口會導向同風格後台，不再使用 Django 原生管理頁面。

在 `.env` 設定以下欄位；不要將真實密碼貼到聊天室、文件或版本庫：

```dotenv
ADMIN_USERNAME=lalainluv_admin
ADMIN_PASSWORD=請換成專用的長隨機密碼
ADMIN_EMAIL=管理員專用信箱
```

初始化／修改密碼後執行 `python manage.py sync_admin`；Docker 啟動時自動執行。此指令將密碼雜湊儲存在資料庫，不印出密碼，不會把同名的一般會員升級成管理員。請使用獨立帳號及信箱。

更換 `ADMIN_USERNAME` 會建立另一個帳號，不會自動刪除或停用舊管理員。密碼輪替應保留帳號名稱、更新密碼後同步；若更換帳號，也須自行停用舊帳號。

## Docker 啟動

確認 Docker Desktop Linux 引擎正常。已有 `.env` 時保留設定；新環境可產生隨機密鑰及管理員密碼：

```powershell
python scripts/init_env.py
docker compose up -d --build
```

容器依序執行 `migrate`、`sync_admin`、`collectstatic`。`SEED_DEMO=True` 時建立展示商品及初始輪播，不覆寫已存在的商品／廣告；正式建檔後可改成 `False`。保留 `.env` 中的管理員帳密即可，無須執行 `createsuperuser`。

```powershell
docker compose ps
docker compose logs -f web
docker compose exec web python manage.py test --noinput
docker compose stop
```

Compose 包含 Nginx、Gunicorn/Django、PostgreSQL。對外僅 Nginx 的 8080，資料庫不開外部 port；資料庫、上傳圖片、靜態檔各自使用命名 volume。請定期備份資料庫與上傳圖片。修改 `.env` 後須重新建立 web 容器載入新設定：`docker compose up -d --force-recreate web`。

## Windows 本機執行

使用 Python 3.10+ 及已建立的 PostgreSQL 資料庫。`.env` 的 `DATABASE_URL` 填入本機連線；Compose 會以 `POSTGRES_*` 覆寫容器資料庫連線。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
python scripts/init_env.py
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py sync_admin
.\.venv\Scripts\python.exe manage.py seed_demo
.\.venv\Scripts\python.exe manage.py seed_banners
$env:DEBUG = 'True'
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8080
```

不會自動切換 SQLite。既有的 `db.sqlite3` 保留但不使用。修改 `.env` 或 Python 程式後請重啟伺服器。

## LINE／Google 登入

實作使用 django-allauth 正式 OAuth 流程，不是輸入 LINE ID 或 Email 就視為綁定。詳見 [OAuth 設定說明](docs/oauth-setup.md)。

```dotenv
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
LINE_CHANNEL_ID=
LINE_CHANNEL_SECRET=
LINE_EMAIL_SCOPE=False
```

**至少設定一個平台才能讓一般會員完成綁定。** 尚未設定的平台會顯示停用按鈕，不會假裝登入成功。管理員不受影響，可以先建檔商品及輪播。正式開放註冊前，務必完成平台憑證、回呼網址及實際授權測試。

安全規則：不因相同 Email 自動合併帳號；既有會員先用密碼登入，再從「登入方式綁定」連接自己的平台帳號。一般會員至少保留一個 LINE／Google 綁定，不可解除最後一個。第三方登入流程使用 CSRF／OAuth state 驗證，Google 啟用 PKCE；不保存平台 access token。

## 其他環境與營運設定

`.env` 已加入 `.gitignore` 和 `.dockerignore`；`.env.example` 提供欄位，`scripts/init_env.py` 不覆寫已有 `.env`。現有部署升級時，請手動補上新增的環境欄位。

- `SECRET_KEY`：正式環境使用長隨機密鑰。
- `POSTGRES_DB / POSTGRES_USER / POSTGRES_PASSWORD`：Docker 資料庫參數。已初始化的 PostgreSQL 角色不會因 `.env` 改密碼而自動更新。
- `ALLOWED_HOSTS / CSRF_TRUSTED_ORIGINS`：正式網域及 HTTPS origin。
- `SITE_DOMAIN`：初次 `seed_demo` 寫入 Django Sites。既有部署更換網域，另執行下列指令更新郵件使用的網站名稱及網域。
- `DEBUG=False`：正式環境關閉偵錯。
- `SECURE_SSL_REDIRECT=True`：配置 HTTPS 反向代理後開啟；代理須正確轉送受信任的協定標頭，並確認 secure cookies。
- `EMAIL_BACKEND`：預設 console backend，信件僅輸出至日誌，**不會真正寄出**。正式通知需改用 SMTP 並設定寄件人、`EMAIL_HOST_*`、`ADMIN_EMAIL`；注意日誌可能含測試訂單或驗證連結。
- 訂單存入資料庫不依賴郵件成功，後台永遠是訂單查詢來源。未接金流、電子發票、物流 API；狀態「已確認」不代表自動收款成功。
- 目前登入限流使用 Django 預設快取。多 worker 正式部署應配置共用快取／入口限流，避免各 worker 各自計數。
- 網站 LINE、Instagram、Email、關於我們、購物須知可在「網站資訊」編輯；LINE 聯絡網址不同於 LINE Login 憑證。

```powershell
.\.venv\Scripts\python.exe manage.py shell -c "import os; from django.contrib.sites.models import Site; Site.objects.update_or_create(pk=1, defaults={'domain': os.environ['SITE_DOMAIN'], 'name': 'Lalainluv'})"
```

商品使用 San-X 拉拉熊原始商品圖。展示售價及庫存不代表正式報價／供貨，正式營運請自行確認商品資料及圖片使用權。來源：[拉拉熊素材記錄](docs/rilakkuma-assets.md)；舊通用素材已退出前台。

## 測試

GitHub Actions 會在 `main` push 及 pull request 自動使用 PostgreSQL 16 / Python 3.12 執行檢查、測試與靜態檔收集。CI 僅使用拋棄式測試憑證，不使用正式 `.env`，不會自動部署。

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py test --noinput
docker compose config --quiet
```

55 項 PostgreSQL 後端測試涵蓋下單與併發庫存、權限隔離、CSRF、完整訂單資料、狀態與回補、後台共用樣式、商品／廣告上傳、過期編輯防護、管理員環境同步、強制社群綁定及禁止解除最後一個平台等。Google 與 LINE 測試會走 allauth callback/session 流程，僅模擬外部 token/profile 回應；**不代表已完成真實平台授權驗證**。

獨立瀏覽器測試環境（會建立唯一名稱的暫存 PostgreSQL 資料庫，不更改正式帳號／訂單）：

```powershell
.\.venv\Scripts\python.exe scripts/preview_test_store.py
```

僅監聽 `127.0.0.1:8081`；測試帳密寫於腳本，僅在暫存資料庫有效。使用不同 cookie 名稱隔離 8080 登入狀態；結束請按 Ctrl+C，腳本會清理暫存資料庫及圖片。資料庫角色須有建立測試資料庫權限。

公開頁面自動檢查工具仍可使用 `scripts/check_ui.py`（需安裝 Playwright、Microsoft Edge，並先啟動 8080）。

### 驗證範圍與限制

- Django 檢查、55 項 PostgreSQL 測試通過；前後台共用 CSS。
- 瀏覽器測試覆蓋 320 / 390 / 768 / 1024 / 1440px、管理頁切換、庫存編輯及首頁第一張廣告替換。
- Compose 語法驗證通過。此電腦 Docker Desktop 引擎先前因 `dockerInference` socket 故障無法啟動，**尚未驗證 image build / container 啟動**；引擎恢復後執行 `docker compose up -d --build`。

## 公開 GitHub repo 注意事項

- 只提交 `.env.example`，**不提交 `.env`**。管理員、SMTP、OAuth、資料庫實際密碼留在部署主機。
- `.gitignore` / `.dockerignore` 排除環境檔、憑證、資料庫與備份、`media/`、`staticfiles/`、虛擬環境、私人上傳、瀏覽器截圖與測試產物。
- 公開程式碼不會發布本機訂單、會員資料或實際上傳的照片。`static/images/` 僅包含專案示範素材；第三方角色、商標及照片權利歸原權利人，來源記錄不等同取得使用授權。
- 提交前先 `git add`，再執行 `.\.venv\Scripts\python.exe scripts/check_public_repo.py` 掃描暫存內容。若曾誤推 secret，必須立即撤銷／輪替，不是刪檔就好。
- 未替作者自行選定開源授權；公開 repo 不代表任意授權第三方素材。若要加 LICENSE，請由權利人決定適用條款。
- 安全回報及正式上線檢查請看 [SECURITY.md](SECURITY.md)。
