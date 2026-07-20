#!/usr/bin/env bash
set -euo pipefail

target="$HOME/.local/bin/spartan-sigil"
bashrc="$HOME/.bashrc"
begin='# >>> Spartan Sigil >>>'
end='# <<< Spartan Sigil <<<'

if [[ -f "$bashrc" ]] && grep -Fqx "$begin" "$bashrc"; then
    temporary=$(mktemp "${bashrc}.spartan-sigil.XXXXXX")
    awk -v begin="$begin" -v end="$end" '
        $0 == begin { removing=1; next }
        $0 == end { removing=0; next }
        !removing { print }
    ' "$bashrc" > "$temporary"
    mv "$temporary" "$bashrc"
fi

if [[ -L "$target" ]]; then
    rm "$target"
fi

echo "Removed Spartan Sigil integration."
