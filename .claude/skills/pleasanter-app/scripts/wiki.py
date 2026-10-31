# spec.json と result.json からアプリの説明書（Markdown）を生成し、アプリのフォルダ内に Wiki として登録・更新する
# 使い方: python wiki.py <spec.json> [--dry-run]   （--dry-run は O/manual.md を書くだけ）
# spec に書けば説明書に反映されるもの: app の description / usage（操作の流れ）、テーブル・列の description
import argparse
import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(__file__))
import build as B  # noqa: E402
from plapi import Client  # noqa: E402

KINDS = {'Class': 'テキスト', 'Num': '数値', 'Date': '日付', 'Description': '長文', 'Check': 'チェック',
         'Attachments': '添付ファイル', 'Title': 'テキスト', 'Body': '長文', 'Status': '選択',
         'Manager': 'ユーザー', 'Owner': 'ユーザー'}
PART_NAMES = {'quickaccess': 'クイックアクセス', 'timeline': 'タイムライン', 'custom': 'カスタム', 'html': 'カスタムHTML',
              'calendar': 'カレンダー', 'kamban': 'カンバン', 'index': '一覧', 'kpi': 'KPI（集計タイル・グラフ）'}
MODES = {'Crosstab': 'クロス集計', 'Kamban': 'カンバン', 'Calendar': 'カレンダー', 'Gantt': 'ガント', 'TimeSeries': '時系列',
         'BurnDown': 'バーンダウン', 'Analy': '分析', 'ImageLib': '画像ライブラリ', 'Index': '一覧'}


def cell(s):
    return str(s if s not in (None, '') else '-').replace('|', '／').replace('\n', ' ')


def label_of(table, col):
    for c in table.get('columns', []):
        if c['name'] == col:
            return c.get('label', col)
    return {'Status': '状況', 'Title': 'タイトル', 'Body': '内容', 'Manager': '管理者', 'Owner': '担当者',
            'UpdatedTime': '更新日時', 'ResultId': 'ID'}.get(col, col)


def column_kind(c, tables):
    if 'link' in c:
        return f'リンク（{tables[c["link"]]["title"]}）'
    ch = c.get('choices')
    if ch == '@users':
        return 'ユーザー'
    if ch == '@depts':
        return '部署'
    if ch == '@groups':
        return 'グループ'
    if isinstance(ch, list):
        return '選択'
    return KINDS.get(B.col_type(c['name']), 'テキスト')


def choices_of(c):
    ch = c.get('choices')
    if not isinstance(ch, list):
        return ''
    vals = [str(x[1] if isinstance(x, (list, tuple)) and len(x) > 1 else (x[0] if isinstance(x, (list, tuple)) else x))
            for x in ch]
    return '、'.join(vals[:10]) + ('…' if len(vals) > 10 else '')


def filter_text(table, flt):
    status = {s[0]: s[1] for s in table.get('status', [])}
    out = []
    for col, v in (flt or {}).items():
        if isinstance(v, list):
            v = '・'.join(status.get(x, str(x)) if col == 'Status' else str(x) for x in v)
        out.append(f'{label_of(table, col)}＝{v}')
    return '、'.join(out)


def expr_text(table, expr):
    return ' '.join(label_of(table, t) if B.EXTENDED.match(t) else t for t in expr.split())


