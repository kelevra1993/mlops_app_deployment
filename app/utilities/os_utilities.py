import json
import shutil
import os
import re
import sys
from typing import List, Dict, Any, Tuple, Optional


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


def get_command_path(command_name: str) -> Optional[str]:
    """
    Finds the absolute path of a system command to be used within the MLOps pipeline scripts.

    This utility is used across deployment and infrastructure scripts (like Docker builds
    and Kubernetes deployments) to ensure that required system commands exist before
    execution, thereby preventing runtime failures in the pipeline.

    Args:
        command_name (str): The name of the command to locate (e.g., 'kubectl', 'docker').

    Returns:
        Optional[str]: The absolute path to the command if found, otherwise None.
    """
    command_path = shutil.which(cmd=command_name)
    return command_path


def extract_information_from_terraform_variables(terraform_variables_file_path: str) -> Dict[str, str]:
    """
    Extracts configuration details from the Terraform variables file.

    This function dynamically retrieves infrastructure parameters such as the zone, 
    region, reservation name, machine type, and accelerator type to configure 
    subsequent steps in the MLOps application deployment pipeline.
    
    Args:
        terraform_variables_file_path (str): The absolute path to the .tfvars file.
        
    Returns:
        Dict[str, str]: A dictionary containing the extracted keys and their corresponding values.
    """
    extracted_information = {}
    try:
        with open(terraform_variables_file_path, 'r') as terraform_variables_file:
            for line_content in terraform_variables_file:
                regex_match = re.match(r'^([a-zA-Z0-9_]+)\s*=\s*"([^"]+)"', line_content.strip())
                if regex_match:
                    key = regex_match.group(1)
                    value = regex_match.group(2)
                    extracted_information[key] = value
    except FileNotFoundError:
        print(f"❌ Error: Could not find the Terraform variables file at {terraform_variables_file_path}")
        sys.exit(1)

    if not extracted_information:
        print("❌ Error: Could not extract any information from the Terraform variables file.")
        sys.exit(1)

    return extracted_information
