# プリザンター API 要約リファレンス（アプリ自動構築用）

> 出典とライセンス: [LICENSE-reference.md](LICENSE-reference.md)（マニュアルの要約部分は CC BY-NC-SA 4.0）

出典: `Implem.Pleasanter.Manual/ja/docs/developers-guide/api/` と実装 `Implem.Pleasanter/Controllers/Api/ItemsController.cs`、
`Models/Sites/SiteUtilities.cs`、`Models/Results/ResultUtilities.cs` ほか。
**マニュアルとソースが食い違う箇所はソースを正とし「⚠ソース」と明記する。**

---

## 1. 共通仕様

| 項目 | 値 |
|:--|:--|
| HTTPメソッド | すべて `POST` |
| URL形式 | `{ベースURL}/api/{コントローラ}/{ID}/{メソッド}`（例 `http://localhost:59803/api/items/123/get`）|
| コントローラ | `items`（サイト・レコード）/ `users` / `depts` / `groups` / `backgroundtasks` |
| Content-Type | `application/json`（Import のみ `multipart/form-data`）。文字コード UTF-8 |
| ApiVersion | `1.1`（数値・文字列どちらでも可）|
| ApiKey | **リクエストボディ**の `ApiKey` に入れる（ヘッダではない）。ブラウザのログインセッションからなら省略可 |
| メソッド名 | 大文字小文字は区別されない（`createsite` = `CreateSite`）|
| 前提 | `Api.json` の `Enabled: true`。サイト操作系はマニュアル上テナント管理者が必要 |
| 時刻 | APIキー作成ユーザのタイムゾーンで返る |

- 接続先: `secret.txt` に `PleasanterApiUrl=http://localhost:59803/api/items/` の形式で入っている。
  **APIキーはファイルから読み込んで使い、ログ・出力・このファイルには書かない。**
- ⚠ソース: Content-Type の厳密チェックは `Security.json` の `MimeTypeCheckOnApi`（既定 `false`）が true のときだけ。
  true の場合は `application/json` と完全一致が必要（`; charset=utf-8` 付きは不可）。

### レスポンス共通形式

更新系（作成・更新・削除など）:
```json
{ "Id": 12345, "StatusCode": 200, "LimitPerDate": 10000, "LimitRemaining": 9996,
  "Message": "\" タイトル \" を作成しました。" }
```
取得系:
```json
{ "StatusCode": 200, "LimitPerDate": 10000, "LimitRemaining": 9990,
  "Response": { "Offset": 0, "PageSize": 200, "TotalCount": 350, "Data": [ ... ] } }
```
エラー時も同じ形（`Id` / `StatusCode` / `Message`）。**HTTPステータスではなくボディの `StatusCode` で判定する。**

| StatusCode | 主な意味 |
|:--|:--|
| 400 | JSON不正・必須パラメータ欠落（例: CreateSite で SiteSettings なし）|
| 401 | 認証できない（APIキー誤り）|
| 403 | 権限なし |
| 404 | 対象が見つからない |
| 429 | 同一テーブルで一括処理（BulkUpsert/Import/サマリ同期）が実行中（排他ロック）|
| 500 | レコード単位エラー、BulkUpsertMax 超過など |

### ページング（レコード取得 / users・depts・groups 取得）

- 1回の上限は `Api.json` の `PageSize`（既定 **200**）。
- リクエストの `Offset` で開始位置を指定。レスポンスの `Response.TotalCount` が全件数。
- ⚠ソース: リクエストの `PageSize` は **Api.json の値より小さい場合のみ**有効（それ以上は Api.json 値に丸められる）。
- ループ条件: `Offset + PageSize >= TotalCount` で終了。

---

## 2. サイト操作

| API | URL の `{id}` | 用途 |
|:--|:--|:--|
| `createsite` | 親サイトID（**0 でトップ**）| サイト作成 |
| `getsite` | サイトID | サイト情報取得 |
| `updatesite` | サイトID | サイト更新（SiteSettings 丸ごと置換）|
| `deletesite` | サイトID | サイト削除（配下も削除）|
| `copysitepackage` | コピー元サイトID | サーバ上の既存サイトをコピー |
| `updatesitesettings` | サイトID | スクリプト等の部分追加/更新/削除 |
| `synchronizesummaries` | サイトID | サマリ同期 |
| `getclosestsiteid` | 検索起点サイトID | サイト名→サイトID |
| `movesite` | 移動するサイトID | 親フォルダ変更（マニュアル未掲載）|

