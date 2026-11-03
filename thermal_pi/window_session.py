"""Hold the camera service for the lifetime of a Mac viewer's SSH connection."""
import argparse
import sys
from .terminal import connect


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--demo', action='store_true')
    args = parser.parse_args()
    with connect(args.demo):
        print('THERMAL_READY', flush=True)
        sys.stdin.buffer.read()


if __name__ == '__main__':
    main()
