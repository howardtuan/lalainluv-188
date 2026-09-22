# LINE／Google 登入與帳號綁定

## 上線前必要設定

在平台開發者後台建立自己的 OAuth 應用，把憑證填入 `.env`，並重啟 Django／重新建立 web 容器。至少啟用一個平台，否則一般會員只能停在綁定頁，無法下單；管理員的專用帳密登入不受影響。

本機測試全程使用同一個 host，例如 `127.0.0.1:8080`，不要與 `localhost:8080` 交替使用，以免 OAuth session/cookie 不一致。實際可登記的本機回呼網址以平台後台驗證為準；必要時使用受控的 HTTPS 測試網域。

## Google

1. 在 Google Cloud 設定 OAuth 同意畫面、應用受眾及測試使用者。
2. 建立 **Web application** OAuth client。
3. 在 Authorized redirect URIs 登記網站實際回呼，例如：
   - 本機：`http://127.0.0.1:8080/accounts/google/login/callback/`
   - 正式：`https://你的網域/accounts/google/login/callback/`
4. 填入 `GOOGLE_CLIENT_ID`、`GOOGLE_CLIENT_SECRET`，重啟應用。
5. 若應用仍在測試模式，使用受允許的測試帳號驗證登入及綁定。

要求 profile/email，啟用 PKCE。不要求離線 access，不在資料庫保存平台 token。參考 [django-allauth Google 設定](https://docs.allauth.org/en/latest/socialaccount/providers/google.html)。

## LINE

1. 在 LINE Developers 建立 provider 及 **LINE Login** channel，啟用 Web app。
2. 設定 callback URL，例如：
   - 本機：`http://127.0.0.1:8080/accounts/line/login/callback/`
   - 正式：`https://你的網域/accounts/line/login/callback/`
3. 將 Channel ID、Channel secret 分別填入 `LINE_CHANNEL_ID`、`LINE_CHANNEL_SECRET`，重啟應用。
4. 確認開發／發布狀態允許測試者或正式會員登入。
5. 預設只要求 profile/openid。只有在 LINE 核准 Email 權限後才將 `LINE_EMAIL_SCOPE=True`；未取得 Email 時，首次註冊可要求會員補填。

LINE Login 不是官方帳號加好友，也不是填寫 LINE ID。`SiteConfig.line_url` 只用於商店聯絡連結，與登入設定無關。參考 [LINE 官方 Web Login 指南](https://developers.line.biz/en/docs/line-login/integrate-line-login/) 和 [django-allauth LINE 設定](https://docs.allauth.org/en/latest/socialaccount/providers/line.html)。

## 會員流程

- **帳密註冊／登入** → 尚未連接平台時，導向「登入方式綁定」→ 完成 Google 或 LINE OAuth → 才開放會員功能。
- **既有帳號加綁** → 用原帳密登入 → 選擇綁定 LINE／Google → 平台授權 → 回到同一會員帳號。
- **已綁定後直接社群登入** → 經平台授權登入原帳號，保留原訂單與購物車。
- 相同 Email 不會自動連接既有帳號；請先登入原帳號，再操作綁定，避免僅憑 Email 判斷帳號所有權。
- 一般會員不可解除最後一個 LINE／Google 綁定。已被別人連接的平台身份不能再加綁其他會員。
- `/manage/login/` 使用管理員帳密，不會要求 OAuth 綁定。只有 `is_staff` 管理員可進入管理頁，一般會員即使已綁定也無權進入。

程式使用 `.env` 的 provider `APPS` 設定。**不要同時替相同平台在資料庫新增 SocialApp**，避免重複憑證造成選擇歧義。參考 [allauth provider 設定](https://docs.allauth.org/en/latest/socialaccount/provider_configuration.html)。

## 實際授權驗收清單

憑證未提供時只能驗證本機流程及模擬 callback，以下項目需由有效平台帳號驗證：

- 全新 Google、LINE 使用者可以完成註冊／登入。
- 密碼會員完成綁定後回到原帳號；登出後使用該平台可再次登入。
- 使用者取消授權時仍未綁定，不會繞過綁定限制。
- 修改網址、錯誤／過期 state 不會登入或綁定成功。
- 已綁平台不可被另一會員占用，最後一個綁定不可移除。
- 測試／正式 callback URL 與實際 HTTPS 網域完全相符，反向代理協定與 cookie 設定正確。
- 設定可用 SMTP 以寄送密碼重設與 Email 驗證信，再開放正式使用。
