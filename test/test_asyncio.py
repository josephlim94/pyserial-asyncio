#!/usr/bin/env python
#
# This file is part of pySerial-asyncio - Cross platform serial port support for Python
# (C) 2016 pySerial-team
#
# SPDX-License-Identifier:    BSD-3-Clause
"""\
Test asyncio related functionality.

To run from the command line with a specific port with a loop-back,
device connected, use:

  $ cd pyserial-asyncio
  $ python -m test.test_asyncio SERIALDEVICE

"""

import os
import unittest
import asyncio
import time
import sys

import serial_asyncio

HOST = '127.0.0.1'
_PORT = 8888

# on which port should the tests be performed:
PORT = 'socket://%s:%s' % (HOST, _PORT)


@unittest.skipIf(os.name != 'posix', "asyncio not supported on platform")
class Test_asyncio(unittest.TestCase):
    """Test asyncio related functionality"""

    def setUp(self):
        self.loop = asyncio.get_event_loop()
        # create a closed serial port

    def tearDown(self):
        self.loop.close()

    def test_asyncio(self):
        TEXT = b'Hello, World!\n'
        received = []
        actions = []

        class Input(asyncio.Protocol):

            def __init__(self):
                super().__init__()
                self._transport = None

            def connection_made(self, transport):
                self._transport = transport

            def data_received(self, data):
                self._transport.write(data)

        class Output(asyncio.Protocol):

            def __init__(self):
                super().__init__()
                self._transport = None

            def connection_made(self, transport):
                self._transport = transport
                actions.append('open')
                transport.write(TEXT)

            def data_received(self, data):
                received.append(data)
                if b'\n' in data:
                    self._transport.close()

            def connection_lost(self, exc):
                actions.append('close')
                self._transport.loop.stop()

            def pause_writing(self):
                actions.append('pause')
                print(self._transport.get_write_buffer_size())

            def resume_writing(self):
                actions.append('resume')
                print(self._transport.get_write_buffer_size())

        if PORT.startswith('socket://'):
            coro = self.loop.create_server(Input, HOST, _PORT)
            self.loop.run_until_complete(coro)

        client = serial_asyncio.create_serial_connection(self.loop, Output, PORT)
        self.loop.run_until_complete(client)
        self.loop.run_forever()
        self.assertEqual(b''.join(received), TEXT)
        self.assertEqual(actions, ['open', 'close'])

@unittest.skipIf(os.name != 'nt', "TDD for windows support")
class Test_WindowsAsyncio(unittest.TestCase):
    """Test asyncio related functionality"""

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        # get_event_loop didn't set new event loop?
        self.loop_write = asyncio.get_event_loop()
        self.loop_read = asyncio.get_event_loop()
        print("Running setup")
        # create a closed serial port

    def tearDown(self):
        self.loop_write.close()
        self.loop_read.close()
        print("Running teardown")

    def test_create_serial_connection(self):
        TEXT = b'Hello, World!\n'
        input_wrote = []
        input_received = []
        output_wrote = []
        output_received = []
        actions = []

        class Input(asyncio.Protocol):

            def __init__(self):
                super().__init__()
                self._transport = None

            def connection_made(self, transport):
                actions.append("INPUT " + 'open')
                self._transport = transport

            def data_received(self, data):
                input_received.append(data)
                self._transport.write(data)
                input_wrote.append(data)
                # wait a bit for data to be written
                #time.sleep(1)
                if b'\n' in data:
                    self._transport.close()

            def connection_lost(self, exc):
                actions.append("INPUT " + 'close')
                self._transport.loop.stop()

        class Output(asyncio.Protocol):

            def __init__(self):
                super().__init__()
                self._transport = None

            def connection_made(self, transport):
                self._transport = transport
                actions.append("OUTPUT " + 'open')
                transport.write(TEXT)
                output_wrote.append(TEXT)

            def data_received(self, data):
                output_received.append(data)
                if b'\n' in data:
                    self._transport.close()

            def connection_lost(self, exc):
                actions.append("OUTPUT " + 'close')
                self._transport.loop.stop()

            def pause_writing(self):
                actions.append("OUTPUT " + 'pause')
                print(self._transport.get_write_buffer_size())

            def resume_writing(self):
                actions.append("OUTPUT " + 'resume')
                print(self._transport.get_write_buffer_size())

        # Hard coding test ports
        PORT_WRITE = 'COM80'
        PORT_READ = 'COM81'

        client_write = serial_asyncio.create_serial_connection(self.loop_write, Output, PORT_WRITE)
        client_read = serial_asyncio.create_serial_connection(self.loop_read, Input, PORT_READ)
        # need to start the read loop first before writting, else some data will be lost
        self.loop_read.run_until_complete(client_read)
        self.loop_write.run_until_complete(client_write)
        self.loop_write.run_forever()
        self.loop_read.run_forever()
        self.assertEqual(b''.join(output_received), TEXT)
        self.assertEqual(actions, ['INPUT open', 'OUTPUT open', 'INPUT close', 'OUTPUT close'])

    def test_open_serial_connection(self):
        TEXT = b'Hello, World!\n'
        input_wrote = []
        input_received = []
        output_wrote = []
        output_received = []
        actions = []

        # Hard coding test ports
        PORT_WRITE = 'COM80'
        PORT_READ = 'COM81'
        '''
        generator1 = serial_asyncio.open_serial_connection(self.loop_write, PORT_WRITE)
        client_write_reader = None
        client_write_writer = None
        generator1.send(None)
        for it in generator1:
            print(it)
        try:
            client_write_reader, client_write_writer = generator1.send(None)
            sys.stdout.write(client_write_reader)
            sys.stdout.write(client_write_writer)
        except StopIteration:
            pass'''
        async def test_gen_write(data):
            (client_write_reader, client_write_writer) = await serial_asyncio.open_serial_connection(self.loop_write, PORT_WRITE)
            while True:
                client_write_writer.write(data)
                break

        async def test_gen_read(data_received):
            client_read_reader, client_read_writer = await serial_asyncio.open_serial_connection(self.loop_read, PORT_READ)
            while True:
                data = await client_read_reader.read(1024)
                print(data)
                data_received.append(data)
                break
        
        client_read = test_gen_read(input_received)
        client_write = test_gen_write(TEXT)
        # need to start the read loop first before writting, else some data will be lost
        self.loop_read.run_until_complete(client_read)
        self.loop_write.run_until_complete(client_write)
        self.loop_write.run_forever()
        self.loop_read.run_forever()
        self.assertEqual(b''.join(input_received), TEXT)

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        PORT = sys.argv[1]
    else:
        sys.stdout.write(__doc__)
    sys.stdout.write("Testing port: %r\n" % PORT)
    sys.argv[1:] = ['-v']
    # When this module is executed from the command-line, it runs all its tests
    unittest.main()
