---
name: Git Cheat Sheet
description: Quick reference for Git commands. Use when user needs help with Git operations, asks "how do I do X in git?", encounters Git-related issues, or needs guidance on common Git workflows like branching, merging, stashing, and rebasing.
---

# Git Cheat Sheet

## Setup & Init

Configuring user information, initializing and cloning repositories.

| Command | Description |
|---------|-------------|
| `git config --global user.name "[name]"` | Set name for commit credits |
| `git config --global user.email "[email]"` | Set email for commits |
| `git config --global color.ui auto` | Enable colored output |
| `git init` | Initialize current directory as Git repo |
| `git clone [url]` | Clone repository from URL |

---

## Stage & Snapshot

Working with snapshots and the Git staging area.

| Command | Description |
|---------|-------------|
| `git status` | Show modified files staged for next commit |
| `git add [file]` | Stage file for next commit |
| `git add .` | Stage all changes |
| `git reset [file]` | Unstage file, keep changes |
| `git diff` | Diff of unstaged changes |
| `git diff --staged` | Diff of staged changes |
| `git commit -m "[message]"` | Commit staged changes |

---

## Branch & Merge

Isolating work in branches, changing context, and integrating changes.

| Command | Description |
|---------|-------------|
| `git branch` | List branches (* = current) |
| `git branch [name]` | Create new branch |
| `git branch -d [name]` | Delete branch |
| `git checkout [branch]` | Switch to branch |
| `git checkout -b [name]` | Create and switch to new branch |
| `git switch [branch]` | Switch to branch (modern) |
| `git switch -c [name]` | Create and switch (modern) |
| `git merge [branch]` | Merge branch into current |
| `git log` | Show commit history |

---

## Inspect & Compare

Examining logs, diffs and object information.

| Command | Description |
|---------|-------------|
| `git log` | Show commit history |
| `git log --oneline` | Compact commit history |
| `git log --graph` | Show branch graph |
| `git log branchB..branchA` | Commits in A not in B |
| `git log --follow [file]` | Commits that changed file (across renames) |
| `git diff branchB...branchA` | Diff of A not in B |
| `git show [SHA]` | Show object in readable format |

---

## Share & Update

Retrieving updates from another repository and updating local repos.

| Command | Description |
|---------|-------------|
| `git remote add [alias] [url]` | Add remote URL as alias |
| `git remote -v` | List remotes |
| `git fetch [alias]` | Fetch all branches from remote |
| `git merge [alias]/[branch]` | Merge remote branch into current |
| `git push [alias] [branch]` | Push commits to remote |
| `git push -u origin [branch]` | Push and set upstream |
| `git pull` | Fetch and merge from tracking remote |

---

## Tracking Path Changes

Versioning file removes and path changes.

| Command | Description |
|---------|-------------|
| `git rm [file]` | Delete file and stage removal |
| `git rm --cached [file]` | Remove from tracking, keep file |
| `git mv [old] [new]` | Move/rename file and stage |
| `git log --stat -M` | Show logs with moved paths |

---

## Rewrite History

Rewriting branches, updating commits and clearing history.

| Command | Description |
|---------|-------------|
| `git rebase [branch]` | Reapply commits on top of branch |
| `git rebase -i [commit]` | Interactive rebase |
| `git reset --soft [commit]` | Reset to commit, keep staged |
| `git reset --mixed [commit]` | Reset to commit, unstage changes |
| `git reset --hard [commit]` | Reset to commit, discard all changes |
| `git commit --amend` | Modify last commit |

**Warning**: `reset --hard` and `push --force` are destructive operations.

---

## Temporary Commits (Stash)

Temporarily store modified files to change branches.

| Command | Description |
|---------|-------------|
| `git stash` | Save modified and staged changes |
| `git stash push -m "[msg]"` | Stash with message |
| `git stash list` | List stashed changes |
| `git stash pop` | Apply and remove top stash |
| `git stash apply` | Apply top stash, keep in list |
| `git stash drop` | Discard top stash |
| `git stash clear` | Remove all stashes |

---

## Ignoring Patterns

Preventing unintentional staging or committing of files.

**`.gitignore` examples:**
```
logs/           # Ignore directory
*.notes         # Ignore by extension
pattern*/       # Wildcard directories
!important.log  # Exception (don't ignore)
```

| Command | Description |
|---------|-------------|
| `git config --global core.excludesfile [file]` | Set global ignore file |

---

## Common Workflows

### Start New Feature
```bash
git checkout main
git pull
git checkout -b feature/my-feature
```

### Save Work in Progress
```bash
git stash
git checkout other-branch
# ... do work ...
git checkout original-branch
git stash pop
```

### Undo Last Commit (Keep Changes)
```bash
git reset --soft HEAD~1
```

### Undo Last Commit (Discard Changes)
```bash
git reset --hard HEAD~1
```

### Sync Fork with Upstream
```bash
git fetch upstream
git checkout main
git merge upstream/main
git push origin main
```

### Squash Last N Commits
```bash
git rebase -i HEAD~N
# Change 'pick' to 'squash' for commits to combine
```

### View File at Specific Commit
```bash
git show [commit]:[file]
```

### Find Who Changed a Line
```bash
git blame [file]
```

### Search Commit Messages
```bash
git log --grep="keyword"
```

### Search Code Changes
```bash
git log -S "code_string"
```

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────────┐
│                    Git Quick Reference                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  DAILY COMMANDS                                             │
│  ──────────────                                             │
│  git status          → What's changed?                      │
│  git add .           → Stage everything                     │
│  git commit -m "msg" → Save snapshot                        │
│  git push            → Upload to remote                     │
│  git pull            → Download from remote                 │
│                                                             │
│  BRANCHING                                                  │
│  ─────────                                                  │
│  git branch          → List branches                        │
│  git checkout -b X   → Create & switch to X                 │
│  git merge X         → Merge X into current                 │
│                                                             │
│  UNDO                                                       │
│  ────                                                       │
│  git reset [file]    → Unstage file                         │
│  git checkout [file] → Discard changes                      │
│  git reset --soft ~1 → Undo commit, keep changes            │
│  git reset --hard ~1 → Undo commit, discard changes         │
│                                                             │
│  INSPECT                                                    │
│  ───────                                                    │
│  git log --oneline   → Compact history                      │
│  git diff            → Show changes                         │
│  git blame [file]    → Who changed what                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

*Source: GitHub Education - git-cheat-sheet-education.pdf*
