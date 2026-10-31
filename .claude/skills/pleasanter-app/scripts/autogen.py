# spec.json の各テーブルの "data"（生成ルール）からテストデータ <key>.rows.json を作る
# 使い方: python autogen.py <spec.json>
# ルールの書き方は reference/spec-format.md の「データ生成ルール」を参照
import json
import os
import random
import re
import sys
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))
from datagen import Gen  # noqa: E402

TODAY = date.today()
RANGE = re.compile(r'^(-?\d+(?:\.\d+)?)\.\.(-?\d+(?:\.\d+)?)(?:/(\d+(?:\.\d+)?))?$')


class RuleError(ValueError):
    pass


def parse_range(text, where):
    m = RANGE.match(text.strip())
    if not m:
        raise RuleError(f'{where}: 範囲は "最小..最大" で書きます: {text}')
    lo, hi, step = m.group(1), m.group(2), m.group(3)
    return float(lo), float(hi), float(step) if step else None


def weighted(items, rnd):
    # "a=3,b=1" / ["a","b"] / {"a":3} を重み付きで選ぶ
    if isinstance(items, dict):
        keys, w = list(items), list(items.values())
    else:
        parts = [p.strip() for p in items.split(',')] if isinstance(items, str) else list(items)
        keys, w = [], []
        for p in parts:
            if isinstance(p, str) and '=' in p and re.match(r'^.*=\d+(\.\d+)?$', p):
                k, v = p.rsplit('=', 1)
                keys.append(k)
                w.append(float(v))
            else:
                keys.append(p)
                w.append(1)
    return rnd.choices(keys, w)[0]


def typed(v):
    if isinstance(v, str) and re.match(r'^-?\d+$', v):
        return int(v)
    return v


