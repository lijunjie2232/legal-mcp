#!/bin/bash

if [ ! -d "../data" ]; then
  mkdir ../data
fi

wget "https://laws.e-gov.go.jp/bulkdownload\?file_section\=1\&only_xml_flag\=true" -O ../data/all_xml.zip

unzip ../data/all_xml.zip -d ../data/all_xml

if [ -d "../.venv" ]; then
  source ../.venv/bin/activate
elif [ -d "../venv" ]; then
  source ../venv/bin/activate
else
  echo "Virtual environment not found!"
  exit 1
fi

python xml_to_json.py -s ../data/all_xml -d ../data/all_json -f