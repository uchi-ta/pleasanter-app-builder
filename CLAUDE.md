# プリザンター アプリ自動作成プロジェクト

ローカルのプリザンター（http://localhost:59803）に、テストデータ付きのアプリを短い指示で作るためのプロジェクト。

## ルール

- アプリの作成・削除・作り直しの依頼は `pleasanter-app` スキルで行う（手順・既定値・設計方針はスキルに書いてある）。
  アプリ名だけ言われたら、確認せずに既定値で最後まで進める
- `secret.txt` に接続先URLとAPIキーがある。キーは画面・ログ・ファイルに出さない。接続先は localhost のみ
- 作業ファイルは `output\<アプリ名>\`（spec.json / gen_rows.py / *.rows.json / package.json / result.json）に置く
- 削除は対象のタイトルと種類を表示してから行う。今回自分が作ったもの以外は、ユーザーが対象を明示した場合のみ
- Python は `PYTHONUTF8=1 python -P <script>` で実行する

## 参照先

- 仕様メモ・API・設定の早見表: `.claude\skills\pleasanter-app\reference\`
- プリザンターのソース: `C:\Implem\Implem.Pleasanter\Implem.Pleasanter`
- マニュアル: `C:\Implem\Implem.Pleasanter.Manual\ja\docs`
- 新しく分かった仕様は `reference\package-format.md` に追記する
