import urllib.request
import urllib.parse
import json
import re
import os

os.makedirs('data/q33-subfertility', exist_ok=True)

def download_data(pk, out_path):
    url = f'https://www.data.go.kr/data/{pk}/fileData.do'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        html = urllib.request.urlopen(req, timeout=30).read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f'{pk}: request failed: {e}')
        return
    
    m = re.search(r"fn_fileDataDown\('" + str(pk) + r"',\s*'([^']+)'", html)
    if not m:
        print(f'{pk}: no detail pk')
        return
    detail_pk = m.group(1)
    print(f'{pk}: detail_pk = {detail_pk}')
    
    post_url = 'https://www.data.go.kr/tcs/dss/selectFileDataDownload.do'
    post_data = urllib.parse.urlencode({
        'publicDataDetailPk': detail_pk,
        'publicDataPk': str(pk),
        'atchFileId': '',
        'fileDetailSn': '1',
        'publicDataTyCode': 'PR0051'
    }).encode('utf-8')
    post_req = urllib.request.Request(post_url, data=post_data, headers={
        'User-Agent': 'Mozilla/5.0',
        'X-Requested-With': 'XMLHttpRequest'
    })
    meta = json.loads(urllib.request.urlopen(post_req, timeout=30).read().decode('utf-8'))
    print(f'{pk} meta: {meta}')
    atchFileId = meta.get('atchFileId')
    if not atchFileId:
        print(f'{pk}: no atchFileId')
        return
    down_url = f'https://www.data.go.kr/cmm/cmm/fileDownload.do?atchFileId={atchFileId}&fileDetailSn=1'
    down_req = urllib.request.Request(down_url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(down_req, timeout=60) as resp, open(out_path, 'wb') as f:
        f.write(resp.read())
        print(f'{pk} -> {out_path} ({os.path.getsize(out_path)} bytes)')

if __name__ == '__main__':
    download_data(15143044, 'data/q33-subfertility/15143044.xlsx')
    for pk in [15127567, 15125614, 15127541]:
        download_data(pk, f'data/q33-subfertility/{pk}.csv')
