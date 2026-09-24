#!/bin/bash

set -euo pipefail

if [[ $# -eq 0 ]]; then
  echo "Usage: $0 <major|minor|patch>"
  echo "  Bumps the version like 'npm version <major|minor|patch>': updates pyproject.toml,"
  echo "  commits and tags. No push, no branch handling."
  exit 1
fi

BUMP_TYPE=$1
PYPROJECT_FILE="pyproject.toml"

if [[ -n "$(git status --porcelain)" ]]; then
  echo "Working tree is not clean. Commit or stash your changes before releasing."
  exit 1
fi

CURRENT_VERSION=$(grep '^version =' "$PYPROJECT_FILE" | sed -E 's/version = "(.*)"/\1/')
BASE_VERSION="${CURRENT_VERSION%%-*}"

if ! [[ "$BASE_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "::error title=Version invalide::La version courante '${CURRENT_VERSION}' dans $PYPROJECT_FILE doit être de la forme X.Y.Z."
  exit 1
fi

IFS='.' read -r MAJOR MINOR PATCH <<< "$BASE_VERSION"

case "$BUMP_TYPE" in
  major)
    RELEASE_VERSION="$((MAJOR + 1)).0.0"
    ;;
  minor)
    RELEASE_VERSION="$MAJOR.$((MINOR + 1)).0"
    ;;
  patch)
    RELEASE_VERSION="$MAJOR.$MINOR.$((PATCH + 1))"
    ;;
  *)
    echo "Invalid bump type '$BUMP_TYPE'. Expected: major, minor or patch."
    exit 1
    ;;
esac

echo "-------------- Preparing release $RELEASE_VERSION (from $CURRENT_VERSION, $BUMP_TYPE bump)"

if git rev-parse -q --verify "refs/tags/$RELEASE_VERSION" >/dev/null; then
  echo "Tag '$RELEASE_VERSION' already exists. Aborting."
  exit 1
fi

sed -i "/^version = /s/\".*\"/\"$RELEASE_VERSION\"/" "$PYPROJECT_FILE"
echo "$PYPROJECT_FILE updated with [version = $RELEASE_VERSION]"

git add "$PYPROJECT_FILE"
git commit -m "chore: release $RELEASE_VERSION"

git tag "$RELEASE_VERSION"
echo "New tag created: $RELEASE_VERSION"

echo "-------------- Done. Commit and tag '$RELEASE_VERSION' are ready locally (nothing pushed)."
