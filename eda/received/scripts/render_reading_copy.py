"""Create a self-contained illustrated HTML copy of the Member 1 context.
Uses only the Python standard library. No remote assets or scripts.
"""
import argparse, base64, html, re
from pathlib import Path

def slug(s):return re.sub(r'[^a-z0-9]+','-',s.lower()).strip('-')

def inline(s):
    s=html.escape(s)
    s=re.sub(r'`([^`]+)`',r'<code>\1</code>',s)
    s=re.sub(r'\*\*([^*]+)\*\*',r'<strong>\1</strong>',s)
    s=re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)',r'<em>\1</em>',s)
    s=re.sub(r'https?://[^\s<;]+',lambda m:f'<a href="{m[0]}">{m[0]}</a>',s)
    return s

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);root=p.parse_args().root
    text=(root/'MEMBER1_CONTEXT_2026-10-13.md').read_text()
    figures={
        '### Sources inspected':('01_inventory','Figure 1. Dataset coverage and binary-label prevalence. Each site has equal weight.'),
        '### B. Pooling':('02_motifs','Figure 2. Sequence representation and positive-label rates. Counts reveal the support behind each comparison.'),
        '### C. Coverage':('03_signal_by_motif','Figure 3. Sequence-conditioned signal differences. Grey denotes fewer than 20 sites in either label; no sites are excluded from the tables.'),
        '### D. data0':('04_coverage_labels','Figure 4. Coverage and labels have different relationships in data0 and data1.'),
        '### E. data2':('05_shared_sites','Figure 5. Observed label concordance and central-current correspondence at shared sites. Neither panel shows model performance.'),
        '### F. Unusual':('06_data2_groups','Figure 6. Differences across matched data2 positions. Shading is an IQR across positions; label semantics remain unconfirmed.')}
    lines=text.splitlines();out=[];i=0;nav=[]
    while i<len(lines):
        line=lines[i]
        for before,(name,caption) in figures.items():
            if line.startswith(before):
                data=base64.b64encode((root/'figures'/(name+'.png')).read_bytes()).decode()
                out.append(f'<figure><img src="data:image/png;base64,{data}" alt="{html.escape(caption)}"><figcaption>{html.escape(caption)}</figcaption></figure>')
        if not line.strip():i+=1;continue
        if line.startswith('```'):
            i+=1;buf=[]
            while i<len(lines) and not lines[i].startswith('```'):buf.append(lines[i]);i+=1
            out.append('<pre><code>'+html.escape('\n'.join(buf))+'</code></pre>');i+=1;continue
        h=re.match(r'^(#{1,6}) (.+)',line)
        if h:
            n=len(h[1]);title=h[2];id_=slug(title)
            out.append(f'<h{n} id="{id_}">{inline(title)}</h{n}>')
            if n==2:nav.append(f'<a href="#{id_}">{html.escape(title)}</a>')
            i+=1;continue
        if line.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].startswith('|'):
                cells=[c.strip() for c in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-+:?',c.replace(' ','')) for c in cells):rows.append(cells)
                i+=1
            tab='<div class="table-scroll"><table><thead><tr>'+''.join('<th>'+inline(c)+'</th>' for c in rows[0])+'</tr></thead><tbody>'
            tab+=''.join('<tr>'+''.join('<td>'+inline(c)+'</td>' for c in row)+'</tr>' for row in rows[1:])
            out.append(tab+'</tbody></table></div>');continue
        if line.startswith('- ') or re.match(r'^\d+\. ',line):
            ordered=bool(re.match(r'^\d+\. ',line));tag='ol' if ordered else 'ul';items=[]
            pattern=r'^\d+\. ' if ordered else r'^- '
            while i<len(lines) and re.match(pattern,lines[i]):
                items.append('<li>'+inline(re.sub(pattern,'',lines[i]))+'</li>');i+=1
            out.append(f'<{tag}>'+''.join(items)+f'</{tag}>');continue
        buf=[line];i+=1
        while i<len(lines) and lines[i].strip() and not lines[i].startswith(('#','|','- ','```')) and not re.match(r'^\d+\. ',lines[i]):buf.append(lines[i]);i+=1
        out.append('<p>'+inline(' '.join(buf))+'</p>')
    style='''
    :root{--ink:#193039;--muted:#597078;--accent:#197a82;--line:#dbe6e7;--paper:#fff}
    *{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#f2f6f6;color:var(--ink);font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif}
    header{background:#163b43;color:white;padding:25px max(25px,calc((100vw - 1100px)/2));border-bottom:6px solid #72b8b6}header b{font-size:14px;letter-spacing:.1em}header p{margin:4px 0 0;color:#dceeed}
    main{max-width:1160px;margin:26px auto 60px;background:white;padding:42px 50px;box-shadow:0 4px 24px #173a4410;border-radius:8px}h1{font-size:32px;line-height:1.2;margin:0 0 16px}h2{font-size:25px;line-height:1.3;margin:48px 0 20px;padding-top:24px;border-top:1px solid var(--line);scroll-margin-top:15px}h3{font-size:20px;line-height:1.4;margin:30px 0 14px;color:var(--accent)}p{margin:15px 0}a{color:#14717a;overflow-wrap:anywhere}strong{font-weight:650}li{margin:8px 0}code{font:13px/1.4 ui-monospace,SFMono-Regular,Consolas,monospace;background:#eef3f3;padding:2px 4px;border-radius:3px;overflow-wrap:anywhere}pre{background:#eef3f3;padding:18px;overflow:auto;border-radius:5px}pre code{padding:0;white-space:pre}nav{display:flex;flex-wrap:wrap;gap:7px 18px;padding:20px;background:#edf6f5;border-radius:5px;margin:26px 0}nav a{font-size:13px;text-decoration:none}.table-scroll{overflow-x:auto;margin:23px 0;border:1px solid var(--line);border-radius:5px}table{width:100%;border-collapse:collapse;font-size:14px;line-height:1.5}th{text-align:left;background:#e6f2f1;color:#1b5057;padding:13px 14px;vertical-align:top}td{padding:12px 14px;border-top:1px solid var(--line);vertical-align:top}tr:nth-child(even) td{background:#f8fafa}figure{margin:32px 0 40px;border:1px solid var(--line);padding:14px;border-radius:6px}figure img{width:100%;height:auto;display:block}figcaption{font-size:13px;line-height:1.5;color:var(--muted);padding:12px 6px 0}footer{font-size:13px;color:var(--muted);margin-top:45px;padding-top:20px;border-top:1px solid var(--line)}
    @media(max-width:720px){main{padding:25px 18px;margin:0;border-radius:0}h1{font-size:27px}h2{font-size:22px}table{min-width:650px;font-size:13px}header{padding:20px}figure{padding:5px}nav{display:block}nav a{display:block;margin:7px 0}}
    @media print{body{background:#fff;font-size:10pt}header,nav{display:none}main{box-shadow:none;padding:0;margin:0}h1{font-size:23pt}h2{font-size:17pt}h3{font-size:13pt}table{font-size:8pt}figure,table{break-inside:avoid}a{color:inherit}.table-scroll{overflow:visible}}
    '''
    body='\n'.join(out);first=body.find('</h1>')+5
    body=body[:first]+'<nav aria-label="Contents">'+''.join(nav)+'</nav>'+body[first:]
    result='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Member 1 · Data exploration and biological context</title><style>'+style+'</style></head><body><header><b>DSA4262 · MEMBER 1</b><p>Verified data findings · Biological interpretation · Proposed validation design</p></header><main>'+body+'<footer>Prepared from the supplied datasets on 13 October 2026. This reading copy embeds all six figures and needs no internet connection.</footer></main></body></html>'
    (root/'Member1_Data_Exploration.html').write_text(result)
    print('Created self-contained HTML with',result.count('<figure>'),'figures.')

if __name__=='__main__':main()
