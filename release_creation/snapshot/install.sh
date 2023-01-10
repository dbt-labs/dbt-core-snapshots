set -e
export DBT_PSYCOPG2_NAME=psycopg2
rm -rf target
mkdir target 
pip install -r $1/requirements/$2.requirements.txt \
--no-index  \
--force-reinstall \
--find-links ./$3 \
--target ./target/$4
