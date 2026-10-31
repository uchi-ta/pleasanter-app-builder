# pleasanter-app-builder

アプリ名を伝えるだけで、テストデータ付きのプリザンターのアプリを Claude Code が作成するための、スキルとスクリプト一式です。
テーブル・ダッシュボード・AI機能・説明書（Wiki）までを、自分のプリザンターに API で登録します。

## はじめにお読みください

- 作者は、プリザンターを作っているインプリムの代表です。個人で作った非公式のものなので、ご意見や不具合は Issue へどうぞ。
- **このリポジトリの内容は、AI（Claude Code）との対話によるバイブコーディングで作成したものです。**
  スクリプト・設定・ドキュメントは AI が生成し、人による網羅的なレビューやテストは行っていません。
  **参考実装として扱い、そのまま本番環境や業務データで使わないでください。**
- 動作確認は、筆者の検証環境（Windows 11 / プリザンター 1.5 系 / SQL Server）で行った範囲に限られます。
  他のバージョン・環境で同じように動く保証はありません。確認できていない点は `docs/11_振り返りと今後.md` にあります。
- ドキュメント（`docs/`）と仕様メモ（`reference/`）は、筆者が個人で作成した**非公式のメモ**で、多くを AI が書いています。誤りを含む可能性があります。プリザンターの正確な仕様は公式マニュアルを参照してください。数値・所要時間は作成時点の実績で、環境や AI の応答によって変わります。
- 生成されるテストデータは Faker などで作ったダミーです。会社名・氏名・連絡先は実在しません。
- 利用は自己責任でお願いします。本リポジトリによって生じた損害について、作成者は責任を負いません。

## AI 機能と外部送信について

- 作成するアプリには、Claude API（Anthropic）を呼ぶ AI 機能が組み込まれます。
  利用者が操作すると、**レコードの内容が外部の AI API に送信されます。**
- **個人情報・機密情報・実際の業務データを入力しないでください。** 実データで使う場合は、
  データの取り扱いルール・契約・送信範囲を別途確認してください。
- AI の出力は参考情報です。誤りを含む可能性があるので、必ず人が確認してください。
- Claude Code でアプリを作るとき、設計の内容（アプリ名・項目・生成ルール）は Anthropic に送信されます。

## API キー・接続先の扱い

- 接続先と API キーは `secret.txt` に書きます。`secret.txt.example` をコピーして作ってください。
  **`secret.txt` は `.gitignore` に入れてあります。コミット・共有しないでください。**

  ```
  PleasanterApiUrl:http://localhost:<ポート>/api/items/
  PleasanterApiKey:<プリザンターのAPIキー>
  ClaudeApiKey:<Claude API のキー>
  ```

- スクリプトは、`localhost` と、`scripts/plapi.py` の `ALLOWED_REMOTE_HOSTS` に書いたホスト以外の
  プリザンターには接続しません（既定は空）。自分が管理する（または利用を許可された）サーバーで使う場合だけ、
  そのホスト名を追加してください。**他人が運営する公開デモ環境などに、サイトの作成や大量のデータ登録を行わないでください。**
- AI 機能の Claude API のキーは、作成したサイトの共有サーバスクリプト「共通設定（APIキー）」に書き込みます。
  AI のスクリプト本体にはキーを書かないので、AI のスクリプトを画面に表示してもキーは映りませんが、
  **サイトの管理権限を持つ人は画面でキーを見られます。** 検証用の環境で使い、本番運用では、拡張サーバスクリプト
  （サーバ側ファイル + `//Include:`）に置く方式を検討してください（`docs/12_AI機能の組み込み.md`）。

## 動かし方

### 1. 準備（初回のみ）

詳しくは [環境構築手順.md](環境構築手順.md) を参照してください。最低限必要なのは次のとおりです。

1. 検証用のプリザンターを用意します（インストール手順はプリザンターのマニュアルを参照）。
2. このリポジトリと、プリザンターのソース・マニュアルの原稿を `C:\Implem` にクローンします。
   Claude Code が仕様を調べるのに使うので、**この場所を前提にしています**（`CLAUDE.md` とスキルの資料）。

   ```bash
   cd /c/Implem
   git clone https://github.com/uchi-ta/pleasanter-app-builder.git
   git clone https://github.com/Implem/Implem.Pleasanter.git
   git clone https://github.com/Implem/Implem.Pleasanter.Manual.git
   ```

