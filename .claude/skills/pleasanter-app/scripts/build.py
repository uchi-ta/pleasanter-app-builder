# spec.json（アプリ定義）からサイト設定を組み立て、整合性をチェックする
# 単体実行: python build.py <spec.json> [--package <out.json> --env <env.json>]
#   --package を付けるとサイトパッケージJSON（画面からのインポート用）も出力する
import argparse
import copy
import json
import os
import re
import sys

EXTENDED = re.compile(r'^(Class|Num|Date|Description|Check|Attachments)[A-Z]$')
FIXED = {'Title', 'Body', 'Status', 'Manager', 'Owner', 'ResultId', 'Ver', 'Comments',
         'Creator', 'Updator', 'CreatedTime', 'UpdatedTime', 'Locked'}
SITE_REF = '@site:'          # 他テーブル参照のプレースホルダ（登録時に実SiteIdへ置換）
ROW_REF_COL = '_key'          # rows 内で keyColumn を持たない表の行キー
OPS = {'+': 1, '-': 2, '*': 3, '/': 4}
AGG_TYPES = {'count': 0, 'total': 1, 'average': 2}  # Aggregation.Types は3種のみ（Aggregation.cs）
VIEW_COMMON = {'ApiColumnKeyDisplayType': 0, 'ApiColumnValueDisplayType': 0, 'CalendarSiteId': 0, 'ApiDataType': 0}


class SpecError(ValueError):
    pass


def load_spec(path):
    spec = json.load(open(path, encoding='utf-8-sig'))
    spec['_dir'] = os.path.dirname(os.path.abspath(path))
    return spec


def load_rows(spec, table):
    src = table.get('rows')
    if isinstance(src, list):
        return src
    path = os.path.join(spec['_dir'], src or f"{table['key']}.rows.json")
    if not os.path.exists(path):
        raise SpecError(f"{table['key']}: データファイルがありません: {path}")
    return json.load(open(path, encoding='utf-8-sig'))


def col_type(name):
    m = EXTENDED.match(name)
    return m.group(1) if m else name


def choices_text(choices):
    if isinstance(choices, str):
        return {'@users': '[[Users]]', '@depts': '[[Depts]]', '@groups': '[[Groups]]'}.get(choices, choices)
    lines = []
    for c in choices:
        lines.append(','.join(str(x) for x in c) if isinstance(c, (list, tuple)) else str(c))
    return '\n'.join(lines)


def parse_formula(expr):
    # "NumA - NumB * 2" のような左から順の式を Formula 構造にする
    tokens = expr.replace('(', ' ').replace(')', ' ').split()
    if not tokens or len(tokens) % 2 == 0:
        raise SpecError(f'計算式を解釈できません: {expr}')
    children, op = [], 0
    for i, t in enumerate(tokens):
        if i % 2:
            if t not in OPS:
                raise SpecError(f'計算式の演算子が不正です: {expr}')
            op = OPS[t]
            continue
        node = {'OperatorType': op}
        if re.match(r'^-?\d+(\.\d+)?$', t):
            node['RawValue'] = float(t)
        else:
            node['ColumnName'] = t
        children.append(node)
    return {'OperatorType': 0, 'Children': children}


def view_filter_value(column, value):
    t = col_type(column)
    if isinstance(value, str):
        return value
    if t in ('Class', 'Status', 'Manager', 'Owner', 'Creator', 'Updator'):
        return json.dumps([str(v) for v in value], ensure_ascii=False)
    if t == 'Check':
        return 'true' if value else 'false'
    return json.dumps(value, ensure_ascii=False)


