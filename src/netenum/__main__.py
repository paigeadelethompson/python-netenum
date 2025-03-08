#!/usr/bin/env python3
import argparse
import random
import sys
from typing import List

from .core import netenum


def get_cidrs_from_stdin() -> List[str]:
    """Read CIDR ranges from stdin, one per line."""
    return [line.strip() for line in sys.stdin if line.strip()]


def main():
    parser = argparse.ArgumentParser(description="Enumerate IP addresses from CIDR ranges")
    parser.add_argument("-r", "--random", action="store_true", help="Output addresses in random order")
    args = parser.parse_args()

    try:
        cidrs = get_cidrs_from_stdin()
        if not cidrs:
            print("Error: No CIDR ranges provided. Pipe CIDR ranges to stdin, one per line.", file=sys.stderr)
            sys.exit(1)

        # If random flag is set, we still need to collect all addresses
        if args.random:
            addresses = list(netenum(cidrs))
            random.shuffle(addresses)
            for addr in addresses:
                print(addr)
        else:
            # Stream addresses directly as they're generated
            for addr in netenum(cidrs):
                print(addr, flush=True)

    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
