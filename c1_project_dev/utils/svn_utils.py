import sys
import os
import string
import shutil
import subprocess
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)

def grant_acces_right(repositoty_path, username, right):
    if (not os.path.isdir(repositoty_path)) or (not username) or (not right):
        raise Exception('You must specify correct project name and user/group list, and then followed by a rights type(r|rw|d)!')

    authzfile = 'conf/authz'
    if right in ['r', 'rw']:
        '''
        cp -f "$ROOT/$PROJECT/$AUTHZFILE" /tmp/authz.$RAN
                sed -i "/$s/d" /tmp/authz.$RAN
                sed -i "/\[\/\]/a\\$s = r" /tmp/authz.$RAN
                cp -f /tmp/authz.$RAN "$ROOT/$PROJECT/$AUTHZFILE"
                rm -f /tmp/authz.$RAN

        '''
        try:
            token = datetime.utcnow().strftime('%Y%m%d%H%M%S')
            cmd = ['cp', '--force', os.path.join(repositoty_path, authzfile), '/tmp/authz.%s' % token]
            # _logger.info(' '.join(cmd))
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
            cmd = ['sed', '--in-place', '/%s/d' % username, '/tmp/authz.%s' % token]
            # _logger.info(' '.join(cmd))
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
            cmd = ['sed', '--in-place', '''/[/]/a\%s = %s''' % (username, right), '/tmp/authz.%s' % token]
            # _logger.info(' '.join(cmd))
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
            cmd = ['cp', '--force', '/tmp/authz.%s' % token, os.path.join(repositoty_path, authzfile)]
            # _logger.info(' '.join(cmd))
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
            cmd = ['rm', '--force', '/tmp/authz.%s' % token]
            # _logger.info(' '.join(cmd))
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            raise
    elif right == 'd':
        try:
            token = datetime.utcnow().strftime('%Y%m%d%H%M%S')
            cmd = ['cp', '--force', os.path.join(repositoty_path, authzfile), '/tmp/authz.%s' % token]
            # _logger.info(' '.join(cmd))
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
            cmd = ['sed', '--in-place', '/%s/d' % username, '/tmp/authz.%s' % token]
            # _logger.info(' '.join(cmd))
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
            cmd = ['cp', '--force', '/tmp/authz.%s' % token, os.path.join(repositoty_path, authzfile)]
            # _logger.info(' '.join(cmd))
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
            cmd = ['rm', '--force', '/tmp/authz.%s' % token]
            # _logger.info(' '.join(cmd))
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            raise
    else:
        raise Exception('r|w|rw')

    return





