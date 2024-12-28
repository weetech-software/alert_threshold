# what is alert_threshold?
Active metrics monitoring if the monitored metric exceed a predefined threshold

# install python 3.13.0
This app require python, please install python. Python install script, see https://github.com/jasonwee/videoOnCloud/blob/master/core/install_software/python/python_3-13-0.sh

# environment setup
This application will run using python virtual environment.
```
/opt/weetech/python-3.13.0/bin/python3.13 -m venv alert_threshold_env
source alert_threshold_env/bin/activate
pip3 install --upgrade pip
```

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

