# (C) Datadog, Inc. 2013-2016
# (C) Josiah C Webb <rootkix@gmail.com> 2013
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import os

# project
from checks import AgentCheck
from utils.subprocess_output import get_subprocess_output

class PostfixCheck(AgentCheck):
    """This check provides metrics on the number of messages in a given postfix queue

    WARNING: the user that dd-agent runs as must have sudo access for the 'find' command
             sudo access is not required when running dd-agent as root (not recommended)

    example /etc/sudoers entry:
        dd-agent ALL=(postfix) NOPASSWD:/usr/bin/find /var/spool/postfix/incoming -type f
        dd-agent ALL=(postfix) NOPASSWD:/usr/bin/find /var/spool/postfix/active -type f
        dd-agent ALL=(postfix) NOPASSWD:/usr/bin/find /var/spool/postfix/deferred -type f

    YAML config options:
        "directory" - the value of 'postconf -h queue_directory'
        "queues" - the postfix mail queues you would like to get message count totals for

    Optionally we can run the check to use "postqueue -p" which is ran with set-group ID privileges
    so that the agent user can connect to Postfix daemon processes without sudo.

    Monitoring the mail queue using "postqueu" will only monitor the following queues.
    - hold
    - active
    - deferred
    Unlike using the "sudo" method, the "incoming" queue will not be moitored. Postqueue does
    not report on the "incomming" mail queue.

    http://www.postfix.org/postqueue.1.html

            postqueue gathers information for active, hold and deferred queue.

                 Each  queue entry shows the queue file ID, message size, arrival
                 time, sender, and the recipients that still need  to  be  deliv-
                 ered.  If mail could not be delivered upon the last attempt, the
                 reason for failure is shown. The queue ID string is followed  by
                 an optional status character:

                 *      The  message  is in the active queue, i.e. the message is
                        selected for delivery.

                 !      The message is in the hold queue, i.e. no further  deliv-
                        ery  attempt  will  be  made  until the mail is taken off
                        hold.

    Postfix has internal access controls that limit activities on the mail queue. By default,
    Postfix allows `anyone` to view the queue. On production systems where the Postfix installation
    maybe configured with access controls. You may need to grant the dd-agent user access to view
    the mail queue.

    postconf -e "authorized_mailq_users = dd-agent"

    http://www.postfix.org/postqueue.1.html

            authorized_mailq_users (static:anyone)
                List of users who are authorized to view the queue.

    """

    def check(self, instance):
        config = self._get_config(instance)

        directory = config['directory']
        queues = config['queues']
        tags = config['tags']

        if self.init_config.get('postqueue', False):
            self.log.debug('running the check using postqueue -p output')
            self._get_postqueue_stats(tags)
        else:
            self.log.debug('running the check in classic mode')
            self._get_queue_count(directory, queues, tags)

    def _get_config(self, instance):
        directory = instance.get('directory', None)
        queues = instance.get('queues', None)
        tags = instance.get('tags', [])
        if not queues or not directory:
            raise Exception('missing required yaml config entry')

        instance_config = {
            'directory': directory,
            'queues': queues,
            'tags': tags,
        }

        return instance_config

    def _get_postqueue_stats(self, tags):

        # get some intersting configuratin values from postconf
        pc_output, _, _ = get_subprocess_output(['postconf', 'mail_version'], self.log, False)
        postfix_version = pc_output.strip('\n').split('=')[1].strip()
        pc_output, _, _ = get_subprocess_output(['postconf', 'authorized_mailq_users'], self.log, False)
        authorized_mailq_users = pc_output.strip('\n').split('=')[1].strip()

        self.log.debug('authorized_mailq_users : %s' % authorized_mailq_users)

        output, _, _ = get_subprocess_output(['postqueue', '-p'], self.log, False)

        active_count = 0
        hold_count = 0
        deferred_count = 0

        # postque -p sample output
        '''
        root@postfix:/opt/datadog-agent/agent/checks.d# postqueue -p
        ----Queue ID----- --Size-- ---Arrival Time---- --Sender/Recipient------
        3xWyLP6Nmfz23fk        367 Tue Aug 15 16:17:33 root@postfix.devnull.home
                                                            (deferred transport)
                                                            alice@crypto.io

        3xWyD86NwZz23ff!       358 Tue Aug 15 16:12:08 root@postfix.devnull.home
                                                            (deferred transport)
                                                            bob@crypto.io

        -- 1 Kbytes in 2 Requests.
        '''

        for line in output.splitlines():
            if '*' in line:
                active_count += 1
                continue
            if '!' in line:
                hold_count += 1
                continue
            if line[0:1].isdigit():
                deferred_count += 1

        self.log.debug('Postfix Version: %s' % postfix_version)

        # Todo: add support for multiple instance by specifying a postqueue -p -c config_dir value
        self.gauge('postfix.queue.size', active_count, tags=tags + ['queue:active', 'instance:postfix'])
        self.gauge('postfix.queue.size', hold_count, tags=tags + ['queue:hold', 'instance:postfix'])
        self.gauge('postfix.queue.size', deferred_count, tags=tags + ['queue:deferred', 'instance:postfix'])

    def _get_queue_count(self, directory, queues, tags):
        for queue in queues:
            queue_path = os.path.join(directory, queue)
            if not os.path.exists(queue_path):
                raise Exception('%s does not exist' % queue_path)

            count = 0
            if os.geteuid() == 0:
                # dd-agent is running as root (not recommended)
                count = sum(len(files) for root, dirs, files in os.walk(queue_path))
            else:
                # can dd-agent user run sudo?
                test_sudo = os.system('setsid sudo -l < /dev/null')
                if test_sudo == 0:
                    # default to `root` for backward compatibility
                    postfix_user = self.init_config.get('postfix_user', 'root')
                    output, _, _ = get_subprocess_output(['sudo', '-u', postfix_user, 'find', queue_path, '-type', 'f'], self.log, False)
                    count = len(output.splitlines())
                else:
                    raise Exception('The dd-agent user does not have sudo access')

            # emit an individually tagged metric
            self.gauge('postfix.queue.size', count, tags=tags + ['queue:%s' % queue, 'instance:%s' % os.path.basename(directory)])

            # these can be retrieved in a single graph statement
            # for example:
            #     sum:postfix.queue.size{instance:postfix-2,queue:incoming,host:hostname.domain.tld}
