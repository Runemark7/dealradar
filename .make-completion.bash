#!/bin/bash
# Bash completion for Makefile targets
# Source this file or add to ~/.bashrc:
# source /path/to/.make-completion.bash

_make_completion() {
    local cur targets
    cur="${COMP_WORDS[COMP_CWORD]}"
    targets=$(make -qp 2>/dev/null | awk -F':' '/^[a-zA-Z0-9][^$#\/\t=]*:([^=]|$)/ {split($1,A,/ /);for(i in A)print A[i]}' | sort -u)
    COMPREPLY=($(compgen -W "${targets}" -- ${cur}))
}

complete -F _make_completion make