def auto_complete(table):
    # views / aggregations を省略したテーブルに標準の内容を補う（spec を短くするため）
    status = table.get('status') or []
    open_values = [s[0] for s in status if s[0] < 900]
    choice_cols = [c['name'] for c in table.get('columns', [])
                   if isinstance(c.get('choices'), (list, str)) and c['name'] != 'Status' and 'link' not in c]
    date_cols = [c['name'] for c in table.get('columns', []) if col_type(c['name']) == 'Date']
    if 'views' not in table:
        views = [{'name': '標準', 'sort': {date_cols[0]: 'desc'} if date_cols else {'UpdatedTime': 'desc'}}]
        if open_values and len(open_values) < len(status):
            views.append({'name': '未完了', 'filter': {'Status': open_values},
                          'sort': {date_cols[-1]: 'asc'} if date_cols else {'UpdatedTime': 'desc'}})
        if status and choice_cols:
            views.append({'name': '状況×' + next(c.get('label', c['name']) for c in table['columns']
                                                  if c['name'] == choice_cols[0]),
                          'mode': 'Crosstab', 'CrosstabGroupByX': choice_cols[0], 'CrosstabGroupByY': 'Status',
                          'CrosstabAggregateType': 'Count', 'CrosstabValue': 'NumA'})
        table['views'] = views
    # extraViews は自動のビュー（または views）の後ろに追加する。集計の sourceView 用のビューなどに使う
    if table.get('extraViews'):
        names = {v['name'] for v in table['views']}
        table['views'] = table['views'] + [v for v in table.pop('extraViews') if v['name'] not in names]
    if 'aggregations' not in table and status:
        table['aggregations'] = [{'groupBy': 'Status'}]


