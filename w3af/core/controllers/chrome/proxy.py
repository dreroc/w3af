"""
proxy_handler.py

Copyright 2018 Andres Riancho

This file is part of w3af, http://w3af.org/ .

w3af is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation version 2 of the License.

w3af is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with w3af; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

"""
import threading

import w3af.core.controllers.output_manager as om
import w3af.core.data.kb.config as cf

from w3af.core.data.request.fuzzable_request import FuzzableRequest
from w3af.core.controllers.daemons.proxy import Proxy, ProxyHandler
from w3af.core.controllers.misc.is_private_site import is_private_site


class LoggingHandler(ProxyHandler):

    SECURITY_HEADERS = ['Strict-Transport-Security',
                        'Public-Key-Pins',
                        'Content-Security-Policy',
                        'Upgrade-Insecure-Requests']

    def _target_is_private_site(self):
        """
        :return: True if the target site w3af is scanning is a private site
                 This means that w3af is scanning:

                    http://127.0.0.1/
                    http://10.1.2.3/

                 Or a domain which resolves to a private IP address.

                 If the target is not set (this should happen only during
                 unittests) the function will return True.
        """
        targets = cf.cf.get('targets')
        if not targets:
            return True

        domain = targets[0].get_domain()
        return is_private_site(domain)

    def _send_http_request(self, http_request, grep=True):
        """
        Send a w3af HTTP request to the web server using w3af's HTTP lib,
        capture the HTTP response and send it to the upstream Queue.

        The Queue should be consumed by another part of the code, requests
        and responses should be sent to the framework for further processing.

        No error handling is performed, someone else should do that.

        :param http_request: The request to send
        :return: The response
        """
        domain = http_request.get_uri().get_domain()
        if is_private_site(domain) and not self._target_is_private_site():
            msg = ('The target site (which is in a public IP address range) is'
                   ' trying to load a resource from a private IP address range.'
                   ' For example, http://public.com/ is trying to load JavaScript,'
                   ' images or CSS from http://127.0.0.1/.\n'
                   '\n'
                   'The scanner is preventing this request to protect itself'
                   ' from SSRF attacks which might be triggered when scanning'
                   ' specially crafted sites.')
            om.out.debug(msg)
            return self._create_error_response(http_request, None, msg)

        http_response = super(LoggingHandler, self)._send_http_request(http_request, grep=grep)

        # Remove security headers to reduce runtime security
        self._remove_security_headers(http_response)

        # Send the request upstream
        fuzzable_request = FuzzableRequest.from_http_request(http_request)
        self.parent_process.queue.put((fuzzable_request, http_response))

        self.parent_process.set_first_request_response(fuzzable_request, http_response)

        # Logging for better debugging
        args = (http_request.get_uri(), self.parent_process.debugging_id)
        msg = 'Chrome proxy received HTTP response for %s (did: %s)'
        om.out.debug(msg % args)

        return http_response

    def _remove_security_headers(self, http_response):
        """
        Remove the security headers which increase the application security on
        run-time (when run by the browser). These headers are things like HSTS
        and CSP.

        We remove them in order to prevent CSP errors from blocking our tests,
        HSTS from breaking mixed content, etc.
        """
        headers = http_response.get_headers()

        for security_header in self.SECURITY_HEADERS:
            _, stored_header_name = headers.iget(security_header)

            if stored_header_name is not None:
                headers.pop(stored_header_name)


class LoggingProxy(Proxy):
    def __init__(self, ip, port, uri_opener, handler_klass=LoggingHandler,
                 ca_certs=Proxy.CA_CERT_DIR, name='LoggingProxyThread',
                 queue=None):
        """
        Override the parent init so we can save the plugin reference, all the
        rest is just the same.
        """
        super(LoggingProxy, self).__init__(ip, port, uri_opener,
                                           handler_klass=handler_klass,
                                           ca_certs=ca_certs,
                                           name=name)
        self.queue = queue
        self.debugging_id = None

        self.first_http_response = None
        self.first_http_request = None
        self.first_lock = threading.RLock()

    def set_first_request_response(self, fuzzable_request, http_response):
        with self.first_lock:
            if self.first_http_response is not None:
                return

            # I don't want to save redirects, that would mess-up the parsing
            # with DocumentParser because the base URL would be incorrect
            if http_response.get_code() in range(300, 400):
                return

            self.first_http_response = http_response
            self.first_http_request = fuzzable_request

    def get_first_response(self):
        return self.first_http_response

    def get_first_request(self):
        return self.first_http_request

    def set_debugging_id(self, debugging_id):
        self.debugging_id = debugging_id
        self.first_http_request = None
        self.first_http_response = None

    def set_traffic_queue(self, http_traffic_queue):
        self.queue = http_traffic_queue
        self.first_http_request = None
        self.first_http_response = None

    def stop(self):
        super(LoggingProxy, self).stop()
        self.set_traffic_queue(None)
        self.set_debugging_id(None)
        self.first_http_request = None
        self.first_http_response = None