#!/usr/bin/env python3
import argparse
import ast
import io
import os
import tokenize
from pathlib import Path

DEFAULT_EXCLUDE_DIRS = {
    ".git",
    ".idea",
    ".vscode",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "venv",
    ".venv",
    "env",
    "node_modules",
    "staticfiles",
    "media",
    "migrations",
}

TEXT_EXTENSIONS = {
    ".py",
    ".html",
    ".htm",
    ".css",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".json",
    ".yml",
    ".yaml",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".env",
    ".txt",
    ".md",
    ".sql",
    ".sh",
    ".dockerfile",
    "",
}

LINE_COMMENT_PREFIXES = {
    ".js": ["//"],
    ".ts": ["//"],
    ".tsx": ["//"],
    ".jsx": ["//"],
    ".yml": ["#"],
    ".yaml": ["#"],
    ".toml": ["#"],
    ".ini": ["#", ";"],
    ".cfg": ["#", ";"],
    ".conf": ["#"],
    ".env": ["#"],
    ".sh": ["#"],
    ".sql": ["--"],
    "": ["#"],
}


def remove_python_comments_docstrings_and_blank_lines(source: str) -> str:
    source = source.replace("\ufeff", "")

    docstring_lines = get_docstring_line_numbers(source)

    filtered_lines = []

    for line_number, line in enumerate(source.splitlines(), start=1):
        if line_number in docstring_lines:
            continue

        filtered_lines.append(line)

    source_without_docstrings = "\n".join(filtered_lines)

    result_tokens = []

    try:
        tokens = tokenize.generate_tokens(
            io.StringIO(source_without_docstrings).readline
        )
    except tokenize.TokenError:
        return remove_generic_comments_and_blank_lines(source_without_docstrings, ".py")

    for token in tokens:
        if token.type == tokenize.COMMENT:
            continue

        result_tokens.append(token)

    try:
        cleaned = tokenize.untokenize(result_tokens)
    except Exception:
        cleaned = source_without_docstrings

    lines = []

    for line in cleaned.splitlines():
        if line.strip():
            lines.append(line.rstrip())

    return "\n".join(lines)


def is_probably_text_file(path: Path) -> bool:
    if path.name.lower() == "dockerfile":
        return True

    return path.suffix.lower() in TEXT_EXTENSIONS


def read_text(path: Path) -> str | None:
    for encoding in ("utf-8-sig", "utf-8", "cp1251"):
        try:
            return path.read_text(encoding=encoding).replace("\ufeff", "")
        except UnicodeDecodeError:
            continue
        except OSError:
            return None

    return None


def get_docstring_line_numbers(source: str) -> set[int]:
    source = source.replace("\ufeff", "")
    docstring_lines = set()

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return docstring_lines

    nodes = [tree]

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            nodes.append(node)

    for node in nodes:
        if not node.body:
            continue

        first_stmt = node.body[0]

        is_docstring = (
            isinstance(first_stmt, ast.Expr)
            and isinstance(first_stmt.value, ast.Constant)
            and isinstance(first_stmt.value.value, str)
        )

        if not is_docstring:
            continue

        start = getattr(first_stmt, "lineno", None)
        end = getattr(first_stmt, "end_lineno", None)

        if start is None:
            continue

        if end is None:
            end = start

        docstring_lines.update(range(start, end + 1))

    return docstring_lines


def remove_python_comments_docstrings_and_blank_lines(source: str) -> str:
    docstring_lines = get_docstring_line_numbers(source)

    filtered_lines = []

    for line_number, line in enumerate(source.splitlines(), start=1):
        if line_number in docstring_lines:
            continue

        filtered_lines.append(line)

    source_without_docstrings = "\n".join(filtered_lines)

    result_tokens = []

    try:
        tokens = tokenize.generate_tokens(
            io.StringIO(source_without_docstrings).readline
        )
    except tokenize.TokenError:
        return remove_generic_comments_and_blank_lines(source_without_docstrings, ".py")

    for token in tokens:
        if token.type == tokenize.COMMENT:
            continue

        result_tokens.append(token)

    try:
        cleaned = tokenize.untokenize(result_tokens)
    except Exception:
        cleaned = source_without_docstrings

    lines = []

    for line in cleaned.splitlines():
        if line.strip():
            lines.append(line.rstrip())

    return "\n".join(lines)


