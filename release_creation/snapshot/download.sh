set -e
export DBT_PSYCOPG2_NAME=psycopg2
base_dir=$1
download_args=$2
rm -rf $base_dir
mkdir  -p $base_dir
python -m pip download \
 --progress-bar off \
 --prefer-binary \
 --dest $base_dir \
 --no-cache-dir \
 $download_args
