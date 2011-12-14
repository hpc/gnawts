# simple script that writes parameters 0-7 to $SPLUNK_HOME/bin/scripts/echo_output.txt 
echo "WHAT UP!!" >> "$SPLUNK_HOME/bin/scripts/echo_output.txt" 
echo "'$0' '$1' '$2' '$3' '$4' '$5' '$6' '$7' '$8'" >> "$SPLUNK_HOME/bin/scripts/echo_output.txt" 
