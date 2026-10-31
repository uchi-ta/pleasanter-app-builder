# IT資産管理のテストデータ生成（資産台帳・修理履歴・ライセンス 各100件）
import os
import sys
from datetime import timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'scripts'))
from datagen import TODAY, Gen, add_years  # noqa: E402

g = Gen(os.path.dirname(os.path.abspath(__file__)), seed=20261016)
IT_STAFF = g.users(2)

# 区分: (接頭辞, 件数, 保証年数, [(メーカー, 型番, 価格, OS)])
CATALOG = {
    'ノートPC': ('NPC', 40, 4, [('Lenovo', 'ThinkPad X1 Carbon Gen 11', 248000, 'Windows 11 Pro'),
                              ('Lenovo', 'ThinkPad L14 Gen 4', 148000, 'Windows 11 Pro'),
                              ('Dell', 'Latitude 5440', 158000, 'Windows 11 Pro'),
                              ('HP', 'EliteBook 840 G10', 189000, 'Windows 11 Pro'),
                              ('Panasonic', "Let's note SV1", 232000, 'Windows 11 Pro'),
                              ('Apple', 'MacBook Pro 14インチ (M3)', 298000, 'macOS')]),
    'デスクトップPC': ('DPC', 12, 5, [('Dell', 'OptiPlex 7010 SFF', 118000, 'Windows 11 Pro'),
                                  ('HP', 'ProDesk 400 G9 SF', 98000, 'Windows 11 Pro'),
                                  ('富士通', 'ESPRIMO D7012', 112000, 'Windows 11 Pro')]),
    'モニター': ('MON', 18, 3, [('Dell', 'P2423D 23.8インチ', 34800, '-'), ('EIZO', 'FlexScan EV2485', 59800, '-'),
                             ('I-O DATA', 'LCD-DF241EDB', 19800, '-')]),
    'スマートフォン': ('MBL', 10, 2, [('Apple', 'iPhone 15 128GB', 124800, 'iOS'),
                                 ('Google', 'Pixel 8a', 72600, 'Android')]),
    'タブレット': ('TAB', 5, 2, [('Apple', 'iPad Air 11インチ', 98800, 'iPadOS'),
                            ('Microsoft', 'Surface Pro 9', 178000, 'Windows 11 Pro')]),
    '複合機／プリンター': ('PRT', 4, 5, [('Canon', 'imageRUNNER ADVANCE DX C3926F', 1180000, '-'),
                                  ('EPSON', 'LP-S3290', 89800, '-')]),
    'ネットワーク機器': ('NW', 7, 5, [('Cisco', 'Catalyst 9200L-24P', 398000, 'Cisco IOS XE'),
                                ('YAMAHA', 'RTX1300', 178000, '-'), ('Fortinet', 'FortiGate 60F', 248000, 'FortiOS')]),
    'サーバー': ('SV', 4, 5, [('Dell', 'PowerEdge R660', 1480000, 'Windows Server 2022'),
                          ('Synology', 'RackStation RS1221+ (NAS)', 198000, 'DSM 7.2')]),
}
PERSONAL = {'ノートPC', 'デスクトップPC', 'モニター', 'スマートフォン', 'タブレット'}
OFFICES = ['本社 3F', '本社 4F', '本社 5F', '大阪支店', '名古屋営業所']

assets = []
for cat, (prefix, count, years, models) in CATALOG.items():
    for i in range(1, count + 1):
        maker, model, price, os_name = g.pick(models)
        acquired = g.date('2019-04-01', TODAY - timedelta(days=20))
        end = add_years(acquired, years) - timedelta(days=1)
        acq = 'リース' if price > 500000 and cat == '複合機／プリンター' else g.pick(['購入', 'リース', 'レンタル'], [80, 15, 5])
        status = 900 if end < TODAY and g.rnd.random() < 0.35 else g.pick([200, 100, 400], [85, 10, 5])
        if cat in PERSONAL:
            place = g.pick(OFFICES + ['在宅勤務'])
        elif cat in ('ネットワーク機器', 'サーバー'):
            place = '本社 サーバールーム'
        else:
            place = g.pick(OFFICES)
        place = {100: '本社 4F', 900: '-'}.get(status, place)
        assets.append({
            'ClassA': f'{prefix}-{i:04d}', 'Title': model, 'Status': status, 'ClassB': cat, 'ClassC': maker,
            'ClassD': maker[:2].upper() + ''.join(g.pick('ABCDEFGHJKLMNPQRSTUVWXYZ0123456789') for _ in range(8)),
            'ClassH': os_name, 'Owner': g.user() if cat in PERSONAL and status in (200, 400) else None,
            'ClassE': g.dept(), 'ClassF': place, 'Manager': g.pick(IT_STAFF), 'ClassG': acq,
            'DateA': acquired, 'DateB': end, 'NumA': price, 'CheckA': status != 900 and g.rnd.random() < 0.8,
            'Body': {900: 'データ消去証明書取得のうえ廃棄。', 400: '短期貸出中（出張・研修用）。',
                     100: '情報システム部 保管庫にて保管。'}.get(status, ''),
            '_acq': acquired, '_end': end})

