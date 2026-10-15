"""Fresh, site-supervised neural predictors. No individual read labels are used."""
import numpy as np
import torch
from torch import nn

def read_transform(x):
    x = np.array(x, dtype=np.float32, copy=True)
    for j in (0, 3, 6):
        x[..., j] = np.sign(x[..., j]) * np.log1p(np.abs(x[..., j]) * 1000)
    for j in (1, 4, 7):
        x[..., j] = np.sign(x[..., j]) * np.log1p(np.abs(x[..., j]))
    return x

def summary_transform(x):
    scale = np.tile([1000., 1., 1.], 21).astype(np.float32)
    return (np.sign(x) * np.log1p(np.abs(x) * scale)).astype(np.float32)

class SiteModel(nn.Module):
    def __init__(self, config, norm):
        super().__init__()
        self.config = config
        for name in ('read_mean','read_sd','summary_mean','summary_sd'):
            self.register_buffer(name, torch.tensor(norm[name], dtype=torch.float32))
        w, drop = config['width'], config['dropout']
        self.embedding = nn.Embedding(5, 4)
        self.encoder = nn.Sequential(nn.Linear(37,w), nn.SiLU(), nn.Linear(w,w),nn.SiLU())
        self.att_v = nn.Linear(w,w)
        self.att_u = nn.Linear(w,w)
        self.att_w = nn.Linear(w,1)
        self.read_logit = nn.Linear(w,1)
        summary_n = config.get('summary_n',63)
        mode = config['pool']
        pooled = 0 if mode == 'summary' else (3*w if mode in ('deepsets','attention') else 1)
        self.head = nn.Sequential(nn.Linear(28+summary_n+pooled,w),nn.SiLU(),
                                  nn.Dropout(drop),nn.Linear(w,w//2),nn.SiLU(),
                                  nn.Dropout(drop),nn.Linear(w//2,1))

    def forward(self, reads, mask, sequence, summaries):
        context = self.embedding(sequence).flatten(1)
        summary = ((summaries-self.summary_mean)/self.summary_sd)[:,:self.config.get('summary_n',63)]
        pieces = [context,summary]
        mode = self.config['pool']
        if mode != 'summary':
            x = (reads-self.read_mean)/self.read_sd
            h = self.encoder(torch.cat([x,context[:,None,:].expand(-1,x.shape[1],-1)],dim=-1))
            m = mask[...,None]
            n = m.sum(1).clamp_min(1)
            mean = (h*m).sum(1)/n
            var = (((h-mean[:,None,:])**2)*m).sum(1)/n
            if mode == 'attention':
                logits = self.att_w(torch.tanh(self.att_v(h))*torch.sigmoid(self.att_u(h))).squeeze(-1)
                weights = torch.softmax(logits.masked_fill(~mask,-torch.inf),dim=1)
                pooled = (weights[...,None]*h).sum(1)
                pieces += [pooled,mean,torch.sqrt(var+1e-6)]
            elif mode == 'deepsets':
                maximum = h.masked_fill(~m,-torch.inf).max(1).values
                pieces += [mean,torch.sqrt(var+1e-6),maximum]
            elif mode == 'noisyor':
                # Geometric survival averaged over ALL reads, scaled to a fixed
                # reference bag of 20. Duplicating a bag cannot cause saturation.
                log_survival = (-nn.functional.softplus(self.read_logit(h))*m).sum(1)/n
                p = -torch.expm1(20*log_survival)
                pieces += [torch.logit(p.clamp(1e-6,1-1e-6))]
            else:
                raise ValueError(mode)
        return self.head(torch.cat(pieces,dim=1)).squeeze(-1)

def load_model(path):
    bundle = torch.load(path,map_location='cpu',weights_only=False)
    if bundle.get('kind') != 'final_data0_model':
        raise ValueError('Prediction requires the frozen final all-data0 model')
    model = SiteModel(bundle['config'],bundle['norm'])
    model.load_state_dict(bundle['state_dict'])
    model.eval()
    return model,bundle
