#!/usr/bin/env bash
set -euo pipefail

project_dir=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
target_dir="$HOME/.local/bin"
target="$target_dir/spartan-sigil"
bashrc="$HOME/.bashrc"
begin='# >>> Spartan Sigil >>>'
end='# <<< Spartan Sigil <<<'

mkdir -p "$target_dir"
chmod +x "$project_dir/spartan_sigil.py"
ln -sfn "$project_dir/spartan_sigil.py" "$target"

if [[ ! -f "$bashrc" ]]; then
    : > "$bashrc"
fi

if ! grep -Fqx "$begin" "$bashrc"; then
    backup="$bashrc.spartan-sigil.bak"
    if [[ ! -e "$backup" ]]; then
        cp -p "$bashrc" "$backup"
    fi
    cat >> "$bashrc" <<'BLOCK'

# >>> Spartan Sigil >>>
__spartan_sigil_start() {
    [[ $- == *i* && -t 1 && -t 0 ]] || return
    [[ ${SPARTAN_SIGIL:-on} != off && -z ${SSH_CONNECTION:-} && ${TERM:-} != dumb ]] || return
    local size lines columns
    size=$(stty size 2>/dev/null) || return
    read -r lines columns <<<"$size"
    (( columns >= 42 && lines >= 16 )) || return

    command spartan-sigil --prepare --rows 11 >/dev/tty 2>/dev/null || return
    command spartan-sigil --render --rows 11 >/dev/tty 2>/dev/null &
    __SPARTAN_SIGIL_PID=$!
    __SPARTAN_SIGIL_ARMED=1
}

__spartan_sigil_stop() {
    local pid=${__SPARTAN_SIGIL_PID:-}
    [[ -n $pid ]] || return 0
    if kill -0 "$pid" 2>/dev/null; then
        kill -TERM "$pid" 2>/dev/null || true
        wait "$pid" 2>/dev/null || true
    fi
    unset __SPARTAN_SIGIL_PID
}

__spartan_sigil_disarm() {
    __spartan_sigil_stop
    trap - DEBUG INT EXIT
    unset __SPARTAN_SIGIL_ARMED
}

__spartan_sigil_before_command() {
    [[ ${__SPARTAN_SIGIL_ARMED:-0} == 1 ]] || return 0
    __spartan_sigil_disarm
}

__spartan_sigil_interrupt() {
    __spartan_sigil_disarm
}

__spartan_sigil_exit() {
    __spartan_sigil_stop
}

__spartan_sigil_start
if [[ ${__SPARTAN_SIGIL_ARMED:-0} == 1 ]]; then
    trap '__spartan_sigil_interrupt' INT
    trap '__spartan_sigil_exit' EXIT
    trap '__spartan_sigil_before_command' DEBUG
fi
# <<< Spartan Sigil <<<
BLOCK
fi

echo "Installed Spartan Sigil: $target"
