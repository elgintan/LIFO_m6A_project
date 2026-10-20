"""Verify 7-mer windows against an exact transcript FASTA before region mapping.

The offset must come from the documented preprocessing convention, not be
chosen to maximise agreement. FASTA indices here are 0-based. This utility
does not map exons or run GTF-based genomic conversion.
"""
import argparse
import csv
import gzip
from pathlib import Path


def main(a):
    with open(a.sites,newline='') as f: rows=list(csv.DictReader(f))
    required={'transcript_id','transcript_position','sequence_7mer'}
    if not rows or not required.issubset(rows[0]):raise ValueError('Expected transcript_id,transcript_position,sequence_7mer')
    for row in rows:
        row['reference_id']=row.get('reference_transcript_id') or row['transcript_id']
    wanted={r['reference_id'] for r in rows};sequences={};active=None;parts=[]
    opener=gzip.open if str(a.fasta).endswith('.gz') else open
    def save():
        if active in wanted:
            if active in sequences:raise ValueError('Duplicate reference ID: '+active)
            sequences[active]=''.join(parts).upper().replace('U','T')
    with opener(a.fasta,'rt') as f:
        for line in f:
            if line.startswith('>'):
                save();active=line[1:].split()[0];parts=[]
            elif active in wanted:parts.append(line.strip())
        save()
    results=[]
    for row in rows:
        pos=int(row['transcript_position']);start=pos+a.window_start_offset
        seq=sequences.get(row['reference_id']);observed=row['sequence_7mer'].upper().replace('U','T')
        expected=seq[start:start+7] if seq is not None and start>=0 else ''
        match=len(observed)==7 and observed==expected and observed[3]=='A'
        results.append({**row,'window_start_zero_based':start,'expected_7mer':expected,
            'candidate_adenosine_zero_based':start+3,'reference_present':seq is not None,'context_match':match})
    with open(a.out,'w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(results[0]));w.writeheader();w.writerows(results)
    print('Context matches:',sum(r['context_match'] for r in results),'/',len(results))
    if not all(r['context_match'] for r in results):raise SystemExit('Reference/context check failed; inspect output before biological mapping')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--sites',required=True);p.add_argument('--fasta',required=True);p.add_argument('--window-start-offset',type=int,required=True);p.add_argument('--out',required=True);main(p.parse_args())
