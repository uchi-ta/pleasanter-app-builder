# プリザンターの仕様メモ（確認済みの事実）

ソース `C:\Implem\Implem.Pleasanter\Implem.Pleasanter` とこの環境での実地確認に基づく。
ここにない仕様を調べたら、この表に追記すること。

## API で登録するときの事実（2026-10-16 実地確認）

| 事実 | 根拠・対処 |
|---|---|
| APIキーではサイトパッケージ(JSONファイル)を取り込めない。`CopySitePackage` はサーバ上の既存サイトをコピーするだけ | `ItemModel.CopySitePackageByApi`。→ CreateSite + BulkUpsert で組み立てる（register.py） |
| `CreateSite` の URL の id は親サイトID（0=トップ）。SiteSettings は必須 | `SiteUtilities.CreateByApi` |
| `UpdateSite` は SiteSettings を丸ごと置換し、Links テーブルも登録し直す | `SiteModel.SetByApi` |
| `DeleteSite` はフォルダ配下のサイト・レコードもまとめて削除（ごみ箱行き） | `SiteModel.Delete` |
| `BulkUpsert` は Keys 省略で全件新規作成。レスポンスは件数メッセージのみで新IDは返らない | 実地確認。→ 登録後に Get でキー列→ResultId の対応を取る |
| BulkUpsert でも計算式(Formulas)と集計(Summaries)は動く | 実地確認（子の投入で親の NumB が更新された） |
| `SynchronizeSummaries` で集計を再計算できる（`SummaryId` に Id の配列） | 実地確認 |
| Get / 書き込みで扱える拡張列は、エディタ(EditorColumnHash)か一覧(GridColumns)に置いた列だけ | `SiteSettings.ReadableColumns`（SiteSettings.cs:4190）。→ キー列は必ずエディタに置く |
| Get は既定200件ずつのページング。`Offset` と `Response.TotalCount` で全件取得 | Api.json PageSize |
| 通知を有効にしたままデータを入れるとメールが飛ぶ | → 通知・リマインダーはデータ投入後に UpdateSite で入れる |
| この環境のユーザーID・部署IDはサンプルのサイトパッケージと一致（Tenant1_UserN） | `output/env.json` |

## サイトパッケージ JSON の事実

| 項目 | 内容 |
|---|---|
| 文字コード | UTF-8 BOM付き |
| `Status` | 数値ではなく `{"Value": 100}`（900=完了） |
| ResultId / SiteId | パッケージ内で一意（同じ辞書に入るので、サイトIDとレコードIDも重複させない）。重複すると取り込み時に例外 |
| ユーザー・部署 | レコードの `Manager.Id` 等 → `PermissionIdList` の LoginId / UserCode / 名前 の順で取り込み先と照合。部署は DeptCode → 名前 |
| リンク列の値 | 旧 ResultId の文字列。`Links` に定義した列だけ取り込み時に新IDへ置換される |
| 集計(Summary)の値 | 取り込みでは再計算されない → 集計先の値を計算して入れておく（build.py が実施） |
| 通知・リマインダー | インポート画面のチェックで取り込み可否が決まる（HeaderInfo の指定では決まらない） |
| 未知のプロパティ | 無視される（名前の誤りは無反応、型の誤りはインポート失敗） |

## 設定値の事実

| 項目 | 内容 |
|---|---|
| ChoicesText | `値,表示名,短縮名,CSSクラス,スタイル`。`[[サイトID]]`=リンク、`[[Users]]` `[[Depts]]` `[[Groups]]` |
| Status の CSS | status-new / status-preparation / status-inprogress / status-review / status-closed / status-rejected |
| 通知 `Type` | Mail=1（0は未定義）。`Name` プロパティは存在しない。Address に `[Manager]` `[Owner]` など列名プレースホルダ可 |
| `Notification.AfterCondition` / `Summary.SourceCondition` / `Reminder.Condition` | ビューIDで指定 |
| ビューの選択肢フィルタ | JSON文字列 `{"ClassC": "[\"異常\"]"}`、Status も `"[\"200\"]"` |
| ColumnSorterHash | `asc` / `desc` |
| View.DefaultMode | Definition_ViewMode の Name（Index, Crosstab, Kamban など） |
| Reminder | `Type`: Daily=10, Weekly=20, NumberWeekly=30, Monthly=40, EndOfMonth=50, Yearly=60。`Column` は日付列、`Range` は日数 |
| ExportColumn の Type | Value=0 / Text=1 |
| Formula の OperatorType | NotSet=0, Addition=1, Subtraction=2, Multiplication=3, Division=4。先頭の子は 0 |
| Aggregation の Type | Count=0, Total=1, Average=2 の3種のみ（Min/Max はない。誤った値は SiteSettings 全体のデシリアライズ失敗＝null になる） |
| SiteSettings.Version | `1.017` を必ず書く（違うと読み込み時にマイグレーションが走る） |
| Notification の After* | null は true 扱い。送らないものは明示的に false |
| BulkUpsert と通知 | 「インポート後」通知は AfterImport が null でも送られる（false で止まる） |
| TitleSeparator | 既定は `)`。複数列タイトルなら `" "` などを指定 |
| クロス集計の既定 | X=Status, Y=Owner, Total, NumA, Monthly（Definition_ViewMode） |

