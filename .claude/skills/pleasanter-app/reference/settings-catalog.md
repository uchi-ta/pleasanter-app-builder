# SiteSettings 早見表（型とプロパティ名）

> 出典とライセンス: [LICENSE-reference.md](LICENSE-reference.md)（マニュアルの要約部分は CC BY-NC-SA 4.0）

プリザンター本体ソース（`C:\Implem\Implem.Pleasanter\Implem.Pleasanter`）から抽出した、
SiteSettings JSON（サイトパッケージの `SiteSettings` / CreateSite API の `SiteSettings`）に
書けるプロパティの一覧。根拠は `ファイル名:行番号` で示す（`Libraries/Settings/` 配下は
ファイル名のみ）。

## 0. 共通ルール（最初に読む）

| 項目 | 内容 | 根拠 |
|---|---|---|
| デシリアライズ | Newtonsoft `JsonConvert.DeserializeObject<T>`。**例外時は黙って null を返す**ので、型を1つ間違えると SiteSettings 全体が読めなくなる | Implem.Libraries/Utilities/Jsons.cs:22-31 |
| enum の書き方 | 数値でも名前文字列でも読める（Newtonsoft の標準動作）。`[StringEnumConverter]` の付いた enum（Column.SearchTypes, AutoNumberingResetTypes, StatusControl.ControlConstraintsTypes）は出力も文字列 | Column.cs:38,57 / StatusControl.cs:16 |
| `Version` | **`1.017` を書く**。Version が現行値と違うと読込時にマイグレーションが走る。1.007 の移行処理は `Columns = ColumnCollection`（旧形式）で Columns/Aggregations/Links を置き換えるため、Version 0 のままだと Columns が消える可能性がある | SiteSettingsUtilities.cs:15,987-1001 / Migrators/SiteSettings/Version1_007.cs |
| `ReferenceType` | `"Results"` / `"Issues"` / `"Wikis"` / `"Sites"` / `"Dashboards"` | SiteSettings.cs:160,345-349 |
| Id 採番 | `SettingList<T>`（Summaries, Formulas, Processes, StatusControls, Notifications, Reminders, Exports, Styles, Scripts, Htmls, ServerScripts, Tabs ...）の各要素は `Id`（int）を持つ。View は `Views[].Id` と `ViewLatestId`、Section は `SectionLatestId`、Tab は `TabLatestId` で採番する | SiteSettings.cs:180-199 |
| 既定値の扱い | 保存時（RecordingData）は既定値と同じ項目を省略する。省略した項目は読込時（Init / UpdateColumn）に既定値で補われる | SiteSettings.cs:343-458, 2144-2282 |
| bool? の三値 | `null` は既定値の意味。Notification の `After*` のように「null=true」のものがあるので注意 | Notification.cs:479-510 |

## 1. 列名の一覧（Results / Issues）

### 1.1 拡張列（A〜Z）

`Class`/`Num`/`Date`/`Description`/`Check`/`Attachments` の6種類に、それぞれ **A〜Z の26列**
（例: `ClassA`〜`ClassZ`）がある。対象テーブルは Depts, Groups, Users, Issues, Results の5つ
（Implem.DefinitionAccessor/Def.cs:6518-6563）。さらに `Parameters/ExtendedColumns/*.json` の件数を
指定すると `Class001` 形式の列が追加されるが、既定値は全種類 0 件（ExtendedColumns/Results.json:4-9）。
商用ライセンスで `DisabledColumns` を設定すると一部の列を無効化できる（Def.cs:6566）。

| 種類 | DB型 | 既定 ControlType | 既定 FieldCss | その他の既定 | 根拠（Parameters/ExtendedColumnDefinitions） |
|---|---|---|---|---|---|
| ClassX | nvarchar(1024) | ChoicesText | （なし=field-normal） | ChoicesText が空なら自由入力テキスト | Class.json |
| NumX | decimal(19,4) | （なし=通常テキスト） | — | DefaultMin/MaxValue=±999999999999999, ValidateNumber=1 | Num.json |
| DateX | datetime | — | — | GridFormat=Ymda, EditorFormat=Ymd, ExportFormat=Ymd, ValidateDate=1 | Date.json |
| DescriptionX | nvarchar(max) | MarkDown | field-markdown | — | Description.json |
| CheckX | bit | — | — | CheckFilterControlType=1(OnOnly) | Check.json |
| AttachmentsX | nvarchar(max) JSON | Attachments | field-wide | — | Attachments.json |

### 1.2 固定列（Results）

| 列名 | 型 | 既定 | 根拠（Definition_Column） |
|---|---|---|---|
| ResultId | bigint | ControlType=Id, EditorReadOnly | Results_ResultId.json |
| Title | nvarchar | ValidateRequired=1, FieldCss=field-wide | Results_Title.json |
| Body | nvarchar(max) | ControlType=MarkDown, field-markdown | _BaseItems_Body.json |
| Status | int | ChoicesText（下記）, DefaultInput="100" | Results_Status.json |
| Manager / Owner | int（ユーザー） | ChoicesText=`[[Users]]`, DefaultInput=`[[Self]]` | Results_Manager.json / Results_Owner.json |
| Locked | bit | — | Results_Locked.json |
| Comments | nvarchar | — | _Bases_Comments.json |
| Creator / Updator / CreatedTime / UpdatedTime / Ver | 自動 | 編集不可 | _Bases_*.json |
| TitleBody / SiteTitle | 表示専用 | — | _BaseItems_TitleBody.json / Results_SiteTitle.json |

Issues は上記に加えて `StartTime`（DefaultInput="0"=今日）, `CompletionTime`（ControlType=Limit,
DefaultInput="7", ValidateRequired=1）, `WorkValue`（Spinner, Unit=h, 0〜100 step 0.1）,
`ProgressRate`（Spinner, Unit=%）, `RemainingWorkValue` がある（Issues_*.json）。

**Status の既定 ChoicesText**（Results/Issues 共通、Results_Status.json）:
```
100,未着手,未,status-new
150,準備,準,status-preparation
200,実施中,実,status-inprogress
300,レビュー,レ,status-review
900,完了,完,status-closed
910,保留,留,status-rejected
```
900 以上を「完了」とみなす（`CompletionCode: 900`、Parameters/General.json:49）。

## 2. SiteSettings 直下

### 2.1 よく使うもの

