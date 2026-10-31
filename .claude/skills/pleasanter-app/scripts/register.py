# spec.json と rows をプリザンターにAPIで登録し、登録結果を検証する
# 使い方: python register.py <spec.json> [--parent 親サイトID(既定0=トップ)] [--keep-on-fail]
# 手順: サイト作成(直列) → 設定更新(リンク・集計、並列) → データ投入(依存段階ごと・表ごとに並列)
#       → 通知・リマインダーを有効化 → 集計の同期 → 検証
import argparse
import copy
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(__file__))
import build as B  # noqa: E402
from env import fetch  # noqa: E402
from plapi import Client  # noqa: E402

CHUNK = 500
WORKERS = 8


def log(*a):
    print(*a, flush=True)


def pmap(fn, items):
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        return list(ex.map(fn, items))


def base_settings(ss):
    # 作成時点では他サイトのIDが未確定なので、参照を含む設定を外す
    ss = copy.deepcopy(ss)
    for k in ('Links', 'Summaries', 'Notifications', 'Reminders', 'ServerScripts'):
        ss.pop(k, None)
    for c in ss['Columns']:
        if B.SITE_REF in c.get('ChoicesText', ''):
            del c['ChoicesText']
    return ss


def without_alerts(ss):
    # データ投入中は通知・リマインダー・サーバスクリプト（AI機能）を動かさない
    ss = copy.deepcopy(ss)
    for k in ('Notifications', 'Reminders', 'ServerScripts'):
        ss.pop(k, None)
    return ss


def with_secrets(ss, client):
    # AI機能のサーバスクリプトに Claude API キーを埋め込む（キーは表示・ログ出力しない）
    if not ss.get('ServerScripts'):
        return ss
    key = client.secret('ClaudeApiKey')
    ss = copy.deepcopy(ss)
    for s in ss['ServerScripts']:
        s['Body'] = s['Body'].replace(B.SECRET_REF, key)
    return ss


def key_map(client, site_id, key_column):
    rows = client.get_all(site_id)
    m = {}
    for r in rows:
        v = r.get('ClassHash', {}).get(key_column) if key_column.startswith('Class') else r.get(key_column)
        m[v] = r['ResultId']
    return m, rows


def register(client, built, parent):
    t0 = time.time()
    timings = {}
    site_ids = {}
    tables = built['tables']
    root = client.item(parent, 'CreateSite', {'Title': built['app'], 'ReferenceType': 'Sites', 'SiteSettings': {}})['Id']
    site_ids['_root'] = root
    log(f'フォルダ作成: {built["app"]} ({root})')
    try:
        # メニューの並び順を spec の順にするため、サイト作成だけは直列で行う（1件0.1秒程度）
        keys = list(tables)
        for k in keys:
            site_ids[k] = client.item(root, 'CreateSite', {
                'Title': tables[k]['title'], 'ReferenceType': 'Results',
                'SiteSettings': base_settings(tables[k]['settings'])})['Id']
        resolved = {k: B.resolve_sites(tables[k]['settings'], site_ids) for k in keys}
        pmap(lambda k: client.item(site_ids[k], 'UpdateSite', {'SiteSettings': without_alerts(resolved[k])}), keys)
        timings['サイト作成'] = time.time() - t0
        log('サイト作成: ' + ', '.join(f'{tables[k]["title"]}({site_ids[k]})' for k in keys))

        t1 = time.time()
        env = fetch(client)
        resolver = B.Resolver(env)
        link_maps, fetched = {}, {}
        referenced = {target for t in tables.values() for target in t['links'].values()}
        for level in built['levels']:
            def load(k):
                t = tables[k]
                recs = [B.to_record(t, r, resolver, link_maps) for r in t['rows']]
                chunks = [recs[i:i + CHUNK] for i in range(0, len(recs), CHUNK)]
                for ch in chunks:
                    client.item(site_ids[k], 'BulkUpsert', {'Data': ch})
                return len(recs)
            counts = pmap(load, level)
            log('データ投入: ' + ', '.join(f'{tables[k]["title"]} {n}件' for k, n in zip(level, counts)))
            need = [k for k in level if k in referenced]
            maps = pmap(lambda k: key_map(client, site_ids[k], tables[k]['keyColumn']), need)
            for k, (m, rows) in zip(need, maps):
                link_maps[k] = m
                fetched[k] = rows
        timings['データ投入'] = time.time() - t1

        t2 = time.time()
        pmap(lambda k: client.item(site_ids[k], 'UpdateSite', {'SiteSettings': with_secrets(resolved[k], client)}), keys)
        sums = [k for k in keys if resolved[k].get('Summaries')]
        pmap(lambda k: client.item(site_ids[k], 'SynchronizeSummaries',
                                   {'SummaryId': [s['Id'] for s in resolved[k]['Summaries']]}), sums)
        timings['通知・集計'] = time.time() - t2
        return site_ids, resolved, sorted(set(resolver.warnings)), timings
    except Exception:
        register.failed_root = root
        raise


