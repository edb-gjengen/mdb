#!/bin/bash


TMP1=$(bash -c "cd .. ; pwd ; echo \":\" ; cd .. ; pwd")
TMP2=$(echo $TMP1 | sed -e "s/ //g")

echo "Run the following to setup the python environment."
echo "export PYTHONPATH=$TMP2"