| プロパティ | 型 | 意味 / 書き方 | 既定 | 根拠 |
|---|---|---|---|---|
| Version | decimal | `1.017` | — | SiteSettingsUtilities.cs:15 |
| ReferenceType | string | テーブル種別 | — | SiteSettings.cs:160 |
| Columns | Column[] | 列ごとの設定（§3）。変更する列だけ書けばよい | 定義から補完 | SiteSettings.cs:188, 2121-2142 |
| GridColumns | string[] | 一覧に表示する列名。並び順＝表示順 | 定義の GridEnabled 列（ResultId, Status, Manager, Owner, TitleBody, Comments, UpdatedTime, Updator 等） | SiteSettings.cs:176,1985 |
| FilterColumns | string[] | フィルタ欄に出す列 | 定義の FilterEnabled 列 | SiteSettings.cs:177,1992 |
| EditorColumnHash | {string: string[]} | タブごとのエディタ列（下記 2.2） | `{"General": [定義の EditorEnabled 列]}` | SiteSettings.cs:178,2021 |
| Sections | Section[] | `{Id, LabelText, AllowExpand?, Expand?, Hide?}` | null | Section.cs:7-11 |
| SectionLatestId | int? | Section の最大 Id | 0 | SiteSettings.cs:182,364 |
| Tabs | Tab[] | `{Id, LabelText}` | null | Tab.cs:8-9 |
| TabLatestId | int? | Tab の最大 Id | 0 | SiteSettings.cs:180,363 |
| GeneralTabLabelText | string | 先頭タブの表示名 | 「全般」 | SiteSettings.cs:179,362 |
| TitleColumns | string[] | タイトルを組み立てる列（複数可） | `["Title"]` | SiteSettings.cs:184,2059-2064 / ColumnUtilities.cs:140-147 |
| TitleSeparator | string | TitleColumns の区切り文字 | `")"` | SiteSettings.cs:428 |
| LinkColumns | string[] | リンク表（子・親一覧）に出す列 | 定義の LinkEnabled 列 | SiteSettings.cs:185 |
| HistoryColumns | string[] | 履歴一覧に出す列 | 定義の HistoryEnabled 列 | SiteSettings.cs:186 |
| Views | View[] | ビュー（§4） | [] | SiteSettings.cs:197 |
| ViewLatestId | int? | View の最大 Id | 0 | SiteSettings.cs:196,381 |
| GridView | int? | 一覧画面の既定ビュー Id | null | SiteSettings.cs:164 |
| Links | Link[] | **書かなくてよい**。読込時に Columns の ChoicesText から再生成される | — | SiteSettings.cs:4662-4710 |
| Summaries | Summary[] | 集計（§7） | [] | SiteSettings.cs:191 |
| Formulas | FormulaSet[] | 計算式（§8） | [] | SiteSettings.cs:192 |
| Aggregations | Aggregation[] | 一覧の集計表示（§9） | [] | SiteSettings.cs:189 |
| Notifications | Notification[] | 通知（§5） | [] | SiteSettings.cs:198 |
| Reminders | Reminder[] | リマインダー（§6） | [] | SiteSettings.cs:199 |
| Processes | Process[] | プロセス（§10） | [] | SiteSettings.cs:194 |
| StatusControls | StatusControl[] | 状況による制御（§11） | [] | SiteSettings.cs:195 |
| Scripts / Styles / Htmls / ServerScripts | 各[] | §12 | [] | SiteSettings.cs:210-218 |
| NearCompletionTimeBeforeDays / AfterDays | decimal? | 「完了間近」の判定日数 | 7 / 7 | SiteSettings.cs:351-354, General.json:21,24 |
| GridPageSize | int? | 一覧の1ページ件数 | 20 | SiteSettings.cs:355 |

### 2.2 EditorColumnHash の書き方

```json
"EditorColumnHash": {
  "General":  ["ResultId", "Title", "_Section-1", "ClassA", "NumA", "_Links-123"],
  "_Tab-1":   ["DescriptionA", "AttachmentsA"]
},
"TabLatestId": 1, "Tabs": [{"Id": 1, "LabelText": "詳細"}],
"SectionLatestId": 1, "Sections": [{"Id": 1, "LabelText": "基本情報", "AllowExpand": true, "Expand": true}]
```

| キー/要素 | 意味 | 根拠 |
|---|---|---|
| `"General"` | 先頭タブ（タブ Id 0） | SiteSettings.cs:2873-2876 |
| `"_Tab-{Id}"` | Tabs[].Id のタブ | SiteSettings.cs:2875 |
| `"_Section-{Id}"` | 列リスト中に置くと、そこから次の見出しまでがそのセクション | SiteSettings.cs:2919-2929 |
| `"_Links-{SiteId}"` | 列リスト中に置くと、そのサイトとのリンク表を表示 | SiteSettings.cs:2902-2917 |

### 2.3 Enable* / Use* / Allow*（既定値）

| プロパティ | 既定 | 根拠 |
|---|---|---|
| EnableCalendar / EnableCrosstab / EnableGantt / EnableBurnDown / EnableTimeSeries / EnableAnaly / EnableKamban / EnableImageLib | すべて true | SiteSettings.cs:416-426 |
| CalendarType | 2（1=Standard, 2=FullCalendar） | SiteSettings.cs:67-71,417 / General.json:61 |
| NoDisplayCrosstabGraph | false | SiteSettings.cs:419 |
| ShowGanttProgressRate | true | SiteSettings.cs:421 |
| UseFilterButton / UseFiltersArea / UseGridHeaderFilters / UseNegativeFilters / UseRelatingColumnsOnFilter | false / true / false / false / false | SiteSettings.cs:429-433 |
| UseIncompleteFilter / UseOwnFilter / UseNearCompletionTimeFilter / UseDelayFilter / UseOverdueFilter / UseSearchFilter | すべて true | SiteSettings.cs:434-439 |
| AllowCopy / AllowReferenceCopy / CharToAddWhenCopying | true / false / `" - コピー"` | SiteSettings.cs:403-405, General.json:39-41 |
| AllowEditingComments / AllowSeparate / AllowLockTable | すべて false | SiteSettings.cs:402,406-407 |
| AllowRestoreHistories / AllowPhysicalDeleteHistories | true / true | SiteSettings.cs:409-410 |
| AllowViewReset | true | SiteSettings.cs:356 |
| AllowStandardExport / StandardExportType | true / 0（0=Default,1=Grid,2=Editor） | SiteSettings.cs:73-78,389-390 |
| ImportEncoding / UpdatableImport / RejectNullImport | `"Shift-JIS"` / false / false | SiteSettings.cs:386-387,408 |
| HideLink / SwitchRecordWithAjax / SwitchCommandButtonsAutoPostBack | すべて false | SiteSettings.cs:411-413 |
| DeleteImageWhenDeleting | true | SiteSettings.cs:414 |
| SearchType | 15（10=FullText, 15=PartialMatch, 20=MatchInFrontOfTitle, 30=BroadMatchOfTitle） | SiteSettings.cs:36-42,441 |
| SaveViewType | 1（0=None, 1=Session, 2=User） | SiteSettings.cs:44-49,446 |
| GridEditorType | null（0=None, 10=Grid, 20=Dialog） | SiteSettings.cs:29-34 |
| FirstMonth | 4 | SiteSettings.cs:357 / General.json:91 |

### 2.4 めったに使わないもの（1行ずつ）

