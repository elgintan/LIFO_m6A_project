"""Site features: read the m6Anet-format JSON and summarise each site's reads.

Each JSON line is {transcript: {position: {7-mer: [[9 numbers per read], ...]}}}.
The 9 numbers are dwell time, signal SD and mean current at positions -1, 0 and +1.
For every site we keep the 7-mer and, for each of the 9 measurements, the mean,
population SD and the 10th, 25th, 50th, 75th and 90th percentiles across reads.
"""
import gzip
import json

import numpy as np
import pandas as pd

KEY = ["transcript_id", "transcript_position"]
MEASUREMENTS = [f"{m}_{p}" for p in ("m1", "0", "p1") for m in ("dwell", "sd", "mean")]
QUANTILES = (10, 25, 50, 75, 90)
NUMERIC = ([f"{m}_mean" for m in MEASUREMENTS] + [f"{m}_std" for m in MEASUREMENTS]
           + [f"{m}_q{q}" for m in MEASUREMENTS for q in QUANTILES])
BASES = [f"base{i}" for i in range(7)]


def read_sites(path):
    """One row per site, in file order. Raises on a site with no complete read or a duplicate key."""
    opener = gzip.open if str(path).endswith(".gz") else open
    rows = []
    with opener(path, "rt") as handle:
        for line in handle:
            if not line.strip():
                continue
            for transcript, positions in json.loads(line).items():
                for position, kmers in positions.items():
                    for kmer, reads in kmers.items():
                        a = np.asarray(reads, dtype=float)
                        if a.ndim != 2 or a.shape[1] != 9:
                            raise ValueError(f"{transcript}:{position}: expected 9 numbers per read")
                        a = a[np.isfinite(a).all(axis=1)]
                        if len(a) == 0:
                            raise ValueError(f"{transcript}:{position}: no read with 9 finite numbers")
                        rows.append((transcript, int(position), kmer, len(a), *a.mean(0), *a.std(0),
                                     *np.percentile(a, QUANTILES, axis=0).T.ravel()))
    df = pd.DataFrame(rows, columns=KEY + ["kmer", "n_reads"] + NUMERIC)
    if df.duplicated(KEY).any():
        raise ValueError(f"{int(df.duplicated(KEY).sum())} duplicate site keys in {path}")
    if (df.kmer.str.len() != 7).any() or not df.kmer.str.fullmatch("[ACGT]+").all():
        raise ValueError("every site needs a 7-base A/C/G/T context")
    return df


class KmerBaseline:
    """Express each numeric feature relative to its sequence context's typical value.

    Fitted on training sites only (no labels used). A 7-mer with fewer than
    `min_sites` training sites falls back to its central 5-mer, then to the
    global training mean. The same fitted table is applied unchanged to every
    later dataset; test files are never standardised against themselves.
    """

    def __init__(self, min_sites=50):
        self.min_sites = min_sites

    def fit(self, sites):
        by7 = sites.groupby("kmer")[NUMERIC].agg(["mean", "size"])
        by5 = sites.assign(motif=sites.kmer.str[1:6]).groupby("motif")[NUMERIC].agg(["mean", "size"])
        self.kmer_ = by7.xs("mean", axis=1, level=1)[by7[(NUMERIC[0], "size")] >= self.min_sites]
        self.motif_ = by5.xs("mean", axis=1, level=1)[by5[(NUMERIC[0], "size")] >= self.min_sites]
        self.global_ = sites[NUMERIC].mean()
        return self

    def reference(self, kmers):
        """Reference table for these 7-mers, and which level each one used."""
        motifs = kmers.str[1:6]
        ref = self.kmer_.reindex(kmers.values)
        level = np.where(ref.notna().all(axis=1), "7mer", "")
        fallback = self.motif_.reindex(motifs.values).set_index(ref.index)
        ref = ref.fillna(fallback)
        level = np.where(level == "", np.where(ref.notna().all(axis=1), "5mer", "global"), level)
        ref = ref.fillna(self.global_)
        return ref.values, level

    def transform(self, sites):
        ref, level = self.reference(sites.kmer)
        out = pd.DataFrame(sites[NUMERIC].values - ref, columns=NUMERIC, index=sites.index)
        for i in range(7):
            out[f"base{i}"] = pd.Categorical(sites.kmer.str[i], categories=list("ACGT"))
        return out, level

    def to_frame(self):
        return pd.concat({"7mer": self.kmer_, "5mer": self.motif_, "global": self.global_.to_frame("all").T})

    @classmethod
    def from_frame(cls, frame, min_sites):
        self = cls(min_sites)
        self.kmer_ = frame.loc["7mer"]
        self.motif_ = frame.loc["5mer"]
        self.global_ = frame.loc["global"].iloc[0]
        return self
