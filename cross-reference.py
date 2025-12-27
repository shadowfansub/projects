import os
import re
import sys
import argparse
from pathlib import Path
from difflib import ndiff, SequenceMatcher


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


class MatchStatus:
    EXACT = "EXACT MATCH"
    SIMILAR = "SIMILAR"
    DIFFERENT = "DIFFERENT"
    NOT_FOUND = "NOT FOUND"


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


def calculate_similarity(text1, text2):
    normalized1 = normalize_text(text1)
    normalized2 = normalize_text(text2)
    return SequenceMatcher(None, normalized1, normalized2).ratio() * 100


def get_match_status(text1, text2, fuzzy_threshold):
    if not text1 or not text2:
        return MatchStatus.NOT_FOUND

    if normalize_text(text1) == normalize_text(text2):
        return MatchStatus.EXACT

    similarity = calculate_similarity(text1, text2)
    if similarity >= fuzzy_threshold:
        return MatchStatus.SIMILAR
    else:
        return MatchStatus.DIFFERENT


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


def process_files(base_path, folder_range, fuzzy_threshold):
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

                similarity = None
                status = MatchStatus.NOT_FOUND

                if target_file and target_text:
                    similarity = calculate_similarity(text, target_text)
                    status = get_match_status(text, target_text, fuzzy_threshold)

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
                        "similarity": similarity,
                        "status": status,
                    }
                )

    return results


def filter_results(results, filter_type):
    if filter_type == "matched":
        return [
            r
            for r in results
            if r["status"] in [MatchStatus.EXACT, MatchStatus.SIMILAR]
        ]
    elif filter_type == "not-found":
        return [r for r in results if r["status"] == MatchStatus.NOT_FOUND]
    elif filter_type == "different":
        return [r for r in results if r["status"] == MatchStatus.DIFFERENT]
    elif filter_type == "similar":
        return [r for r in results if r["status"] == MatchStatus.SIMILAR]
    elif filter_type == "exact":
        return [r for r in results if r["status"] == MatchStatus.EXACT]
    return results


