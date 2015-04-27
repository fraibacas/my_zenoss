#!/bin/bash

while true
do
  for host in ucs1-vcenter.zenoss.loc solutions-vcenter.zenoss.loc perf2-vcenter.zenoss.loc
  do
     zenmodeler run -d $host
     sleep 5
  done
  sleep 60
  echo "sleeping"
done