### 2.1 CreateSite — `/api/items/{親サイトID}/createsite`

```json
{
  "ApiVersion": 1.1, "ApiKey": "...",
  "Title": "顧客マスタ",
  "ReferenceType": "Results",
  "SiteSettings": { "Version": 1.017, "ReferenceType": "Results",
                    "EditorColumnHash": { "General": ["ResultId","Ver","Title","ClassA","NumA","Comments"] } }
}
```
| パラメータ | 説明 |
|:--|:--|
| Title | サイト名（タイトル）|
| ReferenceType | `Sites`（フォルダ）/ `Issues`（期限付き）/ `Results`（記録）/ `Wikis` / `Dashboards` |
| SiteSettings | **必須**。⚠ソース: 省略すると 400。最小は `{"ReferenceType":"Results"}` |
| InheritPermission | 権限継承元サイトID。⚠ソース: 省略時は親サイトの InheritPermission を引き継ぐ |
| SiteName / SiteGroupName / Body / 各種 Guide / Publish など | サイトパッケージの `Sites[n]` と同じキーが使える |

- レスポンス: `{"Id": <新サイトID>, "StatusCode": 200, "Message": "\"顧客マスタ\" を作成しました。"}` → **`Id` が新サイトID**。
- ⚠ソース: 親は **URL の ID で決まる**。ボディの `ParentId`・`TenantId` は無視される（マニュアル例に書かれているが効かない）。
- サイトパッケージ JSON を使う場合は `Sites[i]` を丸ごとボディにし、`SiteId` を削除して投げる（マニュアルのサンプルの方法）。
  サイト間のリンク（`Links`/ChoicesText の `[[サイトID]]`）は旧IDのままなので、作成後に新IDへ置換して UpdateSite する必要がある。

### 2.2 GetSite — `/api/items/{サイトID}/getsite`

ボディは `ApiVersion` と `ApiKey` のみ。レスポンス `Response.Data` に
`SiteId, Title, ReferenceType, ParentId, InheritPermission, Permissions, SiteSettings{...}, Ver, UpdatedTime ...`。
- マニュアル: Wiki には非対応。
- UpdateSite の前に必ず GetSite で現行 SiteSettings を取得し、そこに差分を加えて送り返す。

### 2.3 UpdateSite — `/api/items/{サイトID}/updatesite`

```json
{ "ApiVersion": 1.1, "ApiKey": "...", "Title": "顧客マスタ", "SiteSettings": { ...GetSite で得た全体＋変更... } }
```
- ⚠ソース: `SiteSettings` を指定すると **オブジェクト全体を置換**（`SiteModel.SetByApi` で `SiteSettings = data.SiteSettings`）。
  送らなかった Columns / Notifications / Reminders / Processes などは消える。SiteSettings 自体を省略すれば既存のまま。
- Title・Body・SiteName 等も指定したものだけ更新（null は無視）。
- ⚠ソース: ボディの `ParentId` は **無視される**（マニュアル例には載っている）。親の変更は `movesite` を使う。
- `ReferenceType` は指定すると書き換わるので、変更しない値を送るか省略する。

### 2.4 DeleteSite — `/api/items/{サイトID}/deletesite`

ボディは `ApiVersion`・`ApiKey` のみ。
- ⚠ソース: **配下のサイトとそのレコードもまとめて削除**（SiteMenu.Children withParent）。
- 配下以外のサイトがこのサイト群から権限継承していると `CannotDeletePermissionInherited` エラーで削除不可。

### 2.5 CopySitePackage — `/api/items/{サイトID}/copysitepackage`

```json
{
  "ApiVersion": 1.1, "ApiKey": "...",
  "TargetSiteId": 466220, "SiteTitle": "コピー後の名前",
  "SelectedSites": [ { "SiteId": 466217 }, { "SiteId": 466218, "IncludeData": false } ],
  "IncludeSitePermission": false, "IncludeRecordPermission": false, "IncludeColumnPermission": false,
  "IncludeNotifications": true, "IncludeReminders": true
}
```
- **サーバ上に既に存在するサイトをコピーするだけ。サイトパッケージ JSON ファイルを送って取り込むことはできない。**
  （⚠ソース: API 経由では常に `GetSitePackage(apiData)` で既存サイトからパッケージを組み立てる。ファイル取込経路は画面専用）
