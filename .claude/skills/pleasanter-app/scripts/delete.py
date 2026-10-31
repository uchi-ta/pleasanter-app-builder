# サイト（フォルダなら配下ごと）を削除する。--yes なしでは対象を表示するだけ
# 使い方: python delete.py <サイトID または items/<id>/index のURL> [--yes]
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from plapi import ApiError, Client  # noqa: E402


def main():
    if len(sys.argv) < 2:
        print('使い方: python delete.py <サイトID|URL> [--yes]')
        sys.exit(1)
    m = re.search(r'(\d+)(?:/index)?/?$', sys.argv[1].split('?')[0])
    site_id = int(m.group(1))
    c = Client()
    try:
        d = c.item(site_id, 'GetSite')['Response']['Data']
    except ApiError as e:
        print('対象が見つかりません:', e)
        sys.exit(1)
    print(f'対象: {d["Title"]} (SiteId {d["SiteId"]}, {d["ReferenceType"]}, 親 {d["ParentId"]}, 更新 {d["UpdatedTime"]})')
    if d['ReferenceType'] == 'Sites':
        print('  フォルダのため配下のサイト・レコードもまとめて削除されます')
    if '--yes' not in sys.argv:
        print('確認のみ（削除するには --yes を付けて再実行）')
        return
    print(c.item(site_id, 'DeleteSite').get('Message'))


if __name__ == '__main__':
    main()