def build_table(spec, table, tables_by_key):
    auto_complete(table)
    key = table['key']
    columns = table.get('columns', [])
    names = [c['name'] for c in columns]
    for n in names:
        if n not in FIXED and not EXTENDED.match(n):
            raise SpecError(f'{key}: 列名が不正です: {n}')
    if len(names) != len(set(names)):
        raise SpecError(f'{key}: 列名が重複しています')

    col_settings, links = [], []
    for c in columns:
        s = {'ColumnName': c['name']}
        if 'label' in c:
            s['LabelText'] = c['label']
        if c.get('required'):
            s['ValidateRequired'] = True
        if c.get('readOnly'):
            s['EditorReadOnly'] = True
        if 'format' in c:
            s['Format'] = c['format']
        if 'default' in c:
            s['DefaultInput'] = str(c['default'])
        if c.get('wide'):
            s['FieldCss'] = 'field-wide'
        if 'choices' in c:
            s['ChoicesText'] = choices_text(c['choices'])
        if 'link' in c:
            target = c['link']
            if target not in tables_by_key:
                raise SpecError(f'{key}.{c["name"]}: リンク先テーブルがありません: {target}')
            s['ChoicesText'] = f'[[{SITE_REF}{target}]]'
            s['Link'] = True
            links.append({'ColumnName': c['name'], 'SiteId': SITE_REF + target})
        # 大文字で始まるキーは Column の設定としてそのまま渡す
        s.update({k: v for k, v in c.items() if k[:1].isupper()})
        col_settings.append(s)
    if 'status' in table:
        s = next((x for x in col_settings if x['ColumnName'] == 'Status'), None)
        if s is None:
            s = {'ColumnName': 'Status'}
            col_settings.append(s)
        s['ChoicesText'] = choices_text(table['status'])
        s['DefaultInput'] = str(table.get('statusDefault', table['status'][0][0]))
        if 'Status' not in names:
            names.insert(1 if 'Title' in names else 0, 'Status')

    editor = table.get('editor') or (['ResultId', 'Ver'] + names + ['AttachmentsA', 'Comments'])
    if 'AttachmentsA' in editor and 'AttachmentsA' not in names:
        col_settings.append({'ColumnName': 'AttachmentsA', 'LabelText': '添付資料'})
    grid = table.get('grid') or (['ResultId'] + [n for n in names if col_type(n) not in ('Description', 'Body')][:12]
                                 + ['UpdatedTime'])
    filters = table.get('filters') or [
        n for n in names if n in ('Status', 'Manager', 'Owner') or col_type(n) in ('Date', 'Check')
        or any(c['name'] == n and ('choices' in c or 'link' in c) for c in columns)]

    views, view_ids = [], {}
    for i, v in enumerate(table.get('views') or [{'name': '標準'}], start=1):
        view = {'Id': i, 'Name': v['name']}
        if 'mode' in v:
            view['DefaultMode'] = v['mode']
        if 'filter' in v:
            view['ColumnFilterHash'] = {k: view_filter_value(k, x) for k, x in v['filter'].items()}
        if 'sort' in v:
            view['ColumnSorterHash'] = v['sort']
        if 'grid' in v:
            view['GridColumns'] = v['grid']
        view.update({k: x for k, x in v.items() if k[:1].isupper()})
        view.update({k: x for k, x in VIEW_COMMON.items() if k not in view})
        views.append(view)
        view_ids[v['name']] = i

    def view_id(name, where):
        if name in (None, 0, ''):
            return 0
        if name not in view_ids:
            raise SpecError(f'{key}.{where}: ビューがありません: {name}')
        return view_ids[name]

    ss = {
        'Version': 1.017,  # 省略すると読み込み時に旧バージョンからの移行処理が走る
        'GridView': 1,
        'GridColumns': grid,
        'FilterColumns': filters,
        'EditorColumnHash': {'General': editor},
        'Columns': col_settings,
        'ViewLatestId': len(views),
        'Views': views,
    }
    if 'titleColumns' in table:
        ss['TitleColumns'] = table['titleColumns']
    if 'titleSeparator' in table:
        ss['TitleSeparator'] = table['titleSeparator']
    for k, prop in (('linkColumns', 'LinkColumns'), ('historyColumns', 'HistoryColumns')):
        if k in table:
            ss[prop] = table[k]
    if 'linkColumns' not in table:
        ss['LinkColumns'] = (['ResultId'] + names)[:8]
    if links:
        ss['Links'] = links

    aggs = []
    for i, a in enumerate(table.get('aggregations', []), start=1):
        t = a.get('type', 'total' if 'target' in a else 'count').lower()
        if t not in AGG_TYPES:
            raise SpecError(f'{key}.aggregations: type は count/total/average のみです: {t}')
        aggs.append({'Id': i, 'GroupBy': a['groupBy'], 'Type': AGG_TYPES[t], 'Target': a.get('target', '')})
    if aggs:
        ss['Aggregations'] = aggs

    formulas = []
    for i, f in enumerate(table.get('formulas', []), start=1):
        formulas.append({'CalculationMethod': 'Default', 'Target': f['target'],
                         'Formula': f.get('Formula') or parse_formula(f['expr']), 'Id': i})
    if formulas:
        ss['Formulas'] = formulas

    summaries = []
    for i, s in enumerate(table.get('summaries', []), start=1):
        target = tables_by_key.get(s['to'])
        if target is None:
            raise SpecError(f'{key}.summaries: 集計先テーブルがありません: {s["to"]}')
        if not any(c['name'] == s['link'] and c.get('link') == s['to'] for c in columns):
            raise SpecError(f'{key}.summaries: {s["link"]} は {s["to"]} へのリンク列ではありません')
        item = {'SiteId': SITE_REF + s['to'], 'DestinationReferenceType': 'Results',
                'DestinationColumn': s['column'], 'LinkColumn': s['link'], 'Type': s.get('type', 'Count'),
                'Id': i}
        if item['Type'] != 'Count':
            item['SourceColumn'] = s['source']
        if s.get('sourceView'):
            item['SourceCondition'] = view_id(s['sourceView'], 'summaries')
        summaries.append(item)
    if summaries:
        ss['Summaries'] = summaries

    notifications = []
    for i, n in enumerate(table.get('notifications', []), start=1):
        item = {'Id': i, 'Type': 1, 'Prefix': n.get('prefix', f'【{spec["app"]}】'), 'Subject': n.get('subject', ''),
                'Address': n.get('to', '[Manager]'),
                'MonitorChangesColumns': n.get('monitor', ['Status']),
                'BeforeCondition': view_id(n.get('beforeView'), 'notifications'),
                'AfterCondition': view_id(n.get('afterView'), 'notifications'),
                'Expression': 1,
                'AfterCreate': n.get('afterCreate', True), 'AfterUpdate': n.get('afterUpdate', True),
                'AfterDelete': False, 'AfterCopy': False, 'AfterBulkUpdate': False,
                'AfterBulkDelete': False, 'AfterImport': False, 'Disabled': False}
        item.update({k: v for k, v in n.items() if k[:1].isupper()})
        notifications.append(item)
    if notifications:
        ss['Notifications'] = notifications

    reminders = []
    for i, r in enumerate(table.get('reminders', []), start=1):
        item = {'Id': i, 'ReminderType': 1, 'Subject': r['subject'], 'Body': r.get('body', ''),
                'Line': r.get('line', '[Title]'), 'From': '', 'To': r.get('to', '[Manager]'),
                'Column': r['column'], 'StartDateTime': r.get('start', '2026-10-19T09:00:00'),
                'Type': {'daily': 10, 'weekly': 20, 'monthly': 40}[r.get('repeat', 'weekly')],
                'Range': r.get('days', 30), 'SendCompletedInPast': False, 'NotSendIfNotApplicable': True,
                'NotSendHyperLink': False, 'ExcludeOverdue': r.get('excludeOverdue', True),
                'Condition': view_id(r.get('view'), 'reminders'), 'Disabled': False}
        item.update({k: v for k, v in r.items() if k[:1].isupper()})
        reminders.append(item)
    if reminders:
        ss['Reminders'] = reminders

    ss.update(table.get('settings', {}))
    return ss