## ダッシュボード・Wiki・サーバスクリプトの事実（2026-10-16 実地確認）

| 事実 | 根拠・対処 |
|---|---|
| ダッシュボードは ReferenceType=`Dashboards` のサイト。SiteSettings.DashboardParts にパーツを並べる。Type: QuickAccess=0, TimeLine=1, Custom=2, CustomHtml=3, Calendar=4, Kamban=5, Index=6 | DashboardPartType.cs。CreateSite で作成できた |
| レイアウトは gridstack の横20列・1単位16px（X/Y/Width/Height） | app js の `GridStack.init({column:20,cellHeight:16})` |
| 対象サイトは `IndexSites` などにカンマ区切りの文字列で書き、`SiteId` は基準サイト（先頭）。絞り込みは part.View | DashboardPart.cs |
| CustomHtml の `<script>` は**非同期読み込みのときだけ実行される**。同期だと gridstack が innerHTML で差し込むため動かない | DashboardUtilities.cs:1450（ReplaceAll）。dashboard.py は kpi があれば async を強制 |
| ブラウザ側は `$p.apiGet({id, data:{View:{ApiDataType:'KeyValues', ApiColumnKeyDisplayType:'ColumnName', ApiColumnValueDisplayType:'Value'/'Text', GridColumns}}})` で集計用データが取れる（ログインセッションで認証、200件ページング） | マニュアル script-api-get.md |
| Wiki は CreateSite で ReferenceType=`Wikis`、Body に本文を入れると Wiki レコードも作られる。更新は Wiki レコードID への `Update`（Title/Body） | SiteModel.cs:2438、実地確認 |
| Wiki・説明（Description）・内容（Body）などの本文は、**先頭が `[md]` のときだけ Markdown として描画**される。それ以外は記号がエスケープされたメモ表示になる | wwwroot の markdown-field（`indexOf('[md]')===0` で `slice(4)` して parse）。wiki.py は先頭に `[md]` を付ける |
| Markdown 表示でも Mermaid は描画されない | 表・箇条書きで書く |
| サーバスクリプトは **10秒で打ち切り**（Script.json の ServerScriptTimeOut=10000、変更不可設定） | → AI 呼び出しは claude-haiku-5-5・effort low・短い出力で 4〜5 秒 |
| API の Update でもサーバスクリプト（BeforeUpdate）が動く | 実地確認（AI機能のテストに利用） |
| サーバスクリプトの `items.Get` は .NET 配列を返す。**件数は `.Length`**（`.length` は undefined） | 実地確認。ai_script.js で対処 |
| `items.Get(siteId, JSON文字列)` の第2引数は API の Get と同じ `{"View": {...}}` | ServerScriptUtilities.Get |
| httpClient: RequestUri / Content / RequestHeaders.Add / Post() / IsSuccess / StatusCode / IsTimeOut | マニュアル httpClient |
| ダッシュボードのカンバンパーツは `KambanColumns`（文字列）を省略すると 0 列扱いになり、表示時に ArgumentOutOfRangeException（Chunk の size）になる。ビューの KambanColumns と違い General.json の既定値 10 は使われない | SysLogs で確認（HtmlKamban.cs:158）。dashboard.py は既定 "10" を入れる |
| パーツの描画エラーは画面に「アプリケーションで問題が発生しました。」とだけ出る。中身は DB の SysLogs（ErrMessage / ErrStackTrace / Url）にある。API キーではパーツ描画を呼べないので、確認はブラウザ表示＋SysLogs | `scripts/syslogs.py`（環境変数の接続文字列で読み取りのみ） |
| サーバスクリプトの `Shared: true`（共有）は、他のサーバスクリプトの実行時に一緒に読み込まれる。共有スクリプトに定義した定数・関数を他のスクリプトから使える | ServerScriptUtilities.cs:1364-1381。AI機能のキーは共有スクリプト「共通設定（APIキー）」の `CLAUDE_API_KEY` に分ける |
