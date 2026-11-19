# usage: dg.sh <publicDataPk> <outprefix>   downloads first file of a data.go.kr file dataset
pk=$1; out=$2
for i in 1 2 3 4; do curl -sSL --max-time 30 "https://www.data.go.kr/data/$pk/fileData.do" -o p_$pk.html && [ -s p_$pk.html ] && break; sleep $((i*2)); done
U=$(grep -o "fn_fileDataDown('$pk', '[^']*'" p_$pk.html | head -1 | cut -d"'" -f4)
for i in 1 2 3 4; do curl -sS --max-time 30 -X POST "https://www.data.go.kr/tcs/dss/selectFileDataDownload.do" -H "X-Requested-With: XMLHttpRequest" --data "publicDataDetailPk=$U&publicDataPk=$pk&atchFileId=&fileDetailSn=1&publicDataTyCode=PR0051" -o m_$pk.json && [ -s m_$pk.json ] && break; sleep $((i*2)); done
F=$(python3 -I -c "import json;d=json.load(open('m_$pk.json'));print(d.get('atchFileId') or '')")
if [ -z "$F" ]; then echo "$pk no file: $(python3 -I -c "import json;d=json.load(open('m_$pk.json'));i=d.get('dataSetFileDetailInfo',{});print(i.get('atchFileUrl') or i.get('linkUrl') or i.get('dwldUrl') or '', d.get('error'))")"; exit 0; fi
for i in 1 2 3 4; do curl -sSL --max-time 90 -o $out -D $out.h "https://www.data.go.kr/cmm/cmm/fileDownload.do?atchFileId=$F&fileDetailSn=1" && [ -s $out ] && break; sleep $((i*2)); done
echo "$pk -> $(grep -i disposition $out.h | sed 's/.*filename=//')  $(file -b $out | cut -c1-40)"
