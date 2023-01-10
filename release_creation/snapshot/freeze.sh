set -e
pip freeze --path ./target/$2 > $1
if [[ "$OSTYPE" == "darwin"* ]]; then
 sed -i "" "s/dbt-core==.*/& --no-binary dbt-postgres/g" $1
else
 sed -i "s/dbt-core==.*/& --no-binary dbt-postgres/g" $1
fi