class Table:
    def __init__(self, spec_table, g, rows_by_key, users):
        self.t = spec_table
        self.g = g
        self.rnd = g.rnd
        self.rows_by_key = rows_by_key
        self.users = users
        self.closed = {s[0] for s in spec_table.get('status', []) if s[0] >= 900}

    def date(self, rule, row, where):
        # "date:-365..0"（今日からの日数）/ "date:@DateA+7..60"（他の列から）/ "date:@tickets.DateA+0..5"（親の列から）
        base = TODAY
        # 末尾の "|max=-15" / "|min=-30" は今日からの日数で上限・下限を付ける（親の日付基準でも未来日にしない）
        limits = dict(re.findall(r'\|(max|min)=(-?\d+)', rule))
        rule = re.sub(r'\|(max|min)=-?\d+', '', rule)
        d = self._date(rule, row, where, base)
        if d is None:
            return None
        if 'max' in limits:
            d = min(d, TODAY + timedelta(days=int(limits['max'])))
        if 'min' in limits:
            d = max(d, TODAY + timedelta(days=int(limits['min'])))
        return d

    def _date(self, rule, row, where, base):
        m = re.match(r'^@([\w.]+)([+-].*)$', rule)
        if m:
            name = m.group(1)
            if '.' in name:  # "@tickets.DateA" = リンクで選んだ親の列
                t, _, c = name.partition('.')
                ref = (row.get('_parents', {}).get(t) or {}).get(c)
            else:
                ref = row.get(name)
            if not ref:
                return None
            base = date.fromisoformat(str(ref)[:10])
            rule = m.group(2).lstrip('+')
            if rule.startswith('-') and '..' not in rule:
                rule = rule + '..' + rule
        lo, hi, _ = parse_range(rule, where)
        return base + timedelta(days=self.rnd.randint(int(lo), int(hi)))

    def value(self, rule, row, i, where):
        if isinstance(rule, list):
            # 条件付き: [{"when": {"Status": [900]}, "gen": "..."}, {"gen": "..."}]
            for r in rule:
                cond = r.get('when', {})
                if all(str(row.get(k)) in [str(x) for x in (v if isinstance(v, list) else [v])]
                       for k, v in cond.items()):
                    return self.value(r['gen'], row, i, where)
            return None
        if not isinstance(rule, str):
            return rule
        m = re.match(r'^(.*)\?(0?\.\d+)$', rule)          # 末尾 "?0.3" = 30% の確率で空
        if m:
            if self.rnd.random() < float(m.group(2)):
                return None
            rule = m.group(1)
        kind, _, arg = rule.partition(':')
        if kind == 'const':
            return typed(arg)
        if kind == 'seq':
            return arg.format(i)
        if kind == 'pick':
            return typed(weighted(arg, self.rnd))
        if kind == 'int':
            lo, hi, step = parse_range(arg, where)
            step = int(step or 1)
            return self.rnd.randint(int(lo) // step, int(hi) // step) * step
        if kind == 'num':
            lo, hi, step = parse_range(arg, where)
            v = self.rnd.uniform(lo, hi)
            return round(round(v / step) * step, 4) if step else round(v, 2)
        if kind == 'date':
            d = self.date(arg, row, where)
            return d.isoformat() if d else None
        if kind == 'datetime':
            d = self.date(arg, row, where)
            return f'{d.isoformat()}T{self.rnd.choice([9, 10, 11, 13, 14, 15, 16, 17]):02d}:{self.rnd.choice(["00", "30"])}:00' if d else None
        if kind == 'bool':
            return self.rnd.random() < float(arg or 0.5)
        if kind == 'user':
            pool = [u.strip() for u in arg.split(',')] if arg else self.users
            return self.rnd.choice(pool) if pool else None
        if kind == 'dept':
            return self.g.dept()
        if kind == 'faker':
            if not self.g.fake:
                raise RuleError('Faker が使えません（pip install faker、python -P で実行）')
            return str(getattr(self.g.fake, arg)())
        if kind == 'link':
            # "link:customers" / "link:customers|Status=300,200"（親の状況で絞る）
            target, _, flt = arg.partition('|')
            parents = self.rows_by_key[target]
            if flt:
                col, _, vals = flt.partition('=')
                ok = {v.strip() for v in vals.split(',')}
                parents = [p for p in parents if str(p.get(col)) in ok] or parents
            p = self.rnd.choice(parents)
            row.setdefault('_parents', {})[target] = p
            return p['_keyvalue']
        if kind == 'parent':
            # "parent:customers.Owner"（リンクで選んだ親の値を引き継ぐ）
            target, _, col = arg.partition('.')
            p = row.get('_parents', {}).get(target)
            return p.get(col) if p else None
        if kind == 'tmpl':
            # "tmpl:{pick:経費精算,勤怠}の導入（{ClassD}）" … {ルール} と {列名} を埋め込む
            def rep(mm):
                inner = mm.group(1)
                if inner in row:
                    return str(row[inner] if row[inner] is not None else '')
                v = self.value(inner, row, i, where)
                return '' if v is None else str(v)
            return re.sub(r'\{([^{}]+)\}', rep, arg)
        raise RuleError(f'{where}: 不明なルールです: {rule}')

    def generate(self):
        data = self.t['data']
        n = data.get('count', 100)
        cols = data.get('cols', {})
        key_col = self.t.get('keyColumn')
        rows = []
        for i in range(1, n + 1):
            row = {}
            for col, rule in cols.items():
                v = self.value(rule, row, i, f'{self.t["key"]}.{col}')
                row[col] = v
            rows.append(row)
        sort = data.get('sortBy')
        if sort:
            rows.sort(key=lambda r: str(r.get(sort) or ''))
            for i, r in enumerate(rows, start=1):
                for col, rule in cols.items():
                    if isinstance(rule, str) and rule.startswith('seq:'):
                        r[col] = rule[4:].format(i)
        for r in rows:
            r['_keyvalue'] = r.get(key_col) if key_col else None
        return rows


def order(spec):
    # link ルールの依存順にテーブルを並べる
    deps = {}
    for t in spec['tables']:
        deps[t['key']] = set()
        for rule in (t.get('data', {}).get('cols', {}) or {}).values():
            for r in (rule if isinstance(rule, list) else [rule]):
                g = r.get('gen', '') if isinstance(r, dict) else r
                if isinstance(g, str) and g.startswith('link:'):
                    deps[t['key']].add(g[5:].split('|')[0])
    done, out = set(), []
    while len(out) < len(deps):
        ready = [k for k in deps if k not in done and deps[k] <= done]
        if not ready:
            raise RuleError('link ルールが循環しています')
        out += ready
        done.update(ready)
    return out


def main():
    spec_path = sys.argv[1]
    spec = json.load(open(spec_path, encoding='utf-8-sig'))
    spec_dir = os.path.dirname(os.path.abspath(spec_path))
    g = Gen(spec_dir, seed=spec.get('seed', 20261016))
    users = [u['LoginId'] for u in g.env.get('users', []) if u['UserId'] > 2]
    tables = {t['key']: t for t in spec['tables']}
    rows_by_key = {}
    targets = [k for k in order(spec) if tables[k].get('data')]
    if not targets:
        print('data（生成ルール）のあるテーブルがありません')
        return
    try:
        for k in order(spec):
            if not tables[k].get('data'):
                continue
            rows_by_key[k] = Table(tables[k], g, rows_by_key, users).generate()
    except RuleError as e:
        print('ルールエラー:', e)
        sys.exit(1)
    for k, rows in rows_by_key.items():
        clean = [{c: v for c, v in r.items() if not c.startswith('_') and v is not None} for r in rows]
        g.write(k, clean)


if __name__ == '__main__':
    main()
