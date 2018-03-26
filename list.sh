#!/bin/sh

set -eu

URL="$1"

token="$(qvarntool -a "$URL" get-token)"
time qvarntool --token="$token" -a "$URL" GET /persons
