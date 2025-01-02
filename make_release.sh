#!/bin/bash

set -e

if [ $# -eq 0 ]; then
  echo "-------------- Missing release version argument"
  exit 1
fi

RELEASE_VERSION=$1
SOURCE_BRANCH="main"
RELEASE_BRANCH="release_$RELEASE_VERSION"
PYPROJECT_FILE="pyproject.toml"

echo "-------------- Preparing a new release: $RELEASE_VERSION"

if git show-ref --verify --quiet refs/heads/"$SOURCE_BRANCH"; then
    git checkout "$SOURCE_BRANCH" || { echo "-------------- Failed to switch to '$SOURCE_BRANCH' branch."; exit 1; }
    git pull origin "$SOURCE_BRANCH" || { echo "-------------- Failed to update '$SOURCE_BRANCH'."; exit 1; }
    git checkout -b "$RELEASE_BRANCH"
else
    echo "-------------- Branch '$SOURCE_BRANCH' does not exist. Aborting."
    exit 1
fi

sed -i "/^version = /s/\".*\"/\"$RELEASE_VERSION\"/" "$PYPROJECT_FILE"

echo "-------------- $PYPROJECT_FILE updated with [version = $RELEASE_VERSION]"

git add "$PYPROJECT_FILE"
git commit -m "new release $RELEASE_VERSION"
git tag "$RELEASE_VERSION"
echo "-------------- New tag created: $RELEASE_VERSION"

echo "-------------- Pushing a new branch: $RELEASE_BRANCH and tag: $RELEASE_VERSION"
git push --set-upstream origin "$RELEASE_BRANCH" --dry-run -v

git checkout $SOURCE_BRANCH

git cliff --latest --prepend CHANGELOG.md
echo "-------------- updated changelog"

# prepare next dev version
IFS='.' read -r MAJOR MINOR PATCH <<< "$RELEASE_VERSION"

NEXT_DEV_VERSION="$MAJOR.$((MINOR + 1)).$PATCH-dev"

sed -i "/^version = /s/\".*\"/\"$NEXT_DEV_VERSION\"/" "$PYPROJECT_FILE"

git add "$PYPROJECT_FILE" CHANGELOG.md
git commit -m "chore: update CHANGELOG.md and bump version to $NEXT_DEV_VERSION"