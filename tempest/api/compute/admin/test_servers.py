# Copyright 2013 IBM Corp.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from tempest.api.compute import base
from tempest.common import waiters
from tempest import config
from tempest.lib.common.utils import data_utils
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc

CONF = config.CONF


class ServersAdminTestJSON(base.BaseV2ComputeAdminTest):
    """Tests Servers API using admin privileges"""

    create_default_network = True

    @classmethod
    def setup_clients(cls):
        super(ServersAdminTestJSON, cls).setup_clients()
        cls.client = cls.os_admin.servers_client
        cls.non_admin_client = cls.servers_client

    @classmethod
    def resource_setup(cls):
        super(ServersAdminTestJSON, cls).resource_setup()

        prefix = CONF.resource_name_prefix
        cls.s1_name = data_utils.rand_name(prefix=prefix,
                                           name=cls.__name__ + '-server')
        server = cls.create_test_server(name=cls.s1_name)
        cls.s1_id = server['id']

        cls.s2_name = data_utils.rand_name(prefix=prefix,
                                           name=cls.__name__ + '-server')
        server = cls.create_test_server(name=cls.s2_name,
                                        wait_until='ACTIVE')
        cls.s2_id = server['id']
        waiters.wait_for_server_status(cls.non_admin_client,
                                       cls.s1_id, 'ACTIVE')

    @decorators.idempotent_id('06f960bb-15bb-48dc-873d-f96e89be7870')
    def test_list_servers_filter_by_error_status(self):
        """Test filtering the list of servers by server error status"""
        params = {'status': 'error'}
        self.client.reset_state(self.s1_id, state='error')
        body = self.non_admin_client.list_servers(**params)
        # Reset server's state to 'active'
        self.client.reset_state(self.s1_id, state='active')
        # Verify server's state
        server = self.client.show_server(self.s1_id)['server']
        self.assertEqual(server['status'], 'ACTIVE')
        servers = body['servers']
        # Verify error server in list result
        self.assertIn(self.s1_id, map(lambda x: x['id'], servers))
        self.assertNotIn(self.s2_id, map(lambda x: x['id'], servers))

    @decorators.idempotent_id('d56e9540-73ed-45e0-9b88-98fc419087eb')
    def test_list_servers_detailed_filter_by_invalid_status(self):
        """Test filtering the list of servers by invalid server status"""
        params = {'status': 'invalid_status'}
        if self.is_requested_microversion_compatible('2.37'):
            body = self.client.list_servers(detail=True, **params)
            servers = body['servers']
            self.assertEmpty(servers)
        else:
            self.assertRaises(lib_exc.BadRequest, self.client.list_servers,
                              detail=True, **params)

    @decorators.idempotent_id('51717b38-bdc1-458b-b636-1cf82d99f62f')
    def test_list_servers_by_admin(self):
        """Test listing servers by admin without other projects

        Listing servers by admin user returns a list which doesn't
        contain the other projects' server by default.
        """
        body = self.client.list_servers(detail=True)
        servers = body['servers']

        # This case is for the test environments which contain
        # the existing servers before testing
        servers_name = [server['name'] for server in servers]
        self.assertNotIn(self.s1_name, servers_name)
        self.assertNotIn(self.s2_name, servers_name)

    @decorators.idempotent_id('9f5579ae-19b4-4985-a091-2a5d56106580')
    def test_list_servers_by_admin_with_all_tenants(self):
        """Test listing servers by admin with all tenants

        Listing servers by admin user with all tenants parameter,
        all servers should be listed.
        """
        params = {'all_tenants': ''}
        body = self.client.list_servers(detail=True, **params)
        servers = body['servers']
        servers_name = [server['name'] for server in servers]

        self.assertIn(self.s1_name, servers_name)
        self.assertIn(self.s2_name, servers_name)

    @decorators.related_bug('1659811')
    @decorators.idempotent_id('7e5d6b8f-454a-4ba1-8ae2-da857af8338b')
    def test_list_servers_by_admin_with_specified_tenant(self):
        """Test listing servers by admin with specified project

        In nova v2, tenant_id is ignored unless all_tenants is specified.
        """
        # List the primary tenant but get nothing due to odd specified behavior
        tenant_id = self.non_admin_client.tenant_id
        params = {'tenant_id': tenant_id}
        body = self.client.list_servers(detail=True, **params)
        servers = body['servers']
        servers_name = [x['name'] for x in servers]
        self.assertNotIn(self.s1_name, servers_name)
        self.assertNotIn(self.s2_name, servers_name)

        # List the primary tenant with all_tenants is specified
        params = {'all_tenants': '', 'tenant_id': tenant_id}
        body = self.client.list_servers(detail=True, **params)
        servers = body['servers']
        servers_name = [x['name'] for x in servers]
        self.assertIn(self.s1_name, servers_name)
        self.assertIn(self.s2_name, servers_name)

        # List the admin tenant shouldn't get servers created by other tenants
        admin_tenant_id = self.client.tenant_id
        params = {'all_tenants': '', 'tenant_id': admin_tenant_id}
        body = self.client.list_servers(detail=True, **params)
        servers = body['servers']
        servers_name = [x['name'] for x in servers]
        self.assertNotIn(self.s1_name, servers_name)
        self.assertNotIn(self.s2_name, servers_name)

    @decorators.idempotent_id('86c7a8f7-50cf-43a9-9bac-5b985317134f')
    def test_list_servers_filter_by_exist_host(self):
        """Test filtering the list of servers by existent host"""
        server = self.client.show_server(self.s1_id)['server']
        hostname = server['OS-EXT-SRV-ATTR:host']
        params = {'host': hostname, 'all_tenants': '1'}
        servers = self.client.list_servers(**params)['servers']
        self.assertIn(server['id'], map(lambda x: x['id'], servers))

        nonexistent_params = {'host': 'nonexistent_host',
                              'all_tenants': '1'}
        nonexistent_body = self.client.list_servers(**nonexistent_params)
        nonexistent_servers = nonexistent_body['servers']
        self.assertNotIn(server['id'],
                         map(lambda x: x['id'], nonexistent_servers))

    @decorators.idempotent_id('ee8ae470-db70-474d-b752-690b7892cab1')
    def test_reset_state_server(self):
        """Test resetting server state to error/active"""
        # Reset server's state to 'error'
        self.client.reset_state(self.s1_id, state='error')

        # Verify server's state
        server = self.client.show_server(self.s1_id)['server']
        self.assertEqual(server['status'], 'ERROR')

        # Reset server's state to 'active'
        self.client.reset_state(self.s1_id, state='active')

        # Verify server's state
        server = self.client.show_server(self.s1_id)['server']
        self.assertEqual(server['status'], 'ACTIVE')

    @decorators.idempotent_id('682cb127-e5bb-4f53-87ce-cb9003604442')
    def test_rebuild_server_in_error_state(self):
        """Test rebuilding server in error state

        The server in error state should be rebuilt using the provided
        image and changed to ACTIVE state.
        """
        # resetting vm state require admin privilege
        self.client.reset_state(self.s1_id, state='error')
        rebuilt_server = self.non_admin_client.rebuild_server(
            self.s1_id, self.image_ref_alt)['server']
        self.addCleanup(waiters.wait_for_server_status, self.non_admin_client,
                        self.s1_id, 'ACTIVE')
        self.addCleanup(self.non_admin_client.rebuild_server, self.s1_id,
                        self.image_ref)

        # Verify the properties in the initial response are correct
        self.assertEqual(self.s1_id, rebuilt_server['id'])
        rebuilt_image_id = rebuilt_server['image']['id']
        self.assertEqual(self.image_ref_alt, rebuilt_image_id)
        self.assert_flavor_equal(self.flavor_ref, rebuilt_server['flavor'])
        waiters.wait_for_server_status(self.non_admin_client,
                                       rebuilt_server['id'], 'ACTIVE',
                                       raise_on_error=False)
        # Verify the server properties after rebuilding
        server = (self.non_admin_client.show_server(rebuilt_server['id'])
                  ['server'])
        rebuilt_image_id = server['image']['id']
        self.assertEqual(self.image_ref_alt, rebuilt_image_id)

    @decorators.idempotent_id('7a1323b4-a6a2-497a-96cb-76c07b945c71')
    def test_inject_network_info(self):
        """Test injecting network info of a server"""
        # Create a server
        server = self.create_test_server(wait_until='ACTIVE')
        # Inject the Network Info into Server
        self.client.inject_network_info(server['id'])

    @decorators.idempotent_id('fdcd9b33-0903-4e00-a1f7-b5f6543068d6')
    def test_create_server_with_scheduling_hint(self):
        """Test creating server with scheduling hint"""
        # Create a server with scheduler hints.
        hints = {
            'same_host': self.s1_id
        }
        self.create_test_server(scheduler_hints=hints,
                                wait_until='ACTIVE')


class ServersAdmin275Test(base.BaseV2ComputeAdminTest):
    """Test compute server with microversion greater than 2.75

    # NOTE(gmann): This test tests the Server APIs response schema
    # for 2.75 microversion. No specific assert or behaviour verification
    # is needed.
    """

    min_microversion = '2.75'

    @decorators.idempotent_id('bf2b4a00-73a3-4d53-81fa-acbcd97d6339')
    def test_rebuild_update_server_275(self):
        server = self.create_test_server()
        # Checking update response schema.
        self.servers_client.update_server(server['id'])
        waiters.wait_for_server_status(self.servers_client, server['id'],
                                       'ACTIVE')
        # Checking rebuild API response schema
        self.servers_client.rebuild_server(server['id'], self.image_ref_alt)
        waiters.wait_for_server_status(self.servers_client,
                                       server['id'], 'ACTIVE')
        # Checking rebuild server with admin response schema.
        self.os_admin.servers_client.rebuild_server(
            server['id'], self.image_ref)
        self.addCleanup(waiters.wait_for_server_status,
                        self.os_admin.servers_client,
                        server['id'], 'ACTIVE')
