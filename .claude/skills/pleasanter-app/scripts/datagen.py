# テストデータ生成の共通ヘルパー（各アプリの gen_rows.py から import する）
import json
import os
import random
from datetime import date, timedelta

TODAY = date.today()


def add_years(d, years):
    # 2/29 の年加算で例外にならないようにする
    try:
        return d.replace(year=d.year + years)
    except ValueError:
        return d.replace(year=d.year + years, day=28)


class Gen:
    def __init__(self, spec_dir, seed=1):
        self.dir = spec_dir
        self.rnd = random.Random(seed)
        env_path = os.path.join(spec_dir, '..', 'env.json')
        self.env = json.load(open(env_path, encoding='utf-8')) if os.path.exists(env_path) else {'users': [], 'depts': []}
        try:
            from faker import Faker
            self.fake = Faker('ja_JP')
            self.fake.seed_instance(seed)
        except ImportError:
            self.fake = None

    # 環境に実在するユーザー・部署から選ぶ（LoginId / 部署名で返す）
    def user(self, exclude_admin=True):
        users = [u for u in self.env['users'] if not (exclude_admin and u['UserId'] <= 2)] or self.env['users']
        return self.rnd.choice(users)['LoginId'] if users else None

    def users(self, n):
        pool = [u['LoginId'] for u in self.env['users'] if u['UserId'] > 2]
        return self.rnd.sample(pool, min(n, len(pool)))

    def dept(self):
        depts = [d for d in self.env['depts'] if d['DeptName'] not in ('会社', '取締役会')] or self.env['depts']
        return self.rnd.choice(depts)['DeptName'] if depts else None

    def date(self, start, end):
        if isinstance(start, str):
            start = date.fromisoformat(start)
        if isinstance(end, str):
            end = date.fromisoformat(end)
        if end <= start:
            return start
        return start + timedelta(days=self.rnd.randint(0, (end - start).days))

    def days_ago(self, lo, hi):
        return TODAY - timedelta(days=self.rnd.randint(lo, hi))

    def pick(self, items, weights=None):
        return self.rnd.choices(items, weights)[0] if weights else self.rnd.choice(items)

    def money(self, lo, hi, step=100):
        return self.rnd.randint(lo // step, hi // step) * step

    def write(self, key, rows):
        for r in rows:
            for k, v in list(r.items()):
                if isinstance(v, date):
                    r[k] = v.isoformat()
        path = os.path.join(self.dir, f'{key}.rows.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(rows, f, ensure_ascii=False, indent=1)
        print(f'{key}: {len(rows)}件 → {path}')
