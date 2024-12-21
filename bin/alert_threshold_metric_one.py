# this script is executed by https://jenkins.weetech.ch/view/Server%20Monitoring/job/apiServer-http-access/
# job execution once every 5minutes 
# max parent script time is 4minutes
# each individual script (this script) max time 1minute


import datetime
import email.utils
import logging
import requests
import json
import operator
import os.path
import smtplib
import subprocess
import sys
import traceback
import threading

from email.mime.text import MIMEText


logger = logging.getLogger(__name__)


# subprocess with thread, so we have timeout and this work in python2 and python3
class Command(object):
    def __init__(self, cmd, res):
        self.cmd = cmd
        self.res = res
        self.process = None

    def run(self, timeout):
        def target(res):
            self.process = subprocess.Popen(self.cmd,stdout=subprocess.PIPE, shell=True)
            stdout, stderr = self.process.communicate()
            res[0] = stdout

        thread = threading.Thread(target=target, args=(self.res,))
        thread.start()

        thread.join(timeout)
        if thread.is_alive():
            self.process.terminate()
            thread.join()
        #print self.process.returncode


# TODO, turn this into cpp app, because we want SPEED
def update_state_file(stateFile, key, value):
    """
    update the stateFile based on the key and value specified

    :param stateFile: the state file where the key and value should be written to
    :param key: the key to write into the stateFile
    :param value: the value that belong to the key to write into the stateFile
    :returns: None

    """
    try:
        with open(stateFile, 'r') as f:
            data = json.load(f)

        with open(stateFile, 'w') as f:
            data[key] = value
            json.dump(data, f, indent=3, sort_keys=True)
            f.write("\n")
    except:
        logger.exception('unable to read or write file %s', stateFile)
        # py2 does not allow message in raising new error
        raise
        

def get_current_value(stateFile, key):
    """
    return the value associated with the key in the specified stateFile

    :param stateFile: the state file where the key and value present
    :param key: the key where the value is associated with
    :returns: 0 if there is not key found in the stateFile. else return the 
              value associated with the key

    """
    try:
        count = 0
        with open(stateFile, 'r') as f:
            data = json.load(f)

            if key not in data:
                return count
            count = data[key]
        return count
    except:
        logger.exception('unable to read file %s', stateFile)
        # py2 does not allow message in raising new error
        raise


def create_state_file(stateFile, template='/home/weetech/monitoring/config/pristine.json'):
    """
    automatically create state file if it does not found in the directory
    /var/lib/monitoring-weetech-ch/state/

    :param stateFile: the state file about to be create
    :param template: the template use to create stateFile. template file can be found at /home/weetech/monitoring/config/pristine.json
    :returns: None

    """
    try:
        with open(template, 'r') as f:
            data = json.load(f)

            with open(stateFile, 'w') as sf:
                json.dump(data, sf, indent=3, sort_keys=True)
                sf.write("\n")
    except:
        logger.exception('unable to read file %s or write file %s', template, stateFile)
        raise


def get_check_configuration(url, config='/home/weetech/monitoring/config/configurations.json'):
    """
    get the check configuration from /home/weetech/monitoring/config/configurations.json,
    return configuration on first found,so url must be unique as it use to make
    comparison
  
    :param url: the url where it is found in the configurations.json
    :returns: None if not found
   
    """
    try:
        with open(config, 'r') as f:
            configurations = json.load(f)
            for config in configurations['configurations']:
                if config['check_url'] == url:
                    return config
    except:
        logger.exception('unable to read config file %s', config)
        raise

    return None


def update_record_set(url_payload, api_url='https://api.weetech.ch/monitoring/aws/route53/update-record-set'):
    """
    execute http get request to api server to change the associated recordset

    example full url with payload
    https://api.weetech.ch/monitoring/aws/route53/update-record-set?name=app.weetech.ch.&ip=1.1.1.1&ip=2.2.2.2

    :param url_payload: url_payload is the parameter require to change the record set
     example url_payload
     payload = {'name': config['aws_geo_hostname'], 'ip': config['fallback_ip']}
     payload = {'name': config['aws_geo_hostname'], 'ip': config['ip']}
    :param api_url: the url where the https get request will be made
     example api_url
     https://api.weetech.ch/monitoring/aws/route53/update-record-set
     https://api.weetech.ch/monitoring/aws/route53/update-record-set
    :returns: None if not found, but logger will save information like status code and response from api
    """

    # http://docs.python-requests.org/en/master/user/quickstart/
    r = requests.get(api_url, params=url_payload)

    logger.info('updating dns using url %s', r.url)
    logger.info('response status code %s', r.status_code)
    logger.info('response %s', r.json())

