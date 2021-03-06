# Copyright 2011 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import boto
import datetime
import multiprocessing
import platform
import os
import sys
import time
import webbrowser

from boto.provider import Provider
from gslib.command import Command
from gslib.command import COMMAND_NAME
from gslib.command import COMMAND_NAME_ALIASES
from gslib.command import CONFIG_REQUIRED
from gslib.command import FILE_URIS_OK
from gslib.command import MAX_ARGS
from gslib.command import MIN_ARGS
from gslib.command import PROVIDER_URIS_OK
from gslib.command import SUPPORTED_SUB_ARGS
from gslib.command import URIS_START_ARG
from gslib.exception import CommandException
from gslib import command
from gslib import wildcard_iterator
from gslib.util import HAVE_OAUTH2
from gslib.util import ONE_MB

try:
  from oauth2_plugin import oauth2_helper
except ImportError:
  pass

GOOG_API_CONSOLE_URI = "http://code.google.com/apis/console"

SCOPE_FULL_CONTROL = 'https://www.googleapis.com/auth/devstorage.full_control'
SCOPE_READ_WRITE = 'https://www.googleapis.com/auth/devstorage.read_write'
SCOPE_READ_ONLY = 'https://www.googleapis.com/auth/devstorage.read_only'

CONFIG_PRELUDE_CONTENT = """
# This file contains credentials and other configuration information needed
# by the boto library, used by gsutil. You can edit this file (e.g., to add
# credentials) but be careful not to mis-edit any of the variable names (like
# "gs_access_key_id") or remove important markers (like the "[Credentials]" and
# "[Boto]" section delimeters).
#
"""

# Default number of OS processes and Python threads for parallel operations.
# On Linux systems we automatically scale the number of processes to match 
# the underlying CPU/core count. Given we'll be running multiple concurrent 
# processes on a typical multi-core Linux computer, to avoid being too 
# aggresive with resources, the default number of threads is reduced from 
# the previous value of 24 to 10.
# On Windows and Mac systems parallel multiprocessing and multithreading
# in Python presents various challenges so we retain compaibility with 
# the established parallel mode operation, i.e. one process and 24 threads.
if platform.system() == 'Linux':
  DEFAULT_PARALLEL_PROCESS_COUNT = multiprocessing.cpu_count()
  DEFAULT_PARALLEL_THREAD_COUNT = 10
else:
  DEFAULT_PARALLEL_PROCESS_COUNT = 1
  DEFAULT_PARALLEL_THREAD_COUNT = 24

CONFIG_BOTO_SECTION_CONTENT = """
[Boto]

# To use a proxy, edit and uncomment the proxy and proxy_port lines. If you
# need a user/password with this proxy, edit and uncomment those lines as well.
#proxy = <proxy host>
#proxy_port = <proxy port>
#proxy_user = <your proxy user name>
#proxy_pass = <your proxy password>

# The following two options control the use of a secure transport for requests
# to S3 and Google Cloud Storage. It is highly recommended to set both options
# to True in production environments, especially when using OAuth2 bearer token
# authentication with Google Cloud Storage.

# Set 'is_secure' to False to cause boto to connect using HTTP instead of the
# default HTTPS. This is useful if you want to capture/analyze traffic
# (e.g., with tcpdump). This option should always be set to True in production
# environments.
#is_secure = False

# Set 'https_validate_certificates' to False to disable server certificate
# checking. This is useful if you want to capture/analyze traffic using an
# intercepting proxy. This option should always be set to True in production
# environments.
# In gsutil, the default for this option is True. *However*, the default for
# this option in the boto library itself is currently 'False'; it is therefore
# recommended to always set this option explicitly to True in configuration
# files.
https_validate_certificates = True

# 'debug' controls the level of debug messages printed: 0 for none, 1
# for basic boto debug, 2 for all boto debug plus HTTP requests/responses.
# Note: 'gsutil -d' sets debug to 2 for that one command run.
#debug = <0, 1, or 2>

# 'num_retries' controls the number of retry attempts made when errors occur.
# The default is 6. Note: don't set this value to 0, as it will cause boto to
# fail when reusing HTTP connections.
#num_retries = <integer value>
"""