- `SiteTitle` は URL のサイトのタイトルを変える場合に指定。`Include*` の既定は false。
- 実行には URL サイトのサイト管理権限と `SitePackage.json` の `Import: true` が必要。
- レスポンス: `Response.Data` は **JSON文字列**（要パース）
  `[{"OldSiteId":466217,"NewSiteId":466221,"ReferenceType":"Sites","Title":"test"}, ...]`
- マニュアル: 「期限付き・記録テーブルのみ」。⚠ソース: Sites/Issues/Results/Wikis/Dashboards いずれも受け付ける。
- `TargetSiteId` 省略時、マニュアルは「トップへコピー」だが、ソースは `context.SiteId`（URL側サイト）にフォールバックしており挙動が読み切れない（未検証）。**必ず明示指定する。**

### 2.6 updatesitesettings — `/api/items/{サイトID}/updatesitesettings`（部分更新）

**部分更新できる。** ただし対象は以下 6 種のみ。各要素は `Id` で突き合わせ、存在すれば更新・無ければ追加、`"Delete": 1` で削除。
要素内で指定しなかったプロパティは変更されない。

| キー | 主な必須項目 | 備考 |
|:--|:--|:--|
| Styles | Id, Title | Body, StyleAll/StyleNew/StyleEdit/StyleIndex... |
| Scripts | Id, Title | Body, ScriptAll/ScriptNew/ScriptEdit/ScriptIndex... |
| Htmls | Id, Title, HtmlPositionType | HeadTop/HeadBottom/BodyScriptTop/BodyScriptBottom |
| ServerScripts | Id, Title, Name | Body, ServerScriptBeforeCreate/AfterCreate/BeforeUpdate/... |
| Processes | Id, Name | CurrentStatus/ChangedStatus（`*`=-1）, ValidateInputs, DataChanges, AutoNumbering, Notifications |
| StatusControls | Id, Name | Status, ReadOnly, ColumnHash `{"ClassA":"Hidden"}`（Required/ReadOnly/Hidden）|

```json
{ "ApiVersion": 1.1, "ApiKey": "...",
  "ServerScripts": [ { "Id": 1, "Title": "採番", "Name": "Numbering",
                       "Body": "context.Log('x');", "ServerScriptBeforeCreate": true } ],
  "Scripts": [ { "Id": 2, "Title": "old", "Delete": 1 } ] }
```
- **Columns（項目設定）、EditorColumnHash、GridColumns、テーブル本体の Notifications / Reminders / Summaries / Formulas は対象外** → UpdateSite で全体置換する。
  （⚠ソース: Columns/EditorColumnHash/GridColumns の部分更新ロジックは存在するが、画面の SmartDesign 専用でありこの API からは呼ばれない）
- ServerScripts はテーブル系サイトのみ反映（ソース `ServerScriptRefTypes`）。
- 必要権限: サイトの管理権限（無いと 403）。`"VerUp": true` で版を上げる。

### 2.7 SynchronizeSummaries — `/api/items/{サイトID}/synchronizesummaries`

```json
{ "ApiVersion": 1.1, "ApiKey": "...", "SummaryId": [1, 2] }
```
- `SummaryId` は SiteSettings.Summaries の Id（サマリ設定を持つ＝集計**元**側のサイトで実行）。
- 成功: `{"Id":6,"StatusCode":200,"Message":"同期が完了しました。"}`。SummaryId 省略は 400、実行中は 429。

### 2.8 GetClosestSiteId — `/api/items/{起点サイトID}/getclosestsiteid`

```json
{ "ApiVersion": 1.1, "ApiKey": "...", "FindSiteNames": ["CustomerMaster", "OrderTable"] }
```
レスポンス（`Response` で包まれない）:
```json
{ "StatusCode": 200, "SiteId": 12345,
  "Data": [ { "SiteName": "CustomerMaster", "SiteId": 12344 }, { "SiteName": "OrderTable", "SiteId": -1 } ] }
```
- タイトルではなく **「サイト名」(SiteName)** で検索。見つからない／権限なしは `-1`。
- ⚠ソース: トップレベルに `StatusCode` が付く（マニュアルの例には無い）。

### 2.9 MoveSite — `/api/items/{サイトID}/movesite`（マニュアル未掲載・ソースのみ）

