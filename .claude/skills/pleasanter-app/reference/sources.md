# 調べ物の索引

参照順: 1) このフォルダの reference → 2) マニュアル（機能・使い方） → 3) ソース（型・既定値・内部動作）。
調べて分かったことは `package-format.md` か `settings-catalog.md` に追記する。

## マニュアル（C:\Implem\Implem.Pleasanter.Manual\ja\docs）

| 知りたいこと | 場所 |
|---|---|
| API 全般・各API | `developers-guide\api\`（basics / site-operations / table-operations / user-operations / department-operations / group-operations） |
| サーバースクリプト | `developers-guide\server-script\` |
| スクリプト(クライアント) | `developers-guide\script\` |
| テーブルの管理画面の各設定 | `managers-guide\manage-table\`（site-package, editor, grid, filters, notification, reminder, summary, formula, process, status-control など） |
| パラメータ（General.json 等） | `setup\parameters\` |
| Pleasanter MCP | `ai-integration\pleasanter-mcp\` |

検索例: `Grep pattern="リマインダー" path="C:\Implem\Implem.Pleasanter.Manual\ja\docs\managers-guide"`

## ソース（C:\Implem\Implem.Pleasanter\Implem.Pleasanter）

公開リポジトリ https://github.com/Implem/Implem.Pleasanter を `C:\Implem\Implem.Pleasanter` にクローンしたもの（手順は `環境構築手順.md`）。
reference に書いた行番号は作成時点のもので、バージョンにより数行ずれることがある（ファイル名とメソッド名で探す）。

| 知りたいこと | 場所 |
|---|---|
| SiteSettings の各設定クラス | `Libraries\Settings\`（SiteSettings / Column / View / Notification / Reminder / Summary / FormulaSet / Process / StatusControl ...） |
| 列の既定値（ラベル・書式・Status の選択肢） | `App_Data\Definitions\Definition_Column\Results_*.json` |
| ビューモードの既定 | `App_Data\Definitions\Definition_ViewMode\Definition.json` |
| サイトパッケージの取り込み | `Libraries\SitePackages\Utilities.cs`, `SitePackage.cs`, `PackageSiteModel.cs`, `IdConvertUtilities.cs` |
| レコードのエクスポート型 | `Models\Results\ResultExportModel.cs` |
| API のルーティング | `Controllers\Api\ItemsController.cs` |
| API の処理（サイト） | `Models\Sites\SiteUtilities.cs`（CreateByApi / UpdateByApi / DeleteByApi） |
| API の処理（レコード） | `Models\Results\ResultUtilities.cs`（GetByApi / CreateByApi / BulkUpsertByApi） |
| パラメータの既定値 | `App_Data\Parameters\*.json`（General.json の ImportMax / BulkUpsertMax、Api.json の PageSize） |
