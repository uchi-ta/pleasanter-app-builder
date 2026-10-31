# spec.json の dashboards を、登録済みアプリ（result.json の SiteId）に対して作成・更新する
# 使い方: python dashboard.py <spec.json> [--only <ダッシュボード名>]
#   2回目以降は result.json の dashboards に記録した SiteId を UpdateSite で上書きする（作り直し不要）
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
import build as B  # noqa: E402
from plapi import Client  # noqa: E402

TEMPLATE = os.path.join(os.path.dirname(__file__), 'kpi_template.html')
TYPES = {'quickaccess': 0, 'timeline': 1, 'custom': 2, 'html': 3, 'calendar': 4, 'kamban': 5, 'index': 6, 'kpi': 3}


def view_of(part):
    view = {}
    if 'filter' in part:
        view['ColumnFilterHash'] = {k: B.view_filter_value(k, v) for k, v in part['filter'].items()}
    if 'sort' in part:
        view['ColumnSorterHash'] = part['sort']
    if 'grid' in part:
        view['GridColumns'] = part['grid']
    view.update(part.get('View', {}))
    return view


def kpi_html(part_id, part, site_ids, tables):
    used = {}
    for item in part.get('cards', []) + part.get('charts', []):
        cols = used.setdefault(item['table'], {'ResultId'})
        for k in ('column', 'weight', 'groupBy'):
            if item.get(k):
                cols.add(item[k])
        for f in [item.get('filter'), (item.get('ratioOf') or {}).get('filter')]:
            cols.update((f or {}).keys())
    conf = {
        'tables': {k: {'siteId': site_ids[k], 'columns': sorted(v)} for k, v in used.items()},
        'cards': part.get('cards', []),
        'charts': part.get('charts', []),
    }
    for k in used:
        if k not in tables:
            raise B.SpecError(f'dashboard: テーブルがありません: {k}')
    html = open(TEMPLATE, encoding='utf-8').read()
    return html.replace('__ID__', str(part_id)).replace('__CONF__', json.dumps(conf, ensure_ascii=False))


def build_parts(dash, site_ids, tables):
    # レイアウトは横20列・1単位16px。y 省略時は、x>0 なら直前のパーツと同じ行、x=0 なら次の行に置く
    parts = []
    y, row_y = 0, 0
    for i, p in enumerate(dash['parts'], start=1):
        t = p['type']
        if t not in TYPES:
            raise B.SpecError(f'dashboard: パーツの type が不正です: {t}')
        w, h = p.get('w', 20), p.get('h', 20)
        x = p.get('x', 0)
        row_y = p.get('y', row_y if x > 0 else y)
        part = {'Id': i, 'Title': p.get('title', ''), 'ShowTitle': p.get('showTitle', True), 'Type': TYPES[t],
                'X': x, 'Y': row_y, 'Width': w, 'Height': h}
        y = max(y, row_y + h)
        if p.get('css'):
            part['ExtendedCss'] = p['css']
        sites = [site_ids[k] for k in p.get('tables', [p['table']] if 'table' in p else [])]
        csv = ','.join(str(s) for s in sites)
        if sites:
            part['SiteId'] = sites[0]
        if t == 'quickaccess':
            part['QuickAccessSites'] = csv or ','.join(str(site_ids[k]) for k in tables)
            if p.get('vertical'):
                part['QuickAccessLayout'] = 1
        elif t == 'timeline':
            part.update({'TimeLineSites': csv, 'TimeLineTitle': p.get('titleTemplate', '[Title]'),
                         'TimeLineBody': p.get('bodyTemplate', '[Body]'), 'TimeLineItemCount': p.get('count', 10),
                         'View': view_of(p)})
            if 'display' in p:
                part['TimeLineDisplayType'] = {'simple': 0, 'standard': 1, 'detailed': 2}[p['display']]
        elif t == 'custom':
            part['Content'] = p['content']
        elif t == 'html':
            part['HtmlContent'] = p['html']
        elif t == 'kpi':
            # 同期読み込みだと gridstack が innerHTML で差し込み <script> が実行されない。
            # 非同期読み込みはサーバ応答を jQuery の ReplaceAll で差し込むのでスクリプトが動く（DashboardUtilities.cs:1450）
            part['HtmlContent'] = kpi_html(i, p, site_ids, tables)
        elif t == 'calendar':
            part.update({'CalendarSites': csv, 'CalendarType': 2 if p.get('full', True) else 1,
                         'CalendarFromTo': p.get('fromTo', 'DateA'), 'CalendarTimePeriod': p.get('period', 'Monthly'),
                         'CalendarShowStatus': p.get('showStatus', True), 'View': view_of(p)})
            if p.get('groupBy'):
                part['CalendarGroupBy'] = p['groupBy']
        elif t == 'kamban':
            part.update({'KambanSites': csv, 'KambanGroupByX': p.get('x_by', 'Status'),
                         'KambanGroupByY': p.get('y_by', ''), 'KambanAggregateType': p.get('aggregate', 'Count'),
                         'KambanValue': p.get('value', 'NumA'), 'KambanAggregationView': p.get('aggregationView', False),
                         'KambanShowStatus': p.get('showStatus', False), 'View': view_of(p),
                         # 未指定だとダッシュボードでは 0 列扱いになり Chunk(0) で例外になる（HtmlKamban.cs:158）
                         'KambanColumns': str(p.get('columns', 10))})
        elif t == 'index':
            part.update({'IndexSites': csv, 'View': view_of(p)})
        parts.append(part)
    return parts


