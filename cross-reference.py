import os
import re
import sys
import argparse
from pathlib import Path
from difflib import ndiff


class Colors:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"


def is_redirected():
    return not sys.stdout.isatty()


def parse_range(range_str):
    if "-" in range_str:
        start, end = range_str.split("-")
        return list(range(int(start), int(end) + 1))
    else:
        return [int(range_str)]


def extract_text_from_line(line):
    parts = line.split(",,")
    if len(parts) >= 2:
        return parts[-1].strip()
    return None


def normalize_text(text):
    if not text:
        return ""
    text = re.sub(r"\\N", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def find_cross_reference_pattern(line):
    match = re.search(r"CR-(\d+)-\[([0-9,\s]+)\]", line)
    if match:
        folder = match.group(1).zfill(2)
        line_numbers = [int(x.strip()) for x in match.group(2).split(",")]
        return folder, line_numbers
    return None, None


def read_ass_file(file_path):
    encodings = ["utf-8-sig", "utf-8", "latin-1", "cp1252"]
    for encoding in encodings:
        try:
            with open(file_path, "r", encoding=encoding) as f:
                return f.readlines()
        except:
            continue
    return []


def get_event_lines(file_path):
    lines = read_ass_file(file_path)
    event_lines = []
    in_events = False
    found_format = False

    for line in lines:
        if "[Events]" in line:
            in_events = True
            continue

        if in_events:
            if line.startswith("Format:"):
                found_format = True
                continue

            if found_format and (
                line.startswith("Dialogue:") or line.startswith("Comment:")
            ):
                event_lines.append(line)

    return event_lines


def get_text_from_lines(file_path, line_numbers):
    event_lines = get_event_lines(file_path)
    texts = []

    for line_num in line_numbers:
        if 1 <= line_num <= len(event_lines):
            text = extract_text_from_line(event_lines[line_num - 1])
            if text:
                texts.append(text)

    return " ".join(texts) if texts else None


def find_text_in_folder(target_folder, line_numbers):
    if not target_folder.exists() or not target_folder.is_dir():
        return None, None, None

    target_ass_files = list(target_folder.glob("*.ass"))

    for target_ass in target_ass_files:
        text = get_text_from_lines(target_ass, line_numbers)
        if text:
            return target_ass.name, text, line_numbers

    return None, None, None


def generate_colored_diff(text1, text2, use_colors=True):
    diff = list(ndiff([text1], [text2]))

    if len(diff) == 1 and diff[0].startswith("  "):
        return None

    result = []
    for line in diff:
        if line.startswith("- "):
            if use_colors:
                result.append(f"{Colors.RED}  - Source:  {line[2:]}{Colors.RESET}")
            else:
                result.append(f"  - Source:  {line[2:]}")
        elif line.startswith("+ "):
            if use_colors:
                result.append(f"{Colors.GREEN}  + Target:  {line[2:]}{Colors.RESET}")
            else:
                result.append(f"  + Target:  {line[2:]}")
        elif line.startswith("? "):
            continue

    return "\n".join(result) if result else None


def has_difference(result):
    if not result["target_file"] or not result["target_text"]:
        return False
    return normalize_text(result["text"]) != normalize_text(result["target_text"])


def process_files(base_path, folder_range):
    base_dir = Path(base_path)
    if not base_dir.exists():
        print(f"Error: Path '{base_path}' does not exist")
        sys.exit(1)

    folders_to_process = [str(f).zfill(2) for f in folder_range]
    results = []

    for folder_name in folders_to_process:
        folder = base_dir / folder_name
        if not folder.exists():
            continue

        ass_files = list(folder.glob("*.ass"))

        for ass_file in ass_files:
            event_lines = get_event_lines(ass_file)

            for line_num, line in enumerate(event_lines, 1):
                target_folder_num, target_line_numbers = find_cross_reference_pattern(
                    line
                )

                if not target_folder_num or not target_line_numbers:
                    continue

                text = extract_text_from_line(line)
                if not text:
                    continue

                target_folder = base_dir / target_folder_num
                target_file, target_text, target_lines = find_text_in_folder(
                    target_folder, target_line_numbers
                )

                results.append(
                    {
                        "folder": folder_name,
                        "file": ass_file.name,
                        "line_num": line_num,
                        "cross_ref": f"CR-{target_folder_num}-{target_line_numbers}",
                        "target_folder": target_folder_num,
                        "target_line_numbers": target_line_numbers,
                        "text": text,
                        "target_file": target_file,
                        "target_text": target_text,
                    }
                )

    return results


def filter_results(results, filter_type):
    if filter_type == "matched":
        return [
            r
            for r in results
            if r["target_file"]
            and normalize_text(r["text"]) == normalize_text(r["target_text"])
        ]
    elif filter_type == "not-found":
        return [r for r in results if not r["target_file"]]
    elif filter_type == "different":
        return [r for r in results if has_difference(r)]
    return results


def print_header_terminal():
    print()
    print(f"{Colors.BOLD}{Colors.CYAN}╔{'═' * 98}╗{Colors.RESET}")
    print(
        f"{Colors.BOLD}{Colors.CYAN}║{' ' * 35}CROSS-REFERENCE REPORT{' ' * 41}║{Colors.RESET}"
    )
    print(f"{Colors.BOLD}{Colors.CYAN}╚{'═' * 98}╝{Colors.RESET}")
    print()


def print_header_file():
    print()
    print("=" * 100)
    print(" " * 35 + "CROSS-REFERENCE REPORT")
    print("=" * 100)
    print()


def print_result_terminal(idx, result, total):
    print(
        f"{Colors.BOLD}{Colors.WHITE}┌─ Entry {idx}/{total} {('─' * (88 - len(str(idx)) - len(str(total))))}┐{Colors.RESET}"
    )
    print(f"{Colors.BOLD}{Colors.WHITE}│{Colors.RESET}")

    print(
        f"{Colors.BOLD}{Colors.WHITE}│{Colors.RESET}  {Colors.MAGENTA}Source:{Colors.RESET}"
    )
    print(
        f"{Colors.BOLD}{Colors.WHITE}│{Colors.RESET}     Folder: {Colors.CYAN}{result['folder']}{Colors.RESET}"
    )
    print(
        f"{Colors.BOLD}{Colors.WHITE}│{Colors.RESET}     File:   {Colors.CYAN}{result['file']}{Colors.RESET}"
    )
    print(
        f"{Colors.BOLD}{Colors.WHITE}│{Colors.RESET}     Line:   {Colors.CYAN}{result['line_num']}{Colors.RESET}"
    )
    print(
        f"{Colors.BOLD}{Colors.WHITE}│{Colors.RESET}     Cross Reference: {Colors.YELLOW}{result['cross_ref']}{Colors.RESET}"
    )
    print(f"{Colors.BOLD}{Colors.WHITE}│{Colors.RESET}")

    print(
        f"{Colors.BOLD}{Colors.WHITE}│{Colors.RESET}  {Colors.BLUE}Text:{Colors.RESET}"
    )
    print(
        f"{Colors.BOLD}{Colors.WHITE}│{Colors.RESET}     {Colors.DIM}\"{result['text']}\"{Colors.RESET}"
    )
    print(f"{Colors.BOLD}{Colors.WHITE}│{Colors.RESET}")

    if result["target_file"] and result["target_text"]:
        print(
            f"{Colors.BOLD}{Colors.WHITE}│{Colors.RESET}  {Colors.GREEN}Found:{Colors.RESET}"
        )
        print(
            f"{Colors.BOLD}{Colors.WHITE}│{Colors.RESET}     Folder: {Colors.CYAN}{result['target_folder']}{Colors.RESET}"
        )
        print(
            f"{Colors.BOLD}{Colors.WHITE}│{Colors.RESET}     File:   {Colors.CYAN}{result['target_file']}{Colors.RESET}"
        )
        print(
            f"{Colors.BOLD}{Colors.WHITE}│{Colors.RESET}     Lines:  {Colors.CYAN}{result['target_line_numbers']}{Colors.RESET}"
        )
        print(f"{Colors.BOLD}{Colors.WHITE}│{Colors.RESET}")
        print(
            f"{Colors.BOLD}{Colors.WHITE}│{Colors.RESET}  {Colors.BLUE}Target Text:{Colors.RESET}"
        )
        print(
            f"{Colors.BOLD}{Colors.WHITE}│{Colors.RESET}     {Colors.DIM}\"{result['target_text']}\"{Colors.RESET}"
        )
        print(f"{Colors.BOLD}{Colors.WHITE}│{Colors.RESET}")

        diff = generate_colored_diff(result["text"], result["target_text"], True)
        if diff:
            print(
                f"{Colors.BOLD}{Colors.WHITE}│{Colors.RESET}  {Colors.YELLOW}Differences:{Colors.RESET}"
            )
            for line in diff.split("\n"):
                print(f"{Colors.BOLD}{Colors.WHITE}│{Colors.RESET}  {line}")
        else:
            print(
                f"{Colors.BOLD}{Colors.WHITE}│{Colors.RESET}  {Colors.GREEN}{Colors.BOLD}  EXACT MATCH{Colors.RESET}"
            )
    else:
        print(
            f"{Colors.BOLD}{Colors.WHITE}│{Colors.RESET}  {Colors.RED}Status:{Colors.RESET}"
        )
        print(
            f"{Colors.BOLD}{Colors.WHITE}│{Colors.RESET}     {Colors.RED}{Colors.BOLD}NOT FOUND in folder {result['target_folder']}{Colors.RESET}"
        )

    print(f"{Colors.BOLD}{Colors.WHITE}│{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.WHITE}└{'─' * 98}┘{Colors.RESET}")
    print()


def print_result_file(idx, result, total):
    print(f"[Entry {idx}/{total}]")
    print()

    print(f"  Source:")
    print(f"     Folder: {result['folder']}")
    print(f"     File:   {result['file']}")
    print(f"     Line:   {result['line_num']}")
    print(f"     Cross Reference: {result['cross_ref']}")
    print()

    print(f"  Text:")
    print(f"     \"{result['text']}\"")
    print()

    if result["target_file"] and result["target_text"]:
        print(f"  Found:")
        print(f"     Folder: {result['target_folder']}")
        print(f"     File:   {result['target_file']}")
        print(f"     Lines:  {result['target_line_numbers']}")
        print()
        print(f"  Target Text:")
        print(f"     \"{result['target_text']}\"")
        print()

        diff = generate_colored_diff(result["text"], result["target_text"], False)
        if diff:
            print(f"  Differences:")
            for line in diff.split("\n"):
                print(f"  {line}")
        else:
            print(f"  Status: EXACT MATCH")
    else:
        print(f"  Status:")
        print(f"     NOT FOUND in folder {result['target_folder']}")

    print()
    print("-" * 100)
    print()


def print_summary_terminal(results, all_results):
    total = len(all_results)
    displayed = len(results)
    found = sum(1 for r in all_results if r["target_file"])
    not_found = total - found
    exact_matches = sum(
        1
        for r in all_results
        if r["target_file"]
        and normalize_text(r["text"]) == normalize_text(r["target_text"])
    )
    different = sum(1 for r in all_results if has_difference(r))

    print(f"{Colors.BOLD}{Colors.CYAN}╔{'═' * 98}╗{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}║{' ' * 42}SUMMARY{' ' * 50}║{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}╠{'═' * 98}╣{Colors.RESET}")
    print(
        f"{Colors.BOLD}{Colors.CYAN}║{Colors.RESET}  Total Entries:     {Colors.WHITE}{total:>4}{Colors.RESET}{' ' * 76}║"
    )
    print(
        f"{Colors.BOLD}{Colors.CYAN}║{Colors.RESET}  Displayed:         {Colors.WHITE}{displayed:>4}{Colors.RESET}{' ' * 76}║"
    )
    print(
        f"{Colors.BOLD}{Colors.CYAN}║{Colors.RESET}  {Colors.GREEN}Exact Matches:{Colors.RESET}     {Colors.GREEN}{exact_matches:>4}{Colors.RESET}{' ' * 76}║"
    )
    print(
        f"{Colors.BOLD}{Colors.CYAN}║{Colors.RESET}  {Colors.YELLOW}Different:{Colors.RESET}         {Colors.YELLOW}{different:>4}{Colors.RESET}{' ' * 76}║"
    )
    print(
        f"{Colors.BOLD}{Colors.CYAN}║{Colors.RESET}  {Colors.RED}Not Found:{Colors.RESET}         {Colors.RED}{not_found:>4}{Colors.RESET}{' ' * 76}║"
    )
    print(f"{Colors.BOLD}{Colors.CYAN}╚{'═' * 98}╝{Colors.RESET}")
    print()


def print_summary_file(results, all_results):
    total = len(all_results)
    displayed = len(results)
    found = sum(1 for r in all_results if r["target_file"])
    not_found = total - found
    exact_matches = sum(
        1
        for r in all_results
        if r["target_file"]
        and normalize_text(r["text"]) == normalize_text(r["target_text"])
    )
    different = sum(1 for r in all_results if has_difference(r))

    print("=" * 100)
    print(" " * 42 + "SUMMARY")
    print("=" * 100)
    print(f"  Total Entries:     {total:>4}")
    print(f"  Displayed:         {displayed:>4}")
    print(f"  Exact Matches:     {exact_matches:>4}")
    print(f"  Different:         {different:>4}")
    print(f"  Not Found:         {not_found:>4}")
    print("=" * 100)
    print()


def generate_report(results, all_results):
    redirected = is_redirected()

    if redirected:
        print_header_file()
    else:
        print_header_terminal()

    total = len(results)
    for idx, result in enumerate(results, 1):
        if redirected:
            print_result_file(idx, result, total)
        else:
            print_result_terminal(idx, result, total)

    if redirected:
        print_summary_file(results, all_results)
    else:
        print_summary_terminal(results, all_results)


def main():
    parser = argparse.ArgumentParser(
        description="Cross-reference report for .ass files with CR-XXXX-[YYY,...] patterns",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python report.py /path/to/episodes 1
  python report.py /path/to/episodes 1-5
  python report.py /path/to/episodes 1-10 --matched
  python report.py /path/to/episodes 1-10 --not-found
  python report.py /path/to/episodes 1-10 --different
  python report.py /path/to/episodes 1-10 --matched > matches.txt
  
Cross Reference Pattern:
  CR-XXXX-[YYY,...]
  Where XXXX is the target folder number (e.g., 01, 02)
  And [YYY,...] are line numbers after Format in [Events] section
  Line counting includes both Dialogue and Comment lines
        """,
    )

    parser.add_argument(
        "path", help="Path to the folder containing numbered episode folders"
    )

    parser.add_argument("range", help='Folder range to analyze (e.g., "1" or "1-5")')

    filter_group = parser.add_mutually_exclusive_group()
    filter_group.add_argument(
        "--matched", action="store_true", help="Show only exact matches"
    )
    filter_group.add_argument(
        "--not-found",
        action="store_true",
        help="Show only entries where target text was not found",
    )
    filter_group.add_argument(
        "--different",
        action="store_true",
        help="Show only entries where source and target text differ",
    )

    args = parser.parse_args()

    folder_range = parse_range(args.range)
    all_results = process_files(args.path, folder_range)

    if args.matched:
        filtered_results = filter_results(all_results, "matched")
    elif args.not_found:
        filtered_results = filter_results(all_results, "not-found")
    elif args.different:
        filtered_results = filter_results(all_results, "different")
    else:
        filtered_results = all_results

    generate_report(filtered_results, all_results)


if __name__ == "__main__":
    main()
