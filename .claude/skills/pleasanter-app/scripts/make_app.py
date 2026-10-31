# アプリ作成の全工程を1回で実行し、工程ごとの所要時間を記録する
# 使い方: python make_app.py <spec.json> [--no-register] [--skip-ai-test] [--requested-at 依頼時刻]
# 工程: 環境取得(1日以内なら省略) → データ生成(autogen または gen_rows.py) → 検査・パッケージ出力
#       → 登録・検証 → ダッシュボード → 説明書Wiki → AI機能の動作確認 → SysLogs 確認
import argparse
import datetime
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
ENV = os.path.join(PROJECT, 'output', 'env.json')
sys.path.insert(0, HERE)
WARN = []


def run(label, args, timings, codes=(0,)):
    t = time.time()
    r = subprocess.run([sys.executable, '-P'] + args, capture_output=True, text=True, encoding='utf-8',
                       env=dict(os.environ, PYTHONUTF8='1'))
    timings[label] = round(time.time() - t, 1)
    out = (r.stdout + r.stderr).strip()
    if r.returncode == 2:
        WARN.append(f'{label}: 検証 NG（内容は上の出力）')
    print(f'■ {label}（{timings[label]}秒）')
    if out:
        print('  ' + out.replace('\n', '\n  '))
    if r.returncode not in codes:
        print(f'NG: {label} が失敗しました（終了コード {r.returncode}）')
        return False
    return True


def ai_test(spec_path, timings):
    # AI 対象テーブルの未完了レコード1件でトリガーを入れ、出力列が埋まることを確かめる
    import build as B
    from plapi import Client
    spec = B.load_spec(spec_path)
    if not spec.get('ai'):
        return True
    result = json.load(open(os.path.join(spec['_dir'], 'result.json'), encoding='utf-8'))
    c = Client()
    t0 = time.time()
    ok = True
    for a in spec['ai']:
        table = next(t for t in spec['tables'] if t['key'] == a['table'])
        sid = result['sites'][table['title']]
        rows = c.get_all(sid)
        open_rows = [r for r in rows if (r.get('Status') or 0) < 900] or rows
        target = open_rows[0]
        c.item(target['ResultId'], 'Update', {'CheckHash': {a['trigger']['check']: True}})
        got = c.item(target['ResultId'], 'Get')['Response']['Data'][0]
        filled = []
        for o in a['outputs']:
            kind = B.col_type(o['column'])
            v = got.get(f'{kind}Hash', {}).get(o['column'])
            filled.append(v not in (None, '', 0))
        reset = got.get('CheckHash', {}).get(a['trigger']['check']) is False
        status = 'OK' if all(filled) and reset else 'NG'
        ok &= status == 'OK'
        print(f'  {a["title"]}: {status}（ID {target["ResultId"]}、出力 {sum(filled)}/{len(filled)} 項目、トリガー解除 {reset}）')
    timings['AI動作確認'] = round(time.time() - t0, 1)
    print(f'■ AI動作確認（{timings["AI動作確認"]}秒）')
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('spec')
    ap.add_argument('--no-register', action='store_true')
    ap.add_argument('--skip-ai-test', action='store_true')
    ap.add_argument('--refresh-env', action='store_true', help='接続先を変えたときにユーザー・部署を取り直す')
    ap.add_argument('--requested-at', help='依頼を受けた時刻（例 2026-10-31T10:55:00）。依頼からデプロイまでの時間を記録する')
    a = ap.parse_args()
    spec_path = os.path.abspath(a.spec)
    spec_dir = os.path.dirname(spec_path)
    spec = json.load(open(spec_path, encoding='utf-8-sig'))
    timings = {}
    t0 = time.time()
    s = lambda name: os.path.join(HERE, name)  # noqa: E731

    if a.refresh_env or not os.path.exists(ENV) or time.time() - os.path.getmtime(ENV) > 86400:
        if not run('環境取得', [s('env.py'), ENV], timings):
            sys.exit(1)
    if any(t.get('data') for t in spec['tables']):
        if not run('データ生成(autogen)', [s('autogen.py'), spec_path], timings):
            sys.exit(1)
    gen = os.path.join(spec_dir, 'gen_rows.py')
    if os.path.exists(gen):
        if not run('データ生成(gen_rows)', [gen], timings):
            sys.exit(1)
    if not run('検査・パッケージ出力', [s('build.py'), spec_path, '--package', os.path.join(spec_dir, 'package.json'),
                                  '--env', ENV], timings):
        sys.exit(1)
    if a.no_register:
        print(f'登録は省略しました（合計 {round(time.time() - t0, 1)} 秒）')
        return
    steps = [('登録・検証', [s('register.py'), spec_path]),
             ('ダッシュボード', [s('dashboard.py'), spec_path]),
             ('説明書Wiki', [s('wiki.py'), spec_path])]
    ok = True
    for label, args in steps:
        # register.py の終了コード 2 は「登録は済んだが検証で NG」。後続の工程は続け、最後に NG として報告する
        if not run(label, args, timings, codes=(0, 2)):
            sys.exit(1)
    ok = True
    if not a.skip_ai_test:
        ok = ai_test(spec_path, timings)
    from plapi import Client
    if Client().is_local:
        run('SysLogs確認', [s('syslogs.py'), '15'], timings)
    else:
        print('■ SysLogs確認: 接続先が外部のため省略（SysLogs はローカルの DB を読む機能）')
    timings['合計'] = round(time.time() - t0, 1)
    result_path = os.path.join(spec_dir, 'result.json')
    result = json.load(open(result_path, encoding='utf-8'))
    result['make_app_seconds'] = timings
    if a.requested_at:
        # 依頼からデプロイまで（設計・spec の作成、失敗後の作り直しを含む）
        req = datetime.datetime.fromisoformat(a.requested_at)
        done = datetime.datetime.now().replace(microsecond=0)
        sec = int((done - req).total_seconds())
        result['request_to_deploy'] = {'requested_at': req.isoformat(), 'deployed_at': done.isoformat(), 'seconds': sec}
    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print('所要時間:', json.dumps(timings, ensure_ascii=False))
    if 'request_to_deploy' in result and a.requested_at:
        sec = result['request_to_deploy']['seconds']
        print(f'依頼からデプロイまで: {sec // 60}分{sec % 60}秒（依頼 {a.requested_at}）')
    print('URL:', result.get('url'))
    for w in WARN:
        print('NG:', w)
    if not ok or WARN:
        sys.exit(2)


if __name__ == '__main__':
    main()
