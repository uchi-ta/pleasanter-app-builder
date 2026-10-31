# プリザンターAPIの共通処理（接続先・APIキーは secret.txt から読む。キーは表示しない）
import json
import os
import urllib.error
import urllib.parse
import urllib.request

LOCAL_HOSTS = {'localhost', '127.0.0.1'}
# localhost 以外の接続先。プリザンターのデモ環境は最初から入れてある。自分のサーバーを使うときはホスト名を追加する
ALLOWED_REMOTE_HOSTS = {'demo.pleasanter.org'}

USER_AGENT = 'pleasanter-app-builder/1.0'

DEFAULT_SECRET = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'secret.txt')


class ApiError(RuntimeError):
    pass


class Client:
    def __init__(self, secret_path=None):
        path = os.path.abspath(secret_path or os.environ.get('PLEASANTER_SECRET') or DEFAULT_SECRET)
        conf = {}
        for line in open(path, encoding='utf-8-sig'):
            if ':' in line:
                k, v = line.strip().split(':', 1)
                conf[k.strip()] = v.strip()
        self.items_url = conf['PleasanterApiUrl'].rstrip('/') + '/'
        self.api_root = self.items_url.rsplit('items/', 1)[0]
        self.web_root = self.api_root.rsplit('api/', 1)[0]
        self._key = conf['PleasanterApiKey']
        self._conf = conf
        # 外部への送信を防ぐため、localhost と、ユーザーが許可したデモ環境以外には接続しない
        host = urllib.parse.urlparse(self.items_url).hostname or ''
        self.is_local = host in LOCAL_HOSTS
        if host not in LOCAL_HOSTS | ALLOWED_REMOTE_HOSTS:
            raise ApiError('接続先が許可されていないため中止しました: ' + host)

    def secret(self, name):
        # secret.txt の任意の値（AI の API キーなど）。呼び出し側で表示・ログ出力しないこと
        if not self._conf.get(name):
            raise ApiError(f'secret.txt に {name} がありません')
        return self._conf[name]

    def post(self, url, body=None, timeout=300):
        data = dict(body or {}, ApiVersion=1.1, ApiKey=self._key)
        req = urllib.request.Request(
            url, data=json.dumps(data, ensure_ascii=False).encode('utf-8'),
            headers={'Content-Type': 'application/json', 'User-Agent': USER_AGENT}, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=timeout) as res:
                r = json.loads(res.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            text = e.read().decode('utf-8', 'replace')
            try:
                r = json.loads(text)
            except ValueError:
                r = {'StatusCode': e.code, 'Message': text[:500]}
        if r.get('StatusCode') != 200:
            raise ApiError(f'{url.replace(self._key, "***")} 失敗: {r.get("StatusCode")} {r.get("Message")}')
        return r

    def item(self, item_id, action, body=None):
        return self.post(f'{self.items_url}{item_id}/{action}', body)

    def get_all(self, site_id, columns=None, body=None):
        # Get はページング（既定200件）されるので全件取得する
        # 列を指定しないと一覧の表示列（GridColumns）しか返らないため、必要な列は columns で渡す
        body = dict(body or {})
        if columns:
            body.setdefault('View', {})['GridColumns'] = list(columns)
        rows, offset = [], 0
        while True:
            r = self.item(site_id, 'Get', dict(body, Offset=offset))['Response']
            rows += r['Data']
            offset += len(r['Data'])
            if not r['Data'] or offset >= r['TotalCount']:
                return rows

    def users(self):
        return self._all(self.api_root + 'users/get')

    def depts(self):
        return self._all(self.api_root + 'depts/get')

    def _all(self, url):
        rows, offset = [], 0
        while True:
            r = self.post(url, {'Offset': offset})['Response']
            rows += r['Data']
            offset += len(r['Data'])
            if not r['Data'] or offset >= r['TotalCount']:
                return rows
