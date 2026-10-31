---
name: pleasanter-app
description: アプリ名（例「図書貸出管理」）を受け取り、テストデータ付きのプリザンターアプリを設計してローカルのプリザンターにAPIで登録する。サイトパッケージJSONの出力、作成したアプリの削除・作り直しもこのスキルで行う。「〜アプリを作って」「〜管理を作成」「プリザンターに〜」と言われたら使う。
---

# プリザンターアプリ自動作成

引数: `<アプリ名> [件数N] [通知なし] [登録しない] [を削除]`
既定値: 各テーブル100件 / 2〜4テーブル / 通知・リマインダーあり / 登録まで実行 / トップ直下に作成。
**設計方針の確認はしない。** 既定値と下の設計ガイドで決めて進め、最後の報告でまとめて伝える。

## 前提（調べ直さない）

- 接続先・APIキーは `C:\Implem\pleasanter-app-builder\secret.txt`（localhost のみ。キーは表示・ログ出力しない。scripts が読む）
- Python は `PYTHONUTF8=1 python -P` で実行する（`-I` だと Faker が読めない。UTF8 指定がないと文字化け）
- S = `C:\Implem\pleasanter-app-builder\.claude\skills\pleasanter-app`、O = `C:\Implem\pleasanter-app-builder\output\<アプリ名>`
- 仕様の事実は `reference/package-format.md`、spec の書き方は `reference/spec-format.md` にある。
  ソースやマニュアルは、そこに載っていない設定を使うときだけ `reference/sources.md` の索引から引く

- **接続先（secret.txt の PleasanterApiUrl）を変えたら** `make_app.py ... --refresh-env` でユーザー・部署を取り直す（env.json は接続先ごとに内容が違う）。
  localhost 以外へは `plapi.py` の `ALLOWED_REMOTE_HOSTS` に載っている、ユーザーが許可したホストにだけ接続できる。外部環境では SysLogs 確認は省略される

## 手順（最短ルート：Claude が書くのは spec.json 1つだけ）

0. **依頼時刻を記録する**: 依頼を受けたら、設計を考える前の最初のツール呼び出しで `date +%FT%T` を実行し、
   表示された時刻を控える（2. の `--requested-at` に渡す。失敗して再実行するときも同じ時刻を渡す）
1. **spec を書く**: `examples/compact/spec.json`（問い合わせ管理）をひな形に、`O/spec.json` を **1回で** 書く。
   - テーブル・列・status・`data`（生成ルール）・`ai`・`description`・`usage` を書く
   - **views・aggregations・dashboards は書かない**（自動で補われる）。特別な集計を見せたいときだけ書く
   - 生成ルールの書き方は `reference/spec-format.md` の「データ生成ルール」。ユーザーは `user`、部署は `dept` で、
     実在の値（`output/env.json`）が自動で使われる
2. **全工程を1コマンドで実行**: `python -P S/scripts/make_app.py O/spec.json --requested-at <0. の時刻>`
   - 環境取得（1日以内なら省略）→ データ生成 → 検査・パッケージ出力 → 登録・検証 → ダッシュボード → 説明書Wiki
     → AI機能の動作確認 → SysLogs 確認 を自動で行い、工程ごとの秒数を表示・`O/result.json` に記録する
   - 目安: 2テーブル×100件で約10秒（うち AI 動作確認 3〜5 秒）
   - NG が出たら、表示されたエラー文の場所（spec の列・ルール）を直して同じコマンドを再実行する。
     登録後の NG（検証・AI）は、作り直さずに `register.py O/spec.json --update-settings` で直せることが多い
3. **報告**: URL（フォルダ・ダッシュボード・説明書 Wiki）、テーブルと件数、AI機能のテーマと動作確認の結果、
   警告、**依頼からデプロイまでの時間**（`make_app.py` の最後に表示、`result.json` の `request_to_deploy`）と
   `make_app.py` の所要時間。ダッシュボードは画面で描画されるので「開いて確認し、エラーが出たら知らせてほしい」と伝え、
   知らされたら `syslogs.py 60 --url DashboardPart --stack` で原因を読む（推測で直さない）

