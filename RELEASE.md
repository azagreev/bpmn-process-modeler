# Release process

This document defines the release process for `bpmn-process-modeler`.

## Supported identity

Use this Git identity for signed release tags:

```text
Andrey Zagreev <a.zagreev@gmail.com>
```

Use this GitHub SSH signing key title:

```text
Andrey Zagreev SSH signing key
```

Do not reuse SSH authentication keys or repository deploy keys as release signing keys. GitHub treats deploy keys, account authentication keys, and SSH signing keys as separate key roles. A key already registered as a deploy key cannot also be registered as an SSH signing key.

## Key types

- SSH authentication key: lets a local machine authenticate to GitHub for clone, fetch, and push.
- Deploy key: grants one repository access to a specific public key. It may be read-only or read-write.
- SSH signing key: lets GitHub verify signatures on commits or annotated tags.

Release tags must be signed with an SSH signing key registered on the releasing GitHub account.

## Pre-release checklist

### v2.3.1 — release date TBD

Release scope: documentation hygiene patch (no behavior changes).

Required local checks:
- `python3 -m unittest discover -s tests/release -v`
- All existing release tests must pass.
- The 6 new tests in `tests/release/test_metadata.py` must pass for v2.3.1:
  - `test_changelog_release_date_is_filled`
  - `test_historic_changelog_dates_are_filled`
  - `test_readme_snapshot_date_matches_frontmatter`
  - `test_readme_bpmn_patterns_count_matches_source`
  - `test_readme_best_practices_count_matches_validation_checklist`
  - `test_release_md_has_current_version_section`

No new test modules in v2.3.1. Existing module `tests/release/test_metadata.py`
gets six new test methods.

### v2.3.0 — 2026-04-27

Release scope:
- Step 0 input classification
- Clarification Wizard
- Mixed input / Update scenario with reuse-ID
- 5-level severity documentation
- «Допущения» sheet in Excel template

Required local checks:
- `pytest tests/release/test_input_classification.py -v`
- `pytest tests/release/test_wizard.py -v`
- `pytest tests/release/test_mixed_input.py -v`
- Snapshot freshness check passes: `snapshot_expiry=2026-10-23`, 179 days after 2026-04-27

New v2.3.0 test modules:
- `tests/release/test_input_classification.py`
- `tests/release/test_wizard.py`
- `tests/release/test_mixed_input.py`

General checklist:

1. Start from a clean `main` synchronized with `origin/main`.
2. Create a release branch, for example `release/v2.0.2`.
3. Make only release-scope changes: version, changelog, tests, CI, packaging, and release documentation.
4. Run local release tests:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/release -v
```

5. Push the branch and open a PR into `main`.
6. Wait for `Release Checks` to pass.
7. Merge the PR only after review.

## Tag and release

After the PR is merged, create an annotated signed tag on the merge commit:

```bash
git switch main
git fetch origin main
git merge --ff-only origin/main
git tag -s vX.Y.Z "$(git rev-parse HEAD)" -m "Release vX.Y.Z - <summary>"
git push origin vX.Y.Z
```

Do not retag an existing public tag unless the correction is explicitly approved. If a tag must be repaired, keep the target commit unchanged and document the reason.

## Verify a release

Run the manual `Release Verify` workflow for the tag. It checks:

- the tag exists;
- the tag is an annotated tag object;
- the tag points to a commit;
- GitHub tag verification is `verified=true` and `reason=valid`;
- the tagger email is `a.zagreev@gmail.com`;
- the GitHub Release exists for the tag;
- the Release is neither draft nor prerelease;
- `bpmn-process-modeler.skill` exists;
- the asset unzips successfully;
- `SKILL.md` inside the asset matches the tag version;
- required package files exist.

Equivalent local smoke-test:

```bash
mkdir -p /tmp/bpmn-release-check
gh release download vX.Y.Z -R azagreev/bpmn-process-modeler \
  -p bpmn-process-modeler.skill \
  -D /tmp/bpmn-release-check \
  --clobber
sha256sum /tmp/bpmn-release-check/bpmn-process-modeler.skill
unzip -t /tmp/bpmn-release-check/bpmn-process-modeler.skill
unzip -p /tmp/bpmn-release-check/bpmn-process-modeler.skill \
  bpmn-process-modeler/SKILL.md | sed -n '1,10p'
```

## Release asset upload policy

`build-skill.yml` intentionally sets `overwrite_files: true` for `softprops/action-gh-release`. A repeated tag workflow may replace `bpmn-process-modeler.skill` on the existing GitHub Release.

Repeated tag pushes are allowed only for explicit release repair, such as correcting tag metadata or signature verification while keeping the target commit unchanged. After any repeated tag push, run `Release Verify` and repeat the release asset smoke-test.

## Post-release checklist

1. Confirm the GitHub tag is verified.
2. Confirm the build workflow is green.
3. Confirm the Release is not draft or prerelease.
4. Confirm the asset SHA256.
5. Download and unzip the published `.skill`.
6. Confirm `SKILL.md` inside the package has the release version.
7. Run one manual smoke-test in the target skill environment.
8. Delete the merged release branch after the release is verified.
