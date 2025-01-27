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
pip3 install -r requirements.txt
```

# how to run this app?
assuming alert_threshold install in /app
```
$ cd /app/alert_threshold/;
$ source alert_threshold_env/bin/activate;
$ python3 alert_threshold_metric.py --log_dir /var/log/monitor
                                    --check_config_dir /app/alert_threshold/conf/
                                    --state_file_dir /var/lib/monitoring-weetech-ch/state
                                    --ssh_username john
                                    --ssh_port 22
                                    --ssh_private_key /app/alert_threshold/key.pem
                                    --ssh_host_script_dir /app/monscript/
                                    --alert_email_recipient root
                                    --alert_email_from john@gmail.com
                                    --alert_email_smtp_host localhost
                                    --alert_email_smtp_port 25
                                    --alert_telegram_token <my_bot_token>
                                    --alert_telegram_api_key <my_api_key>
                                    --alert_telegram_chat_id <my_chat_id>;
```

# integration alert_threshold with Jenkins
In order to run this application periodically so system admin/support can get
prompt alert, a Jenkins installation is required.
1. Ensure you have you run this app before as described in the [section](# how to run this app?) how to run this app.
2. Download and install Jenkins. This is out of topic but you should be able to
find more information [here](https://www.jenkins.io/download/).
3. Create a ![Freestyle Project](https://raw.githubusercontent.com/weetech-software/alert_threshold/refs/heads/main/docs/assets/alert_threshold_jenkins.png) and appropriate settings. The ![minimal required settings](https://raw.githubusercontent.com/weetech-software/alert_threshold/refs/heads/main/docs/assets/jenkins_alert_threshld_configuration.png):
are
3.1 `Build periodically`
3.2 `Execute Shell`
4. That's it, take a look at the console log output for any error.
