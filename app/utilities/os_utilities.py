import json
from typing import Dict, Any, Tuple


def print_blue(output: str, add_separators: bool = False) -> None:
    """
    Prints a string to the console in bold blue color.

    This utility is used throughout the project to highlight informational
    messages, status updates, and progress indicators during model training
    or data processing.

    Args:
        output (str): The string to be printed.
        add_separators (bool): If True, wraps the output with horizontal
            separators for better visibility.
    """
    if add_separators:
        length = max(len(line) for line in output.split("\n")) + 1
        print("\033[94m" + "\033[1m" + str(length * "-") + "\033[0m")
        print("\033[94m" + "\033[1m" + output + "\033[0m")
        print("\033[94m" + "\033[1m" + str(length * "-") + "\033[0m")
    else:
        print("\033[94m" + "\033[1m" + output + "\033[0m")


def print_green(output: str, add_separators: bool = False) -> None:
    """
    Prints a string to the console in bold green color.

    This utility is typically used to indicate successful operations, such
    as completed training iterations, saved model weights, or successful
    data extraction.

    Args:
        output (str): The string to be printed.
        add_separators (bool): If True, wraps the output with horizontal
            separators for better visibility.
    """
    if add_separators:
        length = max(len(line) for line in output.split("\n")) + 1
        print("\033[32m" + "\033[1m" + str(length * "-") + "\033[0m")
        print("\033[32m" + "\033[1m" + output + "\033[0m")
        print("\033[32m" + "\033[1m" + str(length * "-") + "\033[0m")
    else:
        print("\033[32m" + "\033[1m" + output + "\033[0m")


def print_yellow(output: str, add_separators: bool = False) -> None:
    """
    Prints a string to the console in bold yellow color.

    This utility is used for warnings or important notices that require
    user attention but are not necessarily critical failures (e.g., missing
    optional configuration fields).

    Args:
        output (str): The string to be printed.
        add_separators (bool): If True, wraps the output with horizontal
            separators for better visibility.
    """
    if add_separators:
        length = max(len(line) for line in output.split("\n")) + 1
        print("\033[93m" + "\033[1m" + str(length * "-") + "\033[0m")
        print("\033[93m" + "\033[1m" + output + "\033[0m")
        print("\033[93m" + "\033[1m" + str(length * "-") + "\033[0m")
    else:
        print("\033[93m" + "\033[1m" + output + "\033[0m")


def print_red(output: str, add_separators: bool = False) -> None:
    """
    Prints a string to the console in bold red color.

    This utility is reserved for error messages, critical failures, and
    exceptions that might halt the execution of the model or data pipeline.

    Args:
        output (str): The string to be printed.
        add_separators (bool): If True, wraps the output with horizontal
            separators for better visibility.
    """
    if add_separators:
        length = max(len(line) for line in output.split("\n")) + 1
        print("\033[91m" + "\033[1m" + str(length * "-") + "\033[0m")
        print("\033[91m" + "\033[1m" + output + "\033[0m")
        print("\033[91m" + "\033[1m" + str(length * "-") + "\033[0m")
    else:
        print("\033[91m" + "\033[1m" + output + "\033[0m")


def print_bold(output: str, add_separators: bool = False) -> None:
    """
    Prints a string to the console in bold font.

    This utility is used for general emphasis in console output, often for
    headers or key parameters in the experiment logs.

    Args:
        output (str): The string to be printed.
        add_separators (bool): If True, wraps the output with horizontal
            separators for better visibility.
    """
    if add_separators:
        length = max(len(line) for line in output.split("\n")) + 1
        print("\033[1m" + str(length * "-") + "\033[0m")
        print("\033[1m" + output + "\033[0m")
        print("\033[1m" + str(length * "-") + "\033[0m")
    else:
        print("\033[1m" + output + "\033[0m")


def print_dictionary(dictionary: Dict[str, Any], indent: int = 4) -> None:
    """
    Prints a dictionary to the console in a formatted JSON-like style.

    This utility is used to display configuration parameters, experiment
    summaries, or manifest data in a readable format during execution.

    Args:
        dictionary (Dict[str, Any]): The dictionary to be printed.
        indent (int): The number of spaces to use for indentation.
    """
    print(json.dumps(dictionary, indent=indent))
