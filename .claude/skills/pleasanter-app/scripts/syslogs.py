# プリザンターの SysLogs から直近のエラーを表示する（読み取りのみ）
# 使い方: python syslogs.py [分 (既定30)] [--url 部分一致] [--stack]
# 接続情報は環境変数 Implem.Pleasanter_Rds_SQLServer_UserConnectionString から取り、
# パスワードは子プロセスの SQLCMDPASSWORD で渡す（表示・ログ出力しない）
import argparse
import os
import subprocess
import sys

SQLCMD = r'C:\Program Files\Microsoft SQL Server\Client SDK\ODBC\180\Tools\Binn\sqlcmd.exe'


def query(sql):
    cs = os.environ.get('Implem.Pleasanter_Rds_SQLServer_UserConnectionString')
    if not cs:
        sys.exit('環境変数 Implem.Pleasanter_Rds_SQLServer_UserConnectionString がありません')
    h = {}
    for part in cs.split(';'):
        if '=' in part:
            k, v = part.split('=', 1)
            h[k.strip().upper()] = v
    env = dict(os.environ, SQLCMDPASSWORD=h['PWD'])
    # ODBC 18 は既定で暗号化を要求するため、ローカル接続では -C（サーバ証明書を信頼）を付ける
    r = subprocess.run([SQLCMD, '-S', h['SERVER'], '-d', h['DATABASE'], '-U', h['UID'], '-C',
                        '-Q', sql, '-s', '|', '-f', '65001', '-y', '0'], env=env, capture_output=True)
    return r.stdout.decode('utf-8', 'replace') + r.stderr.decode('utf-8', 'replace')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('minutes', nargs='?', type=int, default=30)
    ap.add_argument('--url', default='')
    ap.add_argument('--stack', action='store_true')
    a = ap.parse_args()
    url = a.url.replace("'", "''")
    cols = "LEFT(ErrStackTrace, 2000)" if a.stack else "LEFT(ErrMessage, 300)"
    sql = ("SET NOCOUNT ON; SELECT TOP 20 CONVERT(varchar(19), CreatedTime, 120), Url, Method, " + cols +
           " FROM SysLogs WHERE ErrMessage IS NOT NULL AND ErrMessage <> ''"
           f" AND CreatedTime > DATEADD(minute, -{a.minutes}, GETDATE()) AND Url LIKE '%{url}%'"
           " ORDER BY CreatedTime DESC")
    out = query(sql).strip()
    print(out if out else f'直近{a.minutes}分のエラーはありません')


if __name__ == '__main__':
    main()