```json
{ "ApiVersion": 1.1, "ApiKey": "...", "ParentId": 200 }
```
- `ParentId` 必須（無いと 400）。移動先は存在する **フォルダ（ReferenceType=Sites）** でなければ不可。
- ⚠ソース: 移動先サイトを `NotFound` 判定するため、**トップ（0）への移動は不可**と読める（未検証）。自分自身・子孫への移動も不可。
- 成功時 `Message` は「移動しました」系。

---

## 3. レコード操作

| API | URL の `{id}` | 用途 |
|:--|:--|:--|
| `get` | サイトID（複数）/ レコードID（単一）| 取得 |
| `create` | サイトID | 1件作成 |
| `update` | レコードID | 1件更新 |
| `upsert` | サイトID | キー一致で更新・なければ作成 |
| `bulkupsert` | サイトID | 複数件の作成・更新 |
| `delete` | レコードID | 1件削除 |
| `bulkdelete` | サイトID | 一括削除 |
| `import` | サイトID | CSV取込（multipart）|
| `export` | サイトID | CSV/JSON出力 |

### 3.1 Get — `/api/items/{サイトID or レコードID}/get`

```json
{ "ApiVersion": 1.1, "ApiKey": "...", "Offset": 0,
  "View": {
    "ColumnFilterHash": { "ClassA": "RC0001", "Status": "[\"100\",\"200\"]",
                          "DateA": "[\"2025/01/01 00:00:00,2025/01/13 23:59:59\"]" },
    "ColumnFilterSearchTypes": { "ClassA": "ExactMatch" },
    "ColumnSorterHash": { "DateA": "asc" } } }
```
レスポンス `Response.Data[]`（既定形式）: `SiteId, ResultId(またはIssueId), Ver, Title, Body, Status, Manager, Owner, Comments(文字列),
Creator, Updator, CreatedTime, UpdatedTime, ItemTitle, ClassHash{}, NumHash{}, DateHash{}, DescriptionHash{}, CheckHash{}, AttachmentsHash{}`。

**View の主要プロパティ**

| プロパティ | 説明 |
|:--|:--|
| ColumnFilterHash | `{"カラム名":"値"}`。複数値・範囲は JSON配列の**文字列**（`"[1,2]"`、`"[\"開始,終了\"]"`）|
| ColumnFilterSearchTypes | `PartialMatch` / `ExactMatch` / `ForwardMatch` |
| ColumnSorterHash | `{"カラム名":"asc"|"desc"}` |
| Incomplete / Own / Delay / Overdue / Search | 未完了・自分・遅延・期限超過・全文検索 |
| ApiDataType | `"KeyValues"` で平坦な `{キー:値}` 形式（既定はカラム名＋～Hash 形式）|
| GridColumns | 返す列の指定。**ApiDataType=KeyValues のときのみ有効**（省略時は一覧タブで有効な列）|
| ApiColumnKeyDisplayType | `LabelText`（既定・表示名）/ `ColumnName` |
| ApiColumnValueDisplayType | `DisplayValue`（既定）/ `Value` / `Text` |

列を絞る例（キー→ID 対応表を作るのに便利）:
```json
{ "ApiVersion": 1.1, "ApiKey": "...",
  "View": { "ApiDataType": "KeyValues", "ApiColumnKeyDisplayType": "ColumnName",
            "ApiColumnValueDisplayType": "Value", "GridColumns": ["ResultId", "ClassA"] } }
```
- サイト統合を設定したテーブルでは統合先レコードも返る。`TableType`（Normal/History/Deleted 等）も指定可（ソース）。

### 3.2 Create — `/api/items/{サイトID}/create`

```json
{ "ApiVersion": 1.1, "ApiKey": "...", "Title": "案件A", "Status": 200, "Manager": 5,
  "ClassHash": { "ClassA": "障害" }, "NumHash": { "NumA": 20 }, "DateHash": { "DateA": "2025/1/20" } }
```
レスポンス: `{"Id": <新レコードID>, "StatusCode": 200, "Message": "\" 案件A \" を作成しました。"}`

### 3.3 Update — `/api/items/{レコードID}/update`