REPAIRS = {
    'ノートPC': [('バッテリー交換', '部品交換', 12000, 25000), ('キーボード故障', '故障修理', 15000, 32000),
               ('液晶破損', '故障修理', 30000, 68000), ('OS再セットアップ', 'ソフトウェア対応', 0, 0)],
    'デスクトップPC': [('電源ユニット故障', '故障修理', 15000, 30000), ('メモリ増設', '部品交換', 8000, 20000)],
    'モニター': [('画面がちらつく', '故障修理', 0, 18000)],
    'スマートフォン': [('画面割れ', '故障修理', 15000, 38000), ('バッテリー劣化', '部品交換', 10000, 16000)],
    'タブレット': [('画面割れ', '故障修理', 20000, 45000)],
    '複合機／プリンター': [('定期保守', '定期保守', 0, 0), ('定着ユニット交換', '部品交換', 25000, 60000)],
    'ネットワーク機器': [('ファームウェア更新', 'ソフトウェア対応', 0, 0), ('電源ユニット交換', '部品交換', 30000, 80000)],
    'サーバー': [('定期保守', '定期保守', 0, 0), ('HDD交換', '部品交換', 35000, 90000)],
}
active = [a for a in assets if a['Status'] == 200 and a['ClassB'] in PERSONAL]
open_targets = g.rnd.sample(active, 7)
candidates = [a for a in assets if a['_acq'] < TODAY - timedelta(days=60)]
weights = [5 if a['ClassB'] in ('ノートPC', 'スマートフォン', 'タブレット') else 2 for a in candidates]
repairs = []
for idx in range(100):
    if idx < len(open_targets):
        a = open_targets[idx]
        a['Status'] = 300
        status, received, done = [100, 200, 200, 200, 300, 300, 200][idx], g.days_ago(1, 20), None
    else:
        a = g.pick(candidates, weights)
        status = 900
        received = g.date(a['_acq'] + timedelta(days=30), TODAY - timedelta(days=21))
        done = received + timedelta(days=g.rnd.randint(1, 14))
    subject, kind, lo, hi = g.pick(REPAIRS[a['ClassB']])
    cost = 0 if a['ClassG'] != '購入' or (received <= a['_end'] and g.rnd.random() < 0.5) else (g.money(lo, hi) if hi else 0)
    repairs.append({
        'ClassA': a['ClassA'], 'Title': subject, 'Status': status, 'ClassB': kind,
        'ClassC': '社内（情報システム部）' if kind == 'ソフトウェア対応' else g.pick(['メーカー保守', '販売代理店']),
        'DateA': received, 'DateB': done, 'NumA': cost, 'Owner': a['Owner'] or g.user(), 'Manager': a['Manager'],
        'Body': '保証・契約範囲内のため費用なし。' if cost == 0 and kind in ('故障修理', '部品交換') else ''})
repairs.sort(key=lambda r: r['DateA'])
for a in assets:
    del a['_acq'], a['_end']

SOFTWARE = [
    ('Microsoft 365 Business Standard', 'Microsoft', 'サブスクリプション', 18720, (10, 60)),
    ('Microsoft 365 E3', 'Microsoft', 'サブスクリプション', 54000, (5, 30)),
    ('Office LTSC Standard 2021', 'Microsoft', 'ボリュームライセンス', 62000, (5, 20)),
    ('Windows 11 Pro', 'Microsoft', 'OEM', 0, (10, 40)),
    ('Adobe Acrobat Pro', 'Adobe', 'サブスクリプション', 23760, (3, 20)),
    ('Adobe Creative Cloud コンプリート', 'Adobe', 'サブスクリプション', 86880, (1, 6)),
    ('AutoCAD', 'Autodesk', 'サブスクリプション', 291500, (1, 5)),
    ('Zoom Workplace Pro', 'Zoom', 'サブスクリプション', 26640, (2, 10)),
    ('Slack プロ', 'Slack', 'サブスクリプション', 12600, (10, 50)),
    ('Box Business', 'Box', 'サブスクリプション', 22800, (5, 30)),
    ('ESET PROTECT Advanced', 'ESET', 'サブスクリプション', 5800, (10, 60)),
    ('JetBrains All Products Pack', 'JetBrains', 'サブスクリプション', 125000, (2, 12)),
    ('GitHub Enterprise', 'GitHub', 'サブスクリプション', 37800, (5, 30)),
    ('Jira Software Standard', 'Atlassian', 'サブスクリプション', 14000, (5, 30)),
    ('弥生会計 23 ネットワーク', '弥生', '永続ライセンス', 165000, (1, 5)),
]
licenses = []
for n in range(1, 101):
    name, vendor, ltype, unit, (lo, hi) = g.pick(SOFTWARE)
    owned = g.rnd.randint(lo, hi)
    used = max(0, owned - g.rnd.randint(-2, max(1, owned // 4)))
    start = g.date('2023-04-01', TODAY - timedelta(days=30))
    end = {'サブスクリプション': add_years(start, 1) - timedelta(days=1),
           'ボリュームライセンス': add_years(start, 3) - timedelta(days=1)}.get(ltype)
    if end and end < TODAY and g.rnd.random() < 0.7:
        start, end = add_years(start, 1), add_years(end, 1)
    status = 100 if not end else (g.pick([900, 900, 910]) if end < TODAY else
                                  g.pick([100, 200]) if end <= TODAY + timedelta(days=45) else 100)
    licenses.append({
        'Title': name, 'Status': status, 'ClassA': ltype, 'ClassB': vendor, 'ClassC': f'LC-{start.year}-{n:04d}',
        'ClassD': g.dept(), 'NumA': owned, 'NumB': used, 'NumD': unit * owned if ltype == 'サブスクリプション' else 0,
        'DateA': start, 'DateB': end, 'Manager': g.pick(IT_STAFF),
        'Body': '使用数が保有数を超過しています。追加購入を検討してください。' if used > owned else ''})

g.write('assets', assets)
g.write('repairs', repairs)
g.write('licenses', licenses)
