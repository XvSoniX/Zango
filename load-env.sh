#!/usr/bin/env bash

# Loads and exports all variables from the project .env file.
#
# Usage (from repository root):
#   source ./load-env.sh
#   source ./load-env.sh /path/to/custom.env

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  echo "برای export در شل فعلی باید source شود:" >&2
  echo "  source \"$(cd "$(dirname "$0")" && pwd)/load-env.sh\"" >&2
  exit 1
fi

_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_env_file="${1:-${_root}/.env}"

if [[ ! -f "${_env_file}" ]]; then
  echo "فایل env پیدا نشد: ${_env_file}" >&2
  return 1
fi

set -a
# shellcheck disable=SC1090
source "${_env_file}"
set +a
