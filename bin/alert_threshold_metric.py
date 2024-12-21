#
# 
# check metric count in statefile if count exceed predefined threshold
#
#

# this script is executed by http://jenkins.weetech.ch:8080/
# job execution once every 5minutes
# this script max time is 4minute
# each individual script max time 1minute

import json
import glob
import logging
import multiprocessing
import os
import signal
import sys
import time
import zipfile
from threading import Thread


#from timed_compressed_rotating_file_handler import TimedCompressedRotatingFileHandler, TimedCompressedRotatingFileHandler1
from logging.handlers import TimedRotatingFileHandler
from alert_threshold_metric_one import check as threshold_check


# TODO, change logging configuration to use yaml? see https://fangpenlin.com/posts/2012/08/26/good-logging-practice-in-python/
# https://stackoverflow.com/questions/29602352/how-to-mix-logging-handlers-file-timed-and-compress-log-in-the-same-config-f
rootLogger = logging.getLogger()
rootLogger.setLevel(logging.INFO)

# Total of 11 rotated log files (10 zip) + 1 current, rotating everymight
fh = TimedRotatingFileHandler('/var/log/monitor/alert_threshold.log', when="midnight", interval=1, backupCount=10)
sh = logging.StreamHandler(sys.stdout)

formatter = logging.Formatter('%(asctime)s %(name)-12s [%(threadName)-12.12s] [%(levelname)-5.5s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
fh.setFormatter(formatter)
formatter = logging.Formatter('%(asctime)s %(name)-12s: %(levelname)-5.5s %(message)s')
sh.setFormatter(formatter)

rootLogger.addHandler(fh)
rootLogger.addHandler(sh)

logger = logging.getLogger(__name__)

def start_check(n):
    threads = []

    try:
        with open('/home/weetech/monitoring/config/configurations.json') as f:
            config_json = json.load(f)
    except:
        logger.error('invalid json detected in config')
        return
    
    if config_json == None or 'configurations' not in config_json:
        logger.error('invalid configuration file')
        return

    #  TODO move config check to a function
    for config in config_json['configurations']:
        # current thread sleep 0.1second here because of update statefile too quickly
        # in the threads causing json invalid. this is a workaround
        for x in threads:
            while x.is_alive():
                logger.info('%s is still alive %s', x.getName(),x.is_alive())
                time.sleep(0.1)
        #print config
        if 'host' not in config and 'hostFile' not in config:
            logger.error('invalid config, host or hostFile not found')
            continue
        if 'metrics' not in config:
            logger.error('invalid config, metrics not found')
            continue
        if 'script' not in config:
            logger.error('invalid config, script not found')
            continue
        if 'value' not in config:
            logger.error('invalid config, value not found')
            continue
        if 'operator' not in config:
            logger.error('invalid config, operator not found')
            continue
        if 'threshold_operator' not in config:
            logger.error('invalid config, threshold_operator not found')
            continue
        if 'alert_value' not in config:
            logger.error('invalid config, alert_value not found')
            continue

        hosts = []
        if 'host' in config:
            hosts.append(config['host'])
        elif 'hostFile' in config:
            with open(config['hostFile']) as f:
                for line in f:
                    if line.startswith('#'):
                        continue
                    hosts.append(line.strip())

        if len(hosts) == 0:
            logger.error('invalid config, empty host found')
            continue

        for host in hosts:
            for metric in config['metrics']:
                logger.debug('%s %s', host, metric)

                metric=metric
                script=config['script']
                stateFile='/var/lib/monitoring-weetech-ch/state/{0}-alert-threshold.json'.format(host.replace('.', '-'))
                value=config['value']
                operator=config['operator']
                threshold_operator=config['threshold_operator']
                alert_value=config['alert_value']
                ssh_host=host
                # 30seconds, so script has time to perform other tasks
                ops_timeout=30

                # this is for test, perhaps can remove later
                thread_name = 'check_{0}_{1}'.format(host, metric.replace('/', '_').replace('.', '_'))
                t = Thread(target = threshold_check, name=thread_name, args = (metric, script, stateFile, value, operator, threshold_operator, alert_value, ssh_host, ops_timeout))
                threads.append(t)
                t.start()

    # Start all threads
    # TODO use threadpoolexecutor and start as soon as possible, so we dont start all at once
    #for x in threads:
    #    x.start()

    # Wait for all of them to finish
    for x in threads:
        x.join()


if __name__ == '__main__':
    # perhaps dont use process, than thread?
    # thread does not have terminate, have to code differently, see
    # https://pymotw.com/2/threading/
    # https://docs.python.org/2/library/thread.html
    # https://stackoverflow.com/questions/323972/is-there-any-way-to-kill-a-thread-in-python

    # when ctrl+c , process must exit
    # https://stackoverflow.com/questions/11312525/catch-ctrlc-sigint-and-exit-multiprocesses-gracefully-in-python/11312948
    # https://stackoverflow.com/questions/11312525/catch-ctrlc-sigint-and-exit-multiprocesses-gracefully-in-python/35134329
    # http://masnun.com/2016/03/29/python-a-quick-introduction-to-the-concurrent-futures-module.html
    # http://elliothallmark.com/2016/12/23/requests-with-concurrent-futures-in-python-2-7/
    original_sigint_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
    pool = multiprocessing.Pool(1)
    signal.signal(signal.SIGINT, original_sigint_handler)
    try:
        res = pool.map_async(start_check, [4,])

        # Wait 241 seconds for start_check (+1 for thread/process initialization)
        #res.get(5) # Without the timeout this blocking call ignores all signals.
        res.get(241)

    except multiprocessing.TimeoutError:
        # it is okay timeout happen, but might need adjustment if there are many scripts and/or server load average
        pool.terminate()
        logger.info("timeout reached at %s", __file__)
    except KeyboardInterrupt:
        logger.info('Caught KeyboardInterrupt, terminating workers')
        pool.terminate()
    else:
        logger.info('start_check is done')
        pool.close()
    pool.join()

    # this code ignore sigint, hence the above code
    #p = multiprocessing.Process(target=start_check, name='start_check_scriptserver', args=(4,))
    #p.start()

    # Wait 31 seconds for start_check (+1 for thread/process initialization)
    #time.sleep(31)
    #time.sleep(5)

    # Terminate start_check
    #p.terminate()

    # Cleanup
    #p.join()