def dependencies(table):
    return sorted({c['link'] for c in table.get('columns', []) if 'link' in c and c['link'] != table['key']})


def levels(spec):
    # リンク先が先に登録されるよう、依存関係で段階分けする（同じ段階は並列に登録できる）
    remaining = {t['key']: t for t in spec['tables']}
    done, result = set(), []
    while remaining:
        ready = [k for k, t in remaining.items() if all(d in done for d in dependencies(t))]
        if not ready:
            raise SpecError('テーブル間のリンクが循環しています: ' + ', '.join(remaining))
        result.append(ready)
        done.update(ready)
        for k in ready:
            del remaining[k]
    return result


SECRET_REF = '__API_KEY__'   # ai_script.js 内のキーのプレースホルダ（登録時に secret.txt の ClaudeApiKey で置換）
AI_TEMPLATE = os.path.join(os.path.dirname(__file__), 'ai_script.js')


def apply_ai(spec, tables_by_key):
    # spec の ai 定義から、トリガーのチェック列・出力列を追加し、Claude API を呼ぶサーバスクリプトを組み込む
    for i, a in enumerate(spec.get('ai', []), start=1):
        t = tables_by_key.get(a['table'])
        if t is None:
            raise SpecError(f'ai: テーブルがありません: {a["table"]}')
        cols = {c['name']: c for c in t['columns']}

        def ensure(name, col):
            if name not in cols:
                t['columns'].append(dict({'name': name}, **col))
                cols[name] = t['columns'][-1]
                if t.get('editor') and name not in t['editor']:
                    t['editor'].append(name)

        trig = a.get('trigger', {})
        ensure(trig['check'], {'label': trig.get('label', f'{a["title"]}を実行する'),
                               'Description': '保存時にAIを実行します（実行後は自動でオフに戻ります）'})
        outputs = []
        for o in a['outputs']:
            ensure(o['column'], {'label': o['label'], 'readOnly': o.get('readOnly', False),
                                 **({'choices': o['allowed']} if o.get('allowed') else {})})
            outputs.append({'key': o.get('key', o['column']), 'column': o['column'], 'instruction': o['instruction'],
                            'type': col_type(o['column']), 'allowed': o.get('allowed')})
        if a.get('stampColumn'):
            ensure(a['stampColumn'], {'label': 'AI実行記録', 'readOnly': True})

        def label(table, name):
            c = next((c for c in table['columns'] if c['name'] == name), None)
            return (c or {}).get('label', {'Status': '状況', 'Title': 'タイトル', 'Body': '内容'}.get(name, name))

        def choice_map(table):
            m = {}
            if table.get('status'):
                m['Status'] = {str(s[0]): s[1] for s in table['status']}
            return m

        conf = {
            'title': a['title'], 'tableTitle': t['title'], 'trigger': trig['check'],
            'model': a.get('model', 'claude-haiku-5-5'), 'effort': a.get('effort', 'low'),
            'maxTokens': a.get('maxTokens', 1500), 'timeoutMs': a.get('timeoutMs', 9000),
            'system': a.get('system', 'あなたは業務アプリのアシスタントです。日本語で簡潔に答えます。'),
            'instruction': a['instruction'],
            'inputs': [{'name': n, 'label': label(t, n)} for n in a['inputs']],
            'outputs': outputs, 'choices': choice_map(t), 'stampColumn': a.get('stampColumn'),
        }
        rel = a.get('related')
        if rel:
            rt = tables_by_key[rel['table']]
            conf['related'] = {'siteId': SITE_REF + rel['table'], 'link': rel['link'], 'title': rel.get('title', rt['title']),
                               'sameParent': rel['table'] == a['table'],
                               'limit': rel.get('limit', 10), 'sort': rel.get('sort'),
                               'columns': [{'name': n, 'label': label(rt, n)} for n in rel['columns']]}
            conf['choices'].update({f'_rel_{k}': v for k, v in choice_map(rt).items()})
        body = (open(AI_TEMPLATE, encoding='utf-8').read()
                .replace('__TITLE__', a['title'])
                .replace('__CONF__', json.dumps(conf, ensure_ascii=False)))
        scripts = t.setdefault('settings', {}).setdefault('ServerScripts', [])
        # API キーは共有スクリプトに分ける（AI のスクリプトを画面に表示してもキーが見えないように）
        if not any(x.get('Name') == 'claudeApiKey' for x in scripts):
            scripts.append({'Id': 90, 'Title': '共通設定（APIキー）※デモで表示しない', 'Name': 'claudeApiKey', 'Shared': True,
                            'Body': "// AI機能で使う Claude API のキー（共有スクリプト：他のサーバスクリプトの実行時に読み込まれる）\n"
                                    f"const CLAUDE_API_KEY = '{SECRET_REF}';"})
        scripts.append({
            'Id': i, 'Title': a['title'], 'Name': f'ai{i}', 'BeforeCreate': True, 'BeforeUpdate': True,
            'Body': body, 'TimeOut': 10000})
        a['trigger_text'] = f'「{label(t, trig["check"])}」をオンにして保存したとき'


