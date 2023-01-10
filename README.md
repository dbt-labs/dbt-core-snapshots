# dbt-core-snapshots (beta)
*NOTE*: this is still under active development please use with caution.
## Overview
Generates snapshots (zip archives) of all python dependencies needed to install and run the verified adapters + core as Github releases. 

### Why? 
Python makes it difficult to create a shippable depdency enclosure that insures predictability at both install and run time. 

These snapshots attempt to solve for two issues:
1. An update to a dependency contains breaking changes so dbt fails at runtime.
2. An update to a dependency creates a version conflict so dbt cannot be installed. 

### How does it work?
When we (dbt Core maintainers) release a new patch version for dbt-core or another dbt-* package we will invoke  major.minor release we will generate a new release with a tag corresponding to the major.minor version. Note that the patch version *will not* match the patch version for dbt-core or any other package as it will increment with a change to any of the included python packages.  

## How to use
To use a snapshot you will need to download, unzip the archive and pass the resulting directory to pip.
```
curl -OL https://github.com/dbt-labs/dbt-core-snapshots/releases/download/1.0.2/snapshot_core_all_adapters_linux_3.8.zip
unzip snapshot_core_all_adapters_linux_3.8.zip -d snapshot_pkgs
 pip3 install \
    dbt-core~=1.0.0 \
    dbt-bigquery~=1.0.0 \
    dbt-snowflake~=1.0.0 \
    dbt-redshift~=1.0.0 \
    dbt-postgres~=1.0.0 \
    dbt-rpc~=0.1.1 \
    dbt-spark[all]~=1.0.0 \
    dbt-databricks~=1.0.0 \
    pyodbc \
    --no-index --find-links ./snapshot_pkgs
```
## Contributing
### Changing the GHA Workflow
You can test updates to the workflow on your feature branch by calling:
`gh workflow run release_snapshot.yml -f version_number=1.3.0 --ref YOUR_BRANCH`