def render(spec, result, client=None):
    tables = {t['key']: t for t in spec['tables']}
    web = client.web_root if client else 'http://localhost/'
    sites = result.get('sites', {})
    L = [f'# {spec["app"]} 説明書', '',
         f'最終更新: {date.today().isoformat()}（この Wiki は spec.json から自動生成されています。手で編集した内容は再生成で上書きされます）', '']
    if spec.get('description'):
        L += ['## このアプリについて', '', spec['description'], '']
    L += ['## 構成', '', '| 種類 | 名前 | 内容 | 件数 |', '|---|---|---|---|']
    for t in spec['tables']:
        sid = sites.get(t['title'])
        name = f'[{t["title"]}]({web}items/{sid}/index)' if sid else t['title']
        L.append(f'| テーブル | {name} | {cell(t.get("description"))} | {result.get("counts", {}).get(t["title"], "-")} |')
    for d in spec.get('dashboards', []):
        sid = result.get('dashboards', {}).get(d['title'])
        name = f'[{d["title"]}]({web}items/{sid}/index)' if sid else d['title']
        L.append(f'| ダッシュボード | {name} | {cell(d.get("description"))} | - |')
    for a in spec.get('ai', []):
        L.append(f'| AI機能 | {a["title"]} | {cell(a.get("description"))} | - |')
    L.append('')

    rel = [(t, c) for t in spec['tables'] for c in t.get('columns', []) if 'link' in c]
    if rel:
        L += ['## テーブルのつながり', '']
        for t, c in rel:
            L.append(f'- **{tables[c["link"]]["title"]}** 1件に対して **{t["title"]}** が複数件つながります'
                     f'（{t["title"]}の「{c.get("label", c["name"])}」で選択）')
        L.append('')
    if spec.get('usage'):
        L += ['## 操作の流れ', ''] + [f'{i}. {s}' for i, s in enumerate(spec['usage'], start=1)] + ['']

    for t in spec['tables']:
        L += [f'## {t["title"]}', '']
        if t.get('description'):
            L += [t['description'], '']
        L += ['### 項目', '', '| 項目 | 種類 | 必須 | 選択肢・補足 |', '|---|---|---|---|']
        auto = {f['target']: '自動計算: ' + expr_text(t, f['expr']) for f in t.get('formulas', []) if 'expr' in f}
        for ot in spec['tables']:
            for s in ot.get('summaries', []):
                if s['to'] == t['key']:
                    what = '件数' if s.get('type', 'Count') == 'Count' else f'{label_of(ot, s["source"])}の{ {"Total": "合計", "Average": "平均", "Min": "最小", "Max": "最大"}[s["type"]]}'
                    cond = f'（{s["sourceView"]}のみ）' if s.get('sourceView') else ''
                    auto[s['column']] = f'自動集計: {ot["title"]}の{what}{cond}'
        for c in t.get('columns', []):
            if c['name'] == 'Status':
                continue
            note = auto.get(c['name']) or choices_of(c) or c.get('description', '')
            L.append(f'| {c.get("label", c["name"])} | {column_kind(c, tables)} | {"○" if c.get("required") else ""} | {cell(note)} |')
        L.append('')
        if t.get('status'):
            L += ['### 状況', '', ' → '.join(s[1] for s in t['status']), '']
        if t.get('views'):
            L += ['### ビュー', '', '| ビュー | 表示 | 絞り込み |', '|---|---|---|']
            for v in t['views']:
                L.append(f'| {v["name"]} | {MODES.get(v.get("mode"), "一覧")} | {cell(filter_text(t, v.get("filter")))} |')
            L.append('')
        alerts = [f'- 通知: 「{n.get("subject", "")}」 … {n.get("afterView", "条件なし")}になったとき {n.get("to", "[Manager]")} にメール'
                  for n in t.get('notifications', [])]
        alerts += [f'- リマインダー: 「{r["subject"]}」 … {label_of(t, r["column"])}の{r.get("days", 30)}日前から'
                   f'{ {"daily": "毎日", "weekly": "毎週", "monthly": "毎月"}[r.get("repeat", "weekly")]} {r.get("to", "[Manager]")} にメール'
                   f'（対象: {r.get("view", "全件")}）' for r in t.get('reminders', [])]
        if alerts:
            L += ['### 通知・リマインダー', ''] + alerts + ['']

    for d in spec.get('dashboards', []):
        L += [f'## ダッシュボード: {d["title"]}', '']
        for p in d['parts']:
            src = '、'.join(tables[k]['title'] for k in p.get('tables', [p['table']] if 'table' in p else []))
            L.append(f'- **{p.get("title") or PART_NAMES[p["type"]]}**（{PART_NAMES[p["type"]]}{"・" + src if src else ""}）')
            for c in p.get('cards', []):
                L.append(f'  - {c["label"]}{"：" + c["note"] if c.get("note") else ""}')
            for c in p.get('charts', []):
                L.append(f'  - グラフ: {c["title"]}')
        L.append('')

    for a in spec.get('ai', []):
        t = tables[a['table']]
        trig = label_of(t, a['trigger']['check'])
        sid = sites.get(t['title'])
        link = f'[{t["title"]}]({web}items/{sid}/index)' if sid else t['title']
        rel = a.get('related')
        L += [f'## AI機能: {a["title"]}', '', a.get('description', ''), '',
              '### 使い方', '',
              f'1. {link} を開き、AIに分析させたいレコードの編集画面を開きます。',
              f'2. 「{trig}」をオンにして、「更新」（新規作成のときは「作成」）を押します。',
              '3. 数秒待つと保存が完了し、画面下に「AIの結果を反映しました。」と表示されます。',
              '4. 次の項目に結果が書き込まれます。' + ''.join(f'\n    - **{o["label"]}**' for o in a['outputs']),
              f'5. 「{trig}」は自動でオフに戻ります。もう一度分析するときは、再びオンにして保存します（活動や項目を更新した後に実行すると、最新の内容で分析されます）。',
              '',
              '### 知っておくこと', '',
              '- AIの結果は参考情報です。内容を確認してから判断に使ってください。同じ内容でも実行のたびに結果が変わることがあります。',
              '- 再実行すると、AIの項目は新しい結果で上書きされます（それ以外の項目は変わりません）。',
              '- AIの呼び出しに失敗したときは黄色い警告が表示されますが、レコードの保存は通常どおり行われます。時間をおいて再実行してください。',
              ]
        if rel:
            L.append(f'- AIには、このレコードの項目に加えて、関連する「{tables[rel["table"]]["title"]}」の新しい順に最大{rel.get("limit", 10)}件も渡します。'
                     '活動や履歴を記録しておくほど、分析の精度が上がります。')
        L += ['',
              '### 仕組み', '',
              f'- 対象: {t["title"]}',
              f'- 実行のタイミング: {a.get("trigger_text", "")}',
              f'- AIに渡す項目: {"、".join(label_of(t, c) for c in a.get("inputs", []))}',
              f'- 結果を書き込む項目: {"、".join(o["label"] for o in a.get("outputs", []))}',
              f'- 使用モデル: {a.get("model", "claude-haiku-5-5")}（1回 4〜5 秒程度。サーバスクリプトの上限は10秒）',
              '- 送信先: 外部のAI API（実在する個人情報・機密情報は入力しないでください）', '']

    L += ['## 補足', '', '- テストデータは自動生成したダミーです。会社名・氏名・連絡先は実在しません。',
          '- 設定を変えたいときは spec.json を修正して再登録します（画面で変更した設定は再生成時に失われます）。', '']
    return '\n'.join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('spec')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    spec = B.load_spec(a.spec)
    B.apply_ai(spec, {t['key']: t for t in spec['tables']})  # AI機能で追加される列・実行条件を説明書に反映する
    for t in spec['tables']:
        B.auto_complete(t)  # 自動で補ったビューも説明書に載せる
    if 'dashboards' not in spec:
        from dashboard import auto_dashboard
        spec['dashboards'] = auto_dashboard(spec)
    result_path = os.path.join(spec['_dir'], 'result.json')
    result = json.load(open(result_path, encoding='utf-8')) if os.path.exists(result_path) else {}
    client = None if a.dry_run else Client()
    md = render(spec, result, client)
    with open(os.path.join(spec['_dir'], 'manual.md'), 'w', encoding='utf-8') as f:
        f.write(md)
    print(f'説明書を生成: {len(md.splitlines())}行 → {os.path.join(spec["_dir"], "manual.md")}')
    if a.dry_run:
        return
    title = f'{spec["app"]} 説明書'
    # 本文が "[md]" で始まるときだけ Markdown として描画される（それ以外は記号がエスケープされたメモ表示）
    body = '[md]\n' + md
    wiki = result.get('wiki')
    if wiki:
        client.item(wiki['wikiId'], 'Update', {'Title': title, 'Body': body})
        print(f'更新: {title} {client.web_root}items/{wiki["wikiId"]}')
    else:
        sid = client.item(result['sites']['_root'], 'CreateSite', {
            'Title': title, 'ReferenceType': 'Wikis', 'Body': body, 'SiteSettings': {'Version': 1.017}})['Id']
        rows = client.item(sid, 'Get').get('Response', {}).get('Data') or []
        wiki_id = rows[0].get('WikiId') if rows else None
        result['wiki'] = {'siteId': sid, 'wikiId': wiki_id or sid}
        with open(result_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=1)
        print(f'作成: {title} (SiteId {sid}, WikiId {wiki_id}) {client.web_root}items/{sid}/index')


if __name__ == '__main__':
    main()