def build(spec, with_rows=True):
    tables_by_key = {t['key']: t for t in spec['tables']}
    apply_ai(spec, tables_by_key)
    if len(tables_by_key) != len(spec['tables']):
        raise SpecError('テーブルの key が重複しています')
    built = {'app': spec['app'], 'levels': levels(spec), 'tables': {}}
    for t in spec['tables']:
        built['tables'][t['key']] = {
            'key': t['key'], 'title': t['title'], 'keyColumn': t.get('keyColumn'),
            'settings': build_table(spec, t, tables_by_key),
            'links': {c['name']: c['link'] for c in t.get('columns', []) if 'link' in c},
            'userColumns': [c['name'] for c in t.get('columns', [])
                            if c['name'] in ('Manager', 'Owner') or c.get('choices') == '@users'],
            'deptColumns': [c['name'] for c in t.get('columns', []) if c.get('choices') == '@depts'],
            'groupColumns': [c['name'] for c in t.get('columns', []) if c.get('choices') == '@groups'],
        }
    if with_rows:
        for t in spec['tables']:
            rows = load_rows(spec, t)
            check_rows(t, rows, built, spec)
            built['tables'][t['key']]['rows'] = rows
        check_links(built)
    return built


def check_rows(table, rows, built, spec):
    key = table['key']
    names = {c['name'] for c in table.get('columns', [])} | {'Status', 'Title', 'Body', ROW_REF_COL}
    for i, r in enumerate(rows):
        unknown = set(r) - names
        if unknown:
            raise SpecError(f'{key} 行{i + 1}: spec にない列があります: {sorted(unknown)}')
    kc = table.get('keyColumn')
    if kc:
        values = [r.get(kc) for r in rows]
        if any(v in (None, '') for v in values):
            raise SpecError(f'{key}: キー列 {kc} が空の行があります')
        if len(values) != len(set(values)):
            raise SpecError(f'{key}: キー列 {kc} の値が重複しています')
    if 'status' in table:
        allowed = {s[0] for s in table['status']}
        bad = {r['Status'] for r in rows if 'Status' in r and r['Status'] not in allowed}
        if bad:
            raise SpecError(f'{key}: 未定義の状況の値があります: {bad}')
    for c in table.get('columns', []):
        if isinstance(c.get('choices'), list) and not c.get('MultipleSelections'):
            allowed = {str(x[0]) if isinstance(x, (list, tuple)) else str(x) for x in c['choices']}
            bad = {r[c['name']] for r in rows if r.get(c['name']) not in (None, '') and str(r[c['name']]) not in allowed}
            if bad:
                raise SpecError(f'{key}.{c["name"]}: 選択肢にない値があります: {sorted(map(str, bad))[:5]}')