ルールで表せない複雑なデータ（例: 親の状況から子の件数を変える）が必要なときだけ、`O/gen_rows.py` を書く
（`examples/it-assets/gen_rows.py` が雛形。make_app.py は gen_rows.py があれば autogen の後に実行する）。

設定だけを直すとき（列・ビュー・通知・AI のプロンプトなど）は、作り直さずに
`python -P S/scripts/register.py O/spec.json --update-settings` → `dashboard.py` → `wiki.py` で反映する（データは変わらない）。

「登録しない」なら `make_app.py O/spec.json --no-register` で package.json まで作る（画面のサイトパッケージのインポート用）。

## 削除・作り直し

- 削除: `python -P S/scripts/delete.py <SiteIdかURL>` で対象を表示 → 自分が今回作ったもの、
  またはユーザーが対象を明示したものだけ `--yes` で削除する。それ以外は表示内容を見せて確認する
- 作り直し: 削除してから `make_app.py` を再実行（spec はそのまま使える）

## 設計ガイド

- 業務の中心となる台帳 1 つ ＋ 履歴・明細などリンクする表 1〜2 つ ＋ 必要ならマスタ。リンクで親子をつなぎ、
  子の件数や金額を親に Summary で集計する
- 各テーブル: 状況（`status`）、担当者（Manager）、利用者・申請者（Owner）、部署（`@depts`）、日付2つ程度、
  金額・数量、選択肢列 2〜3、備考。列は 10〜18 程度
- ビュー: 省略すると 標準 / 未完了 / 状況×最初の選択肢列のクロス集計 が自動で入る
- 通知: 重要な状況変化 1 件（`afterView`）。リマインダー: 期限日がある表に 1 件
- **ダッシュボード（毎回1つ）**: 省略すると、状況列と数値列が多い中心のテーブルから自動で作る（件数・未完了・完了率・
  金額合計・期限14日以内・期限超過、状況別/担当別/選択肢別のグラフ、未完了一覧、タイムライン、カンバン、カレンダー）。
  期限の列は label に「期限・予定・納期・期日・締切」を含めると KPI に使われる。業務固有の指標が要るときだけ `dashboards` を書く
- **AI機能（毎回1つ）**: アプリの業務に合うテーマを決める（例: 商談の分析と次のアクション、問い合わせの分類と回答案、
  日報の要約、点検記録からの異常検知、求人票の改善提案）。中心の台帳か履歴の表に付け、関連テーブルの直近履歴も渡す。
  出力は 2〜4 項目（要約・分類（選択肢）・数値・提案の箇条書き）。サーバスクリプトの上限が10秒なので、
  入力は必要な項目に絞り、出力は短くする
- **説明書**: spec に `description`（アプリ・各テーブル・ダッシュボード）と `usage`（操作の流れ 4〜7 手順）を書く。
  wiki.py がこれと設定から Wiki を生成する
- 計算式: 残数・差額・合計など自然に出るものだけ
- データ: 業務としてもっともらしい値（実在しそうな製品名・件名）、状況や日付の分布に偏りを付ける。今日の日付を基準にする
  - 未完了（受付・対応中など）は各表の **10〜20%** を、直近（概ね30日以内）の日付で必ず作る。
    日付を一様に散らすと未完了が数件になり、「未完了」ビューや通知・リマインダーの確認ができない
  - 期限切れ・超過・在庫不足などの例外データを数件混ぜる。ビューの絞り込み結果が 0 件にならないようにする
- ユーザー・部署は `output/env.json` の実在値を使う（UserId 1〜2 の管理者は避ける）
- 個人情報に見える値（実在人物の住所・電話など）は作らない。Faker のダミー値は可
- AI機能はレコード内容を外部の Claude API に送る。テストデータはダミーなので可。実データを入れる運用にしない

## 時間をかけないために

- 見本は `examples/compact/spec.json`（最短の書き方）。ダッシュボードを手で書く例は `reference/spec-format.md`

- spec にない設定が必要なときだけソースを見る。見たら `reference/package-format.md` に1行追記する
- 失敗したら推測で直さず、register.py / build.py のエラー文を読む
- env.py は設計と並行して走らせる。gen_rows.py と spec は同時に書いてよい