- `DisableSiteConditions` bool?, `GuideAllowExpand` bool?, `GuideExpand` string（SiteSettings.cs:107-109）
- `HistoryOnGrid`, `AlwaysRequestSearchCondition`, `DisableLinkToEdit`, `OpenEditInNewTab`, `EnableExpandLinkPath` bool?（:167-171）
- `LinkTableView` int?, `LinkPageSize` int?, `FirstDayOfWeek` int?（:172-174）
- `MoveTargets` long[]（移動先サイト）、`IntegratedSites` string[]（統合サイト）（:187,275）
- `FormulasGetErrorDetails`, `OutputFormulaLogs` bool?（:193,263）
- `DefaultImportKey` string, `AllowMigrationMode` bool?（:205-206）
- `StylesAllDisabled` / `ScriptsAllDisabled` / `HtmlsAllDisabled` / `ServerScriptsAllDisabled` / `ServerScriptsGetErrorDetails` bool?（:211-220）
- `Responsive` bool?, `DashboardPartsAsynchronousLoading` bool?（:212-213）
- `BulkUpdateColumns`, `RelatingColumns`（`{Id, Title, Columns[], ColumnsLinkedClass}`）, `DashboardParts`, `AiProviders`（:221-223,200）
- `ExtendedHeader` string（:224）
- `AutoVerUpType` / `AfterCreateActionType` / `AfterUpdateActionType`（Versions の enum、既定 Default）（:225-227）
- `ImageLibPageSize` int?（既定 20）（:251,427）
- `FullTextIncludeBreadcrumb` / `FullTextIncludeSiteId` / `FullTextIncludeSiteTitle` bool?, `FullTextNumberOfMails` int?（:266-269）
- `AddressBook`, `MailToDefault`, `MailCcDefault`, `MailBccDefault` string（:271-274）
- `NoDisplayIfReadOnly`, `NotInheritPermissionsWhenCreatingSite` bool（null 不可）（:276-277）
- `PermissionForCreating` / `PermissionForUpdating` {列名: Permissions.Types}（:278-279）
- `CreateColumnAccessControls` / `ReadColumnAccessControls` / `UpdateColumnAccessControls` ColumnAccessControl[]（§13）（:280-282）
- `FormStartDateTime` / `FormEndDateTime` / `FormUnavailableMessage` / `FormThanksMessage`（フォーム機能）（:314-317）
- 互換用（書かない）: `GridColumnsOrder` 等 `*Order`, `FormulaHash`, `ColumnCollection`, `NewStyle`/`EditScript` 等, `EditInDialog`, `EditorColumns`（:284-312）

## 3. Column（`Columns[]`）

`ColumnName` は必須。指定しなかったプロパティは定義（§1）から補われる（SiteSettings.cs:2144-2282）。

### 3.1 よく使うもの

