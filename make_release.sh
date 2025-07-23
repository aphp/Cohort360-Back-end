#!/bin/bash

set -e

if [ $# -eq 0 ]; then
  echo "Usage: $0 <release_version> [--live]"
  echo "  <release_version>: The version to release (e.g., 1.2.3)."
  echo "  --live (optional): Performs a real push. Defaults to --dry-run."
  exit 1
fi

RELEASE_VERSION=$1
DRY_RUN_FLAG="--dry-run"

if [ "$2" == "--live" ]; then
  echo "!!! LIVE MODE: Pushes will be sent to the remote repository. !!!"
  DRY_RUN_FLAG=""
else
  echo "--- DRY RUN MODE: No changes will be pushed. Use '--live' to execute pushes. ---"
fi


SOURCE_BRANCH="main"
RELEASE_BRANCH="release_$RELEASE_VERSION"
PYPROJECT_FILE="pyproject.toml"

echo "-------------- Preparing a new release: $RELEASE_VERSION"

if git show-ref --verify --quiet refs/heads/"$SOURCE_BRANCH"; then
    git checkout "$SOURCE_BRANCH" || { echo "Failed to switch to '$SOURCE_BRANCH' branch."; exit 1; }
    git pull origin "$SOURCE_BRANCH" || { echo "Failed to update '$SOURCE_BRANCH'."; exit 1; }
else
    echo "Branch '$SOURCE_BRANCH' does not exist. Aborting."
    exit 1
fi

sed -i "/^version = /s/\".*\"/\"$RELEASE_VERSION\"/" "$PYPROJECT_FILE"
echo "$PYPROJECT_FILE updated with [version = $RELEASE_VERSION]"

git add "$PYPROJECT_FILE"
git commit -m "chore: new release $RELEASE_VERSION"
git tag "$RELEASE_VERSION"
echo "New tag created: $RELEASE_VERSION"

echo "Create release branch $RELEASE_BRANCH from tag $RELEASE_VERSION"
git checkout -b "$RELEASE_BRANCH" "$RELEASE_VERSION"

echo "Pushing release branch: $RELEASE_BRANCH and tag: $RELEASE_VERSION"
git push --set-upstream origin "$RELEASE_BRANCH" -v $DRY_RUN_FLAG

git checkout "$SOURCE_BRANCH"

echo "-------------- Update CHANGELOG.md and set next dev version"
git cliff --latest --prepend CHANGELOG.md

# prepare next dev version
IFS='.' read -r MAJOR MINOR PATCH <<< "$RELEASE_VERSION"

NEXT_DEV_VERSION="$MAJOR.$((MINOR + 1)).$PATCH-dev"

sed -i "/^version = /s/\".*\"/\"$NEXT_DEV_VERSION\"/" "$PYPROJECT_FILE"

git add "$PYPROJECT_FILE" CHANGELOG.md
git commit -m "chore: update CHANGELOG.md and bump version to $NEXT_DEV_VERSION"

echo "Pushing branch $SOURCE_BRANCH"
git push $DRY_RUN_FLAG