3. Python 3.12 以上と Faker を入れます。

   ```bash
   python -m pip install --user faker
   ```

4. プリザンターで API キーを作り（検証用のテナントで、管理者権限のあるユーザー）、
   `secret.txt.example` を `secret.txt` にコピーして接続先とキーを書きます。AI 機能を使う場合は Claude API のキーも書きます。
5. [Claude Code](https://claude.com/claude-code) をインストールしてログインします。

### 2. アプリを作る（Claude Code から）

このフォルダで Claude Code を起動し、作りたいアプリを伝えます。

```
/pleasanter-app 図書貸出管理
```

「中野の飲み屋を登録し、管理するアプリをつくって」のような文章でもかまいません。
Claude Code が設計図（`output\<アプリ名>\spec.json`）を書き、テストデータの生成・登録・ダッシュボード・説明書 Wiki・
AI 機能の動作確認までを実行して、最後に URL と、依頼からデプロイまでの時間を表示します。
作成後に「〇〇の選択肢に△△を追加して」のように頼むと、データはそのままで設定だけを直します。

### 3. スクリプトだけで動かす（Claude Code を使わない確認）

見本の設計図を使って、スクリプトだけで動作を確認できます。

```bash
cd /c/Implem/pleasanter-app-builder
mkdir -p "output/問い合わせ管理"
cp .claude/skills/pleasanter-app/examples/compact/spec.json "output/問い合わせ管理/"
PYTHONUTF8=1 python -P .claude/skills/pleasanter-app/scripts/make_app.py "output/問い合わせ管理/spec.json"
```

| よく使うコマンド（`S` = `.claude/skills/pleasanter-app/scripts`、`O` = `output/<アプリ名>`） | 内容 |
|---|---|
| `python -P S/make_app.py O/spec.json` | 全工程（環境取得 → データ生成 → 検査 → 登録 → ダッシュボード → 説明書 → AI 確認） |
| `python -P S/make_app.py O/spec.json --no-register` | 登録せず、画面からインポートするサイトパッケージ（`package.json`）だけ作る |
| `python -P S/make_app.py O/spec.json --refresh-env` | 接続先を変えたときに、ユーザー・部署の一覧を取り直して作る |
| `python -P S/register.py O/spec.json --update-settings` | データはそのままで、設定（列・選択肢・ビュー・通知・AI）だけ直す |
| `python -P S/delete.py <SiteId>` | 削除する対象を表示する（`--yes` を付けると削除） |

- コマンドはすべて Git Bash で、先頭に `PYTHONUTF8=1` を付けて実行します。
- 結果に表示される URL から、フォルダ・ダッシュボード・説明書 Wiki を開いて確認します。

## フォルダ構成

| パス | 内容 |
|---|---|
| `環境構築手順.md` | 環境の作り方（インストール、公開リポジトリのクローン、API キー、secret.txt） |
| `CLAUDE.md` | Claude Code に常に読ませるプロジェクトのルール |
| `.claude/skills/pleasanter-app/` | アプリ作成スキル（手順書 `SKILL.md`、スクリプト、仕様メモ、見本） |
| `.claude/settings.json` | スクリプト実行の許可リスト（削除系は含めていない） |
| `docs/` | 仕組み・工夫・実績の説明資料（章ごとのファイル） |
| `output/` | アプリごとの作業ファイル（`.gitignore` でコミットの対象外） |
| `secret.txt.example` | 接続先と API キーの書き方の見本 |

## ライセンス

- このリポジトリのスクリプトとドキュメントは [MIT ライセンス](LICENSE) です。
- ただし、`.claude/skills/pleasanter-app/reference/` のうちプリザンターのマニュアルを要約した部分は、
  元のマニュアルと同じ **CC BY-NC-SA 4.0** です（[出典とライセンス](.claude/skills/pleasanter-app/reference/LICENSE-reference.md)）。
- プリザンター本体は OSS（AGPL-3.0）です: https://github.com/Implem/Implem.Pleasanter
- マニュアルの原稿: https://github.com/Implem/Implem.Pleasanter.Manual （CC BY-NC-SA 4.0）
- 作成したアプリの利用にあたっては、プリザンターのライセンスと、Claude API の利用規約を確認してください。
