# What is `alert_threshold`?
Active metrics monitoring triggers an alert if the monitored metric exceeds a predefined threshold.

# Install python 3.13.0
This app requires Python. Please install Python. For the Python install script, see [here](https://github.com/jasonwee/videoOnCloud/blob/master/core/install_software/python/python_3-13-0.sh).

# Environment setup
This application will run in a Python virtual environment.
```
/opt/weetech/python-3.13.0/bin/python3.13 -m venv alert_threshold_env
source alert_threshold_env/bin/activate
pip3 install --upgrade pip
pip3 install -r requirements.txt
```

# How to run this app?
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

# Integration alert_threshold with Jenkins
In order to run this application periodically so system admin/support can get
prompt alert, a Jenkins installation is required.
1. Ensure you have you run this app before as described in the [section](# how to run this app?) how to run this app.
2. Download and install Jenkins. This is out of topic but you should be able to
find more information [here](https://www.jenkins.io/download/).
4. Create a Freestyle Project and appropriate settings. The minimal required settings are
  * `Build periodically`
  * `Execute Shell`
<img src="https://raw.githubusercontent.com/weetech-software/alert_threshold/refs/heads/main/docs/assets/alert_threshold_jenkins.png" width="250" width="250" />
<img src="https://raw.githubusercontent.com/weetech-software/alert_threshold/refs/heads/main/docs/assets/jenkins_alert_threshld_configuration.png" width="250" width="250" />
4. That's it! Take a look at the console log output for any errors. I've also created a YouTube video here to briefly describe this integration

<a href="http://www.youtube.com/watch?feature=player_embedded&v=L9Fhhnr_RiY
" target="_blank"><img src="http://img.youtube.com/vi/L9Fhhnr_RiY/0.jpg" 
alt="integration alert_threshold with Jenkins" width="240" height="180" border="10" /></a>