- 指定した項目のみ更新。`Comments` は追記。Body/Description は上書き。
- 添付削除: `"AttachmentsHash": {"AttachmentsA": [{"Guid": "大文字GUID", "Deleted": 1}]}`。
- レコード権限: `"RecordPermissions": ["Dept,1,31","Group,1,511","User,10,1"]`（**既存を全置換**、要「権限の管理」）。
  権限値: 読1 作成2 更新4 削除8 メール16 エクスポート32 インポート64 サイト管理128 権限管理256（合計で指定、全権511）。
- 日付を NULL にするには FAQ（`faq-api-set-date-to-null`）の方法による。

### 3.4 Upsert — `/api/items/{サイトID}/upsert`

```json
{ "ApiVersion": 1.1, "ApiKey": "...", "Keys": ["ClassA"],
  "Title": "案件A", "ClassHash": { "ClassA": "RC0001" } }
```
- 一致0件→作成、1件→更新、**複数件→エラー**。キー値が NULL なら比較せず新規作成。
- ⚠ソース: `Keys` に挙げた項目はボディ内に必ず存在し、かつサイトの列定義に存在する名前でなければ `InvalidUpsertKey` エラー。

### 3.5 BulkUpsert — `/api/items/{サイトID}/bulkupsert`

```json
{ "ApiVersion": 1.1, "ApiKey": "...",
  "Keys": ["ClassA"], "KeyNotFoundCreate": true,
  "Data": [ { "Title": "顧客1", "ClassHash": { "ClassA": "C001" } },
            { "Title": "顧客2", "ClassHash": { "ClassA": "C002" } } ] }
```
| パラメータ | 説明 |
|:--|:--|
| Keys | キー項目（複数可＝複合キー）。**省略時は全件新規作成**（KeyNotFoundCreate は無視）|
| KeyNotFoundCreate | 一致なし時に作成するか（既定 true）。false なら更新のみ |
| Data | レコード配列（各要素は Create と同じ形式。ProcessId も可）|

- レスポンスは**件数メッセージのみ。作成されたレコードIDは返らない。** `Id` はサイトID。
  ```json
  { "Id": 12345, "StatusCode": 200, "Message": "記録テーブル: 2 件追加し、0 件更新しました。" }
  ```
  → 新IDが必要なら後で Get してキー→ID対応を取る。
- 件数上限: `General.json` の `BulkUpsertMax`（⚠ソース: 既定 `0` = 無制限。0超で件数超過なら全体を処理せず 500
  `"1000 行を超えるデータは一度にインポートできません。"`）。大量データは数百件単位に分割して送る。
- **レコード単位で順に処理し、エラーが出た時点で中止。それ以前の件は確定済み（ロールバックされない）**（⚠ソース: 一括トランザクションなし）。
  エラー例: `"記録テーブル:エラーが発生しました。0 件追加し、0 件更新。\nIndex:1(ClassA=RC00011)\nエラー内容:条件に一致するレコードが複数存在します。"`
  → キーを付けて再実行すれば冪等に再開できる。
- ⚠ソース: Keys 指定時、**全 Data 要素にキー項目が含まれている必要がある**（欠けると InvalidUpsertKey）。日付キーは範囲外値もエラー。
- 同一テーブルで別の一括処理が実行中なら 429。必要権限: サイトの作成＋更新。Wiki 不可。

### 3.6 Delete / BulkDelete

- Delete: `/api/items/{レコードID}/delete`、ボディは `ApiVersion`・`ApiKey`。
- BulkDelete: `/api/items/{サイトID}/bulkdelete`

| パラメータ | 説明 |
|:--|:--|
| Selected | 削除するレコードIDの配列 `[135, 376]` |
| View | `{"ColumnFilterHash": {...}}` 条件指定 |
| All | true でテーブル全件 |
| PhysicalDelete | true でごみ箱・履歴からも消去（復元不可）|

レスポンス: `{"Id": <サイトID>, "StatusCode": 200, "Message": "サンプルテーブル: 3 件 一括削除しました。"}`

### 3.7 Import（CSV）— `/api/items/{サイトID}/import`

`multipart/form-data` で `parameters`（下記JSON文字列）と `file`（CSVバイナリ）を送る。
```json
{ "ApiVersion": 1.1, "ApiKey": "...", "Encoding": "UTF-8",
  "UpdatableImport": true, "Key": "ClassA", "MigrationMode": false }
```
- `Encoding`: `UTF-8` / `Shift-JIS`。CSV ヘッダは画面インポートと同じく表示名。
- レスポンス: `"Message": "テーブル名: 50 件追加し、12 件更新しました。"`（ID は返らない）。

