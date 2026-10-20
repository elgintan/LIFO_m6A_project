"""Refresh official metadata + public S3 listings without downloading signal data.
Writes to a NEW snapshot directory, preserving the analysis snapshot.
python scripts/refresh_inventory.py --out metadata/new_snapshot
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
import xml.etree.ElementTree as ET


def main(dest):
    p=Path(dest);p.mkdir(parents=True,exist_ok=False);receipts=[]
    def get(url,name):
        with urlopen(url,timeout=90) as r:b=r.read()
        (p/name).write_bytes(b)
        receipts.append({'url':url,'file':name,'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'retrieved_utc':datetime.now(timezone.utc).isoformat()})
        return b
    for name in ['samples.tsv','samples_with_RNAmod_data.tsv']:
        get('https://raw.githubusercontent.com/GoekeLab/sg-nex-data/master/docs/'+name,name)
    ns={'s':'http://s3.amazonaws.com/doc/2006-03-01/'}
    for label,delimiter in [('prefixes','/'),('objects','')]:
        token=None;page=1
        while True:
            q={'list-type':'2','prefix':'data/processed_data/m6Anet/'}
            if delimiter:q['delimiter']=delimiter
            if token:q['continuation-token']=token
            name=f's3_m6anet_{label}'+('' if page==1 else f'_{page}')+'.xml'
            b=get('https://sg-nex-data.s3.ap-southeast-1.amazonaws.com/?'+urlencode(q),name)
            root=ET.fromstring(b)
            if root.findtext('s:IsTruncated',namespaces=ns)!='true':break
            token=root.findtext('s:NextContinuationToken',namespaces=ns);page+=1
    (p/'download_receipt.json').write_text(json.dumps(receipts,indent=2)+'\n')
    print('Saved snapshot:',p)


if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--out',required=True);main(a.parse_args().out)
