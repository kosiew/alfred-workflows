#!/usr/bin/env bash

PATH=$PATH:$PRETTIER_PATH

cd /Users/kosiew/prettier-sql

pbpaste | npx prettier --parser $1 $PRETTIER_OPTIONS 2>&1
