# spec.json / rows の書き方

アプリ定義は `output/<アプリ名>/spec.json` に書く。SiteSettings への変換・ID採番・リンクの付け替えは
`scripts/build.py` と `scripts/register.py` が行うので、spec には「何を作るか」だけを書く。
完全な見本: `examples/it-assets/spec.json`（3テーブル、リンク・集計・計算式・通知・リマインダー・クロス集計・カンバン入り）

## 全体

```json
{
  "app": "アプリ名（フォルダ名になる）",
  "tables": [ { テーブル定義 }, ... ]
}
```

テーブルの並び順がメニューの並び順になる。登録順はリンクの依存関係から自動で決まる。

## テーブル定義

| キー | 必須 | 内容 |
|---|---|---|
| `key` | ○ | 英字の論理名（`assets` など）。リンク・集計の参照先指定に使う |
| `title` | ○ | テーブル名 |
| `keyColumn` | リンク先なら○ | 行を一意に識別する列（例 `ClassA` = 資産番号）。値は全行で一意・必須 |
| `columns` | ○ | 列定義の配列（下記）。並び順がエディタの並び順になる |
| `status` | | 状況の選択肢 `[[値, 表示名, 短縮名, CSSクラス], ...]`。既定値は先頭（`statusDefault` で変更可） |
| `titleColumns` / `titleSeparator` | | タイトル表示に使う列と区切り（区切りの既定は `)` なので `" "` 推奨） |
| `grid` / `editor` / `filters` | | 一覧・エディタ・フィルタの列。省略時は columns から自動生成 |
| `linkColumns` / `historyColumns` | | リンク先に表示する列 / 履歴の列 |
| `views` | | ビュー（下記）。**省略すると 標準 / 未完了 / 状況×最初の選択肢列 のクロス集計 が自動で入る。書くと書いた内容だけになる** |
| `extraViews` | | 自動のビュー（または views）に**追加**するビュー。集計の `sourceView` 用（例: 受講済みだけ）に使う |
| `aggregations` | | `{"groupBy": "ClassB"}`=件数、`{"groupBy": "ClassB", "target": "NumA"}`=合計（`type`: count/total/average のみ） |
| `formulas` | | `{"target": "NumC", "expr": "NumA - NumB"}`。演算子は `+ - * /`、左から順に計算（優先順位なし）。数値リテラル可（例 `"NumA * 1.1"`） |
| `summaries` | | 集計先へ書き込む: `{"to": "assets", "column": "NumB", "link": "ClassA", "type": "Total", "source": "NumA"}`。type は Count/Total/Average/Min/Max。**Count のときは `source` 不要**。`sourceView` でビュー名による絞り込み |
| `notifications` | | `{"subject", "to": "[Manager]", "monitor": ["Status"], "afterView": "ビュー名"}` |
| `reminders` | | `{"subject", "body", "line": "[ClassA] [Title]", "column": "DateB", "days": 30, "view": "ビュー名", "repeat": "weekly"}` |
| `settings` | | SiteSettings にそのまま上書きする値（spec で表せない設定用。`settings-catalog.md` 参照） |
| `rows` | | データファイル名（省略時 `<key>.rows.json`） |

## 列定義

```json
{"name": "ClassA", "label": "資産番号", "required": true}
```

| キー | 内容 |
|---|---|
| `name` | 列名。`Title` `Body` `Status` `Manager` `Owner` と `ClassA`〜`ClassZ` / `NumA`〜 / `DateA`〜 / `DescriptionA`〜 / `CheckA`〜 / `AttachmentsA`〜 |
| `label` | 表示名 |
| `required` / `readOnly` / `wide` | 必須 / 読取専用 / 横幅いっぱい |
| `format` | 数値の書式（`"C"`=通貨） |
| `default` | 既定値（日付の `"0"`=今日） |
| `choices` | 選択肢: 文字列の配列、`[[値, 表示名, ...]]`、`"@users"` / `"@depts"` / `"@groups"` |
| `link` | リンク先テーブルの key。ChoicesText・Links・Link表示を自動設定 |
| 大文字始まりのキー | Column の設定としてそのまま渡す（`"Unit": "本"`, `"DecimalPlaces": 1`, `"EditorFormat": "Ymdhm"` など） |

Manager / Owner / `choices: "@users"` の列はユーザー列、`@depts` は部署列として値が変換される。

## ビュー