### 3.8 Export — `/api/items/{サイトID}/export`

```json
{ "ApiVersion": 1.1, "ApiKey": "...",
  "Export": { "Name": "x", "Columns": [{"ColumnName":"Title"}], "Header": true, "Type": "csv" },
  "View": { "ColumnFilterHash": { "Owner": "[1]" } } }
```
- `ExportId` で画面作成済みのエクスポート設定を使うことも可。`Type` は `csv` / `json`。
- レスポンス: `Response.Name`（ファイル名）・`Response.Content`（中身の文字列）。

---

## 4. レコード JSON の項目名と型（Create / Update / Upsert / BulkUpsert 共通）

| キー | 型 | 備考 |
|:--|:--|:--|
| Title | 文字列 | タイトル |
| Body | 文字列 | 内容 |
| Status | 整数 | 状況のコード値（例 100, 200, 900）|
| Manager / Owner | 整数 | 管理者・担当者のユーザID |
| StartTime / CompletionTime | 日時文字列 | 期限付きテーブル（Issues）のみ |
| WorkValue / ProgressRate / RemainingWorkValue | 数値 | Issues のみ |
| Locked | 真偽 | ロック |
| Comments | 文字列 | コメント追加 |
| ClassHash | `{ "ClassA": "文字列" }` | 分類。ユーザ選択項目もユーザIDを文字列で。リンク項目は親レコードIDを文字列で |
| NumHash | `{ "NumA": 数値 }` | 数値（null 可）|
| DateHash | `{ "DateA": "2025/01/20" }` | 日付・日時（`yyyy/MM/dd` や `yyyy/MM/dd HH:mm`、ISO 形式も可）|
| DescriptionHash | `{ "DescriptionA": "文字列" }` | 説明 |
| CheckHash | `{ "CheckA": true }` | チェック |
| AttachmentsHash | `{ "AttachmentsA": [ {"ContentType":"text/plain","Name":"a.txt","Base64":"..."} ] }` | 添付 |
| ImageHash | `{ "Body"|"Comments"|"DescriptionA": {"Base64":"...","Extension":".png","Alt":"..","Position":-1,"HeadNewLine":true,"EndNewLine":true} }` | 画像埋め込み |
| ProcessId / ProcessIds | 整数 / 整数配列 | プロセス実行（ProcessIds が優先、実行順はサイト設定のプロセス順）|
| RecordPermissions | 文字列配列 | `"User,10,1"` 形式。全置換 |
| VerUp | 真偽 | 更新時に版を上げる |
| MigrationMode | 真偽 | 移行モード（サイト側で許可されている場合のみ）|

- 項目名は表示名ではなく **カラム名**（ClassA〜ClassZ、Class001〜 など拡張列も同様）。
- 2019年10月以降の仕様では分類・数値等は `～Hash` の中に書く（トップレベル直書きは旧形式。ソース上は互換で受け付ける）。
- 文字列の Class に数値を入れる場合も `"ClassA": "338"` のように文字列で送る。

---

## 5. API 登録時に動くもの（通知・計算式・サマリ等）

| 機能 | Create/Update/Upsert | BulkUpsert | 根拠 |
|:--|:--|:--|:--|
| 通知（作成時・更新時など）| 動く | 動く（1件ごと）| ⚠ソース: `Create/Update(notice: true)` |
| 通知「インポート後」| — | 処理完了時に1回送信 | マニュアル: 「インポート後」を有効化。⚠ソース: `AfterImport` 未設定（null）も有効扱い、明示 false のみ送らない |
| 計算式（Formulas）| 動く | 動く | ⚠ソース: `SetByApi` 内で `SetByFormula` |
| Lookup（リンク先値の取込）| 動く | 動く | ⚠ソース: `SetByLookups` |
| サマリ（集計先への反映）| 動く | 全件処理後にまとめて同期 | ⚠ソース: `Summaries.SynchronizeTargets` |
| サーバスクリプト（作成前/後等）| 動く | 動く | ⚠ソース |
| プロセス | `ProcessId` 指定時のみ | 同左 | マニュアル。条件不一致かつ「追加したボタン」型は BadRequest |
| リマインダー | 登録時には動かない（スケジュール実行）| 同左 | 仕様 |

