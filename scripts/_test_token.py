# -*- coding: utf-8 -*-
import urllib.request, json, sys

appid = 'wx1b940e41e6a54afd'
secret = '899faede77c0b025c9b1f5e5f59f4ae9'
url = f'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={appid}&secret={secret}'

try:
    with urllib.request.urlopen(url, timeout=10) as r:
        data = json.loads(r.read())
    if 'access_token' in data:
        token = data['access_token']
        expires = data.get('expires_in', 0)
        print(f'OK: access_token={token[:20]}... expires={expires}s')
        # Save to .env
        with open(r'D:\coser_helper\.env', 'r', encoding='utf-8') as f:
            lines = f.readlines()
        with open(r'D:\coser_helper\.env', 'w', encoding='utf-8') as f:
            for line in lines:
                if line.startswith('WECHAT_ACCESS_TOKEN='):
                    f.write(f'WECHAT_ACCESS_TOKEN={token}\n')
                else:
                    f.write(line)
        print('Token saved to .env')
    else:
        print('FAIL:', data)
        sys.exit(1)
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