```json
{"name": "未完了", "filter": {"Status": [100, 200]}, "sort": {"DateA": "asc"}}
{"name": "部署別", "mode": "Crosstab", "CrosstabGroupByX": "ClassD", "CrosstabGroupByY": "ClassA",
 "CrosstabAggregateType": "Total", "CrosstabValue": "NumD"}
{"name": "ボード", "mode": "Kamban", "KambanGroupByX": "Status", "KambanGroupByY": "ClassB",
 "KambanAggregateType": "Count", "KambanValue": "NumA"}
```

- `filter`: Class/Status/ユーザー列は値の配列で書く（JSON文字列への変換は自動）。Check は true/false。
  それ以外の書式（数値・日付の範囲など）は文字列でそのまま書く（`settings-catalog.md` の View 参照）
- `sort`: `asc` / `desc`
- `mode`: `Index` `Calendar` `Crosstab` `Gantt` `BurnDown` `TimeSeries` `Analy` `Kamban` `ImageLib`
- 大文字始まりのキーは View の設定としてそのまま渡す
- 通知・リマインダー・集計の条件はビュー**名**で指定する（ID は自動採番）

## rows（データ）

`output/<アプリ名>/<key>.rows.json` に、1行 = 列名→値 のフラットな配列で書く。
通常は `gen_rows.py`（`scripts/datagen.py` の `Gen` を使う）で生成する。

```json
[{"ClassA": "NPC-0001", "Title": "ThinkPad L14", "Status": 200, "Owner": "Tenant1_User11",
  "ClassE": "開発1部", "DateA": "2025-07-14", "NumA": 148000, "CheckA": true, "Body": ""}]
```

| 列の種類 | 値 |
|---|---|
| ユーザー列 | LoginId / 名前 / UserId（`output/env.json` にある実在ユーザー） |
| 部署・グループ列 | 部署名 / 部署コード / ID |
| リンク列 | リンク先テーブルの `keyColumn` の値（例 `"NPC-0001"`）。ResultId への変換は自動 |
| Date | `"YYYY-MM-DD"` または `"YYYY-MM-DDTHH:MM:SS"`。空なら null |
| Num / Check / Status | 数値 / true・false / 状況の値 |
| 集計先・計算式の列 | 書かない（登録時にプリザンターが計算する） |

`build.py` が検査すること: spec にない列、キー列の空・重複、状況・選択肢にない値、存在しないリンク先キー、
リンクの循環、ビュー名の誤り。

## 説明書用の記述（wiki.py が使う）

| キー | 場所 | 内容 |
|---|---|---|
| `description` | spec 直下 / 各テーブル / 各ダッシュボード / 各 ai | 何のための表・画面か（1〜2文） |
| `usage` | spec 直下 | 操作の流れ（文字列の配列、4〜7手順） |
| 列の `Description` | 列定義 | 入力欄のツールチップ（大文字始まりなのでそのまま Column に渡る） |

## ダッシュボード（dashboard.py が使う）

```json
"dashboards": [{"title": "営業ダッシュボード", "description": "...", "parts": [
  {"type": "quickaccess", "title": "メニュー", "showTitle": false, "h": 5, "tables": ["customers", "deals"]},
  {"type": "kpi", "title": "営業KPI", "h": 36, "cards": [...], "charts": [...]},
  {"type": "index", "title": "進行中の案件", "table": "deals", "w": 12, "h": 24,
   "filter": {"Status": [100, 200]}, "sort": {"DateB": "asc"}, "grid": ["ClassA", "Title", "Status", "DateB"]},
  {"type": "timeline", "title": "最近の更新", "tables": ["deals", "activities"], "x": 12, "w": 8, "h": 24,
   "titleTemplate": "[Title]", "bodyTemplate": "[Status] [Owner]", "count": 10, "display": "simple"},
  {"type": "kamban", "table": "deals", "h": 26, "filter": {...}, "x_by": "Status", "y_by": "Owner",
   "aggregate": "Total", "value": "NumC", "aggregationView": true},
  {"type": "calendar", "table": "activities", "h": 34, "fromTo": "DateA"}
]}]
```

- レイアウトは横20列・高さ1単位16px。`w` 既定20、`h` 既定20。`y` 省略時、`x>0` なら直前のパーツと同じ行、`x=0` なら次の行
- type: `quickaccess` `timeline` `custom`（`content`）`html`（`html`）`calendar` `kamban` `index` `kpi`
- `filter` / `sort` / `grid` はビューと同じ書き方（大文字始まりの `View` で生の View も渡せる）
- 日付の絞り込みは View では `["Today"]` `["ThisMonth"]` `["ThisYear"]` か絶対範囲のみ。直近N日は kpi の側で行う

