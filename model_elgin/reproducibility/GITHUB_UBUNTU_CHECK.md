# Hosted Ubuntu prediction check

The workflow `.github/workflows/ubuntu_prediction.yml` runs the existing isolated
Docker recipe on an Ubuntu 24.04 GitHub runner. It copies only five inference
sources, exact pins, the selected 98,043-byte model and the real ten-site example
into its image. It performs no training, SG-NEx batch prediction or AWS launch.

The unchanged verifier checks the model SHA, all ten original site keys, all
1,887 example reads, complete prediction metadata and numerical agreement within
3e-6. It writes a receipt and retains success/failure logs as a workflow artifact.
The artifact excludes the build context and any local environments or raw data.
Checkout and upload actions are pinned to verified commit SHAs; the workflow has
read-only repository permissions and does not receive project credentials.

Publication triggers one check when this workflow or its recipe/pins change on
main. It can also be run manually in GitHub Actions. A queued or failed workflow
is not a successful Ubuntu check; inspect the completed job and receipt first.
A successful hosted container establishes this Linux prediction path, not fresh
AWS-host verification, training replay or independent model accuracy.

The laptop's earlier Docker startup failure is preserved in local evidence.
This alternative does not reset Docker, change Windows settings or start a paid
cloud instance. Actual execution outcome belongs in the current stage tracker.
