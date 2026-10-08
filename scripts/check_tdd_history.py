"""Проверяет, что часть 2 выполнена по TDD: тесты раньше кода.

    uv run python scripts/check_tdd_history.py

Что проверяется:

1. в `tests/test_checkout.py` не меньше MIN_TESTS тестов, и в каждом есть `assert`;
2. в тестах нет `skip` и `xfail`;
3. функции в `src/shop/checkout.py` — не заглушки;
4. в истории git коммит, где тестов стало достаточно (не меньше MIN_TESTS
   строк с `assert`), раньше коммита, где заглушка `...` исчезла; и на момент
   коммита с тестами реализация ещё была заглушкой.

Проверка 4 пропускается с предупреждением, если это не git-репозиторий или
репозиторий склонирован не полностью (`git clone --depth=1`): на мелких клонах
история недоступна, и ругаться на это бессмысленно.

Код возвращает 0, если всё в порядке, и 1 иначе.
"""

import ast
import subprocess
import sys
from pathlib import Path

TESTS_PATH = Path("tests/test_checkout.py")
IMPL_PATH = Path("src/shop/checkout.py")
MIN_TESTS = 10
FORBIDDEN_MARKERS = ("skip", "xfail")


def git(*args: str) -> str | None:
    """Выполнить команду git и вернуть её вывод. None, если команда не удалась."""
    done = subprocess.run(("git", *args), capture_output=True, text=True, check=False)
    if done.returncode != 0:
        return None
    return done.stdout.strip()


def note(text: str) -> None:
    print(f"  {text}")


def test_functions(tree: ast.Module) -> list[ast.FunctionDef]:
    """Тестовые функции верхнего уровня."""
    return [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")]


def is_stub(node: ast.FunctionDef) -> bool:
    """Заглушка: кроме докстринга в теле ничего нет, либо единственное `...` / `pass`."""
    body = list(node.body)
    if body and isinstance(body[0], ast.Expr):
        value = body[0].value
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            body = body[1:]
    if not body:
        return True
    if len(body) > 1:
        return False
    first = body[0]
    if isinstance(first, ast.Pass):
        return True
    if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
        return first.value.value is Ellipsis
    return False


def check_tests() -> tuple[ast.Module | None, list[str]]:
    """Проверки 1 и 2. Возвращает разобранное дерево (если получилось) и список претензий."""
    problems: list[str] = []
    if not TESTS_PATH.exists():
        return None, [f"нет файла {TESTS_PATH}"]
    tree = ast.parse(TESTS_PATH.read_text(encoding="utf-8"))
    source = TESTS_PATH.read_text(encoding="utf-8")

    functions = test_functions(tree)
    if len(functions) < MIN_TESTS:
        problems.append(f"написано {len(functions)} тестов, нужно минимум {MIN_TESTS}")

    empty = [node.name for node in functions if not any(isinstance(child, ast.Assert) for child in ast.walk(node))]
    if empty:
        problems.append(f"в этих тестах нет assert: {', '.join(empty)}")

    for marker in FORBIDDEN_MARKERS:
        if f"pytest.mark.{marker}" in source:
            problems.append(f"в тестах есть pytest.mark.{marker}: тесты нельзя пропускать")

    return tree, problems


def check_implementation() -> list[str]:
    """Проверка 3: обе функции должны быть не заглушками."""
    if not IMPL_PATH.exists():
        return [f"нет файла {IMPL_PATH}"]
    tree = ast.parse(IMPL_PATH.read_text(encoding="utf-8"))
    problems: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and is_stub(node):
            problems.append(f"функция {node.name}() всё ещё заглушка")
    return problems


def is_ancestor(older: str, newer: str) -> bool:
    """True, если коммит `older` — предок коммита `newer`."""
    return git("merge-base", "--is-ancestor", older, newer) == ""


def commits_for(path: Path) -> list[str]:
    """Коммиты, менявшие файл, от самого раннего к самому позднему."""
    raw = git("log", "--reverse", "--format=%H", "--", str(path)) or ""
    return [line for line in raw.splitlines() if line]


def history_is_available() -> bool:
    """Проверить, что историю git вообще можно читать."""
    if git("rev-parse", "--is-inside-work-tree") != "true":
        note("внимание: это не git-репозиторий, порядок коммитов не проверяем")
        return False
    if git("rev-parse", "--is-shallow-repository") == "true":
        note("внимание: репозиторий склонирован с --depth=1, порядок коммитов не проверяем")
        return False
    return True


def count_asserts(source: str) -> int:
    """Приблизительное число assert в тексте: строки, начинающиеся с `assert`."""
    return sum(1 for line in source.splitlines() if line.lstrip().startswith("assert "))


def is_stub_source(source: str) -> bool:
    """Похоже на заглушку: есть отдельная строка, где тело — только `...` или `pass`.

    Разбирать код через `ast` здесь нельзя: промежуточный коммит может не
    парситься, а исключения в этом проекте запрещены. Поэтому ищем отдельную
    строку, а не подстроку: аннотация `tuple[int, ...]` заглушкой не является.
    """
    return any(line.strip() in {"...", "pass"} for line in source.splitlines())


def first_commit_with_full_tests() -> str | None:
    """Первый коммит, где тестов достаточно: строк с `assert` не меньше MIN_TESTS."""
    for sha in commits_for(TESTS_PATH):
        blob = git("show", f"{sha}:{TESTS_PATH}")
        if blob is not None and count_asserts(blob) >= MIN_TESTS:
            return sha
    return None


def first_commit_without_stub() -> str | None:
    """Первый коммит, где заглушка исчезла из реализации."""
    for sha in commits_for(IMPL_PATH):
        blob = git("show", f"{sha}:{IMPL_PATH}")
        if blob is not None and not is_stub_source(blob):
            return sha
    return None


def check_history() -> list[str]:
    """Проверка 4: тесты закоммичены раньше реализации."""
    if not history_is_available():
        return []

    first_impl = first_commit_without_stub()
    if first_impl is None:
        return ["реализация не менялась с момента создания заглушки"]

    first_test = first_commit_with_full_tests()
    if first_test is None:
        return [f"тестов с assert меньше, чем нужно: {MIN_TESTS}"]

    problems: list[str] = []
    if not is_ancestor(first_test, first_impl):
        problems.append("тесты закоммичены не раньше реализации")

    stub_at_that_time = git("show", f"{first_test}:{IMPL_PATH}")
    if stub_at_that_time is None:
        problems.append("не удалось прочитать реализацию на момент коммита с тестами")
    elif is_stub_source(stub_at_that_time):
        note(f"тесты закоммичены раньше реализации: {first_test[:8]} -> {first_impl[:8]}")
    else:
        problems.append("на момент коммита с тестами реализация уже была готова — это не TDD")
    return problems


def main() -> int:
    print("Проверка порядка TDD в части 2")
    _, test_problems = check_tests()
    problems = test_problems + check_implementation() + check_history()

    if problems:
        print("\nПроблемы:")
        for problem in problems:
            print(f"  - {problem}")
        print("\nКак исправить: docs/part2-tdd-agent.md")
        return 1

    print("\nПорядок TDD соблюдён.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