def auto_dashboard(spec):
    # spec に dashboards が無いとき、中心のテーブル（状況列と数値列が多いもの）から標準のダッシュボードを作る
    tables = spec['tables']
    with_status = [t for t in tables if t.get('status')] or tables
    main_t = max(with_status, key=lambda t: sum(1 for c in t['columns'] if B.col_type(c['name']) == 'Num'))
    key = main_t['key']
    cols = {c['name']: c for c in main_t['columns']}
    status = main_t.get('status') or []
    open_v = [s[0] for s in status if s[0] < 900]
    money = next((n for n, c in cols.items() if B.col_type(n) == 'Num' and c.get('format') == 'C'), None)
    due = next((n for n, c in cols.items() if B.col_type(n) == 'Date'
                and re.search('期限|予定|納期|期日|締切|更新日|返却', c.get('label', ''))), None)
    choice = next((n for n, c in cols.items() if isinstance(c.get('choices'), list) and n != 'Status'), None)
    label = lambda n: cols[n].get('label', n)  # noqa: E731
    cards = [{'label': f'{main_t["title"]}（全件）', 'table': key, 'agg': 'count', 'format': 'num'}]
    charts = []
    if open_v:
        cards.append({'label': '未完了', 'table': key, 'agg': 'count', 'filter': {'Status': open_v}, 'format': 'num'})
        done = [s[0] for s in status if s[0] >= 900]
        if done:
            cards.append({'label': '完了率', 'table': key, 'agg': 'count', 'filter': {'Status': [done[0]]},
                          'ratioOf': {'agg': 'count'}, 'format': 'pct', 'note': f'{status[[s[0] for s in status].index(done[0])][1]} ÷ 全件'})
        charts.append({'title': '状況別の件数', 'table': key, 'groupBy': 'Status', 'agg': 'count', 'format': 'num', 'order': 'key'})
    if money:
        cards.append({'label': f'{label(money)}（未完了の合計）', 'table': key, 'agg': 'sum', 'column': money,
                      'filter': {'Status': open_v} if open_v else {}, 'format': 'man'})
        cards.append({'label': f'{label(money)}（全体の合計）', 'table': key, 'agg': 'sum', 'column': money, 'format': 'man'})
    if due and open_v:
        cards.append({'label': f'{label(due)}が14日以内', 'table': key, 'agg': 'count',
                      'filter': {'Status': open_v, due: 'next:14'}, 'format': 'num', 'note': '件'})
        cards.append({'label': f'{label(due)}を超過', 'table': key, 'agg': 'count',
                      'filter': {'Status': open_v, due: 'overdue'}, 'format': 'num', 'note': '件（要フォロー）'})
    if 'Owner' in cols:
        charts.append({'title': f'{label("Owner")}別の件数（未完了）', 'table': key, 'groupBy': 'Owner', 'agg': 'count',
                       'filter': {'Status': open_v} if open_v else {}, 'format': 'num'})
    if choice:
        charts.append({'title': f'{label(choice)}別' + (f'の{label(money)}' if money else 'の件数'), 'table': key,
                       'groupBy': choice, 'agg': 'sum' if money else 'count', 'column': money, 'format': 'man' if money else 'num'})
    parts = [{'type': 'quickaccess', 'title': 'メニュー', 'showTitle': False, 'h': 7, 'tables': [t['key'] for t in tables]},
             {'type': 'kpi', 'title': f'{main_t["title"]}の状況', 'h': 30, 'cards': cards[:8], 'charts': charts[:4]}]
    grid = [n for n in ([main_t.get('keyColumn')] + ['Title', 'Status', money, due, 'Owner']) if n and (n in cols or n == 'Status')]
    idx = {'type': 'index', 'title': f'未完了の{main_t["title"]}', 'table': key, 'w': 12, 'h': 24, 'grid': grid}
    if open_v:
        idx['filter'] = {'Status': open_v}
    if due:
        idx['sort'] = {due: 'asc'}
    parts += [idx, {'type': 'timeline', 'title': '最近の更新', 'tables': [t['key'] for t in tables], 'x': 12, 'w': 8,
                    'h': 24, 'count': 10, 'display': 'simple', 'bodyTemplate': '[Status] [Owner]'}]
    if open_v:
        parts.append({'type': 'kamban', 'title': f'{main_t["title"]}ボード', 'table': key, 'h': 26,
                      'filter': {'Status': open_v}, 'x_by': 'Status', 'y_by': 'Owner' if 'Owner' in cols else '',
                      'aggregate': 'Total' if money else 'Count', 'value': money or 'NumA', 'aggregationView': bool(money)})
    cal = next(((t, n) for t in tables for n, c in ((c['name'], c) for c in t['columns'])
                if B.col_type(n) == 'Date' and (c.get('EditorFormat') == 'Ymdhm' or re.search('日時|実施日|予約', c.get('label', '')))), None)
    if cal:
        parts.append({'type': 'calendar', 'title': f'{cal[0]["title"]}カレンダー', 'table': cal[0]['key'], 'h': 34, 'fromTo': cal[1]})
    return [{'title': f'{spec["app"]} ダッシュボード', 'description': f'{main_t["title"]}の状況・未完了・最近の更新をまとめて確認する画面',
             'parts': parts, 'auto': True}]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('spec')
    ap.add_argument('--only')
    a = ap.parse_args()
    spec = B.load_spec(a.spec)
    result_path = os.path.join(spec['_dir'], 'result.json')
    result = json.load(open(result_path, encoding='utf-8'))
    tables = {t['key']: t for t in spec['tables']}
    title_to_key = {t['title']: t['key'] for t in spec['tables']}
    site_ids = {title_to_key.get(k, k): v for k, v in result['sites'].items()}
    client = Client()
    done = result.setdefault('dashboards', {})
    # dashboards を書かなければ標準のダッシュボードを自動で作る（"dashboards": [] なら作らない）
    dashes = spec['dashboards'] if 'dashboards' in spec else auto_dashboard(spec)
    for dash in dashes:
        if a.only and dash['title'] != a.only:
            continue
        try:
            parts = build_parts(dash, site_ids, tables)
        except (B.SpecError, KeyError) as e:
            print('spec エラー:', e)
            sys.exit(1)
        if any(p['type'] == 'kpi' for p in dash['parts']):
            dash['async'] = True
        ss = {'Version': 1.017, 'DashboardParts': parts,
              'DashboardPartsAsynchronousLoading': dash.get('async', True)}
        if dash['title'] in done:
            sid = done[dash['title']]
            client.item(sid, 'UpdateSite', {'Title': dash['title'], 'SiteSettings': ss})
            print(f'更新: {dash["title"]} ({sid})')
        else:
            sid = client.item(site_ids['_root'], 'CreateSite', {
                'Title': dash['title'], 'ReferenceType': 'Dashboards', 'SiteSettings': ss})['Id']
            done[dash['title']] = sid
            print(f'作成: {dash["title"]} ({sid})')
        got = client.item(sid, 'GetSite')['Response']['Data']['SiteSettings'].get('DashboardParts') or []
        print(f'  パーツ {len(got)}/{len(parts)} 反映  {client.web_root}items/{sid}/index')
        if len(got) != len(parts):
            print('  NG: パーツが反映されていません')
    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
