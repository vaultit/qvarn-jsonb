#!/bin/sh

set -eu

URL="$1"

N=1000

token="$(qvarntool -a "$URL" get-token)"

for i in $(seq $N)
do
    echo -n "$i "
    qvarntool --token="$token" -a "$URL" POST /persons '{"names": ["James Bond"]}'
done
echo OK