CONFIG_INPUTLESS_GSUTIL_SECTION_CONTENT = """
[GSUtil]

# 'resumable_threshold' specifies the smallest file size [bytes] for which
# resumable Google Cloud Storage transfers are attempted. The default is 1048576
# (1MB).
#resumable_threshold = %(resumable_threshold)d

# 'resumable_tracker_dir' specifies the base location where resumable
# transfer tracker files are saved. By default they're in ~/.gsutil
#resumable_tracker_dir = <file path>

# 'parallel_process_count' and 'parallel_thread_count' specify the number 
# of OS processes and Python threads, respectively, to use when executing 
# operations in parallel. The default settings should work well as configured, 
# however, to enhance performance for transfers involving large numbers of 
# files, you may experiment with hand tuning these values to optimize 
# performance for your particular system configuration. 
# MacOS and Windows users should see
# http://code.google.com/p/gsutil/issues/detail?id=78 before attempting
# to experiment with these values.
#parallel_process_count = %(parallel_process_count)d
#parallel_thread_count = %(parallel_thread_count)d
""" % {'resumable_threshold': ONE_MB,
       'parallel_process_count': DEFAULT_PARALLEL_PROCESS_COUNT,
       'parallel_thread_count': DEFAULT_PARALLEL_THREAD_COUNT}

CONFIG_OAUTH2_CONFIG_CONTENT = """
[OAuth2]
# This section specifies options used with OAuth2 authentication.

# 'token_cache' specifies how the OAuth2 client should cache access tokens.
# Valid values are:
#  'in_memory': an in-memory cache is used. This is only useful if the boto
#      client instance (and with it the OAuth2 plugin instance) persists
#      across multiple requests.
#  'file_system' : access tokens will be cached in the file system, in files
#      whose names include a key derived from the refresh token the access token
#      based on.
# The default is 'file_system'.
#token_cache = file_system
#token_cache = in_memory

# 'token_cache_path_pattern' specifies a path pattern for token cache files.
# This option is only relevant if token_cache = file_system.
# The value of this option should be a path, with place-holders '%(key)s' (which
# will be replaced with a key derived from the refresh token the cached access
# token was based on), and (optionally), %(uid)s (which will be replaced with
# the UID of the current user, if available via os.getuid()).
# Note that the config parser itself interpolates '%' placeholders, and hence
# the above placeholders need to be escaped as '%%(key)s'.
# The default value of this option is
#  token_cache_path_pattern = <tmpdir>/oauth2client-tokencache.%%(uid)s.%%(key)s
# where <tmpdir> is the system-dependent default temp directory.

# The following options specify the OAuth2 client identity and secret that is
# used when requesting and using OAuth2 tokens. If not specified, a default
# OAuth2 client for the gsutil tool is used; for uses of the boto library (with
# OAuth2 authentication plugin) in other client software, it is recommended to
# use a tool/client-specific OAuth2 client. For more information on OAuth2, see
# http://code.google.com/apis/accounts/docs/OAuth2.html
#client_id = <OAuth2 client id>
#client_secret = <OAuth2 client secret>

# The following options specify the label and endpoint URIs for the OAUth2
# authorization provider being used. Primarily useful for tool developers.
#provider_label = Google
#provider_authorization_uri = https://accounts.google.com/o/oauth2/auth
#provider_token_uri = https://accounts.google.com/o/oauth2/token
"""

