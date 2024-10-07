# how to run this app?
```
$ cd /app/alert_threshold/;
$ source alert_threshold_env/bin/activate;
$ python alert_threshold_metric.py --log_dir /var/log/monitor 
                                   --check_config_dir /app/alert_threshold/conf/
                                   --state_file_dir /var/lib/monitoring-weetech-ch/state
                                   --ssh_username john
                                   --ssh_port 22
                                   --ssh_private_key /app/alert_threshold/key.pem
                                   --ssh_host_script_dir /app/monscript/
                                   --alert_email_recipient root
                                   --alert_email_from john@gmail.com
                                   --alert_email_smtp_host localhost
                                   --alert_email_smtp_port 25;
```

# environment setup
```
python3.9 -m venv alert_threshold_env
source alert_threshold_env/bin/activate;
pip3 install --upgrade pip
```