- マニュアルの「プロセス実行時の制限事項（入力検証）」は文章が途中で切れており内容未確認。
- マニュアルでは通知・計算式の API 時の挙動は BulkUpsert の「インポート後」通知以外に明記がない（上表の多くはソースから確認）。

---

## 6. ユーザ / 組織 / グループ取得（Get のみ）

| API | URL | フィルタ例 |
|:--|:--|:--|
| ユーザ取得 | `/api/users/get` | `"View": {"ColumnFilterHash": {"UserId": "[11,12]", "DeptId": "[7,8]"}}` |
| 組織取得 | `/api/depts/get` | `"View": {"ColumnFilterHash": {"DeptId": "[1]"}}` |
| グループ取得 | `/api/groups/get` | `"View": {"ColumnFilterHash": {"GroupId": "[11,12]"}}` |

- ボディは `ApiVersion`・`ApiKey`（＋任意で `View`・`Offset`）。View 省略で全件（ページングあり、PageSize 200）。
- レスポンス `Response.{Offset, PageSize, TotalCount, Data[]}`。Data は `UserId, LoginId, Name, DeptId ...` / `DeptId, DeptCode, DeptName ...` /
  `GroupId, GroupName, GroupMembers[...]`。パスワードは取得できない。
- 用途: Manager/Owner や ユーザ選択項目に入れる ID の解決。
- **取得結果は個人情報を含むため、外部送信やログ出力をしない。**

---

## 7. アプリ自動構築でのおすすめ手順

前提: APIキーは `secret.txt` から読み、URL は `PleasanterApiUrl`（`.../api/items/`）を基点にする。

1. **フォルダ作成**: `POST {base}0/createsite` に `ReferenceType: "Sites"`、`SiteSettings: {"ReferenceType":"Sites"}` → `Id` を親フォルダIDとして保持。
2. **テーブル作成（親→子の順）**: `POST {base}{フォルダID}/createsite` に `ReferenceType: "Results"`（期限管理が要るなら `Issues`）と
   SiteSettings（Columns の LabelText・ChoicesText、EditorColumnHash、GridColumns、Formulas、Summaries など）。
   - **通知・リマインダーはこの時点では入れない**（データ投入中に大量送信されるため。BulkUpsert は1件ごとに通知が飛ぶ）。
   - 子テーブルのリンク列（例 ClassA）の ChoicesText には `[[親サイトID]]` を入れる。親IDは手順2の親作成レスポンスから得る。
   - `SiteName` を付けておくと後で `getclosestsiteid` で引ける。
3. **親テーブルへ投入**: `POST {base}{親ID}/bulkupsert`。業務キー（例 ClassA=顧客コード）を `Keys` に指定して冪等にする。
   `BulkUpsertMax` を考慮し数百件ずつ分割。レスポンスでは ID が返らない。
4. **キー→ResultId 対応の取得**: `POST {base}{親ID}/get` を `Offset` でページングし、
   `ResultId` と `ClassHash.ClassA`（または KeyValues＋GridColumns で `["ResultId","ClassA"]`）を辞書化。
   `Offset + PageSize >= TotalCount` まで繰り返す。
5. **子テーブルへ投入**: リンク列に親の ResultId を**文字列**で入れて `POST {base}{子ID}/bulkupsert`
   （例 `"ClassHash": {"ClassA": "1234", "ClassB": "明細コード"}`、`Keys` は子側の業務キー）。
   サマリ（子→親の集計）は BulkUpsert 完了時にまとめて同期される。不整合時は `synchronizesummaries` を実行。
6. **通知・リマインダー有効化**: `POST {base}{サイトID}/getsite` で現行 SiteSettings を取得 →
   `Notifications` / `Reminders` を追加 → `POST {base}{サイトID}/updatesite` で **SiteSettings 全体**を送る（部分送信すると他設定が消える）。
7. **スクリプト・プロセス・状況による制御**: `updatesitesettings` で Id 単位に部分追加（UpdateSite で入れても可）。
8. **検証**: 各サイトを GetSite / Get して件数（TotalCount）と設定を確認。失敗時は `StatusCode` と `Message` をそのまま記録する。

再実行・やり直し:
- BulkUpsert はキー指定なら再実行しても重複しない（キー無しは毎回新規作成になるので注意）。
- 作り直す場合はフォルダを `deletesite` すれば配下のテーブル・レコードごと削除される（取り消し不可）。