CONFIG_COMMAND_HELP = """
Help on the gsutil config command:
  gsutil [-D] config [OPTION]

  The gsutil config command obtains access credentials for Google Cloud Storage,
  and writes a boto/gsutil configuration file with the obtained credentials.

  Unless specified otherwise, the configuration file is written to the default
  config file path '%s'. If the default config file already exists, an attempt
  is made to rename the existing file to a backup file '%s'; if that attempt
  fails the command will exit.

  A different destination file can be specified with the -o <file> option (use
  '-o -' to write the config to standard output). If the specified file already
  exists, the command will fail.

  By default, gsutil config obtains OAuth2 tokens as follows (for background
  on OAuth2, see http://code.google.com/apis/accounts/docs/OAuth2.html):
  The command asks the user to open a web broswer to a URL for Google's
  OAuth2 authorization page. In the browser, the user will be asked to sign
  into the user's Google Account, unless already signed in. The user is then
  prompted to authorize gsutil to access the user's Google Cloud Storage account
  on the user's behalf. If the user approves the request, a verification
  code is shown. The gsutil config command prompts for this verification
  code, which is used to obtain an OAuth2 token that is written to the
  configuration file.

  The -b option can be used to instruct gsutil config to launch a browser,
  (using python's webbrowser module) to navigate to Google's OAuth2
  authorization page.  Note that this will probably not work as expected
  if you are running gsutil from an ssh window, or using gsutil on Windows.

  The -r, -w, -f options cause gsutil config to request a token with restricted
  scope; the resulting token will be restricted to read-only operations,
  read-write operation, or all operations (including getacl/setacl/
  getdefacl/setdefacl/disablelogging/enablelogging/getlogging operations).  
  In addition, -s <scope> can be used to request additional 
  (non-Google-Storage) scopes.

  If no explicit scope option is given, -f (full control) is assumed by default.

  The -a option can be used to prompt for Google Cloud Storage access key and
  secret instead.

  Options:
    -h          Print this help.
    -a          Prompt for Google Cloud Storage access key and secret instead of
                obtaining an OAuth2 token.
    -b          Launch browser to obtain OAuth2 approval and project ID instead
                of showing the URL and asking user to open the browser.
    -f          Request token with full-control access (default).
    -o <file>   Write the configuration to <file> (use '-' for stdout)
    -r          Request token restricted to read-only access.
    -s <scope>  Request additional OAuth2 <scope>.
    -w          Request token restricted to read-write access.

"""

