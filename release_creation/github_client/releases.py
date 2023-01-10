import copy
import imp
import logging
import os
import requests
from typing import Dict, List, Optional, Set, Tuple
from semantic_version import Version
from github import Github
from github.GithubException import GithubException
from github.GitRelease import GitRelease
from github.GitReleaseAsset import GitReleaseAsset
from snapshot.create import SNAPSHOT_REQ_NAME_PREFIX

_GH_SNAPSHOT_REPO = "dbt-labs/dbt-core-snapshots"
_GH_ACCESS_TOKEN = os.environ["GH_ACCESS_TOKEN"]

logger = logging.getLogger(__name__)

def get_github_client() -> Github:
    return Github(_GH_ACCESS_TOKEN)


def get_latest_snapshot_release(input_version: str) -> Tuple[ Version, Optional[GitRelease]]:
    """Retrieve the latest release matching the major.minor and release stage
       semantic version if it exists. Ignores the patch version. 

    Args:
        input_version (str): semantic version (1.0.0.0rc, 2.3.5) to match against 

    Returns:
        Tuple[ Version, Optional[GitRelease]]: A tuple of the latest release tag 
        and the latest release itself.
    """
    gh = get_github_client()
    target_version = Version.coerce(input_version)
    latest_version = copy.copy(target_version)
    latest_version.patch = 0
    repo = gh.get_repo(_GH_SNAPSHOT_REPO)
    releases = repo.get_releases()
    latest_release = None
    for r in releases:
        release_version = Version.coerce(r.tag_name)
        if (
            release_version.major == latest_version.major
            and release_version.minor == latest_version.minor
            and release_version.prerelease == latest_version.prerelease
            and release_version.build == latest_version.build
            and release_version.patch >= latest_version.patch  # type: ignore
        ):
            latest_version = release_version
            latest_release = r
    return latest_version, latest_release    


def _get_local_snapshot_reqs(snapshot_req_path: str) -> List[str]:
    with open(snapshot_req_path) as f:
        reqs = f.read()
    return reqs.split()


def _get_gh_release_asset(release_asset: GitReleaseAsset) -> List[str]:
    resp = requests.get(release_asset.browser_download_url)
    resp.raise_for_status()
    return resp.content.decode("utf-8").split()


def _compare_reqs(snapshot_req: List[str], release_req: List[str]) -> Tuple[Set[str], Set[str]]:
    snapshot_req_set = set(snapshot_req)
    release_req_set = set(release_req)
    added_req = snapshot_req_set - release_req_set
    removed_req = release_req_set - snapshot_req_set
    return added_req, removed_req


def _diff_snapshot_requirements(
    snapshot_req_path: str, latest_release: Optional[GitRelease]
) -> str:
    # Scenarios being handled:
    # 1. No change - raise exception
    # 2. No prior patch version - Creat major.minor.0 snapshot
    # 3. New changes - generate diff
    if latest_release:
        diff_result = ""
        release_reqs = [
            _asset for _asset in latest_release.get_assets() if SNAPSHOT_REQ_NAME_PREFIX in _asset.name
        ]
        snapshot_req = _get_local_snapshot_reqs(snapshot_req_path=snapshot_req_path)
        release_req = _get_gh_release_asset(release_reqs[0])
        added, removed = _compare_reqs(snapshot_req=snapshot_req, release_req=release_req)
        if added:
            diff_result += "Added:\n* " + "\n* ".join(added) + "\n___\n"
        if removed:
            diff_result += "\nRemoved:\n* " + "\n* ".join(removed) + "\n"
        return diff_result
    else:
        return "No prior snapshot"


def create_new_release_for_version(
    release_version: Version, assets: Dict, latest_release: Optional[GitRelease]
) -> None:
    """Given an input version it creates a matching Github Release and attaches the assets
       as a ReleaseAsset

    Args:
        release_version (Version): semantic version to be used when creating the release
        assets (Dict): assets to be added to the created release where a key is the asset name
        latest_release (Optional[GitRelease]): supply if there is a prior release to be diffed against

    Raises:
        RuntimeError: _description_
        e: _description_
    """
    gh = get_github_client()
    release_tag = str(release_version)
    repo = gh.get_repo(_GH_SNAPSHOT_REPO)
    logger.info(f"Assets for release: {assets.keys()}")
    reqs_files = [x for x in assets if SNAPSHOT_REQ_NAME_PREFIX in x]

    release_body = _diff_snapshot_requirements(
        assets[reqs_files[0]], latest_release=latest_release
    )
    if not release_body:
        raise RuntimeError("New snapshot does not contain any new changes")
    created_release = repo.create_git_release(
        tag=release_tag, name="Snapshot Release", message=release_body
    )
    try:
        for asset_name, asset_path in assets.items():
            created_release.upload_asset(path=asset_path, name=asset_name)
    except Exception as e:
        created_release.delete_release()
        raise e


def add_assets_to_release(assets: Dict, latest_release: Optional[GitRelease]) -> None:
    if not latest_release:
        raise ValueError("Cannot update that which doth not exist!")
    for asset_name, asset_path in assets.items():
        try:
            latest_release.upload_asset(path=asset_path, name=asset_name)
        except GithubException as e:
            if e.status == 422:
                logger.warning("Asset already exists!")
            else:
                raise e
