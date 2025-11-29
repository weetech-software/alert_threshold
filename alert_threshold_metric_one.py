
import datetime
import email.utils
import logging
import json
import operator
import os.path
import requests
import smtplib
import subprocess
import sys
import threading

from email.mime.text import MIMEText
from argparse import Namespace


logger = logging.getLogger(__name__)


# subprocess with thread, so we have timeout and this work in python2 and python3
class Command(object):
    def __init__(self, cmd: str, res: list[bytes], arguments: Namespace):
        self.cmd = cmd
        self.res = res
        self.arguments = arguments
        self.process: subprocess.Popen[bytes] | None = None

    def run(self, timeout: float | None):
        def target(res: list[bytes]):
            self.process = subprocess.Popen(self.cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            stdout, stderr = self.process.communicate()
            res[0] = stdout
            if stderr:
                logger.error("error is %s", stderr)
                alert_root("mon script error", f"{stderr}\n{self.cmd}\n{stdout}", self.arguments)

        thread = threading.Thread(target=target, args=(self.res,))
        thread.start()

        thread.join(timeout=timeout)
        if thread.is_alive():
            if self.process is not None:
                self.process.terminate()
            thread.join()
        #print self.process.returncode


def update_state_file(stateFile: str, key: str, value: str) -> None:
    """
    update the stateFile based on the key and value specified

    :param stateFile: the state file where the key and value should be written to
    :param key: the key to write into the stateFile
    :param value: the value that belong to the key to write into the stateFile
    :returns: None

    """
    try:
        with open(stateFile, 'r', encoding='utf-8') as f:
            data = json.load(f)

        with open(stateFile, 'w', encoding='utf-8') as f:
            data[key] = value
            json.dump(data, f, indent=3, sort_keys=True)
            f.write("\n")
    except Exception:
        logger.exception(f"unable to read or write file {stateFile}")
        raise
        

def get_current_value(stateFile: str, key: str) -> int:
    """
    return the value associated with the key in the specified stateFile

    :param stateFile: the state file where the key and value present
    :param key: the key where the value is associated with
    :returns: 0 if there is not key found in the stateFile. else return the 
              value associated with the key
    :raises:
        JSONDecodeError: If file contains invalid JSON
        OSError: If file cannot be read
    """
    try:
        count = 0
        with open(stateFile, 'r', encoding='utf-8') as f:
            data = json.load(f)

            if key not in data:
                return count
            count = data[key]
        return count
    except (OSError, json.JSONDecodeError):
        logger.exception(f"unable to read file {stateFile}")
        raise


def create_state_file(stateFile: str, template: str='conf/pristine.json') -> None:
    """
    automatically create state file if it does not found in the directory temp/

    :param stateFile: the state file about to be create
    :param template: the template use to create stateFile. template file can be found at conf/pristine.json
    :returns: None

    """
    try:
        with open(template, 'r', encoding='utf-8') as f:
            data = json.load(f)

            with open(stateFile, 'w', encoding='utf-8') as sf:
                json.dump(data, sf, indent=3, sort_keys=True)
                sf.flush()
                sf.write("\n")
    except:
        logger.exception(f"unable to read file {template} or write file {stateFile}")
        raise

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

def alert_root(email_subject, message, arguments):
    msg = MIMEText(message)
    msg['To'] = email.utils.formataddr(('monitoring', arguments.alert_email_recipient))
    msg['From'] = email.utils.formataddr(('SMTPD', arguments.alert_email_from))
    msg['Subject'] = email_subject

    server = smtplib.SMTP(arguments.alert_email_smtp_host, arguments.alert_email_smtp_port)
    #server.set_debuglevel(True)
    try:
        server.sendmail(arguments.alert_email_from, [arguments.alert_email_recipient], msg.as_string())
    finally:
        server.quit()

def alert_email(email_subject, message, arguments, recipients):
    msg = MIMEText(message)
    msg['To'] = ', '.join(recipients)
    msg['From'] = email.utils.formataddr(('SMTPD', arguments.alert_email_from))
    msg['Subject'] = email_subject

    server = smtplib.SMTP(arguments.alert_email_smtp_host, arguments.alert_email_smtp_port)
    #server.set_debuglevel(True)
    try:
        server.sendmail(arguments.alert_email_from, recipients, msg.as_string())
    finally:
        server.quit()

def alert_telegram(subject, message, arguments):
    payload = {'chat_id': arguments.alert_telegram_chat_id, 'text': subject + "\n\n" + message}
    url = 'https://api.telegram.org/{0}:{1}/sendMessage'.format(arguments.alert_telegram_token, arguments.alert_telegram_api_key)
    requests.get(url, params=payload)

def alert(alert_configs, subject, content, arguments):
    for alert_config in alert_configs:
        if alert_config['type'] == 'email':
            alert_email(subject, content, arguments, alert_config['recipients'])
        if alert_config['type'] == 'telegram':
            alert_telegram(subject, content, arguments)

def check1(check_config, ssh_host, arguments, ops_timeout=60):
    #logger.info("hi, this is check1 " + ssh_host + " " + str(check_config));
    stateFile='{0}/{1}-alert-threshold.json'.format(arguments.state_file_dir, ssh_host.replace('.', '-'))

    if not os.path.isfile(stateFile):
        logger.warn('state file %s not exists, creating...', stateFile)
        create_state_file(stateFile, template='conf/pristine.json')

    r = None
    why_trace_back = None
    why_type = None
    why_value = None

    try:
        result=[None]
        scripts=[]
        cmd = 'ssh -q -o StrictHostKeyChecking=no -p{0} -i {1} {2}@{3} "cd {4};'.format(arguments.ssh_port, arguments.ssh_private_key, arguments.ssh_username, ssh_host, arguments.ssh_host_script_dir)
        for config in check_config:
            #logger.info(config)
            cmd += './{0}; echo ""; '.format(config.script)
            scripts.append(config.script)
        cmd += '"'
        #logger.info(cmd)
        #logger.debug(cmd)
        command = Command(cmd, result, arguments)
        command.run(timeout=ops_timeout)
    except: 
        why_type, why_value, why_trace_back = sys.exc_info()
    #logger.info(result[0].decode('UTF-8'))
    results = result[0].decode('UTF-8').strip().split('\n')
    #logger.info(results)
    results = filter(None, results)
    #logger.info(len(results))
    script_results = dict(zip(scripts, results))
    #logger.info(tuple(script_results))
    #for key,value in script_results.items():
    #    logger.info("key " + key)
    #    logger.info("value " + value)

    for config in check_config:
        #logger.info("hi " + config.script)
        #logger.info(script_results[config.script])
        if config.script not in script_results:
            logger.error("expected script {0} not in script_results {1}".format(config.script, script_results))
            continue
        jsonString = '{{ {0} }}'.format(script_results[config.script])
        #logger.info(jsonString)
        try:
            jsonObj = json.loads(jsonString)
        except:
            alert_root("bad json string", jsonString, arguments)
            continue

        for metric in config.metrics:

            if metric not in jsonObj:
                logger.error('metric {0} not found in {1} ?!'.format(metric, jsonString))
            """
            try:
                float(jsonObj[metric])
            except:
                alert_root("exception alertThreshold", jsonObj[metric], arguments)
                continue
            """
            try:
                current_value = float(jsonObj.get(metric, 0))
            except ValueError:
                logger.info('value error = %s', jsonObj.get(metric))
                current_value = 0

            # rename metric
            state_file_metric = '{0}.{1}'.format(config.script.replace('.', '_'), metric.replace('.', '_'));
            #logger.info('{0}'.format(state_file_metric))

            count_metric = float(get_current_value(stateFile, state_file_metric))
            current_datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

            if cmp(current_value, config.operator, config.value):
                count_metric += 1
                update_state_file(stateFile, state_file_metric, count_metric)
            else:
                update_state_file(stateFile, state_file_metric, 0)
        
            update_state_file(stateFile, 'timestamp', current_datetime)

            # read again
            count_metric = int(get_current_value(stateFile, state_file_metric))

            if cmp(count_metric, config.threshold_operator, config.alert_value):
                email_subject = 'alertThreshold - {0} - {1}:{2}/{3}'.format(ssh_host, metric, count_metric, config.alert_value)
                email_content = 'host         : {0}\ndescription  : {6}\nmetric       : {1}\nscript       : {2}\nvalue        : {7}\ncurrent_value: {8}\ncount_metric : {3}\nalert_value  : {4}\ntimestamp    : {5}\n'.format(ssh_host, metric, config.script, count_metric, config.alert_value, current_datetime, config.description, config.value, current_value)
                alert_root(email_subject, email_content, arguments)
                alert(config.alert_methods, email_subject, email_content, arguments)
            else:
                pass

    return threading.current_thread().name + ": done"

if __name__ == '__main__':
    logging.basicConfig(
      level=logging.INFO,
      format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
      stream=sys.stdout,
    )

    logger.info('see unit test for usage')