def remove_block_comments(source: str, start: str, end: str) -> str:
    result = []
    i = 0

    while i < len(source):
        start_pos = source.find(start, i)

        if start_pos == -1:
            result.append(source[i:])
            break

        result.append(source[i:start_pos])
        end_pos = source.find(end, start_pos + len(start))

        if end_pos == -1:
            break

        i = end_pos + len(end)

    return "".join(result)


def remove_generic_comments_and_blank_lines(source: str, suffix: str) -> str:
    suffix = suffix.lower()

    if suffix in {".html", ".htm"}:
        source = remove_block_comments(source, "<!--", "-->")

    if suffix in {".css", ".js", ".ts", ".tsx", ".jsx"}:
        source = remove_block_comments(source, "/*", "*/")

    prefixes = LINE_COMMENT_PREFIXES.get(suffix, [])

    lines = []

    for line in source.splitlines():
        stripped = line.strip()

        if not stripped:
            continue

        if any(stripped.startswith(prefix) for prefix in prefixes):
            continue

        lines.append(line.rstrip())

    return "\n".join(lines)


def compress_file(path: Path) -> str | None:
    source = read_text(path)

    if source is None:
        return None

    suffix = path.suffix.lower()

    if path.name.lower() == "dockerfile":
        suffix = ""

    if suffix == ".py":
        return remove_python_comments_docstrings_and_blank_lines(source)

    return remove_generic_comments_and_blank_lines(source, suffix)


def iter_project_files(directory: Path, exclude_dirs: set[str]) -> list[Path]:
    files = []

    for root, dirs, filenames in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for filename in filenames:
            file_path = Path(root) / filename

            if is_probably_text_file(file_path):
                files.append(file_path)

    return sorted(files, key=lambda p: str(p).lower())


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Сжимает директорию Django-проекта в один txt-файл: удаляет пустые строки, комментарии и docstring-и."
    )

    parser.add_argument(
        "directory",
        help="Директория проекта или модуля, которую нужно сжать.",
    )

    parser.add_argument(
        "-o",
        "--output",
        default="compressed_modules.txt",
        help="Путь к итоговому txt-файлу. По умолчанию: compressed_modules.txt",
    )

    parser.add_argument(
        "--include-migrations",
        action="store_true",
        help="Не исключать папки migrations.",
    )

    args = parser.parse_args()

    project_dir = Path(args.directory).resolve()
    output_path = Path(args.output).resolve()

    if not project_dir.exists():
        raise FileNotFoundError(f"Директория не найдена: {project_dir}")

    if not project_dir.is_dir():
        raise NotADirectoryError(f"Это не директория: {project_dir}")

    exclude_dirs = set(DEFAULT_EXCLUDE_DIRS)

    if args.include_migrations:
        exclude_dirs.discard("migrations")

    files = iter_project_files(project_dir, exclude_dirs)

    parts = []

    for file_path in files:
        if file_path.resolve() == output_path:
            continue

        compressed = compress_file(file_path)

        if compressed is None or not compressed.strip():
            continue

        relative_path = file_path.relative_to(project_dir)

        parts.append(f"# {relative_path.as_posix()}\n{compressed}\n")

    output_path.write_text("\n".join(parts), encoding="utf-8")

    print(f"Готово: {output_path}")
    print(f"Директория: {project_dir}")
    print(f"Файлов добавлено: {len(parts)}")


if __name__ == "__main__":
    main()