def get_status_color(status):
    if status == MatchStatus.EXACT:
        return Colors.GREEN
    elif status == MatchStatus.SIMILAR:
        return Colors.CYAN
    elif status == MatchStatus.DIFFERENT:
        return Colors.YELLOW
    elif status == MatchStatus.NOT_FOUND:
        return Colors.RED
    return Colors.WHITE


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
    status_color = get_status_color(result["status"])

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

    if result["status"] != MatchStatus.NOT_FOUND:
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
        if result["similarity"] is not None:
            print(
                f"{Colors.BOLD}{Colors.WHITE}│{Colors.RESET}     Similarity: {status_color}{result['similarity']:.2f}%{Colors.RESET}"
            )
        print(f"{Colors.BOLD}{Colors.WHITE}│{Colors.RESET}")
        print(
            f"{Colors.BOLD}{Colors.WHITE}│{Colors.RESET}  {Colors.BLUE}Target Text:{Colors.RESET}"
        )
        print(
            f"{Colors.BOLD}{Colors.WHITE}│{Colors.RESET}     {Colors.DIM}\"{result['target_text']}\"{Colors.RESET}"
        )
        print(f"{Colors.BOLD}{Colors.WHITE}│{Colors.RESET}")

        print(
            f"{Colors.BOLD}{Colors.WHITE}│{Colors.RESET}  {status_color}Status: {result['status']}{Colors.RESET}"
        )

        if result["status"] in [MatchStatus.SIMILAR, MatchStatus.DIFFERENT]:
            diff = generate_colored_diff(result["text"], result["target_text"], True)
            if diff:
                print(f"{Colors.BOLD}{Colors.WHITE}│{Colors.RESET}")
                print(
                    f"{Colors.BOLD}{Colors.WHITE}│{Colors.RESET}  {Colors.YELLOW}Differences:{Colors.RESET}"
                )
                for line in diff.split("\n"):
                    print(f"{Colors.BOLD}{Colors.WHITE}│{Colors.RESET}  {line}")
    else:
        print(
            f"{Colors.BOLD}{Colors.WHITE}│{Colors.RESET}  {status_color}Status: {result['status']} in folder {result['target_folder']}{Colors.RESET}"
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

    if result["status"] != MatchStatus.NOT_FOUND:
        print(f"  Found:")
        print(f"     Folder: {result['target_folder']}")
        print(f"     File:   {result['target_file']}")
        print(f"     Lines:  {result['target_line_numbers']}")
        if result["similarity"] is not None:
            print(f"     Similarity: {result['similarity']:.2f}%")
        print()
        print(f"  Target Text:")
        print(f"     \"{result['target_text']}\"")
        print()

        print(f"  Status: {result['status']}")

        if result["status"] in [MatchStatus.SIMILAR, MatchStatus.DIFFERENT]:
            diff = generate_colored_diff(result["text"], result["target_text"], False)
            if diff:
                print()
                print(f"  Differences:")
                for line in diff.split("\n"):
                    print(f"  {line}")
    else:
        print(f"  Status: {result['status']} in folder {result['target_folder']}")

    print()
    print("-" * 100)
    print()


def print_summary_terminal(results, all_results, fuzzy_threshold):
    total = len(all_results)
    displayed = len(results)
    exact = sum(1 for r in all_results if r["status"] == MatchStatus.EXACT)
    similar = sum(1 for r in all_results if r["status"] == MatchStatus.SIMILAR)
    different = sum(1 for r in all_results if r["status"] == MatchStatus.DIFFERENT)
    not_found = sum(1 for r in all_results if r["status"] == MatchStatus.NOT_FOUND)

    print(f"{Colors.BOLD}{Colors.CYAN}╔{'═' * 98}╗{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}║{' ' * 42}SUMMARY{' ' * 50}║{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}╠{'═' * 98}╣{Colors.RESET}")
    print(
        f"{Colors.BOLD}{Colors.CYAN}║{Colors.RESET}  Fuzzy Threshold:   {Colors.WHITE}{fuzzy_threshold:>4.0f}%{Colors.RESET}{' ' * 74}║"
    )
    print(
        f"{Colors.BOLD}{Colors.CYAN}║{Colors.RESET}  Total Entries:     {Colors.WHITE}{total:>4}{Colors.RESET}{' ' * 76}║"
    )
    print(
        f"{Colors.BOLD}{Colors.CYAN}║{Colors.RESET}  Displayed:         {Colors.WHITE}{displayed:>4}{Colors.RESET}{' ' * 76}║"
    )
    print(
        f"{Colors.BOLD}{Colors.CYAN}║{Colors.RESET}  {Colors.GREEN}Exact Match:{Colors.RESET}       {Colors.GREEN}{exact:>4}{Colors.RESET}{' ' * 76}║"
    )
    print(
        f"{Colors.BOLD}{Colors.CYAN}║{Colors.RESET}  {Colors.CYAN}Similar:{Colors.RESET}           {Colors.CYAN}{similar:>4}{Colors.RESET}{' ' * 76}║"
    )
    print(
        f"{Colors.BOLD}{Colors.CYAN}║{Colors.RESET}  {Colors.YELLOW}Different:{Colors.RESET}         {Colors.YELLOW}{different:>4}{Colors.RESET}{' ' * 76}║"
    )
    print(
        f"{Colors.BOLD}{Colors.CYAN}║{Colors.RESET}  {Colors.RED}Not Found:{Colors.RESET}         {Colors.RED}{not_found:>4}{Colors.RESET}{' ' * 76}║"
    )
    print(f"{Colors.BOLD}{Colors.CYAN}╚{'═' * 98}╝{Colors.RESET}")
    print()


def print_summary_file(results, all_results, fuzzy_threshold):
    total = len(all_results)
    displayed = len(results)
    exact = sum(1 for r in all_results if r["status"] == MatchStatus.EXACT)
    similar = sum(1 for r in all_results if r["status"] == MatchStatus.SIMILAR)
    different = sum(1 for r in all_results if r["status"] == MatchStatus.DIFFERENT)
    not_found = sum(1 for r in all_results if r["status"] == MatchStatus.NOT_FOUND)

    print("=" * 100)
    print(" " * 42 + "SUMMARY")
    print("=" * 100)
    print(f"  Fuzzy Threshold:   {fuzzy_threshold:.0f}%")
    print(f"  Total Entries:     {total:>4}")
    print(f"  Displayed:         {displayed:>4}")
    print(f"  Exact Match:       {exact:>4}")
    print(f"  Similar:           {similar:>4}")
    print(f"  Different:         {different:>4}")
    print(f"  Not Found:         {not_found:>4}")
    print("=" * 100)
    print()


def generate_report(results, all_results, fuzzy_threshold):
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
        print_summary_file(results, all_results, fuzzy_threshold)
    else:
        print_summary_terminal(results, all_results, fuzzy_threshold)


def main():
    parser = argparse.ArgumentParser(
        description="Cross-reference report for .ass files with CR-XXXX-[YYY,...] patterns",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python report.py episodes/ 1
  python report.py episodes/ 1-5
  python report.py episodes/ 1-10 --threshold 95
  python report.py episodes/ 1-10 --filter matched
  python report.py episodes/ 1-10 --filter exact
  python report.py episodes/ 1-10 --filter similar --threshold 90
  python report.py episodes/ 1-10 --filter different
  python report.py episodes/ 1-10 --filter not-found
  python report.py episodes/ 1-10 --filter matched > matches.txt
  python report.py episodes/ 1-10 --fail-on-issues
  
Cross Reference Pattern:
  CR-XXXX-[YYY,...]
  Where XXXX is the target folder number (e.g., 01, 02)
  And [YYY,...] are line numbers after Format in [Events] section
  Line counting includes both Dialogue and Comment lines
  
Status Types:
  exact      - EXACT MATCH: Texts are identical
  similar    - SIMILAR: Similarity >= threshold (default 95%)
  different  - DIFFERENT: Similarity < threshold
  not-found  - NOT FOUND: Target lines not found in target folder
  matched    - Shows both exact and similar (all successful matches)
  
Exit Codes:
  0 - Success (no issues or --fail-on-issues not set)
  1 - Failure (found DIFFERENT or NOT FOUND entries when --fail-on-issues is set)
        """,
    )

    parser.add_argument(
        "path", help="Path to the folder containing numbered episode folders"
    )

    parser.add_argument("range", help='Folder range to analyze (e.g., "1" or "1-5")')

    parser.add_argument(
        "-t",
        "--threshold",
        type=float,
        default=95.0,
        metavar="PERCENT",
        help="Similarity threshold for fuzzy matching (default: 95.0)",
    )

    parser.add_argument(
        "-f",
        "--filter",
        choices=["all", "matched", "exact", "similar", "different", "not-found"],
        default="all",
        help="Filter results by status (default: all)",
    )

    parser.add_argument(
        "--fail-on-issues",
        action="store_true",
        help="Exit with code 1 if DIFFERENT or NOT FOUND entries exist",
    )

    args = parser.parse_args()

    if not 0 <= args.threshold <= 100:
        print("Error: Threshold must be between 0 and 100")
        sys.exit(1)

    folder_range = parse_range(args.range)
    all_results = process_files(args.path, folder_range, args.threshold)

    if args.filter == "all":
        filtered_results = all_results
    else:
        filtered_results = filter_results(all_results, args.filter)

    generate_report(filtered_results, all_results, args.threshold)

    if args.fail_on_issues:
        different_count = sum(
            1 for r in all_results if r["status"] == MatchStatus.DIFFERENT
        )
        not_found_count = sum(
            1 for r in all_results if r["status"] == MatchStatus.NOT_FOUND
        )

        if different_count > 0 or not_found_count > 0:
            if not is_redirected():
                print(f"{Colors.RED}{Colors.BOLD}✗ Validation failed:{Colors.RESET}")
                print(f"  {Colors.YELLOW}Different:{Colors.RESET} {different_count}")
                print(f"  {Colors.RED}Not Found:{Colors.RESET} {not_found_count}")
                print()
            sys.exit(1)
        else:
            if not is_redirected():
                print(
                    f"{Colors.GREEN}{Colors.BOLD}✓ Validation passed: All entries matched successfully{Colors.RESET}"
                )
                print()


if __name__ == "__main__":
    main()