### kpi パーツ（CustomHtml に集計テンプレートを埋め込む。外部ライブラリなし）

```json
"cards": [
  {"label": "契約MRR", "table": "customers", "agg": "sum", "column": "NumA", "filter": {"Status": [300]}, "format": "man", "note": "補足"},
  {"label": "加重パイプライン", "table": "deals", "agg": "sum", "column": "NumC", "weight": "NumE", "filter": {...}, "format": "man"},
  {"label": "受注率", "table": "deals", "agg": "count", "filter": {"Status": [900]},
   "ratioOf": {"agg": "count", "filter": {"Status": [900, 910]}}, "format": "pct"},
  {"label": "予定日超過", "table": "deals", "agg": "count", "filter": {"Status": [100], "DateB": "overdue"}, "format": "num"}
],
"charts": [
  {"title": "フェーズ別パイプライン", "table": "deals", "groupBy": "Status", "agg": "sum", "column": "NumC",
   "filter": {...}, "format": "man", "order": "key", "top": 10}
]
```

- `agg`: count / sum / avg。`weight` は値×weight列/100（確度で重み付け）。`ratioOf` で率
- `filter` の値: 配列＝いずれかに一致（Status は数値）、日付列は `thisMonth` `lastMonth` `thisYear` `overdue` `next:N` `past:N`
- `format`: `yen`（¥1,234）`man`（1,234.5万円）`pct`（%）`num`
- `order`: 既定は値の大きい順、`key` は選択肢の値の順（Status のフェーズ順など）
- グラフのラベルは表示名（Text）で出る。ユーザー列は氏名、Status は状況名

## AI機能（build.py が列とサーバスクリプトを生成）

```json
"ai": [{
  "title": "AI商談アシスト", "description": "...", "table": "deals",
  "trigger": {"check": "CheckA", "label": "AIで商談を分析する"},
  "model": "claude-haiku-5-5", "effort": "low", "maxTokens": 1500,
  "system": "あなたは〜です。",
  "instruction": "次の商談の状況を分析し〜",
  "inputs": ["ClassA", "Title", "Status", "NumC", "DateB", "Body"],
  "related": {"table": "activities", "link": "ClassA", "sort": "DateA", "limit": 8, "title": "この案件の営業活動",
              "columns": ["DateA", "ClassB", "Title", "Status", "Body"]},
  "outputs": [
    {"column": "DescriptionA", "key": "summary", "label": "AI: 状況サマリー", "instruction": "状況の要約（2〜3文の文字列）"},
    {"column": "ClassG", "key": "risk", "label": "AI: 失注リスク", "allowed": ["高", "中", "低"], "instruction": "..."},
    {"column": "NumG", "key": "probability", "label": "AI: 推定受注確度", "instruction": "0〜100の整数"},
    {"column": "DescriptionB", "key": "actions", "label": "AI: 次のアクション", "instruction": "文字列の配列、3件以内"}
  ],
  "stampColumn": "ClassH"
}]
```

- `trigger.check` のチェック列・`outputs` の列・`stampColumn` は、columns に無ければ自動で追加される（未使用の列名を選ぶ）
- 利用者がチェックをオンにして保存 → サーバスクリプト（BeforeCreate/BeforeUpdate）が Claude API を呼び、結果を書き込み、チェックを戻す
- `related` は `link` 列がこのレコードを指す関連テーブルの行を `items.Get` で取得してプロンプトに含める。
  `related.table` が AI 対象と同じテーブルのときは「`link` 列が同じ値の他のレコード」（例: 同じ訪問先の過去の日報）を取る
- Summary は数値の集計（Count/Total/Average/Min/Max）だけ。**「最終訪問日」のような日付の集計はできない**ので列を作らない
- 配列で返った値は「・」付きの改行区切りに、`allowed` 付きの列は許可値以外を書き込まない、Num 列は数値化
- API キーは登録時に secret.txt の `ClaudeApiKey` から差し込む（spec・rows・ログには書かない）。
  キーは共有サーバスクリプト「共通設定（APIキー）」（Id 90）だけに書き、AI のスクリプトは `CLAUDE_API_KEY` を参照する。
  デモで AI のスクリプトを画面に表示してもキーは映らない（共有スクリプトは開かないこと）
