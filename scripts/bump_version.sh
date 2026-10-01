#!/usr/bin/env bash
# ------------------------------------------------------------------------
# bump_version.sh
#
# Определяет тип следующей версии (major/minor/patch) на основе сообщений
# коммитов от последнего тега до HEAD (Conventional Commits) и обновляет
# файл VERSION.
#
# Правила:
#   - коммит содержит "BREAKING CHANGE" или тип с "!" (например "feat!:")  -> MAJOR
#   - коммит начинается с "feat:"  (новый метод/фича калькулятора)         -> MINOR
#   - коммит начинается с "fix:", "chore:", "build:", "perf:", "refactor:",
#     "deps:" (в т.ч. переход на новые версии компонентов/образов)        -> PATCH
#   - если ни один коммит не подходит под правила                         -> PATCH (по умолчанию)
#
# Использование:
#   ./scripts/bump_version.sh            # выводит новую версию и обновляет VERSION
#   ./scripts/bump_version.sh --dry-run  # только печатает, не меняет VERSION
# ------------------------------------------------------------------------
set -euo pipefail

VERSION_FILE="VERSION"
DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

if [[ ! -f "$VERSION_FILE" ]]; then
    echo "0.0.0" > "$VERSION_FILE"
fi

CURRENT_VERSION=$(cat "$VERSION_FILE" | tr -d '[:space:]')
IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT_VERSION"

# Находим последний тег версии (vX.Y.Z), если есть
LAST_TAG=$(git describe --tags --match "v[0-9]*.[0-9]*.[0-9]*" --abbrev=0 2>/dev/null || echo "")

if [[ -n "$LAST_TAG" ]]; then
    COMMIT_RANGE="${LAST_TAG}..HEAD"
else
    COMMIT_RANGE="HEAD"
fi

COMMITS=$(git log "$COMMIT_RANGE" --pretty=format:"%s%n%b" 2>/dev/null || echo "")

BUMP="patch"

if echo "$COMMITS" | grep -qiE "BREAKING CHANGE|^[a-z]+(\([^)]*\))?!:"; then
    BUMP="major"
elif echo "$COMMITS" | grep -qE "^feat(\([^)]*\))?:"; then
    BUMP="minor"
elif echo "$COMMITS" | grep -qE "^(fix|chore|build|perf|refactor|deps)(\([^)]*\))?:"; then
    BUMP="patch"
fi

case "$BUMP" in
    major)
        MAJOR=$((MAJOR + 1)); MINOR=0; PATCH=0
        ;;
    minor)
        MINOR=$((MINOR + 1)); PATCH=0
        ;;
    patch)
        PATCH=$((PATCH + 1))
        ;;
esac

NEW_VERSION="${MAJOR}.${MINOR}.${PATCH}"

echo "Текущая версия: $CURRENT_VERSION"
echo "Тип изменения:  $BUMP"
echo "Новая версия:   $NEW_VERSION"

if [[ "$DRY_RUN" == false ]]; then
    echo "$NEW_VERSION" > "$VERSION_FILE"
fi

# Выводим версию отдельной строкой для удобного парсинга в CI (последняя строка)
echo "$NEW_VERSION"
