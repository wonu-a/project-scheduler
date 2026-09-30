#!/usr/bin/env bash
# Compile translations, bundle Qt resources, then start the app.
#
#   1. pyside6-lupdate refreshes translations/*.ts from the Python sources.
#   2. pyside6-lrelease compiles the .ts files to src/project_scheduler/resources/i18n/*.qm.
#   3. pyside6-rcc bundles stylesheets, icons and .qm files into src/project_scheduler/resources_rc.py.
#   4. uv run project-scheduler starts the app (skip with --no-run, e.g. before running tests).
#
# Run from anywhere, after changing .qss files, icons, .ts files or any tr() string:
#
#   ./build_assets.sh                 # build, then run the app
#   ./build_assets.sh --language de   # other options go to the app (--language, --theme)
#   ./build_assets.sh --no-run        # build only

# The script uses bash features; if started with `zsh` or `sh` (on macOS, bash in POSIX mode,
# which lacks process substitution), restart it in full bash.
if [ -z "${BASH_VERSION:-}" ]; then
    exec bash "$0" "$@"
fi
if shopt -oq posix; then
    exec bash "$0" "$@"
fi
set -euo pipefail

run_app=true
app_args=()
for arg in "$@"; do
    case "$arg" in
        --no-run) run_app=false ;;
        -h|--help) sed -n '2,14p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) app_args+=("$arg") ;;  # passed on to the app, e.g. --language de
    esac
done
if ! "$run_app" && [ ${#app_args[@]} -gt 0 ]; then
    echo "app options (${app_args[*]}) given with --no-run; nothing would use them" >&2
    exit 2
fi

cd "$(dirname "$0")"

PACKAGE=src/project_scheduler
RESOURCES=$PACKAGE/resources
LANGUAGES=(de ja)

run() {
    echo "\$ $1 … ${*: -1}"
    uv run --quiet "$@"
}

sources=()
while IFS= read -r file; do
    sources+=("$file")
done < <(find "$PACKAGE" -name '*.py' ! -name resources_rc.py | sort)

mkdir -p translations "$RESOURCES/i18n"
for lang in "${LANGUAGES[@]}"; do
    ts=translations/project_scheduler_$lang.ts
    run pyside6-lupdate "${sources[@]}" -no-obsolete -target-language "$lang" -ts "$ts"
    run pyside6-lrelease "$ts" -qm "$RESOURCES/i18n/project_scheduler_$lang.qm"
done
run pyside6-rcc "$RESOURCES/resources.qrc" -o "$PACKAGE/resources_rc.py"

if "$run_app"; then
    echo "\$ uv run project-scheduler ${app_args[*]:-}"
    exec uv run project-scheduler ${app_args[@]+"${app_args[@]}"}
fi