class ConfigCommand(Command):
  """Implementation of gsutil config command."""

  # Command specification (processed by parent class).
  command_spec = {
    # Name of command.
    COMMAND_NAME : 'config',
    # List of command name aliases.
    COMMAND_NAME_ALIASES : ['configure'],
    # Min number of args required by this command.
    MIN_ARGS : 0,
    # Max number of args required by this command, or NO_MAX.
    MAX_ARGS : 0,
    # Getopt-style string specifying acceptable sub args.
    SUPPORTED_SUB_ARGS : 'habfwrs:o:',
    # True if file URIs acceptable for this command.
    FILE_URIS_OK : False,
    # True if provider-only URIs acceptable for this command.
    PROVIDER_URIS_OK : False,
    # Index in args of first URI arg.
    URIS_START_ARG : 0,
    # True if must configure gsutil before running command.
    CONFIG_REQUIRED : False,
  }

  def _OpenConfigFile(self, file_path):
    """Creates and opens a configuration file for writing.

    The file is created with mode 0600, and attempts to open existing files will
    fail (the latter is important to prevent symlink attacks).

    It is the caller's responsibility to close the file.

    Args:
      file_path: Path of the file to be created.

    Returns:
      A writable file object for the opened file.

    Raises:
      CommandException: if an error occurred when opening the file (including
          when the file already exists).
    """
    flags = os.O_RDWR | os.O_CREAT | os.O_EXCL
    # Accommodate Windows; stolen from python2.6/tempfile.py.
    if hasattr(os, 'O_NOINHERIT'):
      flags |= os.O_NOINHERIT
    try:
      fd = os.open(file_path, flags, 0600)
    except (OSError, IOError), e:
      raise CommandException("Failed to open %s for writing: %s" %
                             (file_path, e))
    return os.fdopen(fd, "w")

  def _WriteBotoConfigFile(self, config_file, use_oauth2=True,
      launch_browser=True, oauth2_scopes=[SCOPE_FULL_CONTROL]):
    """Creates a boto config file interactively.

    Needed credentials are obtained interactively, either by asking the user for
    access key and secret, or by walking the user through the OAuth2 approval
    flow.

    Args:
      config_file: file object to which the resulting config file will be
          written.
      use_oauth2: if True, walk user through OAuth2 approval flow and produce a
          config with an oauth2_refresh_token credential. If false, ask the
          user for access key and secret.
      launch_browser: in the OAuth2 approval flow, attempt to open a browser
          window and navigate to the approval URL.
      oauth2_scopes: a list of OAuth2 scopes to request authorization for, when
          using OAuth2.
    """

    # Collect credentials
    provider_map = {'aws': 'aws', 'google': 'gs'}
    uri_map = {'aws': 's3', 'google': 'gs'}
    key_ids = {}
    sec_keys = {}
    if use_oauth2:
      oauth2_refresh_token = oauth2_helper.OAuth2ApprovalFlow(
          oauth2_helper.OAuth2ClientFromBotoConfig(boto.config),
          oauth2_scopes, launch_browser)
    else:
      got_creds = False
      for provider in provider_map:
        if provider == 'google':
          key_ids[provider] = raw_input('What is your %s access key ID? ' %
                                        provider)
          sec_keys[provider] = raw_input('What is your %s secret access key? ' %
                                         provider)
          got_creds = True
          if not key_ids[provider] or not sec_keys[provider]:
            raise CommandException(
                'Incomplete credentials provided. Please try again.')
      if not got_creds:
        raise CommandException('No credentials provided. Please try again.')

    # Write the config file prelude.
    config_file.write(CONFIG_PRELUDE_CONTENT)
    config_file.write(
        '# This file was created by gsutil version "%s"\n# at %s.\n'
        % (self.LoadVersionString(),
           datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    config_file.write('#\n# You can create additional configuration files by '
        'running\n# gsutil config [options] [-o <config-file>]\n\n\n')

    # Write the config file Credentials section.
    config_file.write('[Credentials]\n\n')
    if use_oauth2:
      config_file.write('# Google OAuth2 credentials (for "gs://" URIs):\n')
      config_file.write('# The following OAuth2 token is authorized for '
          'scope(s):\n')
      for scope in oauth2_scopes:
        config_file.write('#     %s\n' % scope)
      config_file.write('gs_oauth2_refresh_token = %s\n\n' %
          oauth2_refresh_token.refresh_token)
    else:
      config_file.write('# To add Google OAuth2 credentials ("gs://" URIs), '
          'edit and uncomment the\n# following line:\n'
          '#gs_oauth2_refresh_token = <your OAuth2 refresh token>\n\n')

    for provider in provider_map:
      key_prefix = provider_map[provider]
      uri_scheme = uri_map[provider]
      if provider in key_ids and provider in sec_keys:
        config_file.write('# %s credentials ("%s://" URIs):\n' %
                  (provider, uri_scheme))
        config_file.write('%s_access_key_id = %s\n' %
            (key_prefix, key_ids[provider]))
        config_file.write('%s_secret_access_key = %s\n' %
            (key_prefix, sec_keys[provider]))
      else:
        config_file.write('# To add %s credentials ("%s://" URIs), edit and '
                  'uncomment the\n# following two lines:\n'
                  '#%s_access_key_id = <your %s access key ID>\n'
                  '#%s_secret_access_key = <your %s secret access key>\n' %
                  (provider, uri_scheme, key_prefix, provider, key_prefix,
                   provider))
      host_key = Provider.HostKeyMap[provider]
      config_file.write('# The ability to specify an alternate storage host '
                'is primarily for cloud\n# storage service developers.\n'
                '#%s_host = <alternate storage host address>\n\n' % host_key)

    # Write the config file Boto section.
    config_file.write('%s\n' % CONFIG_BOTO_SECTION_CONTENT)

    # Write the config file GSUtil section that doesn't depend on user input.
    config_file.write(CONFIG_INPUTLESS_GSUTIL_SECTION_CONTENT)

    # Write the default API version.
    config_file.write("""
# 'default_api_version' specifies the default Google Cloud Storage API
# version to use. If not set below gsutil defaults to API version 1.
""")
    api_version = 2
    if not use_oauth2: api_version = 1

    config_file.write('default_api_version = %d\n' % api_version)

    # Write the config file GSUtil section that includes the default
    # project ID input from the user.
    if launch_browser:
      sys.stdout.write(
          'Attempting to launch a browser to open the Google API console at '
          'URL: %s\n\n'
          '[Note: due to a Python bug, you may see a spurious error message '
          '"object is not\n callable [...] in [...] Popen.__del__" which can '
          'be ignored.]\n\n' % GOOG_API_CONSOLE_URI)
      sys.stdout.write(
          'In your browser you should see the API Console. Click "Storage" and '
          'look for the value under "Identifying your project\n\n')
      if not webbrowser.open(GOOG_API_CONSOLE_URI, new=1, autoraise=True):
        sys.stdout.write(
            'Launching browser appears to have failed; please navigate a '
            'browser to the following URL:\n%s\n' % GOOG_API_CONSOLE_URI)
      # Short delay; webbrowser.open on linux insists on printing out a message
      # which we don't want to run into the prompt for the auth code.
      time.sleep(2)
    else:
      sys.stdout.write(
          '\nPlease navigate your browser to %s,\nthen click "Services" on the '
          'left side panel and ensure you have Google Cloud\nStorage'
          'activated, then click "Google Cloud Storage" on the left side '
          'panel and\nfind the "x-goog-project-id" on that page.\n' %
          GOOG_API_CONSOLE_URI)
    default_project_id = raw_input('What is your project-id? ')
    project_id_section_prelude = """
# 'default_project_id' specifies the default Google Cloud Storage project ID to
# use with the 'mb' and 'ls' commands. If defined it overrides the default value
# you set in the API Console. Either of these defaults can be overridden
# by specifying the -p option to the 'mb' and 'ls' commands.
"""
    if default_project_id:
      config_file.write('%sdefault_project_id = %s\n\n\n' %
                        (project_id_section_prelude, default_project_id))
    else:
      sys.stderr.write('No default project ID entered. You will need to edit '
                       'the default_project_id value\nin your boto config file '
                       'before using "gsutil ls gs://" or "mb" commands'
                       'with the default API version 2.\n')
      config_file.write('%s#default_project_id = <value>\n\n\n' %
                        project_id_section_prelude)

    # Write the config file OAuth2 section.
    config_file.write(CONFIG_OAUTH2_CONFIG_CONTENT)

  # Command entry point.
  def RunCommand(self):
    scopes = []
    use_oauth2 = True
    launch_browser = False
    output_file_name = None
    for opt, opt_arg in self.sub_opts:
      if opt == '-a':
        use_oauth2 = False
      elif opt == '-b':
        launch_browser = True
      elif opt == '-f':
        scopes.append(SCOPE_FULL_CONTROL)
      elif opt == '-h':
        sys.stderr.write(CONFIG_COMMAND_HELP)
        sys.exit(0)
      elif opt == '-o':
        output_file_name = opt_arg
      elif opt == '-r':
        scopes.append(SCOPE_READ_ONLY)
      elif opt == '-s':
        scopes.append(opt_arg)
      elif opt == '-w':
        scopes.append(SCOPE_READ_WRITE)

    if use_oauth2 and not HAVE_OAUTH2:
      raise CommandException(
          "OAuth2 is only supported when running under Python 2.6 or later\n"
          "(unless additional dependencies are installed, "
          "see README for details);\n"
          "you are running Python %s.\nUse 'gsutil config -a' to create a "
          "config with Developer Key authentication credentials." % sys.version)

    if not scopes:
      scopes.append(SCOPE_FULL_CONTROL)

    if output_file_name is None:
      # Use the default config file name, if it doesn't exist or can be moved
      # out of the way without clobbering an existing backup file.
      default_config_path = os.path.expanduser(os.path.join('~', '.boto'))
      if not os.path.exists(default_config_path):
        output_file_name = default_config_path
      else:
        default_config_path_bak = default_config_path + ".bak"
        if os.path.exists(default_config_path_bak):
          raise CommandException("Cannot back up existing config "
              "file '%s': backup file exists ('%s')."
              % (default_config_path, default_config_path_bak))
        else:
          try:
            sys.stderr.write(
                "Backing up existing config file '%s' to '%s'...\n"
                % (default_config_path, default_config_path_bak))
            os.rename(default_config_path, default_config_path_bak)
          except e:
            raise CommandException("Failed to back up existing config "
                "file ('%s' -> '%s'): %s."
                % (default_config_path, default_config_path_bak, e))
          output_file_name = default_config_path

    if output_file_name == '-':
      output_file = sys.stdout
    else:
      output_file = self._OpenConfigFile(output_file_name)
      sys.stderr.write(
          'This script will create a boto config file at\n%s\ncontaining your '
          'credentials, based on your responses to the following questions.\n\n'
          % output_file_name)

    try:
      self._WriteBotoConfigFile(output_file, use_oauth2=use_oauth2,
          launch_browser=launch_browser, oauth2_scopes=scopes)
    except Exception, e:
      # If an error occurred during config file creation, remove the invalid
      # config file.
      if output_file_name != '-':
        output_file.close()
        os.unlink(output_file_name)
      raise

    if output_file_name != '-':
      output_file.close()
      sys.stderr.write(
          '\nBoto config file "%s" created. If you need to use\na proxy to '
          'access the Internet please see the instructions in that file.\n'
          % output_file_name)
