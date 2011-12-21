require 'rubygems'
require 'action_mailer'

hostname = `hostname`

$DEBUG = true
$on_ceedev1 = hostname =~ /ceedev1/
$do_splunk_hpc = true if $on_ceedev1
$username = 'splunk_api'
$password = 'Zm9vYmFy'
$splunk_path = '/logs/splunk/bin'
$splunk_path = '/opt/splunk/bin' if $on_ceedev1

ActionMailer::Base.smtp_settings =
{
  :address => "mailgate.sandia.gov",
  :port    => 25,
  :domain  => "splunk-hpc.sandia.gov"
}

template_path = "/logs/splunk/etc/apps/hpc/bin/scripts/templates"
template_path = "/opt/splunk/etc/apps/hpc/bin/scripts/templates" if $on_ceedev1
ActionMailer::Base.template_root = template_path

class OomMailer < ActionMailer::Base
  def oom_error(to, user, details)
    recipients to
    from "noreply@sandia.gov"
    subject "OOM Message"
    body :details => details, :user => user
  end
end

def main
  # file path to
  debug "Starting ..."
  search   = ARGV[2]
  #filename = ARGV[7]
  debug "Search: #{search}"
  search_results = get_search_results(search)
  debug "GOT SEARCH RESULTS"
  to_email = process_search_results(search_results)
  send_email_notices(to_email)
  debug "Completed"
end

def get_search_results(search)
  debug "Getting search results...."
  splunk_search(search)
end

def send_email_notices(to_email)
  debug(to_email)
  # to_email looks like:
  # {"jtholle"=>{"rs1086"=>["6928523"]}, "meliass"=>{"rs2715"=>["6920825"], "rs2552"=>["6920825"], ...
  # {username => {host => [jobids]}}
  to_email.each do |user, data|
    # TODO skip emailing user if in "recently emailed" yaml file
    # TODO send email to "user"
    # with list of jobs
    # TODO track user in "recently emailed" yaml file

    # TODO go to real user
    email_to = ["cjsnide@sandia.gov", "jrstear@sandia.gov"]
    OomMailer.deliver_oom_error(email_to, user, data)
  end
end

def process_search_results(search_results)
  # search results 
  to_email = {}
  search_results = search_results.split("\n") unless search_results.is_a?(Array)
  search_results.each do |s|
    host, username, jobid = s.split(" ").map(&:strip)
    next if host == "host"
    next if host =~ /---/
    to_email[username] ||= {}
    to_email[username][jobid] ||= []
    to_email[username][jobid] << host
  end
  return to_email
end

# echo some debug info to the log file
def debug(msg)
  return nil unless $DEBUG
  `echo "#{time_now} DEBUG #{msg}" >> /tmp/output.txt`
end

def time_now
  now = Time.now
  now.strftime("%Y-%m-%d %H:%M:%S.#{now.to_f.to_s.split(".").last[0..2]}")
end

def splunk_search(search='oom')
  debug "searching ..."
  search += " | lookup jobstart host OUTPUT user,jobid | table host, user, jobid" if search and $do_splunk_hpc
  search ||= "oom | lookup jobstart host OUTPUT user,jobid | table host, user, jobid"
  # TODO use auth token - http://docs.splunk.com/Documentation/Splunk/4.2/Developer/RESTAuthToken
  command = "nice -n 5 #{$splunk_path}/splunk search '#{search}' -auth #{$username}:#{$password} -app hpc"
  command += " -uri https://splunk-hpc.sandia.gov:8089" if $do_splunk_hpc
  debug "Splunk Searching: #{command}"
  # get the results here
  results = `#{command}`
  if results && $?.exitstatus == 0
    return results 
  else
    return []
  end
end

main