ops = {
    '<': operator.lt,
    '<=': operator.le,
    '==': operator.eq,
    '!=': operator.ne,
    '>=': operator.ge,
    '>': operator.gt
}

def cmp(arg1, op, arg2):
    operation = ops.get(op)
    return operation(arg1, arg2)

def alert(email_subject, message):
    msg = MIMEText(message)
    msg['To'] = email.utils.formataddr(('monitoring', 'root'))
    msg['From'] = email.utils.formataddr(('SMTPD', 'jenkins@api.weetech.ch'))
    msg['Subject'] = email_subject

    server = smtplib.SMTP('localhost', 25)
    #server.set_debuglevel(True)
    try:
        server.sendmail('jenkins@monitor.weetech.ch', ['root'], msg.as_string())
    finally:
        server.quit()


def check(metric, script, stateFile, value, operator, threshold_operator, alert_value, ssh_host, ops_timeout=60):
    """
    SSH to ssh_host with a max timeout specified by ops_timeout. Once ssh 
    to remote host, script will be execute. The return json will be match 
    against the metric specified. Current metric's value will be compare
    with specified value. If the value satisfy the comparison, then +1 to the
    metric in the statFile, else metrics in the stateFile is reset. 

    The metric value in the stateFile will be compare with alert_value and 
    comparison with alert_value is true, an alert is sent.
  
    :param metric: metric in the script
    :param script: mon script in remote host to execute
    :param stateFile: the stateFile that belong to this metric check, if it is not
     found, it will be automatically created, preferable state file should exists at 
     /var/lib/monitoring-weetech-ch/state/ with the file extension of json
     e.g. /var/lib/monitoring-weetech-ch/state/es1-weetech-ch-alert-threshold.json
    :param value: the value use for comparison if the alert hit the threshold
    :param operator: comparison operator use to determine if the metric's value
     exceed the specified value
    :param threshold_operator: the threshold operator use for compare with the value
    :param alert_value: the alert value
    :param ssh_host: remote host to ssh into
    :param ops_timeout: the total time in second allocated for this ssh 
     request check. Preferably less than 60seconds and default is 60. too high 
     value set, something is wrong with the app and/or network as it is slow. too low 
     value set could become an invalid timeout. remember max time this script
     run is 1minute

    :returns: None
   
    """

    if not os.path.isfile(stateFile):
        logger.warn('state file %s not exists, creating...', stateFile)
        create_state_file(stateFile, template='/home/weetech/monitoring/config/pristine.json')

    r = None
    why_trace_back = None
    why_type = None
    why_value = None


    try:
        result=[None]
        cmd = 'ssh -q -o StrictHostKeyChecking=no -p12345 -i /home/weetech/.ssh/publickey monitoring@{0} /home/weetech/monitor/scripts/{1}'.format(ssh_host, script)
        logger.debug(cmd)
        command = Command(cmd, result)
        command.run(timeout=ops_timeout)
    except: 
        why_type, why_value, why_trace_back = sys.exc_info()

    jsonString = '{{ {0} }}'.format(result[0])
    logger.debug(jsonString)
    jsonObj = json.loads(jsonString)

    if metric not in jsonObj:
        logger.error('metric {0} not found in {1} ?!'.format(metric, jsonString))
        return

    current_value = float(jsonObj[metric])
    count_metric = float(get_current_value(stateFile, metric))
    current_datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    if cmp(current_value, operator, value):
        count_metric += 1
        update_state_file(stateFile, metric, count_metric)
    else:
        update_state_file(stateFile, metric, 0)
        
    update_state_file(stateFile, 'timestamp', current_datetime)

    # read again
    count_metric = int(get_current_value(stateFile, metric))

    if cmp(count_metric, threshold_operator, alert_value):
        email_subject = 'alert_threshold - {0} - {1}:{2}/{3}'.format(ssh_host, metric, count_metric, alert_value)
        email_content = 'host         : {0}\nmetric       : {1}\nscript       : {2}\ncount_metric : {3}\nalert_value  : {4}\ntimestamp    : {5}\n'.format(ssh_host, metric, script, count_metric, alert_value, current_datetime)
        alert(email_subject, email_content)
    else:
        pass
    

if __name__ == '__main__':
    logging.basicConfig(
      level=logging.INFO,
      format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
      stream=sys.stdout,
    )

    logger.info('see unit test for usage')

