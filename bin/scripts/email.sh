#!/bin/bash
echo "hello1" >> /tmp/output.txt
[ -s "/usr/local/rvm/scripts/rvm" ] && . "/usr/local/rvm/scripts/rvm"
export PATH=$PATH:/usr/local/rvm/bin/
export http_proxy=http://wwwproxy.sandia.gov:80
export https_proxy=http://wwwproxy.sandia.gov:80
echo "hello2" >> /tmp/output.txt
echo "hello3" >> /tmp/output.txt
# use ruby 1.8.7 and the splunk gemset
rvm use 1.8.7@splunk
echo "hello4" >> /tmp/output.txt
echo `which ruby` >> /tmp/output.txt
ruby /logs/splunk/etc/apps/hpc/bin/scripts/email.rb 2>&1 >> /tmp/output.txt
echo "hello5" >> /tmp/output.txt
