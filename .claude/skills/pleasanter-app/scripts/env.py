# 接続先プリザンターのユーザー・部署・グループを取得して env.json に保存する
# テストデータの利用者・部署はここにある値（LoginId / 名前 / 部署名）から選ぶ
# 使い方: python env.py [出力先 (既定: <プロジェクト>/output/env.json)]
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from plapi import Client  # noqa: E402

PROJECT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))


def fetch(client):
    users = [{'UserId': u['UserId'], 'LoginId': u['LoginId'], 'Name': u['Name'], 'UserCode': u.get('UserCode') or '',
              'DeptId': u.get('DeptId') or 0}
             for u in client.users() if not u.get('Disabled') and not u.get('Lockout')]
    depts = [{'DeptId': d['DeptId'], 'DeptCode': d.get('DeptCode') or '', 'DeptName': d['DeptName']}
             for d in client.depts() if not d.get('Disabled')]
    try:
        groups = [{'GroupId': g['GroupId'], 'GroupName': g['GroupName']}
                  for g in client._all(client.api_root + 'groups/get') if not g.get('Disabled')]
    except Exception:
        groups = []
    names = {d['DeptId']: d['DeptName'] for d in depts}
    for u in users:
        u['DeptName'] = names.get(u['DeptId'], '')
    return {'users': users, 'depts': depts, 'groups': groups}


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(PROJECT, 'output', 'env.json')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    env = fetch(Client())
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(env, f, ensure_ascii=False, indent=1)
    print(f'ユーザー {len(env["users"])} / 部署 {len(env["depts"])} / グループ {len(env["groups"])} → {out}')


if __name__ == '__main__':
    main()
