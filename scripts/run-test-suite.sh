#!/usr/bin/env bash

set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python_bin="${project_root}/.venv/bin/python"
inode_limit_percent="${GNI_TEST_INODE_LIMIT_PERCENT:-65}"

if [[ ! -x "${python_bin}" ]]; then
    echo "Missing executable virtual-environment Python: ${python_bin}" >&2
    exit 1
fi

check_var_inodes() {
    local inode_percent

    inode_percent="$(
        df -Pi /var \
            | awk 'NR == 2 {gsub(/%/, "", $5); print $5}'
    )"

    if [[ -z "${inode_percent}" ]]; then
        echo "Unable to determine /var inode usage." >&2
        exit 1
    fi

    echo "/var inode usage: ${inode_percent}%"

    if (( inode_percent >= inode_limit_percent )); then
        echo \
            "Refusing to continue: /var inode use is at or above " \
            "${inode_limit_percent}%." >&2
        echo \
            "Inspect PostgreSQL pending relation files and recover the " \
            "test cluster before continuing." >&2
        exit 1
    fi
}

cd "${project_root}"

check_var_inodes

echo "Running migration safety tests separately..."
"${python_bin}" -m pytest -q tests/migrations

check_var_inodes

echo "Running non-migration regression tests..."
"${python_bin}" -m pytest -q --ignore=tests/migrations

check_var_inodes
