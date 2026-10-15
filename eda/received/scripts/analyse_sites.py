"""Descriptive site-level comparisons; no trained model or model predictions.
Run after extract_sites.py: python scripts/analyse_sites.py --out .
Plots and tables are exploratory, not inferential tests or an untouched test.
"""
import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from extract_sites import FEATURES

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);o=p.parse_args().out
    tab=o/'tables';fig=o/'figures';fig.mkdir(exist_ok=True)
    ds=[pd.read_csv(tab/f'data{i}_site_summaries.csv.gz') for i in range(3)]
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,
                         'figure.facecolor':'white','savefig.facecolor':'white'})
    colors=['#197A82','#B65F3F','#64549A']; labs=['data0','data1','data2']
    def save(f,name):
        f.savefig(fig/(name+'.png'),dpi=180,bbox_inches='tight');plt.close(f)
    for d in ds:
        d['coverage_bin']=pd.cut(d.coverage,[0,19,49,99,199,499,np.inf],
            labels=['<20','20–49','50–99','100–199','200–499','500+'])
    f,ax=plt.subplots(1,2,figsize=(11.8,4.2),layout='constrained')
    for i,d in enumerate(ds):
        v=np.sort(d.coverage);ax[0].plot(v,np.arange(1,len(v)+1)/len(v),c=colors[i],label=labs[i])
    ax[0].set(xscale='log',xlabel='Reads per site (log scale)',ylabel='Fraction of sites at or below coverage',title='Coverage differs between datasets');ax[0].legend()
    rates=[100*d.label.mean() for d in ds[:2]]
    ax[1].bar(labs[:2],rates,color=colors[:2],width=.5)
    for i,v in enumerate(rates):ax[1].text(i,v+.2,f'{v:.2f}%',ha='center')
    ax[1].set(ylabel='Sites labelled 1 (%)',ylim=(0,10),title='Binary label prevalence')
    ax[1].text(.5,-.21,'data2 has fractional labels and is excluded from this panel.',ha='center',transform=ax[1].transAxes,fontsize=9)
    save(f,'01_inventory')
    motif=pd.concat([d.groupby('motif').agg(n_sites=('label','size'),positive_sites=('label','sum')).reset_index().assign(dataset=labs[i]) for i,d in enumerate(ds[:2])])
    motif['positive_percent']=100*motif.positive_sites/motif.n_sites;motif.to_csv(tab/'motif_summary.csv',index=False)
    motifs=sorted(ds[0].motif.unique());x=np.arange(len(motifs));f,ax=plt.subplots(2,1,figsize=(12,6),sharex=True,layout='constrained')
    for i in range(2):
        m=motif[motif.dataset==labs[i]].set_index('motif').reindex(motifs)
        ax[0].bar(x+(i-.5)*.37,m.n_sites,.37,color=colors[i],label=labs[i])
        ax[1].bar(x+(i-.5)*.37,m.positive_percent,.37,color=colors[i])
    ax[0].set(ylabel='Number of sites',title='Sequence context changes both representation and label prevalence');ax[0].legend()
    ax[1].set(ylabel='Sites labelled 1 (%)',xticks=x,xticklabels=motifs,xlabel='Central 5-mer (all are DRACH motifs)')
    ax[1].tick_params(axis='x',rotation=55);save(f,'02_motifs')
    cov=pd.concat([d.groupby(['label','coverage_bin'],observed=True).size().rename('n_sites').reset_index().assign(dataset=labs[i]) for i,d in enumerate(ds[:2])])
    cov.to_csv(tab/'coverage_label_counts.csv',index=False)
    global_stats=[];effects=[];strat=[]
    for i,d in enumerate(ds[:2]):
        for label,g in d.groupby('label'):
            for col in ['coverage']+[f'{a}_{s}' for a in FEATURES for s in ['median','iqr']]:
                q=g[col].quantile([.25,.5,.75]);global_stats.append({'dataset':labs[i],'label':label,'feature':col,'n_sites':len(g),'q25':q.iloc[0],'median':q.iloc[1],'q75':q.iloc[2]})
        for motif_,g in d.groupby('motif'):
            for feature in FEATURES:
                col=feature+'_median';z=g[g.label==0][col];p_=g[g.label==1][col]
                scale=g[col].quantile(.75)-g[col].quantile(.25)
                effects.append({'dataset':labs[i],'motif':motif_,'feature':feature,'n0':len(z),'n1':len(p_),
                    'median0':z.median(),'median1':p_.median(),'median_difference':p_.median()-z.median(),
                    'pooled_iqr':scale,'difference_in_iqr_units':(p_.median()-z.median())/scale if scale else np.nan})
        for (motif_,b),g in d.groupby(['motif','coverage_bin'],observed=True):
            for feature in FEATURES:
                col=feature+'_median';z=g[g.label==0][col];p_=g[g.label==1][col]
                strat.append({'dataset':labs[i],'motif':motif_,'coverage_bin':str(b),'feature':feature,
                    'n0':len(z),'n1':len(p_),'median_difference':p_.median()-z.median()})
    pd.DataFrame(global_stats).to_csv(tab/'label_signal_summary.csv',index=False)
    ef=pd.DataFrame(effects);ef.to_csv(tab/'within_motif_effects.csv',index=False)
    pd.DataFrame(strat).to_csv(tab/'motif_coverage_effects.csv',index=False)
    f,axs=plt.subplots(1,2,figsize=(13,7.8),layout='constrained',sharey=True)
    for i,ax in enumerate(axs):
        m=ef[ef.dataset==labs[i]].pivot(index='motif',columns='feature',values='difference_in_iqr_units').reindex(index=motifs,columns=FEATURES)
        counts_=ef[ef.dataset==labs[i]].groupby('motif')[['n0','n1']].first().reindex(motifs)
        m.loc[(counts_.n0<20)|(counts_.n1<20),:]=np.nan
        cmap=plt.get_cmap('RdBu_r').copy();cmap.set_bad('#c8cdd0')
        im=ax.imshow(m,cmap=cmap,vmin=-1.5,vmax=1.5,aspect='auto')
        ax.set(yticks=np.arange(18),yticklabels=motifs,xticks=np.arange(9),
            xticklabels=[v.replace('minus1','−1').replace('plus1','+1').replace('_',' ') for v in FEATURES],title=labs[i])
        ax.tick_params(axis='x',rotation=65)
    f.colorbar(im,ax=axs,shrink=.7,label='(Label 1 median − label 0 median) / pooled site IQR')
    f.suptitle('Within-motif differences in site medians\nRed: higher in label 1; blue: lower. Grey: fewer than 20 sites in either label.\nDescriptive effects; colour capped at ±1.5. No sites removed from tables.',fontsize=12)
    save(f,'03_signal_by_motif')
    f,axs=plt.subplots(2,2,figsize=(12,6.4),layout='constrained')
    for i,d in enumerate(ds[:2]):
        for label,col in [(0,'#77868A'),(1,colors[i])]:
            v=np.sort(d[d.label==label].coverage);axs[0,i].plot(v,np.arange(1,len(v)+1)/len(v),label=f'Label {label}',color=col)
        axs[0,i].set(xscale='log',xlabel='Reads per site',ylabel='Cumulative fraction within label',title=labs[i]);axs[0,i].legend()
        m=d.groupby('coverage_bin',observed=True).agg(n=('label','size'),rate=('label','mean'))
        axs[1,i].bar(m.index.astype(str),m.rate*100,color=colors[i]);axs[1,i].set(ylabel='Sites labelled 1 (%)',xlabel='Coverage bin')
        for j,(n,v) in enumerate(zip(m.n,m.rate)):axs[1,i].text(j,v*100+.13,f'n={n:,}',ha='center',rotation=55,fontsize=8)
        axs[1,i].set_ylim(0,m.rate.max()*100+5)
    f.suptitle('Coverage can change how label groups are compared',fontsize=13);save(f,'04_coverage_labels')
    a,b,c=ds;keys=['transcript_id','transcript_position']
    paired=a.merge(b,on=keys,suffixes=('_0','_1'),validate='one_to_one')
    gene_map=a[['transcript_id','gene_id']].drop_duplicates()
    assert not gene_map.transcript_id.duplicated().any()
    b_genes=b.merge(gene_map,on='transcript_id',how='left',validate='many_to_one')
    metadata={'shared_sites':len(paired),'label_disagreements':int((paired.label_0!=paired.label_1).sum()),
        'transcripts_data1':int(b.transcript_id.nunique()),
        'shared_transcripts':len(set(a.transcript_id)&set(b.transcript_id)),
        'data1_mapped_gene_sites':int(b_genes.gene_id.notna().sum()),
        'data1_unmapped_gene_sites':int(b_genes.gene_id.isna().sum()),
        'data1_mapped_genes':int(b_genes.gene_id.nunique()),
        'data1_unmapped_transcripts':int(b_genes.loc[b_genes.gene_id.isna(),'transcript_id'].nunique()),
        'data0_only_sites':len(a)-len(paired),'data1_only_sites':len(b)-len(paired)}
    (tab/'metadata_overlap.json').write_text(json.dumps(metadata,indent=2))
    pd.crosstab(paired.label_0,paired.label_1).to_csv(tab/'paired_label_counts.csv')
    details={'shared_sites':len(paired),'same_sequence':int((paired.sequence_0==paired.sequence_1).sum()),
        'same_ordered_signal_matrix':int((paired.ordered_signal_sha256_0==paired.ordered_signal_sha256_1).sum()),
        'discordant_labels':int((paired.label_0!=paired.label_1).sum()),
        'spearman_coverage':float(paired.coverage_0.corr(paired.coverage_1,method='spearman')),
        'spearman_centre_current_medians':float(paired.centre_current_median_0.corr(paired.centre_current_median_1,method='spearman'))}
    (tab/'signal_overlap.json').write_text(json.dumps(details,indent=2))
    paired.loc[paired.label_0!=paired.label_1,keys+['gene_id','sequence_0','label_0','label_1','coverage_0','coverage_1','centre_current_median_0','centre_current_median_1']].to_csv(tab/'discordant_sites.csv',index=False)
    f,ax=plt.subplots(1,2,figsize=(11.8,4.8),layout='constrained')
    counts=pd.crosstab(paired.label_0,paired.label_1).reindex(index=[0,1],columns=[0,1]);im=ax[0].imshow(np.log10(counts+1),cmap='Blues')
    for i in range(2):
        for j in range(2):ax[0].text(j,i,f'{counts.iloc[i,j]:,}',ha='center',va='center',color='white' if counts.iloc[i,j]>10000 else '#111',fontsize=16)
    ax[0].set(xticks=[0,1],yticks=[0,1],xlabel='data1 label',ylabel='data0 label',title='Labels for 67,320 shared site IDs')
    sample=paired.sample(min(5000,len(paired)),random_state=42)
    ax[1].scatter(sample.centre_current_median_0,sample.centre_current_median_1,s=5,alpha=.12,c='#197A82',rasterized=True)
    lo=min(sample.centre_current_median_0.min(),sample.centre_current_median_1.min());hi=max(sample.centre_current_median_0.max(),sample.centre_current_median_1.max())
    ax[1].plot([lo,hi],[lo,hi],c='black',lw=.8,ls='--');ax[1].set(xlabel='data0 central current: site median',ylabel='data1 central current: site median',title='Paired sites: 5,000 shown (seed 42)')
    save(f,'05_shared_sites')
    template=c.groupby('transcript_position').agg(n_rows=('label','size'),n_sequences=('sequence','nunique'),n_labels=('label','nunique'))
    template.to_csv(tab/'data2_template_check.csv')
    dc={'n_positions':len(template),'all_positions_seven_rows':bool((template.n_rows==7).all()),
        'positions_with_same_7mer_at_all_labels':int((template.n_sequences==1).sum()),
        'unique_7mers':int(c.sequence.nunique()),
        'label_groups':c.groupby(['transcript_id','label']).size().rename('n_sites').reset_index().to_dict('records')}
    (tab/'data2_structure.json').write_text(json.dumps(dc,indent=2))
    c.groupby('label').agg(n_sites=('label','size'),coverage_median=('coverage','median'),coverage_min=('coverage','min'),coverage_max=('coverage','max')).to_csv(tab/'data2_label_summary.csv')
    f,ax=plt.subplots(1,2,figsize=(11.8,4.8),layout='constrained');delta_rows=[]
    for axis,col,title in [(ax[0],'centre_current_median','Central current'),(ax[1],'centre_dwell_median','Central dwell time')]:
        v=c.pivot(index='transcript_position',columns='label',values=col)
        diff=v.subtract(v[0.0],axis=0);levels=v.columns.to_numpy(dtype=float)
        q=diff.quantile([.25,.5,.75])
        axis.plot(levels,q.loc[.5],marker='o',c=colors[2]);axis.fill_between(levels,q.loc[.25],q.loc[.75],alpha=.2,color=colors[2])
        axis.axhline(0,color='#777',ls='--',lw=.7);axis.set(xlabel='Supplied fractional label (meaning unconfirmed)',ylabel='Difference from matching label-0 position',title=title)
        for level in levels:delta_rows.append({'feature':col,'label':level,'n_templates':len(v),'q25_delta':q.loc[.25,level],'median_delta':q.loc[.5,level],'q75_delta':q.loc[.75,level]})
    f.suptitle('data2: matched-position summaries\nLine = median; band = IQR across positions, not a confidence interval.',fontsize=12)
    save(f,'06_data2_groups');pd.DataFrame(delta_rows).to_csv(tab/'data2_matched_deltas.csv',index=False)
    unusual=[]
    for d in ds:
        for (data,motif_),g in d.groupby(['dataset','motif']):
            for col in ['centre_current_iqr','centre_dwell_iqr']:
                row=g.nlargest(1,col).iloc[0]
                unusual.append({k:row[k] for k in ['dataset','transcript_id','transcript_position','sequence','motif','label','coverage']}|{'ranking_feature':col,'value':row[col],'motif_site_median':g[col].median(),'interpretation':'High within-site spread; cause unverified. Keep unless a reproducible quality defect is established.'})
    pd.DataFrame(unusual).to_csv(tab/'unusual_sites_review.csv',index=False)
    print(json.dumps(details,indent=2));print(json.dumps(dc,indent=2));print('All six figures and descriptive tables complete.')

if __name__=='__main__':main()
