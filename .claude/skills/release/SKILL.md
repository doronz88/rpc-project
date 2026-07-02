---
name: release
description: Cut a new rpcclient release — create the GitHub release (which publishes rpcclient to PyPI and attaches the server binaries) with a curated Highlights section. Use when asked to "release vX.Y.Z", "cut a release", or "publish a new version".
---

# Releasing rpc-project

## How releasing works here

- **Version is derived from the git tag** via `setuptools_scm` (`src/rpcclient/pyproject.toml` →
  `[tool.setuptools_scm]`, `version = { attr = "rpcclient._version.__version__" }`, with
  `root = "../.."` because the package lives under `src/rpcclient/`).
  There is **no version string to bump** in any file — the tag *is* the version.
- **Creating a GitHub release triggers two workflows** (both `on: release: types: [created]`):
  - `.github/workflows/python-publish.yml` — builds `rpcclient` in `src/rpcclient` (`python -m build`,
    after generating the protobuf stubs) and publishes to PyPI via trusted publishing. Needs full
    history + submodules for `setuptools_scm`.
  - `.github/workflows/server-publish.yml` — builds and **attaches the `rpcserver_ios` /
    `rpcserver_linux` / `rpcserver_macosx` binaries** to the release automatically. You don't upload
    assets by hand.
- Tags are `vMAJOR.MINOR.PATCH` (e.g. `v8.0.2`). Patch = bug-fix-only; minor = new features;
  major = breaking changes.

## Steps

1. **Confirm the tree is clean and pushed.** `git status` should be clean and up to date with
   `origin/master`. The release is cut from `master`.

2. **Review what's shipping** so you can write accurate highlights:
   ```shell
   PREV=$(git tag --sort=-creatordate | head -1)
   git log $PREV..HEAD --oneline
   git show <sha>   # inspect each meaningful change to describe it correctly
   ```

3. **Create the release** (this triggers the PyPI publish + server-asset builds). Use
   `--target master`, **not** a raw SHA — targeting a bare commit SHA fails with
   `Release.target_commitish is invalid`:
   ```shell
   gh release create vX.Y.Z --repo doronz88/rpc-project --target master --title vX.Y.Z --generate-notes
   ```

4. **Add a curated `## Highlights` section** above `## What's Changed`.
   `--generate-notes` alone does NOT include highlights — always add it. Match the house style
   (see `gh release view v8.0.2 --repo doronz88/rpc-project`):
   - One `###` subsection per notable change, prefixed with an emoji:
     `✨` new feature · `🐛` bug fix · `📚`/`📝` docs · other emoji as fitting.
   - A short prose paragraph explaining the user-visible impact, plus a fenced ```shell``` example
     for new commands/features.

5. **Rewrite `## What's Changed` as a commit history**, not the PR-link list `--generate-notes`
   produces. One line per commit since the previous tag, formatted
   `* <shortsha8> <subject> (#<pr>) (@<committer>)`. Use `--no-merges` — this repo merges PRs with
   merge commits, so listing the merge commits alongside their contents would be redundant:
   ```shell
   for sha in $(git log $PREV..HEAD --no-merges --format='%H'); do
     short=$(git rev-parse --short=8 $sha)
     subj=$(git show -s --format='%s' $sha)
     login=$(gh api repos/doronz88/rpc-project/commits/$sha --jq '.author.login')
     pr=$(gh api repos/doronz88/rpc-project/commits/$sha/pulls --jq '.[0].number')
     echo "* $short $subj (#$pr) (@$login)"
   done
   ```
   Keep the generated `## New Contributors` and `**Full Changelog**` lines.

   Write the full body (Highlights + What's Changed + New Contributors + Full Changelog) to a file
   and apply it:
   ```shell
   gh release edit vX.Y.Z --repo doronz88/rpc-project --notes-file /tmp/rel_notes.md
   ```
   Editing notes does **not** re-trigger the workflows — they already fired on creation.

6. **Verify the workflows.**
   ```shell
   gh run list --repo doronz88/rpc-project --workflow=python-publish.yml --limit 3
   gh run list --repo doronz88/rpc-project --workflow=server-publish.yml --limit 3
   ```
   Watch them to `completed / success` if the user wants confirmation the wheel landed on PyPI and
   the server binaries are attached to the release.

## Notes

- `gh` must be installed and authenticated (`gh auth status`).
- Don't create the tag manually with `git tag` — `gh release create` creates both the tag and the
  release. A lone tag push will not publish to PyPI or build the server assets.
- Run everything against `doronz88/rpc-project` explicitly (`--repo`): there is usually also a fork
  remote (`benj`), so a bare `gh` invocation can target the wrong repo.
