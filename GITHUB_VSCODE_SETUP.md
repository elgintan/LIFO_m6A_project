# GitHub and VS Code: first setup

Git saves versions of files locally. GitHub hosts those versions online. VS Code provides the editor and Git controls. Git and VS Code are already installed on Elgin's computer; GitHub CLI is not required.

The clean prepared project is `Team_Project_export/LIFO_m6A_project`. Open this folder, not the whole DSA4262 module folder. The wider module folder contains unrelated coursework and private credential files.

Publication is complete: [elgintan/LIFO_m6A_project](https://github.com/elgintan/LIFO_m6A_project) is public, uses branch `main`, and is connected to the prepared local folder. Anonymous GitHub metadata and the published commit were checked on 15 October 2026. Elgin can keep using this folder; do not publish or clone a second copy merely to reconnect it. Start with **Give teammates access** below. The initial setup routes are retained for reference and for members setting up their own clone.

## Choose one route

Use **Route A** only if the GitHub repository does not exist. Use **Route B** if it already exists. Do not create a second repository to connect to an existing one.

### Route A: publish a new public repository from VS Code

1. Open VS Code. Select **File > Open Folder**, choose `LIFO_m6A_project`, and select **Select Folder**. Trust it if you recognise the prepared project.
2. Select **Source Control** in the left sidebar, or press **Ctrl+Shift+G**. If **Initialize Repository** appears, select it. If a branch is already shown, Git is already initialised.
3. Before committing, review the proposed public files. Select each changed file to see its contents/differences. Check `.gitignore`, exclude secrets and raw/cache/environment files, and retain the intended public documentation, code and results.
4. Select the **+** beside each intended file to stage it. Staging chooses what the next saved version will contain. Avoid **Stage All** until the complete file list has been reviewed.
5. Enter a commit message such as `Add reviewed project structure and existing work`, then select **Commit**. If Git requests an author name/email, use the identity instructions below and retry.
6. Press **Ctrl+Shift+P**, type **Publish to GitHub**, and select that command. Sign in through the browser if prompted, authorising your own account.
7. Enter the chosen repository name and select **Public** / **Publish to GitHub public repository** when offered. This action creates the public repository and uploads its commits. Complete the public-file review before this step.
8. Open the resulting GitHub link. Check that it says **Public**, contains the six intended folders, and shows your latest commit. Keep that repository URL for the team and their AI chats.

### Route B: the public GitHub repository already exists

First provide its normal repository URL to Elgin's project assistant so the remote contents can be inspected. An existing README or other commit must be preserved/reconciled; do not blindly push an unrelated local history over it.

The simplest route for a new user is:

1. In VS Code press **Ctrl+Shift+P**, run **Git: Clone**, and paste the existing repository URL.
2. Choose a separate parent folder so cloning does not overwrite the prepared `LIFO_m6A_project` folder. Select **Open** when cloning finishes.
3. Copy the reviewed project files into this clone, preserving any existing remote files. **Do not copy the prepared folder's hidden `.git` directory.** Resolve overlapping files by reviewing their contents.
4. Review, stage and commit the intended changes through **Source Control**, as described in Route A steps 3-5. Select **... > Push** in Source Control to upload them.
5. Check the repository on GitHub. Do not select **Publish to GitHub** to create another repository, and do not use force push to bypass a rejection.

Alternatively, an experienced helper can attach the existing remote to the prepared local repository, fetch its history and reconcile it normally. The exact steps depend on whether the remote already contains commits; inspect that state first.

## If Git asks for your author identity

Commit author information becomes part of public Git history. Use the name and commit email you want public. To use GitHub's private-email option, open GitHub **profile picture > Settings > Emails**, enable the appropriate privacy option and copy the exact no-reply address shown for your account. Do not invent an address.

In VS Code select **Terminal > New Terminal** and confirm the prompt is inside the intended repository. Replace both quoted examples below with your chosen values, then run:

```powershell
git config user.name "YOUR CHOSEN AUTHOR NAME"
git config user.email "YOUR CHOSEN COMMIT EMAIL"
```

These commands set identity for this repository only. They do not log in to GitHub. Return to Source Control and retry the commit.

## Give teammates access

Anyone can read/clone a public repository, including AI tools capable of accessing GitHub. Public visibility does not guarantee that every AI can browse files, run code or upload changes.

For direct team uploads, on GitHub open the repository and select **Settings > Collaborators > Add people**. Invite each contributor using their GitHub username/email; they must accept. They sign in using their own accounts. Never share account passwords or tokens.

Members 3-5 can then clone the repository through **Ctrl+Shift+P > Git: Clone**, work in their assigned folders and upload changes. Member 1 sends her package directly to Elgin and does not need to upload it. If a contributor is not granted write access, a fork and pull request is an alternative; public visibility alone does not allow direct writes.

## After the first setup

Before starting work, select **Source Control > ... > Pull**. After editing: **review -> stage -> commit -> ... > Push -> check GitHub**. Pull downloads and integrates team changes; push uploads committed local changes. A saved file or local commit is not visible to teammates until pushed.

If a pull/push reports conflicts, ask Elgin to help inspect the specific message. Do not choose **Discard Changes** or force push to make the message disappear.

## Official references

- [VS Code: repositories, cloning, publishing and remotes](https://code.visualstudio.com/docs/sourcecontrol/repos-remotes)
- [VS Code: source-control quickstart](https://code.visualstudio.com/docs/sourcecontrol/quickstart)
- [GitHub: collaborator permissions](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/repository-access-and-collaboration/permission-levels-for-a-personal-account-repository)
- [GitHub: large files](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)