def check_links(built):
    for t in built['tables'].values():
        for col, target in t['links'].items():
            tt = built['tables'][target]
            kc = tt['keyColumn']
            if not kc:
                raise SpecError(f'{target}: {t["key"]}.{col} から参照されるので keyColumn が必要です')
            keys = {r[kc] for r in tt['rows']}
            bad = {r[col] for r in t['rows'] if r.get(col) not in (None, '') and r[col] not in keys}
            if bad:
                raise SpecError(f'{t["key"]}.{col}: {target} に存在しないキーを参照しています: {sorted(bad)[:5]}')


def resolve_sites(obj, site_ids):
    # @site:<key> を実SiteIdに置換する
    if isinstance(obj, dict):
        return {k: resolve_sites(v, site_ids) for k, v in obj.items()}
    if isinstance(obj, list):
        return [resolve_sites(v, site_ids) for v in obj]
    if isinstance(obj, str) and SITE_REF in obj:
        if obj.startswith(SITE_REF):
            return site_ids[obj[len(SITE_REF):]]
        return re.sub(re.escape(SITE_REF) + r'(\w+)', lambda m: str(site_ids[m.group(1)]), obj)
    return obj


# ------------------------------------------------------------------ 値の変換（登録・パッケージ共通）
class Resolver:
    def __init__(self, env):
        self.users, self.depts, self.groups = {}, {}, {}
        for u in env.get('users', []):
            for k in (u['UserId'], str(u['UserId']), u['LoginId'], u['Name']):
                self.users.setdefault(k, u['UserId'])
        for d in env.get('depts', []):
            for k in (d['DeptId'], str(d['DeptId']), d['DeptCode'], d['DeptName']):
                self.depts.setdefault(k, d['DeptId'])
        for g in env.get('groups', []):
            for k in (g['GroupId'], str(g['GroupId']), g['GroupName']):
                self.groups.setdefault(k, g['GroupId'])
        self.warnings = []

    def _get(self, table, value, kind):
        if value in (None, ''):
            return None
        if value in table:
            return table[value]
        self.warnings.append(f'{kind} が見つかりません: {value}')
        return None

    def user(self, v):
        return self._get(self.users, v, 'ユーザー')

    def dept(self, v):
        return self._get(self.depts, v, '部署')

    def group(self, v):
        return self._get(self.groups, v, 'グループ')


def to_record(t, row, resolver, link_maps):
    # rows のフラットな1行を API / パッケージ共通のレコード形式にする
    rec = {'ClassHash': {}, 'NumHash': {}, 'DateHash': {}, 'DescriptionHash': {}, 'CheckHash': {}}
    for col, v in row.items():
        if col == ROW_REF_COL:
            continue
        if col in t['links']:
            v = None if v in (None, '') else str(link_maps[t['links'][col]][v])
        elif col in t['userColumns']:
            v = resolver.user(v)
        elif col in t['deptColumns']:
            v = resolver.dept(v)
        elif col in t['groupColumns']:
            v = resolver.group(v)
        ct = col_type(col)
        if ct in ('Title', 'Body', 'Status', 'Manager', 'Owner'):
            if v is not None:
                rec[ct] = v
        elif ct == 'Class':
            rec['ClassHash'][col] = '' if v is None else str(v)
        elif ct == 'Num':
            if v is not None:
                rec['NumHash'][col] = v
        elif ct == 'Date':
            if v:
                rec['DateHash'][col] = v if 'T' in v else v + 'T00:00:00'
        elif ct == 'Description':
            rec['DescriptionHash'][col] = '' if v is None else str(v)
        elif ct == 'Check':
            rec['CheckHash'][col] = bool(v)
    return {k: v for k, v in rec.items() if v != {}}


