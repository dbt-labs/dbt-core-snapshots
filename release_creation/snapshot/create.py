from typing import Dict, List, Optional, Tuple
from semantic_version import Version
import os, platform
import platform
import subprocess
import shutil

_OUTPUT_ARCHIVE_FILE_BASE = "dbt-core-all-adapters-snapshot"
_FILE_DIR = os.path.dirname(os.path.realpath(__file__))
SNAPSHOT_REQ_NAME_PREFIX = "snapshot_requirements"

def _get_local_os() -> str:
    local_sys = platform.system()
    if local_sys == "Linux":
        return "linux"
    elif local_sys == "Windows":
        return "windows"
    elif local_sys == "Darwin":
         return "mac"
    else:
        raise ValueError(f"Unsupported system {local_sys}")

def _get_extra_platforms_for_os(_os: str) -> List[str]:
    if _os == "mac":
        return ['macosx_10_9_x86_64', 'macosx_11_0_arm64']
    else:
        return ['manylinux_2_17_x86_64','manylinux2014_x86_64']


def _get_requirements_prefix(
    major_version: Optional[int], minor_version: Optional[int], is_pre: bool = False
):
    suffix = "latest"
    if is_pre:
        suffix = "pre"
    return f"v{major_version}.{minor_version}.{suffix}"


def _generate_download_command_args(
    requirements_prefix: str, is_pre: bool = False
) -> str:
    download_args = []
    if is_pre:
        download_args.append("--pre")
    download_args.append(
        f"-r {_FILE_DIR}/requirements/{requirements_prefix}.requirements.txt")
    return " ".join(download_args)


def generate_snapshot(target_version: Version) -> Dict[str, str]:
    """creates a zip archive of the python dependencies for the provided 
       semantic version

    Args:
        target_version (Version): the input version to use when determining 
        the requirements to download.

    Returns:
        Dict[str, str]: dict of generated snapshot assets, key is it's name 
                        and the value is the path to the file.
    """
    is_pre = True if target_version.prerelease else False
    requirements_prefix = _get_requirements_prefix(
        major_version=target_version.major, minor_version=target_version.minor, is_pre=is_pre
    )
    # Setup confiuration variables
    archive_path = f"{_OUTPUT_ARCHIVE_FILE_BASE}-{target_version}"
    local_os = _get_local_os()
    os_archive_path = f"{archive_path}-{local_os}"
    base_tmp_path = f"tmp/{local_os}/"
    py_version = platform.python_version()
    py_major_minor = ".".join(py_version.split(".")[:-1])
    requirements_file = f"{_FILE_DIR}/snapshot.requirements.{py_major_minor}.txt"
    py_version_tmp_path = f"{base_tmp_path}{py_major_minor}"
    py_version_archive_path = os_archive_path + f"-{py_major_minor}"

    download_cmd = _generate_download_command_args(requirements_prefix=requirements_prefix, is_pre=is_pre)
    # Download pip dependencies
    subprocess.run(
        ['sh',f"{_FILE_DIR}/download.sh", py_version_tmp_path, download_cmd, py_version], 
        check=True)
    # Check install
    subprocess.run(
        ['sh',f"{_FILE_DIR}/install.sh", _FILE_DIR, requirements_prefix, py_version_tmp_path, py_version], 
        check=True)
    # Freeze complete requirements (i.e. including transitive dependencies)
    subprocess.run(['sh',f"{_FILE_DIR}/freeze.sh", requirements_file, py_version], check=True)
    
    # Use the complete requirements to do a no-deps download (doesn't check system compatibility)
    # This allows us to download requirements for platform architectures other than the local
    extra_platforms = _get_extra_platforms_for_os(local_os)
    for extra_platform in extra_platforms:
        subprocess.run(
            ['sh',f"{_FILE_DIR}/download_no_deps.sh", 
            py_version_tmp_path, extra_platform, requirements_file],
                check=True)

    # Generate a Zip archive of required packages
    shutil.make_archive(py_version_archive_path, 'zip', py_version_tmp_path)

    assets = {}
    assets[f"snapshot_core_all_adapters_{local_os}_{py_major_minor}.zip"] = py_version_archive_path + ".zip"
    assets[f"{SNAPSHOT_REQ_NAME_PREFIX}_{py_major_minor}.txt"] = requirements_file

    return assets