| プロパティ | 型 | 意味 / 書き方 | 既定 | 根拠 |
|---|---|---|---|---|
| ColumnName | string | 列名（`ClassA` 等） | — | Column.cs:74 |
| LabelText | string | 表示名 | 定義の表示名（「分類A」等） | Column.cs:75 / SiteSettings.cs:2162 |
| GridLabelText | string | 一覧の見出し | LabelText | Column.cs:76 |
| ChoicesText | string | 選択肢（§3.2）。改行 `\n` 区切り | 定義（Status, Manager, Owner のみ） | Column.cs:79 |
| ChoicesControlType | string | `"DropDown"` / `"Radio"` | `"DropDown"` | SiteSettings.cs:2185 / SiteUtilities.cs:9231-9232 |
| MultipleSelections | bool? | 複数選択（nvarchar 型＝Class のみ）。値は `["a","b"]` 形式の JSON 文字列で保存される | false | Column.cs:81 / SiteUtilities.cs:9240-9243 |
| UseSearch | bool? | 選択肢を検索ダイアログで選ぶ（件数が多い時） | 定義 | Column.cs:80 |
| NotInsertBlankChoice | bool? | 空の選択肢を入れない | false | Column.cs:82 |
| DefaultInput | string | 既定値（§3.3） | 定義 | Column.cs:83 |
| ValidateRequired | bool? | 必須 | 定義（Title, CompletionTime が true） | Column.cs:108 |
| EditorReadOnly | bool? | 編集画面で読み取り専用 | 定義 | Column.cs:136 |
| Description | string | 項目の説明文 | null | Column.cs:77 |
| InputGuide | string | 入力ガイド（入力欄の案内文） | null | Column.cs:78 |
| FieldCss | string | `"field-normal"` / `"field-wide"`。MarkDown 系はさらに `"field-markdown"` / `"field-rte"`（リッチテキスト） | 定義（Title=field-wide, Description=field-markdown, Attachments=field-wide） | SiteUtilities.cs:9338-9359 |
| EditorFormat | string | 日付の入力書式: `"Ymd"` / `"Ymdhm"` / `"Ymdhms"` | Date 列は `"Ymd"` | SiteUtilities.cs:9487-9495 |
| GridFormat / ExportFormat | string | 日付の表示書式: `Ymd`, `Ymda`（曜日付き）, `Ymdhm`, `Ymdahm`, `Ymdhms`, `Ymdahms`, `Ym`, `Md` | Date 列は `"Ymda"` / `"Ymd"` | App_Data/Displays/*.json（Type 120） |
| Format | string | 数値書式: `""`=標準, `"C"`=通貨, `"N"`=桁区切り, その他=.NET のカスタム書式文字列 | null | SiteUtilities.cs:9474-9482 |
| DecimalPlaces | int? | 小数点以下の桁数（最大は Size の小数部 = 4） | 定義（Num は 0） | Column.cs:124 / SiteUtilities.cs:9502 |
| RoundingType | int? | 10=AwayFromZero, 20=Ceiling, 30=Truncate, 40=Floor, 50=ToEven | 10 | SiteSettings.cs:51-58,2201 |
| Unit | string | 単位（「円」等） | 定義 | Column.cs:126 |
| Min / Max / Step | decimal? | 数値の範囲とスピナーの刻み。Num の既定は ±999999999999999, Step 1。日付列では Min/Max が日付ピッカーの範囲（日数、±365）になる | 定義 | SiteSettings.cs:2202-2204, 2385-2408 |
| ControlType | string | Num は `"Normal"` / `"Spinner"`。定義値: `ChoicesText`, `MarkDown`, `Attachments`, `Spinner`, `Id`, `Limit` | 定義 | SiteUtilities.cs:9008-9022 |
| Nullable | bool? | 数値列で未入力を 0 ではなく空として扱う | false | SiteSettings.cs:2198 |
| ValidateMaxLength | int? | 最大文字数 | 定義の MaxLength（Class=1024） | SiteSettings.cs:2194 |
| ClientRegexValidation / ServerRegexValidation / RegexValidationMessage | string | 正規表現でチェック（画面側 / サーバー側）とエラー文 | 定義 | Column.cs:115-117 |
| NoDuplication / MessageWhenDuplicated | bool? / string | 重複禁止とメッセージ | false | Column.cs:133-134 |
| CopyByDefault | bool? | 複製時に値をコピーする | 定義 | Column.cs:135 |
| AutoPostBack / ColumnsReturnedWhenAutomaticPostback | bool? / string | 値変更で再計算・再描画 | false | Column.cs:137-138 |
| ExtendedFieldCss / ExtendedControlCss / ExtendedCellCss | string | 項目・入力部品・一覧セルに追加する CSS クラス（自由記述） | null | Column.cs:100-102 |
| Hide | bool? | エディタで非表示 | null | Column.cs:95 |
| NoWrap | bool? | 折り返さない（エディタの列設定にある項目） | null | Column.cs:94 / SiteUtilities.cs:9306 |
| TextAlign | int? | 10=Left, 15=Center, 20=Right | 10 | SiteSettings.cs:60-65,2218 |
| Anchor / OpenAnchorNewTab / AnchorFormat | bool? / bool? / string | 値をリンクとして表示（AnchorFormat は `{Value}` を含む URL） | false | Column.cs:85-87 |

### 3.2 ChoicesText の書式

1行が1つの選択肢。カンマ区切りで `値,表示名,短縮名,CSSクラス,スタイル`（Choice.cs:31-60）。
表示名を省略すると値、短縮名を省略すると表示名が使われる（Choice.cs:56-57）。値にカンマを含める場合は
`\,` と書く（`ChoiceSplitRegexPattern: (?<!\\),`、General.json:42-44）。

| 行の書き方 | 意味 | 根拠 |
|---|---|---|
| `A` / `A,表示名` / `100,未着手,未,status-new` | 固定の選択肢 | Choice.cs:45-59 |
| `[[Users]]` | サイトにアクセス権のあるユーザー（ユーザー列になる） | Column.cs:453-468, 550-555 |
| `[[Users*]]` | テナントの全ユーザー | Column.cs:550-554 |
| `[[Users,ShowDeptName]]` / `[[Users*,ShowDeptName]]` | 組織名付きで表示 | Column.cs:559-563 |
| `[[Depts]]` | テナントの全組織（組織列） | Column.cs:389-406 |
| `[[Groups]]` | サイトのグループ / `[[Groups*]]` はテナントの全グループ | Column.cs:407-442 |
| `[[TimeZones]]` | タイムゾーン一覧 | Column.cs:443-451 |
| `[[サイトID]]` | そのサイトのレコードを選択肢にする（リンク列。値はレコードID） | Column.cs:469-510 / SiteSettings.cs:4687-4708 |
| `[[サイトID,NoAddButton]]` 等 | 2番目以降のオプション: `NoAddButton`（追加ボタンなし）, `AddSource`, `NotReturnParentRecord` | Link.cs:51-79 |
| `[{"SiteId":123,"SearchFormat":"...","View":{...},"Lookups":[...]}]` | ChoicesText 全体を Link の JSON 配列にする書き方（絞り込みビューや Lookups を指定する場合） | SiteSettings.cs:4675-4684 |
| CheckX 等の bit 列 | 1行目が "1"、2行目以降が "0" の表示名 | Column.cs:522-527 |

Link（JSON 形式）のプロパティ: `SiteId` long, `TableName`, `Priority` int?, `NoAddButton`, `AddSource`,
`NotReturnParentRecord`, `ExcludeMe`, `MembersOnly`, `SelectNewLink` bool?, `SearchFormat` string,
`View` View, `Lookups`（`[{From, To, Type?(0=Value,1=DisplayName), Overwrite?, OverwriteForm?}]`）,
`LinkActions`（`[{Type:"CopyWithLinks"|"DeleteWithLinks", View, CharToAddWhenCopying, CopyWithComments}]`）（Link.cs:21-35 / Lookup.cs:12-22 / LinkAction.cs:17-20）。
`Column.Link`（bool）は SetLinks で毎回上書きされるので書く必要はない（SiteSettings.cs:4673）。

### 3.3 DefaultInput の書き方

| 列の種類 | 書き方 | 根拠 |
|---|---|---|
| 日付 | 今日からの日数（文字列）。`"0"`=今日, `"7"`=7日後, `"-1"`=昨日。空なら未入力。EditorFormat が Ymd なら日付のみ、それ以外は現在時刻＋日数 | Column.cs:1085-1092 |
| ユーザー / 組織 / グループ列 | `"[[Self]]"`=ログインユーザー（組織・グループ）。MultipleSelections なら JSON 配列になる | Column.cs:1094-1117 |
| Status / 選択肢 | 選択肢の値（`"100"` 等） | Results_Status.json |
| Check | `"1"` / `"true"` でオン | ResultModel.cs:98 |
| Num / Class / Description | その値 | — |

### 3.4 めったに使わないもの

- `ImportKey` bool?（インポートの照合キー。Id 列と Num 列のみ）（SiteUtilities.cs:8926-8930）
- `ValidateNumber` / `ValidateDate` / `ValidateEmail` bool?, `ValidateEqualTo` string（Column.cs:109-113）
- `DefaultMinValue` / `DefaultMaxValue` decimal?（Column.cs:131-132）
- `AllowBulkUpdate` bool?（既定 false）（Column.cs:142）
- `ViewerSwitchingType` int?: 1=Auto, 2=Manual, 3=Disabled（既定 1）（Column.cs:31-36 / General.json:37）
- `SearchType` string: `"PartialMatch"`(1), `"ExactMatch"`(2), `"ForwardMatch"`(3), `"PartialMatchMultiple"`(11), `"ExactMatchMultiple"`(12), `"ForwardMatchMultiple"`(13)。既定は選択肢あり＆単一選択なら ExactMatch、それ以外 PartialMatch（Column.cs:38-47,305-310）
- `FullTextType` int?: 0=None, 1=DisplayName, 2=Value, 3=ValueAndDisplayName（Column.cs:49-55）
- `CheckFilterControlType` int?: 1=OnOnly, 2=OnAndOff（ColumnUtilities.cs:48）
- `NumFilterMin` / `NumFilterMax` / `NumFilterStep` decimal?（既定 0 / 10000 / 1000）（Num.json）
- `DateFilterSetMode` int?: 1=Default, 2=Range。`DateFilterMinSpan` / `DateFilterMaxSpan` int?（-1 / 1）、`DateFilterFy` / `Half` / `Quarter` / `Month` bool?（既定 true）（ColumnUtilities.cs:60 / SiteSettings.cs:2226-2231）
- `DateTimeStep` int?（分の刻み、既定 10）（SiteSettings.cs:2279）
- `CellSticky` bool?, `CellWidth` int?, `CellWordWrap` bool?, `GridDesign` string（一覧セルの表示。GridDesign は `[列名]` を含む HTML）（Column.cs:104-107）
- `ExtendedHtmlBeforeField` / `BeforeLabel` / `BetweenLabelAndControl` / `AfterControl` / `AfterField` string（Column.cs:118-122）
- `MultilingualLabelText` string（Column.cs:123）
- 添付: `AllowDeleteAttachments`(true), `NotDeleteExistHistory`(false), `OverwriteSameFileName`(false), `LimitQuantity`, `LimitSize`, `TotalLimitSize`, `LocalFolderLimitSize`, `LocalFolderTotalLimitSize`, `BinaryStorageProvider`（`"DataBase"`/`"LocalFolder"`/`"AutoDataBaseOrLocalFolder"`）（Column.cs:139-140,160-166 / SiteUtilities.cs:9093-9099）
- 画像: `AllowImage`(true), `ThumbnailLimitSize`（Column.cs:141,164）
- 自動採番: `AutoNumberingFormat` string, `AutoNumberingResetType` string（`"None"`=0, `"Year"`=10, `"Month"`=20, `"Day"`=30, `"String"`=90）, `AutoNumberingDefault` int?(1), `AutoNumberingStep` int?(1)（Column.cs:57-65,96-99）
- 互換用（書かない）: `GridVisible` 等 `*Visible`, `GridDateTime`, `ControlDateTime`, `ControlFormat`, `Section`（Column.cs:103,274-287）

## 4. View（`Views[]`）

### 4.1 基本

| プロパティ | 型 | 意味 / 書き方 | 既定 | 根拠 |
|---|---|---|---|---|
| Id | int | ビュー ID。Summary/Notification/Reminder/Formula の条件から参照される | — | View.cs:43 |
| Name | string | ビュー名 | — | View.cs:44 |
| DefaultMode | string | 開いた時の表示: `Index`, `Calendar`, `Crosstab`, `Gantt`, `BurnDown`, `TimeSeries`, `Analy`, `Kamban`, `ImageLib`（Gantt/BurnDown は Issues のみ） | 一覧（Index） | View.cs:45 / Definition_ViewMode/Definition.json |
| GridColumns | string[] | このビューの一覧列 | サイトの GridColumns | View.cs:46 |
| FilterColumns | string[] | このビューのフィルタ列 | サイトの FilterColumns | View.cs:47 |
| ColumnFilterHash | {列名: string} | 絞り込み条件（§4.2）。値は**文字列**（JSON 配列も文字列として書く） | null | View.cs:75 |
| ColumnFilterSearchTypes | {列名: SearchTypes} | 列ごとの一致方法（`"ExactMatch"` 等） | 列の SearchType | View.cs:77 |
| ColumnFilterNegatives | string[] | 否定条件にする列名（UseNegativeFilters が必要） | null | View.cs:78 |
| ColumnSorterHash | {列名: `"asc"`/`"desc"`} | 並び順。記述順に優先 | null | View.cs:80 / SqlOrderBy.cs:18-23 |
| Search | string | 全文検索語 | null | View.cs:79 |
| Incomplete | bool? | 未完了（Status < 900）のみ | null | View.cs:54,1950-1963 |
| Own | bool? | 自分が Manager または Owner | null | View.cs:55,1964-1970 |
| NearCompletionTime | bool? | 完了間近（CompletionTime 必須＝Issues のみ） | null | View.cs:56,2095-2103 |
| Delay | bool? | 遅延（Status, ProgressRate, CompletionTime 必須） | null | View.cs:57,2105-2115 |
| Overdue | bool? | 期限切れ（Status, CompletionTime 必須） | null | View.cs:58,2117-2126 |

### 4.2 ColumnFilterHash の値の書式

| 列の型 | 書き方（JSON 内では文字列） | 根拠 |
|---|---|---|
| 選択肢付き Class | `"[\"a\",\"b\"]"`（いずれかに一致）。未設定は `"[\"\\t\"]"`（`\t` = 未設定） | View.cs:2940-3060 |
| 選択肢なし Class / Description / Title | `"文字列"`（既定は部分一致）。JSON 配列も可 | View.cs:3065-3160 |
| Status / Num / ユーザー列（int） | 単一値 `"100"`、または `"[\"100\",\"200\"]"`。範囲は `"[\"0,100\"]"`（以上・以下）、`"[\",100\"]"`（100以下）、`"[\"100,\"]"`（100以上）、未設定 `"[\"\\t\"]"` | View.cs:2576-2639, 2709-2742 |
| ユーザー / 組織列 | `"[\"Own\"]"` でログインユーザー（組織）、`"[\"5\"]"` でユーザー ID | View.cs:2452-2481 |
| Date / CreatedTime 等 | `"[\"2025/01/01,2025/12/31\"]"`（範囲）、`"[\"2025/01/01,\"]"`（以降）、`"[\",2025/12/31\"]"`（以前）、`"[\"Today\"]"` / `"[\"ThisMonth\"]"` / `"[\"ThisYear\"]"`、未設定 `"[\"\\t\"]"` | View.cs:2752-2938 |
| Check（bit） | `"1"` / `"true"` = オン、`"2"` / `"false"` = オフ（null を含む） | View.cs:2539-2574 |
| 特殊キー `or_任意名` / `and_任意名` | 値に ColumnFilterHash と同じ形の辞書を JSON 文字列で入れる（OR / AND グループ） | View.cs:2205-2260 |
| 特殊キー `eq_任意名` / `notEq_任意名` | `"列名1\|列名2"`（2列の値が等しい / 等しくない） | View.cs:2262-2282 |

例:
```json
{"Id":1,"Name":"未完了・自分","DefaultMode":"Index","Incomplete":true,"Own":true,
 "ColumnFilterHash":{"ClassA":"[\"東京\",\"大阪\"]","NumA":"[\"0,100\"]","DateA":"[\"ThisMonth\"]","CheckA":"1"},
 "ColumnSorterHash":{"DateA":"desc","ResultId":"asc"}}
```

### 4.3 表示モード別のプロパティ

未指定時は Definition_ViewMode/Definition.json の Option1〜5 が既定値になる（View.cs:283-522）。

| モード | プロパティ | 取りうる値 | Results の既定 |
|---|---|---|---|
| Calendar | CalendarTimePeriod | `Yearly` / `Monthly` / `Weekly`（SiteSettings.cs:3785） | Monthly |
| | CalendarFromTo | `"StartTime-CompletionTime"` または日付列名（`"DateA"`）。`-` で開始・終了を分ける（View.cs:193-210, SiteSettings.cs:3795） | `DateA` |
| | CalendarViewType | `dayGridMonth` / `timeGridWeek` / `timeGridDay` / `listMonth`（FullCalendar 用、SiteSettings.cs:3818） | dayGridMonth |
| | CalendarGroupBy / CalendarShowStatus | 選択肢列 / bool? | 空 / false |
| | CalendarType / CalendarSiteId | ダッシュボード用（通常はサイトの CalendarType を使う、View.cs:252-259） | — |
| Crosstab | CrosstabGroupByX | 選択肢列・日付列・CreatedTime/UpdatedTime（SiteSettings.cs:3829） | Status |
| | CrosstabGroupByY | 選択肢列 または `"Columns"`（数値列を縦に並べる）（:3836-3841） | Owner |
| | CrosstabColumns | GroupByY=Columns の時の列リスト。JSON 配列の文字列 `"[\"NumA\",\"NumB\"]"`（ResultUtilities.cs:9606） | — |
| | CrosstabAggregateType | `Count` / `Total` / `Average` / `Max` / `Min`（:3906） | Total |
| | CrosstabValue | 数値列（:3879） | NumA |
| | CrosstabTimePeriod | `Yearly` / `Monthly` / `Weekly` / `Daily`（:3918） | Monthly |
| | CrosstabMonth / CrosstabNotShowZeroRows | DateTime? / bool? | 今月 / — |
| Kamban | KambanGroupByX / KambanGroupByY | 選択肢列（単一選択）。Y は `"Nothing"` で分類なし（:4090-4109） | Status / Owner |
| | KambanAggregateType | `Count` / `Total` / `Average` / `Max` / `Min`（:4111） | Count |
| | KambanValue | 数値列（:4123） | NumA |
| | KambanColumns / KambanAggregationView / KambanShowStatus | int?（既定 10、General.json:78） / bool? / bool? | — |
| TimeSeries | TimeSeriesGroupBy | 選択肢列（:3969） | Owner |
| | TimeSeriesAggregateType | `Count` / `Total` / `Average` / `Max` / `Min`（:3983） | Count |
| | TimeSeriesValue | 数値列（:3995） | NumA |
| | TimeSeriesChartType | `AreaChart` / `LineChart`（:4009） | AreaChart |
| | TimeSeriesHorizontalAxis | `"Histories"` または日付列（:4018） | Histories |
| Gantt（Issues） | GanttGroupBy / GanttSortBy / GanttPeriod / GanttStartDate | 選択肢列 / 列名 / int? / DateTime? | — |
| Analy | AnalyPartSettings | `[{Id, GroupBy, TimePeriodValue, TimePeriod, AggregationType, AggregationTarget}]`。TimePeriod は `DaysAgoNoArgs` / `MonthsAgoNoArgs` / `YearsAgoNoArgs` / `HoursAgoNoArgs` / `MinutesAgoNoArgs` / `SecondsAgoNoArgs`（AnalyPartSetting.cs:6-11, SiteSettings.cs:3736） | — |

### 4.4 めったに使わないもの

- `FiltersDisplayType` / `AggregationsDisplayType` int?: 0=Displayed, 1=Hidden, 2=AlwaysDisplayed, 3=AlwaysHidden（View.cs:21-27,48,51）
- `GuidesReduced`, `FiltersReduced`, `AggregationsReduced`, `KeepFilterState`, `KeepSorterState` bool?（View.cs:49-59）
- コマンドボタンの表示 int?（0=Displayed, 1=None, 2=Disabled, 3=Hidden）: `BulkMoveTargetsCommand`, `BulkDeleteCommand`, `EditImportSettings`, `OpenExportSelectorDialogCommand`, `OpenBulkUpdateSelectorDialogCommand`, `EditOnGridCommand`, `ExportCrosstabCommand`, `CreateCommand`, `UpdateCommand`, `OpenCopyDialogCommand`, `ReferenceCopyCommand`, `MoveTargetsCommand`, `EditOutgoingMail`, `DeleteCommand`, `OpenDeleteSiteDialogCommand`（View.cs:29-35,60-74）
- `ColumnFilterExpressions` {列名: string}, `ViewExtensionsHash` {string: string}（View.cs:76,81）
- API 用: `ApiColumnHash`, `ApiColumnKeyDisplayType`（0=LabelText, 1=ColumnName）, `ApiColumnValueDisplayType`（0=DisplayValue, 1=Value, 2=Text）, `ApiDataType`（0=Default, 1=KeyValues）, `ApiGetMailAddresses`（View.cs:82-84,131-132 / ApiColumn.cs:5-16）
- `Depts` / `Groups` / `Users` int[]（ビューを使える人の制限）（View.cs:128-130）
- `CalendarSuffix`, `IndexSuffix`, `KambanSuffix`, `Calendar*Hash`, `DashboardPartLayoutHash`（ダッシュボード用）（View.cs:85-101,127）
- 互換用: `KambanGroupBy`, `CalendarColumn`, `ShowHistory`, `MergeSessionViewFilters`, `MergeSessionViewSorters`（View.cs:145-151）

## 5. Notification（`Notifications[]`）

**`Name` プロパティは存在しない**（表示名は `Prefix` / `Subject`）。

| プロパティ | 型 | 意味 / 書き方 | 既定 | 根拠 |
|---|---|---|---|---|
| Id | int | — | — | Notification.cs:22 |
| Type | int | 1=Mail, 2=Slack, 3=ChatWork, 4=Line, 5=LineGroup, 6=Teams, 7=RocketChat, 8=InCircle, 9=HttpClient, 10=LineWorks | — | Notification.cs:53-65 |
| Prefix | string | 件名の前に付ける文字列 | null | Notification.cs:24 |
| Subject | string | 件名（`[列名]` で値を差し込み） | null | Notification.cs:25 |
| Address / CcAddress / BccAddress | string | 宛先（下表）。Slack 等では Webhook URL | null | Notification.cs:26-28 |
| Body | string | 本文 | null | Notification.cs:36 |
| MonitorChangesColumns | string[] | 変更を監視する列。更新時はこの列が変わった時だけ通知 | null | Notification.cs:37,404-410 |
| BeforeCondition / AfterCondition | int | 変更前 / 変更後の条件（**ビュー ID**）。0 = 条件なし | 0 | Notification.cs:38-39 |
| Expression | int | 1=Or, 2=And（Before と After の組み合わせ） | 0（未設定） | Notification.cs:40,67-71 |
| AfterCreate / AfterUpdate / AfterDelete / AfterCopy / AfterBulkUpdate / AfterBulkDelete / AfterImport | bool? | **null は true 扱い**。通知しないものだけ `false` を書く | null(=true) | Notification.cs:41-47 / ResultModel.cs:3987,4014 |
| Disabled | bool? | 無効化 | null | Notification.cs:48 |
| UseCustomFormat / Format | bool? / string | 本文の書式を独自にする | null | Notification.cs:34-35,565-577 |
| Token | string | ChatWork / Line 等のトークン | null | Notification.cs:29 |
| MethodType / Encoding / MediaType / Headers | int? / string / string / string | HttpClient 用。MethodType 1=Get, 2=Post, 3=Put, 4=Delete。MediaType 既定 `"application/json"` | — | Notification.cs:30-33,73-79 |

宛先（Address / CcAddress / BccAddress）の書き方。区切りは `,` `;` 改行（Mails/Addresses.cs:37-60）。

| 書き方 | 意味 | 根拠 |
|---|---|---|
| `user@example.com` / `"表示名" <user@example.com>` | 直接指定 | Addresses.cs:37-60 |
| `[Manager]` / `[Owner]` / `[Creator]` / `[Updator]` / `[ClassA]` 等 | その列の値（ユーザー・組織・グループ）のメールアドレスに置換。`[Creator]` は作成時、`[Updator]` は常に操作者 | SiteSettings.cs:4617-4642 / Notification.cs:239-262,380-402 |
| `[User5]` / `[Dept3]` / `[Group2]` | ID を指定したユーザー / 組織の全員 / グループの全員 | Addresses.cs:83-108 |
| `[RelatedUsers]` | 関係するユーザー | Notification.cs:20,416-460 |

## 6. Reminder（`Reminders[]`）

| プロパティ | 型 | 意味 / 書き方 | 既定 | 根拠 |
|---|---|---|---|---|
| Id | int | — | — | Reminder.cs:26 |
| ReminderType | int | 1=Mail, 2=Slack, 3=ChatWork, 4=Line, 5=LineGroup, 6=Teams, 7=RocketChat, 8=InCircle, 9=LineWorks（Notification と番号が違う） | 0（未設定） | Reminder.cs:45-56 |
| Subject | string | 件名 | — | Reminder.cs:28 |
| Body | string | 本文。`[[Records]]` の位置にレコード一覧が入る | `"[[Records]]"` | Reminder.cs:25,64 |
| Line | string | 1レコード分の行書式 | `"[Title] --- [Owner] ([Status])"` | Reminder.cs:65 / Reminder.json:14 |
| From | string | 送信元アドレス | — | Reminder.cs:31 |
| To | string | 宛先（Notification と同じく `[Owner]` 等が使える） | — | Reminder.cs:32,389-393 |
| Token | string | チャット系のトークン | — | Reminder.cs:33 |
| Column | string | 期限の判定に使う日付列 | `CompletionTime`（無ければ null） | Reminder.cs:34,157-163 |
| StartDateTime | DateTime | 初回送信日時（`"2025-10-17T08:00:00"`） | 明日 0:00 | Reminder.cs:35,66 |
| Type | int | 繰り返し（Times.RepeatTypes）: 10=Daily, 20=Weekly, 30=NumberWeekly, 40=Monthly, 50=EndOfMonth, 60=Yearly | 0（未設定） | Reminder.cs:36 / Server/Times.cs:22-30 |
| Range | int | 何日先までの期限を対象にするか（1〜1000） | 30 | Reminder.cs:37,67 / Reminder.json:15-17 |
| Condition | int | 条件（**ビュー ID**）。0 = 条件なし | 0 | Reminder.cs:42,552 |
| ExcludeOverdue | bool? | 期限切れを除外 | null | Reminder.cs:41,603 |
| SendCompletedInPast | bool? | 期限を過ぎた完了済みも送る | null | Reminder.cs:38,627 |
| NotSendIfNotApplicable | bool? | 対象レコードが無ければ送らない | null | Reminder.cs:39,204 |
| NotSendHyperLink | bool? | レコードへのリンクを付けない | null | Reminder.cs:40,499 |
| Disabled | bool? | 無効化 | null | Reminder.cs:43 |

既定では Status < 900（未完了）のみが対象（Reminder.cs:604-618）。

## 7. Summary（`Summaries[]`、集計）

**子（集計元）サイト側の SiteSettings に書く**。親サイトの列へ値を書き込む（ResultModel.cs:3405-3427）。

| プロパティ | 型 | 意味 | 根拠 |
|---|---|---|---|
| Id | int | — | Summary.cs:6 |
| SiteId | long | 集計先（親）サイト ID | Summary.cs:7 / ResultModel.cs:3409 |
| DestinationReferenceType | string | 親の種別（`"Results"` / `"Issues"`） | Summary.cs:8 |
| DestinationColumn | string | 親側の書き込み先（数値列。日付列は不可） | Summary.cs:9 / SiteUtilities.cs:10358-10365 |
| DestinationCondition | int? | 親側の条件（**親サイトのビュー ID**） | Summary.cs:10 / ResultModel.cs:3418 |
| SetZeroWhenOutOfCondition | bool? | 条件外の時 0 にする（条件がある時だけ有効） | Summary.cs:11,49-52 |
| LinkColumn | string | 子側で親を指しているリンク列（`ClassA` 等） | Summary.cs:12 |
| Type | string | `"Count"` / `"Total"` / `"Average"` / `"Min"` / `"Max"` | Summary.cs:13 / SiteUtilities.cs:10374-10384 |
| SourceColumn | string | 子側の集計対象列。`Type="Count"` の時は null にされる | Summary.cs:14,45-47 |
| SourceCondition | int? | 子側の条件（**子サイトのビュー ID**） | Summary.cs:15 / ResultModel.cs:3425 |

## 8. FormulaSet / Formula（`Formulas[]`、計算式）

### 8.1 FormulaSet

| プロパティ | 型 | 意味 | 既定 | 根拠 |
|---|---|---|---|---|
| Id | int | — | — | FormulaSet.cs:6 |
| CalculationMethod | string | `"Default"`（四則演算ツリー）/ `"Extended"`（関数式） | `"Default"` | FormulaSet.cs:7,19-23 |
| Target | string | 結果を書き込む列。Default は decimal 列（Num 等）のみ、Extended は添付・Id・Comments 等以外の列 | — | FormulaSet.cs:8 / SiteSettings.cs:2561-2579 |
| Condition | int? | 条件（**ビュー ID**）。一致しない時は OutOfCondition を使う | null | FormulaSet.cs:9 |
| Formula | Formula | Default の式（下記） | — | FormulaSet.cs:10 |
| OutOfCondition | Formula | 条件外の時の式（Default） | null | FormulaSet.cs:13 |
| FormulaScript | string | Extended の式 | null | FormulaSet.cs:14 |
| FormulaScriptOutOfCondition | string | Extended の条件外の式 | null | FormulaSet.cs:15 |
| FormulaMapping | string | `{列名: 表示名}` の JSON 文字列（画面で保存した時に自動生成） | null | FormulaSet.cs:16 / FormulaBuilder.cs:304-312 |
| NotUseDisplayName / IsDisplayError / Disabled | bool? | 表示名を使わない / エラーを画面に表示 / 無効化 | null | FormulaSet.cs:11-12,17 |

### 8.2 Formula（Default の式ツリー）

| プロパティ | 型 | 意味 | 根拠 |
|---|---|---|---|
| ColumnName | string | 列の値を使う | Formula.cs:9 |
| RawValue | decimal? | 定数 | Formula.cs:10 |
| OperatorType | int | 0=NotSet, 1=Addition, 2=Subtraction, 3=Multiplication, 4=Division（直前の兄弟要素との演算子） | Formula.cs:11,18-25 |
| Children | Formula[] | 括弧の中身。先頭の子は 0(NotSet) か 1。乗除を先に計算し、その後で加減する | Formula.cs:12,50-94 |

例: `NumC = (NumA + NumB) * 1.1`
```json
{"Id":1,"Target":"NumC","Formula":{"Children":[
  {"OperatorType":0,"Children":[{"ColumnName":"NumA"},{"ColumnName":"NumB","OperatorType":1}]},
  {"OperatorType":3,"RawValue":1.1}]}}
```

### 8.3 Extended の FormulaScript

- 列は `[ColumnName]`（例 `[NumA]`）または表示名で書く。実行時に `model.NumA` に置換される（FormulaBuilder.cs:247-266）。
- 使える関数（`$` は省略可・大小文字不問。FormulaServerScriptUtilities.cs:132-）:
  DATE, DATEDIF, DATETIME, DAY, DAYS, EOMONTH, HOUR, MINUTE, MONTH, NOW, SECOND, TODAY, WEEKDAY, YEAR,
  CONCAT, FIND, LEFT, LEN, LOWER, MID, REPLACE, RIGHT, SEARCH, SUBSTITUTE, TEXT, TRIM, UPPER, ASC, JIS, VALUE,
  AND, IF, IFS, IFERROR, NOT, OR, ISBLANK, ISERROR, ISEVEN, ISNUMBER, ISODD, ISTEXT,
  ABS, AVERAGE, MAX, MIN, MOD, ODD, POWER, RAND, ROUND, ROUNDDOWN, ROUNDUP, SQRT, TRUNC, LOGINUSERID, LOGINUSERNAME
- `#DIV/0!` 等のエラー値は IsDisplayError=true の時だけ例外になり、それ以外は SysLog に記録される（ResultModel.cs:3664-3683）。

## 9. Aggregation（`Aggregations[]`、一覧の集計表示）

| プロパティ | 型 | 意味 | 根拠 |
|---|---|---|---|
| Id | long | — | Aggregation.cs:14 |
| GroupBy | string | 分類する列（選択肢列）。分類しない時は `"[NotGroupBy]"` | Aggregation.cs:15 / SiteSettings.cs:3756,3774 |
| Type | int | **0=Count, 1=Total, 2=Average のみ**（Min / Max はない） | Aggregation.cs:7-12 |
| Target | string | 集計する数値列。Count の時は `""` | Aggregation.cs:17,29 |

## 10. Process（`Processes[]`、プロセス）

最小構成（実施中 → 完了 のボタン）:
```json
{"Id":1,"Name":"完了にする","CurrentStatus":200,"ChangedStatus":900}
```

| プロパティ | 型 | 意味 | 既定 | 根拠 |
|---|---|---|---|---|
| Id / Name | int / string | Name はボタン名 | — | Process.cs:48-49 |
| DisplayName | string | 表示名（Name と別にしたい時） | null | Process.cs:50 |
| ScreenType | int? | 10=New（新規画面）, 20=Edit（編集画面）。New 以外は編集画面に出る | null(=Edit) | Process.cs:15-19,51 / HtmlProcess.cs:24-25 |
| CurrentStatus | int | 表示する時の Status。**-1 = すべて** | 0 | Process.cs:52 / ResultModel.cs:2855-2856 |
| ChangedStatus | int | 実行後の Status。**-1 = 変更しない**（0 を書くと Status=0 になる） | 0 | Process.cs:53 / ResultModel.cs:3163-3165 |
| Description / Tooltip / Icon / ConfirmationMessage / SuccessMessage / ErrorMessage / OnClick | string | 説明・ツールチップ・アイコン・確認文・成功文・条件不一致時のエラー文・クリック時スクリプト | null | Process.cs:54-59,70 |
| ExecutionType | int? | 0=AddedButton（ボタン）, 10=CreateOrUpdate（保存時に自動）, 20=AddedButtonOrCreateOrUpdate | 0 | Process.cs:21-26 / ResultUtilities.cs:3318 |
| ActionType | int? | 0=Save, 10=PostBack, 90=None | 0 | Process.cs:28-33 |
| AfterProcessStatusChangeActionType | int? | 0=Default, 10=ReturnToList | 0 | Process.cs:35-39 |
| AllowBulkProcessing | bool? | 一覧から一括実行 | null | Process.cs:63 |
| ValidationType | int? | 0=Merge, 10=Replacement, 90=None | 0 | Process.cs:41-46 |
| ValidateInputs | ValidateInput[] | `{Id, ColumnName, Required?, ClientRegexValidation, ServerRegexValidation, RegexValidationMessage, Min?, Max?}` | null | ValidateInput.cs:10-17 |
| View | View | 実行できる条件（**View オブジェクトを埋め込む**。ID ではない） | null | Process.cs:69 |
| Depts / Groups / Users | int[] | 実行できる人。全部空なら全員（更新権限は必要） | null | Process.cs:66-68,464-478 |
| DataChanges | DataChange[] | 値の変更（下記） | null | Process.cs:71 |
| AutoNumbering | `{ColumnName, Format, ResetType?, Default?(1), Step?(1)}` | 自動採番 | null | AutoNumbering.cs:11-15 |
| Notifications | Notification[] | 実行時の通知 | null | Process.cs:73 |
| Disabled | bool? | 無効化 | null | Process.cs:74 |

DataChange: `{Id, Type, ColumnName, Value, BaseDateTime}`。Type は 0=CopyValue, 1=CopyDisplayValue,
2=InputValue, 3=InputValueFormula, 4=InputDate, 5=InputDateTime, 6=InputUser, 7=InputDept（DataChange.cs:18-28）。
InputDate / InputDateTime の Value は `"数値,単位"`（単位: Days / Months / Years / Hours / Minutes / Seconds）、
BaseDateTime は `"CurrentDate"` / `"CurrentTime"` / 日付列名（DataChange.cs:178-266）。

## 11. StatusControl（`StatusControls[]`、状況による制御）

最小構成（完了したら読み取り専用）:
```json
{"Id":1,"Name":"完了後ロック","Status":900,"ReadOnly":true}
```

| プロパティ | 型 | 意味 | 根拠 |
|---|---|---|---|
| Id / Name / Description | int / string / string | — | StatusControl.cs:25-27 |
| Status | int? | 対象の Status。**-1 = すべて** | StatusControl.cs:28 / ResultModel.cs:3357-3358 |
| ReadOnly | bool? | レコード全体を読み取り専用 | StatusControl.cs:29 |
| ColumnHash | {列名: string} | `"None"` / `"Required"` / `"ReadOnly"` / `"Hidden"`（文字列 enum） | StatusControl.cs:16-23,30 |
| View | View | 追加条件（**View オブジェクトを埋め込む**） | StatusControl.cs:31 / ResultModel.cs:3360-3364 |
| Depts / Groups / Users | int[] | 対象者。全部空なら全員 | StatusControl.cs:32-34,213-224 |
| Disabled | bool? | 無効化 | StatusControl.cs:36 |

## 12. Script / Style / Html / ServerScript

Script・Style・Html は共通で `Id`, `Title`, `Body` と、出力する画面の bool?: `All`, `New`, `Edit`, `Index`,
`Calendar`, `Crosstab`, `Gantt`, `BurnDown`, `TimeSeries`, `Analy`, `Kamban`, `ImageLib`、および `Disabled`,
`DraftOutputMode` int?, `DraftKey`（Script.cs:7-24 / Style.cs:7-24 / Html.cs:16-34）。

- Html の `PositionType` int: 1000=HeadTop, 1010=HeadBottom, 9000=BodyScriptTop, 9010=BodyScriptBottom。既定の 0 は該当なしなので必ず書く（Html.cs:8-14）。
- ServerScript: `Id`, `Title`, `Name`, `Body` と実行タイミングの bool?: `WhenloadingSiteSettings`, `WhenViewProcessing`, `WhenloadingRecord`, `BeforeFormula`, `AfterFormula`, `BeforeCreate`, `AfterCreate`, `BeforeUpdate`, `AfterUpdate`, `BeforeDelete`, `BeforeBulkDelete`, `AfterDelete`, `AfterBulkDelete`, `BeforeOpeningPage`, `BeforeOpeningRow`、ほかに `Shared`, `Functionalize`, `TryCatch`, `Disabled`, `Background` bool?, `TimeOut` int?（ServerScript.cs:9-35）。

## 13. めったに使わないクラス

- **Export**（`Exports[]`）: `Id`, `Name`, `Header` bool?, `Columns` ExportColumn[], `Type`（0=Csv, 1=Json）, `DelimiterType`（0=Comma, 1=Tab）, `EncloseDoubleQuotes` bool?, `ExecutionType`（0=Direct, 1=MailNotify）, `Depts`/`Groups`/`Users`, `Join`, `ExportCommentsJsonFormat` bool（Export.cs:12-42）
- **ExportColumn**: `Id`, `ColumnName`, `LabelText`, `ChoiceText`, `ChoiceValue`, `Type`（0=Value, 1=Text, 2=TextMini）, `Format`, `OutputClassColumn` bool?, `SiteId` long?（ExportColumn.cs:12-44）
- **ColumnAccessControl**（`Create/Read/UpdateColumnAccessControls[]`）: `ColumnName`, `No`, `Depts`/`Groups`/`Users` int[], `RecordUsers` string[]（`"Creator"`, `"Updator"`, `"Manager"`, `"Owner"` 等のレコード上のユーザー列）, `Type`（Permissions.Types のビット値: 1=Read, 2=Create, 4=Update, 8=Delete, 16=SendMail, 32=Export, 64=Import, 128=ManageSite, 256=ManagePermission）。全部空なら制限なし（ColumnAccessControl.cs:16-24,75-118 / Security/Permissions.cs:16-30）
- **Lookup**（Link.Lookups の要素）: `From`（リンク先の列）, `To`（自サイトの列）, `Type`（0=Value, 1=DisplayName）, `Overwrite` bool?（既定 true）, `OverwriteForm` bool?（Lookup.cs:12-33）

## 14. よくある間違い

1. ColumnFilterHash の値を配列のまま書く → **文字列** `"[\"a\"]"` にする（Dictionary<string,string>、View.cs:75）。
2. Summary / Notification / Reminder / Formula の条件にビュー名を書く → **ビュー ID（int）** を書く。Process / StatusControl の View は ID ではなく View オブジェクト。
3. Notification に `Name` を書く → 存在しない。`Prefix` / `Subject` を使う。
4. Process の ChangedStatus を省略する → 0 になり Status=0 に書き換わる。変えない時は `-1`。
5. Aggregation に Min / Max を書く → enum にない（0〜2 のみ）。
6. Links を手書きする → ChoicesText から再生成されるので不要。
7. `Version` を書かない → 移行処理が走る。`1.017` を書く。