# ------------------------------------------------------------------ サイトパッケージ出力
def summary_values(built, records_by_table):
    # パッケージ取り込みでは集計が再計算されないので、集計先の値を計算しておく
    for t in built['tables'].values():
        for s in t['settings'].get('Summaries', []):
            dest = s['SiteId'][len(SITE_REF):]
            groups = {}
            for rec in records_by_table[t['key']]:
                link = rec.get('ClassHash', {}).get(s['LinkColumn'])
                if link:
                    groups.setdefault(link, []).append(rec.get('NumHash', {}).get(s.get('SourceColumn'), 0) or 0)
            for rec in records_by_table[dest]:
                vals = groups.get(str(rec['ResultId']), [])
                agg = {'Count': len(vals), 'Total': sum(vals),
                       'Average': sum(vals) / len(vals) if vals else 0,
                       'Min': min(vals) if vals else 0, 'Max': max(vals) if vals else 0}[s['Type']]
                rec.setdefault('NumHash', {})[s['DestinationColumn']] = agg


def build_package(built, env):
    site_ids = {'_root': 101}
    for i, key in enumerate(built['tables'], start=102):
        site_ids[key] = i
    resolver = Resolver(env)
    users_by_id = {u['UserId']: u for u in env.get('users', [])}
    depts_by_id = {d['DeptId']: d for d in env.get('depts', [])}
    next_id = [1001]
    link_maps, records = {}, {}
    for level in built['levels']:
        for key in level:
            t = built['tables'][key]
            recs = []
            link_maps[key] = {}
            for row in t['rows']:
                rec = to_record(t, row, resolver, link_maps)
                rec['ResultId'] = next_id[0]
                next_id[0] += 1
                kv = row.get(t['keyColumn']) if t['keyColumn'] else row.get(ROW_REF_COL)
                if kv is not None:
                    link_maps[key][kv] = rec['ResultId']
                recs.append(rec)
            records[key] = recs
    summary_values(built, records)

    def user_obj(uid):
        u = users_by_id.get(uid, {'UserId': uid, 'LoginId': '', 'Name': '', 'DeptId': 0})
        d = depts_by_id.get(u.get('DeptId'))
        return {'TenantId': 1, 'Id': uid, 'DeptId': u.get('DeptId', 0),
                'Dept': {'TenantId': 1, 'Id': d['DeptId'], 'Code': d['DeptCode'], 'Name': d['DeptName'],
                         'Body': '', 'Disabled': False} if d else None,
                'LoginId': u['LoginId'], 'Name': u['Name'], 'UserCode': u.get('UserCode', ''), 'Body': '',
                'TenantManager': False, 'ServiceManager': False, 'AllowCreationAtTopSite': False,
                'AllowGroupAdministration': False, 'AllowGroupCreation': False, 'AllowApi': False,
                'AllowMovingFromTopSite': False, 'Disabled': False}

    admin = env.get('apiUserId') or (env['users'][0]['UserId'] if env.get('users') else 1)
    data, sites = [], []
    guides = {k: '' for k in ('Body', 'GridGuide', 'EditorGuide', 'CalendarGuide', 'CrosstabGuide', 'GanttGuide',
                              'BurnDownGuide', 'TimeSeriesGuide', 'AnalyGuide', 'KambanGuide', 'ImageLibGuide')}

    def site(sid, title, ref, parent, ss):
        s = {'TenantId': 1, 'SiteId': sid, 'Title': title, 'SiteName': '', 'SiteGroupName': ''}
        s.update(guides)
        s.update({'ReferenceType': ref, 'ParentId': parent, 'InheritPermission': site_ids['_root'],
                  'SiteSettings': dict({'Version': 1.017, 'ReferenceType': ref}, **ss),
                  'Publish': False, 'DisableCrossSearch': False, 'Comments': []})
        return s

    sites.append(site(site_ids['_root'], built['app'], 'Sites', 0, {}))
    for key, t in built['tables'].items():
        sid = site_ids[key]
        sites.append(site(sid, t['title'], 'Results', site_ids['_root'], resolve_sites(t['settings'], site_ids)))
        body = []
        for rec in records[key]:
            r = {'ClassHash': rec.get('ClassHash', {}), 'NumHash': rec.get('NumHash', {}),
                 'DateHash': rec.get('DateHash', {}), 'DescriptionHash': rec.get('DescriptionHash', {}),
                 'CheckHash': rec.get('CheckHash', {}), 'SiteId': sid, 'ResultId': rec['ResultId'], 'Ver': 1}
            if 'Title' in rec:
                r['Title'] = {'Id': rec['ResultId'], 'Ver': 1, 'IsHistory': False, 'Value': rec['Title'],
                              'DisplayValue': rec['Title'], 'ItemTitle': True}
            r['Body'] = rec.get('Body', '')
            if 'Status' in rec:
                r['Status'] = {'Value': rec['Status']}
            for uc in ('Manager', 'Owner'):
                if uc in rec:
                    r[uc] = user_obj(rec[uc])
            r.update({'Locked': False, 'Comments': [], 'Creator': user_obj(admin), 'Updator': user_obj(admin)})
            body.append(r)
        labels = {c['ColumnName']: c.get('LabelText', c['ColumnName']) for c in t['settings']['Columns']}
        data.append({'Header': [{'SiteId': sid, 'SiteTitle': t['title'], 'Columns': dict({'ResultId': 'ID'}, **labels)}],
                     'Body': body})

    convertors = [{'SiteId': site_ids['_root'], 'SiteTitle': built['app'], 'ReferenceType': 'Sites',
                   'IncludeData': True, 'Order': json.dumps([site_ids[k] for k in built['tables']])}]
    convertors += [{'SiteId': site_ids[k], 'SiteTitle': t['title'], 'ReferenceType': 'Results', 'IncludeData': True}
                   for k, t in built['tables'].items()]
    return {
        'HeaderInfo': {'AssemblyVersion': env.get('assemblyVersion', '1.5.5.0'), 'BaseSiteId': site_ids['_root'],
                       'Server': 'http://localhost', 'CreatorName': '', 'PackageTime': '2026-01-01T00:00:00+09:00',
                       'Convertors': convertors, 'IncludeSitePermission': False, 'IncludeRecordPermission': False,
                       'IncludeColumnPermission': True, 'IncludeNotifications': True, 'IncludeReminders': True},
        'Sites': sites,
        'Data': data,
        'Permissions': [{'SiteId': site_ids[k], 'Permissions': []} for k in ['_root'] + list(built['tables'])],
        'PermissionIdList': {
            'DeptIdList': [{'DeptId': d['DeptId'], 'DeptCode': d['DeptCode'], 'DeptName': d['DeptName']}
                           for d in env.get('depts', [])],
            'GroupIdList': [{'GroupId': g['GroupId'], 'GroupName': g['GroupName']} for g in env.get('groups', [])],
            'UserIdList': [{'UserId': u['UserId'], 'LoginId': u['LoginId'], 'UserCode': u.get('UserCode', ''),
                            'Name': u['Name']} for u in env.get('users', [])]},
    }, resolver.warnings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('spec')
    ap.add_argument('--package')
    ap.add_argument('--env')
    a = ap.parse_args()
    try:
        built = build(load_spec(a.spec))
    except SpecError as e:
        print('NG:', e)
        sys.exit(1)
    for key, t in built['tables'].items():
        print(f'OK {key}: {t["title"]} {len(t["rows"])}件')
    print('登録順:', ' → '.join('[' + ', '.join(lv) + ']' for lv in built['levels']))
    if a.package:
        env = json.load(open(a.env or os.path.join(os.path.dirname(a.spec), '..', 'env.json'), encoding='utf-8-sig'))
        pkg, warnings = build_package(built, env)
        with open(a.package, 'w', encoding='utf-8-sig') as f:
            json.dump(pkg, f, ensure_ascii=False, indent=1)
        for w in sorted(set(warnings)):
            print('警告:', w)
        print('パッケージ出力:', a.package)


if __name__ == '__main__':
    main()