- **10秒制限**: サーバスクリプトは10秒で打ち切られる。入力は 10〜15 項目、関連は 10 件以内、出力は短く。既定の haiku・low で 4〜5 秒
- 動作確認は API で行える: `client.item(<ResultId>, 'Update', {'CheckHash': {'CheckA': True}})` → Get で出力列を確認

## データ生成ルール（autogen.py が使う。gen_rows.py を書かずに済む）

各テーブルに `data` を書くと、`<key>.rows.json` が自動で作られる。見本: `examples/compact/spec.json`

```json
"data": {"count": 100, "sortBy": "DateA", "cols": {
  "ClassA": "seq:Q-{:04d}",
  "Status": "pick:100=8,200=8,900=76,910=8",
  "ClassB": "faker:company",
  "Title": [{"when": {"ClassD": "不具合"}, "gen": "pick:画面が真っ白になる,検索できない"}, {"gen": "pick:操作方法の質問"}],
  "DateA": [{"when": {"Status": [100, 200]}, "gen": "date:-20..0"}, {"gen": "date:-300..-21"}],
  "DateB": "date:@DateA+3..10",
  "NumA": "int:10000..500000/1000",
  "Owner": "user", "ClassE": "dept",
  "Body": "tmpl:{ClassB}様より「{Title}」の問い合わせ"
}}
```

| ルール | 意味 |
|---|---|
| `seq:書式` | 連番（`{:04d}` → 0001）。`sortBy` を指定すると並べ替え後に振り直す |
| `pick:a,b,c` / `pick:a=3,b=1` | 選択（`=数` は重み）。数字だけの値は数値になる（Status など） |
| `int:最小..最大/刻み` / `num:最小..最大/刻み` | 整数 / 小数 |
| `date:-365..0` | 今日からの日数の範囲 |
| `date:@DateA+3..10` | 同じ行の別の日付列からの日数。前にずらすときは `date:@DateA-14..-7` |
| `date:@tickets.DateA+0..5` | リンクで選んだ親の日付列からの日数 |
| `date:@assets.DateA+30..900\|max=-15` | 末尾の `\|max=N` / `\|min=N` で、今日からN日の上限・下限に丸める（親の日付基準で未来日・矛盾した日付を作らないため） |
| `datetime:...` | `date` と同じ範囲で、業務時間帯の時刻付き（EditorFormat が Ymdhm の列用） |
| `bool:0.8` | 80% の確率で true |
| `user` / `user:LoginId1,LoginId2` | 実在ユーザー（env.json、管理者を除く）/ 指定のユーザーから |
| `dept` | 実在の部署（会社・取締役会を除く） |
| `faker:メソッド名` | Faker ja_JP（company, name, city, phone_number, email, catch_phrase など）。連絡先は架空の値 |
| `link:tickets` / `link:tickets\|Status=100,200` | リンク先テーブルの行を選び、その keyColumn の値を入れる（親の状況で絞れる） |
| `parent:tickets.Owner` | link で選んだ親の列の値を引き継ぐ |
| `tmpl:文章{列名}{ルール}` | 文章に他の列の値やルールの結果を埋め込む |
| `const:値` | 固定値 |
| 末尾 `?0.3` | 30% の確率で空にする（例 `date:-30..0?0.3`） |
| `[{"when": {...}, "gen": "..."}, {"gen": "..."}]` | 条件付き。上から順に、when の列の値が一致した最初のルールを使う |

- **子テーブルの日付は親の日付を基準にする**（例: 修理の受付日は資産の取得日より後）。今日からの固定範囲で作ると、親より前の日付になり AI や利用者に矛盾として指摘される
- `pick:` はカンマで区切るので、**選択肢の値にカンマを入れない**（「2,000円」は「2千円」と書く）。入れると値が分割されて検査で NG になる
- `cols` は書いた順に生成される。条件や `@列` で参照する列は先に書く
- 条件付きルールで、どの `when` にも当たらず最後に `when` なしのルールも無い行は、空になる
- 子テーブル（link する側）の件数は親の **2〜3倍** にすると、親1件あたりの明細が業務らしくなる（`count` で指定）
- 計算式・集計先・AI 出力・トリガーの列は書かない（プリザンターが計算・空のまま）
- Average / Min / Max の集計で、欠席・キャンセルなど対象外の行を除くときは `extraViews` に対象の状況のビューを作り、
  `summaries` の `sourceView` に指定する（空欄は 0 として平均に入るため）
- 未完了の状況は 10〜20% にし、日付を直近（-20..0 など）に寄せる。期限超過の例外も数件出るように範囲を取る
