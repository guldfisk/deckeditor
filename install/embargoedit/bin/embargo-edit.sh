#!/usr/bin/env bash

# Shamelessly stolen from arcanist

# Do bash magic to resolve the real location of this script through aliases,
# symlinks, etc.
SOURCE="${BASH_SOURCE[0]}";
while [ -h "$SOURCE" ]; do
  LINK="$(readlink "$SOURCE")";
  if [ "${LINK:0:1}" == "/" ]; then
    # absolute symlink
    SOURCE="$LINK"
  else
    # relative symlink
    SOURCE="$(cd -P "$(dirname "$SOURCE")" && pwd)/$LINK"
  fi
done;
DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"

exec "$DIR/../editor/editor" "$@"