def formula_ok(f, nums):
    # 左から順の四則演算として期待値を計算し、登録値と比べる（0除算は照合しない）
    value = None
    for node in f['Formula'].get('Children', []):
        x = node['RawValue'] if 'RawValue' in node else (nums.get(node.get('ColumnName')) or 0)
        op = node.get('OperatorType', 0)
        if value is None or op == 0:
            value = x
        elif op == 1:
            value += x
        elif op == 2:
            value -= x
        elif op == 3:
            value *= x
        elif op == 4:
            if x == 0:
                return True
            value /= x
    return value is None or abs((nums.get(f['Target']) or 0) - value) < 0.01


def verify(client, built, site_ids, resolved):
    problems = []
    rows = dict(zip(built['tables'], pmap(lambda k: client.get_all(site_ids[k]), list(built['tables']))))
    for k, t in built['tables'].items():
        n = len(rows[k])
        if n != len(t['rows']):
            problems.append(f'{t["title"]}: 件数 {n} (想定 {len(t["rows"])})')
        for col, target in t['links'].items():
            ids = {str(r['ResultId']) for r in rows[target]}
            expected = sum(1 for r in t['rows'] if r.get(col) not in (None, ''))
            got = sum(1 for r in rows[k] if r.get('ClassHash', {}).get(col) in ids)
            if got != expected:
                problems.append(f'{t["title"]}.{col}: リンク {got}件 (想定 {expected})')
        for s in resolved[k].get('Summaries', []):
            if s.get('SourceCondition'):
                continue  # ビュー条件付きの集計はここでは再現できないので値の照合をしない
            dest = next(d for d, sid in site_ids.items() if sid == s['SiteId'])
            agg = {}
            for r in rows[k]:
                link = r.get('ClassHash', {}).get(s['LinkColumn'])
                if link:
                    agg.setdefault(link, []).append(r.get('NumHash', {}).get(s.get('SourceColumn'), 0) or 0)
            for r in rows[dest]:
                vals = agg.get(str(r['ResultId']), [])
                exp = {'Count': len(vals), 'Total': sum(vals),
                       'Average': sum(vals) / len(vals) if vals else 0,
                       'Min': min(vals) if vals else 0, 'Max': max(vals) if vals else 0}.get(s['Type'])
                got = r.get('NumHash', {}).get(s['DestinationColumn'])
                # 集計先の列に DecimalPlaces があればプリザンターはその桁で丸めて保存するので、同じ桁で比べる
                dp = next((c.get('DecimalPlaces') for c in resolved[dest]['Columns']
                           if c['ColumnName'] == s['DestinationColumn']), None)
                tol = 0.5 * 10 ** -dp + 1e-9 if dp is not None else 1e-6
                if exp is not None and abs((got or 0) - exp) > tol:
                    problems.append(f'{built["tables"][dest]["title"]}.{s["DestinationColumn"]}: 集計不一致 '
                                    f'ID {r["ResultId"]} {got} (想定 {exp})')
                    break
        for f in resolved[k].get('Formulas', []):
            ng = sum(1 for r in rows[k] if not formula_ok(f, r.get('NumHash', {})))
            if ng:
                problems.append(f'{t["title"]}.{f["Target"]}: 計算式の結果が不一致 {ng}件')
        ss = client.item(site_ids[k], 'GetSite')['Response']['Data']['SiteSettings']
        for prop in ('Views', 'Notifications', 'Reminders', 'Summaries', 'Formulas', 'Links', 'ServerScripts'):
            if len(ss.get(prop) or []) != len(resolved[k].get(prop) or []):
                problems.append(f'{t["title"]}: {prop} が反映されていません')
    return problems, {k: len(v) for k, v in rows.items()}


