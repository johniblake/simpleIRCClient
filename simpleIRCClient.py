'''
A simple "echo" client written in Python.

author:  Amy Csizmar Dalal and [YOUR NAMES HERE]
CS 331, Fall 2015
date:  21 September 2015
'''
import sys, string, socket, time, os
from multiprocessing import Process, Pipe

class SimpleIRCClient:
    HOST = 'irc.twitch.tv'
    PORT = 6667
    CHANNEL = None
    NICK = None
    COMMANDS = {'nick':'NICK {}', 'help':'HELP', 'motd':'MOTD', 'join':'JOIN #{}', 'quit':'QUIT'}

    def __init__(self, channel, nick=None, oauth_token=None):
        print("initializing client")

        if nick is None:
            nick = "john_blake_"
        if oauth_token is None:
            oauth_token = "91ud4nk0ab2jcdeptdhx2x02yuywa3"

        self.oauth_token = oauth_token
        self.NICK = nick
        self.CHANNEL = channel
        self.readBuffer = ""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.HOST, self.PORT))
        self.connected = False

    def _usage(self, command_token):
        print "Unrecognized command:", command_token

    def _connect_to_server(self):
        self._send('PASS oauth:{}'.format(self.oauth_token))
        self._send('NICK {}'.format(self.NICK))

    def _join_channel(self, channel, parent_conn, child_conn):
        self._send("JOIN {}".format(channel))
        self.CHANNEL = channel

    def _help_query(self):
        self._send("HELP")

    def _pong(self, server):
        self._send("PONG {}".format(server))

    def _send_user_message(self, message):
        priv_msg = "PRIVMSG "+self.CHANNEL+" :{}".format(message)
        #print temp
        self._send(priv_msg)
        self._display_own_msg(self.NICK, message)

    def _send(self, message):
        message+='\r\n'
        #print "sending message: ", message
        self.socket.send(message.encode('UTF-8'))

    def _display_user_msg(self, username, msg):
        if list(username)[0] == 'j':
            sys.stdout.write('\033[38;5;82m' + username + ': \033[0m')
        elif list(username)[0] == 'g':
            sys.stdout.write('\033[38;5;214m' + username + ': \033[0m')
        else:
            sys.stdout.write('\033[38;5;256m' + username + ': \033[0m')
        print msg

    def _display_own_msg(self, username, msg):
        if list(username)[0] == 'j':
            sys.stdout.write('\033[F\033[38;5;82m' + username + ': \033[0m')
        elif list(username)[0] == 'g':
            sys.stdout.write('\033[F\033[38;5;214m' + username + ': \033[0m')
        else:
            sys.stdout.write('\033[F\033[38;5;256m' + username + ': \033[0m')
        print msg

    def startup_and_listen(self, parent_conn, child_conn):
        self._connect_to_server()
        while True:
            self.readBuffer = self.readBuffer + self.socket.recv(1024).decode('UTF-8')
            temp = self.readBuffer.split('\n')
            self.readBuffer = temp.pop()
            child_conn.send(temp)
            self._handle_server_input(parent_conn, child_conn)
            #print "sent parent thread some data"

    def _issue_(self,user_input, parent_conn, child_conn):
        if len(user_input) > 0:
                parent_conn.send([1,user_input])
                self._parse_msg_update_client(parent_conn, child_conn)
        else:
            parent_conn.send([2,user_input])
            self._parse_msg_update_client(parent_conn, child_conn)


    def _handle_server_input(self, parent_conn, child_conn):
        server_input = parent_conn.recv()
        self._issue_(server_input, parent_conn, child_conn)



    def _parse_msg_update_client(self, parent_conn , child_conn):
        message = child_conn.recv()
        if message[0] == 2:
            parent_conn.close()
            child_conn.close()
            SystemExit(0)
        elif message[0] == 1:
            server_message = message[1]
            while True:
                for line in server_message:
                    #print line
                    line = line.rstrip()
                    line = line.split(':', 2)
                    if line[0] == 'PING ':
                        self._pong(line[1])
                        break
                    elif line[1] == 'tmi.twitch.tv 376 {} '.format(self.NICK):
                        print "Connected"
                        self.connected = True
                        self._join_channel(self.CHANNEL, parent_conn, child_conn)
                        break

                    message_description = line[1].split()

                    if len(message_description) > 1:
                        if message_description[1] == 'PRIVMSG':
                            #print "recieved message"
                            username = message_description[0].split('!')[0]
                            self._display_user_msg(username,line[2])
                            break
                break
        elif message[0] == 0:
            client_message = message[1]
            if client_message.isspace():
                usage(1)
            else:
                first_word = client_message.split()[0]
            first_char = list(first_word)[0]
            if first_char == '/':
                input_tokens = client_message.split()
                first_word = input_tokens[0]
                command_token = first_word.split('/')[1]
                command_body = ""
                if len(input_tokens) > 1:
                    command_body = input_tokens[1]
                if command_token in self.COMMANDS:
                    if command_token == 'join':
                        self._send("PART {}".format(self.CHANNEL))
                        self._join_channel(command_body, parent_conn, child_conn)
                        self.CHANNEL = command_body
                    elif command_token == 'help':
                        self._help_query()
                    elif command_token == 'nick':
                        self._usage(command_token)
                    elif command_token == 'quit':
                        self._send(command_token)

                    else:
                        self._send(command_token + command_body)
            else:
                #print client_message
                self._send_user_message(client_message)

    def _issue_command(self,user_input, parent_conn, child_conn):
        if len(user_input) > 0:
                parent_conn.send([0,user_input])
                self._parse_msg_update_client(parent_conn, child_conn)
        else:
            self._usage(user_input)


    def _handle_input(self, parent_conn, child_conn):
        user_input = parent_conn.recv()
        self._issue_command(user_input, parent_conn, child_conn)



    def _user_input_listener(self, parent_conn, child_conn):
        #print "starting input listen"
        user_input = ""
        while True:
            user_input = raw_input()
            child_conn.send(user_input)
            self._handle_input(parent_conn, child_conn)

if __name__ == '__main__':
    # Process command line args (server, port, message)
    #super unsafe, but I'm not implementing a protected login server
    username_auth = {'john_blake_':'91ud4nk0ab2jcdeptdhx2x02yuywa3', 'goodgoodlovin':'h1dch0jgcbu9ti3xa05y7mfsjihrvq'}

    user_name = raw_input("username: ")
    oauth_token = None
    channel = '#'+user_name

    if user_name in username_auth:
        oauth_token = username_auth[user_name]

    irc_client = SimpleIRCClient(channel, user_name, oauth_token)

    parent_conn, child_conn = Pipe()

    client_listen_process = Process(target = irc_client.startup_and_listen, args= (parent_conn,child_conn,))

    client_listen_process.start()
    irc_client._user_input_listener(parent_conn, child_conn)
