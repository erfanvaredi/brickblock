#!/usr/bin/env python3

import argparse
import os


def create_folders():
    folders = ["a", "b", "c"]
    for folder in folders:
        try:
            os.makedirs(folder)
            print(f"Folder '{folder}' created successfully.")
        except FileExistsError:
            print(f"Folder '{folder}' already exists.")


def main():
    parser = argparse.ArgumentParser(description="Brickblock CLI Tool")
    parser.add_argument("command", choices=["init"], help="Command to run")

    args = parser.parse_args()

    if args.command == "init":
        create_folders()


if __name__ == "__main__":
    main()