def update_settings(client, built, spec):
    # 列・ビュー・通知・AI機能などの設定変更を、作り直さずに反映する（UpdateSite は設定を丸ごと置換）
    result_path = os.path.join(spec['_dir'], 'result.json')
    result = json.load(open(result_path, encoding='utf-8'))
    by_title = {t['title']: k for k, t in built['tables'].items()}
    site_ids = {by_title.get(k, k): v for k, v in result['sites'].items()}
    missing = [t['title'] for k, t in built['tables'].items() if k not in site_ids]
    if missing:
        log('未登録のテーブルがあります（新規テーブルの追加は作り直しが必要）:', ', '.join(missing))
        sys.exit(1)
    keys = list(built['tables'])
    resolved = {k: B.resolve_sites(built['tables'][k]['settings'], site_ids) for k in keys}
    pmap(lambda k: client.item(site_ids[k], 'UpdateSite', {'SiteSettings': with_secrets(resolved[k], client)}), keys)
    problems, counts = verify(client, built, site_ids, resolved)
    log('設定更新: ' + ', '.join(built['tables'][k]['title'] for k in keys))
    log('検証: ' + ('OK' if not problems else 'NG'))
    for p in problems:
        log('  -', p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('spec')
    ap.add_argument('--parent', type=int, default=0)
    ap.add_argument('--keep-on-fail', action='store_true')
    ap.add_argument('--update-settings', action='store_true',
                    help='登録済みアプリ（result.json）の設定だけを spec の内容で更新する。データは変更しない')
    a = ap.parse_args()
    t0 = time.time()
    spec = B.load_spec(a.spec)
    try:
        built = B.build(spec)
    except B.SpecError as e:
        log('spec エラー:', e)
        sys.exit(1)
    client = Client()
    if a.update_settings:
        update_settings(client, built, spec)
        return
    try:
        site_ids, resolved, warnings, timings = register(client, built, a.parent)
    except Exception as e:
        root = getattr(register, 'failed_root', None)
        log('登録失敗:', e)
        if root and not a.keep_on_fail:
            client.item(root, 'DeleteSite')
            log(f'途中まで作成したフォルダ {root} を削除しました')
        sys.exit(1)
    t3 = time.time()
    problems, counts = verify(client, built, site_ids, resolved)
    timings['検証'] = time.time() - t3
    result = {
        'app': built['app'],
        'url': f'{client.web_root}items/{site_ids["_root"]}/index',
        'sites': {('_root' if k == '_root' else built['tables'][k]['title']): v for k, v in site_ids.items()},
        'counts': {built['tables'][k]['title']: n for k, n in counts.items()},
        'warnings': warnings, 'problems': problems,
        'seconds': {k: round(v, 1) for k, v in timings.items()}, 'total_seconds': round(time.time() - t0, 1),
    }
    with open(os.path.join(spec['_dir'], 'result.json'), 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    for w in warnings:
        log('警告:', w)
    log('検証: ' + ('OK' if not problems else 'NG'))
    for p in problems:
        log('  -', p)
    log(json.dumps({k: result[k] for k in ('url', 'sites', 'counts', 'seconds', 'total_seconds')}, ensure_ascii=False))
    sys.exit(0 if not problems else 2)


if __name__ == '__main__':
    main()
