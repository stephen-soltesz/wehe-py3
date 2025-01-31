'''
#######################################################################################################
#######################################################################################################
Copyright 2018 Northeastern University

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

#######################################################################################################
#######################################################################################################
'''

import sys, os, configparser, math, json, time, subprocess, \
    random, string, logging.handlers, socket, psutil, hashlib, scapy.all, ipaddress

import multiprocessing, threading, logging, sys, traceback


try:
    import dpkt
except:
    pass

logger = logging.getLogger('replay_server')


def name2code(key, what):
    '''
    Codes are 5 digits and follow these rules (just for the hech of it!):
        right most: 1 if random, 0 otherwise
        2 left most: app code
        2 midd: subapp code
    '''
    names = {
        'hangout-video-10secs': '01000',
        'hangout-video-10secs-random': '01001',

        'netflix-auto-5secs': '02000',
        'netflix-auto-5secs-random': '02001',

        'skype-video-10secs': '03000',
        'skype-video-10secs-random': '03001',

        'spotify-normal-15secs': '04000',
        'spotify-normal-15secs-random': '04001',

        'viber-video-10secs': '05000',
        'viber-video-10secs-random': '05001',

        'youtube-144p': '06010',
        'youtube-144p-random': '06011',
        'youtube-240p': '06020',
        'youtube-240p-random': '06021',
        'youtube-360p': '06030',
        'youtube-360p-random': '06031',
        'youtube-480p': '06040',
        'youtube-480p-random': '06041',
        'youtube-720p': '06050',
        'youtube-720p-random': '06051',
        'youtube-144p-oneStream': '06060',
        'youtube-144-oneStream-random': '06061',
    }

    codes = {
        '01000': 'hangout-video-10secs',
        '01001': 'hangout-video-10secs-random',

        '02000': 'netflix-auto-5secs',
        '02001': 'netflix-auto-5secs-random',

        '03000': 'skype-video-10secs',
        '03001': 'skype-video-10secs-random',

        '04000': 'spotify-normal-15secs',
        '04001': 'spotify-normal-15secs-random',

        '05000': 'viber-video-10secs',
        '05001': 'viber-video-10secs-random',

        '06010': 'youtube-144p',
        '06011': 'youtube-144p-random',
        '06020': 'youtube-240p',
        '06021': 'youtube-240p-random',
        '06030': 'youtube-360p',
        '06031': 'youtube-360p-random',
        '06040': 'youtube-480p',
        '06041': 'youtube-480p-random',
        '06050': 'youtube-720p',
        '06051': 'youtube-720p-random',
        '06060': 'youtube-144p-oneStream',
        '06061': 'youtube-144-oneStream-random',
    }

    if what.lower() == 'name':
        try:
            return names[key]
        except KeyError:
            return key

    elif what.lower() == 'code':
        try:
            return codes[key]
        except KeyError:
            return key


class MultiProcessingLog(logging.Handler):
    def __init__(self, logFile):
        logging.Handler.__init__(self)

        # self._handler = RotatingFileHandler(name, mode, maxsize, rotate)
        self._handler = logging.handlers.TimedRotatingFileHandler(logFile, backupCount=200, when="midnight")
        self.queue = multiprocessing.Queue(-1)

        t = threading.Thread(target=self.receive)
        t.daemon = True
        t.start()

    def setFormatter(self, fmt):
        logging.Handler.setFormatter(self, fmt)
        self._handler.setFormatter(fmt)

    def receive(self):
        while True:
            try:
                record = self.queue.get()
                self._handler.emit(record)
            except (KeyboardInterrupt, SystemExit):
                raise
            except EOFError:
                break
            except:
                traceback.print_exc(file=sys.stderr)

    def send(self, s):
        self.queue.put_nowait(s)

    def _format_record(self, record):
        # ensure that exc_info and args
        # have been stringified.  Removes any chance of
        # unpickleable things inside and possibly reduces
        # message size sent over the pipe
        if record.args:
            record.msg = record.msg % record.args
            record.args = None
        if record.exc_info:
            dummy = self.format(record)
            record.exc_info = None

        return record

    def emit(self, record):
        try:
            s = self._format_record(record)
            self.send(s)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)

    def close(self):
        self._handler.close()
        logging.Handler.close(self)


def createRotatingLog(logger, logFile):
    formatter = logging.Formatter('%(asctime)s--%(name)s--%(levelname)s\t%(message)s', datefmt='%m/%d/%Y--%H:%M:%S')
    handler = logging.handlers.TimedRotatingFileHandler(logFile, backupCount=200, when="midnight")
    # handler = MultiProcessingLog(logFile)
    handler.setFormatter(formatter)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)


def createRotatingLog_multip(logger, logFile):
    formatter = logging.Formatter('%(asctime)s--%(name)s--%(levelname)s\t%(message)s', datefmt='%m/%d/%Y--%H:%M:%S')
    # handler = logging.handlers.TimedRotatingFileHandler(logFile, backupCount=200, when="midnight")
    handler = MultiProcessingLog(logFile)
    handler.setFormatter(formatter)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)


def getCurrentResultsFolder():
    currentResultsFolder = Configs().get('resultsFolder')
    currentYMD = time.strftime("%Y-%m-%d", time.gmtime())
    currentY = currentYMD.split("-")[0]
    currentResultsFolder = "{}/{}/".format(currentResultsFolder, currentY)
    if not os.path.exists(currentResultsFolder):
        os.mkdir(currentResultsFolder)
    currentM = currentYMD.split("-")[1]
    currentResultsFolder = "{}/{}/".format(currentResultsFolder, currentM)
    if not os.path.exists(currentResultsFolder):
        os.mkdir(currentResultsFolder)
    currentD = currentYMD.split("-")[2]
    currentResultsFolder = "{}/{}/".format(currentResultsFolder, currentD)
    if not os.path.exists(currentResultsFolder):
        os.mkdir(currentResultsFolder)

    return currentResultsFolder

def LOG_ACTION(logger, message, level=20, doPrint=True, indent=0, action=True, exit=False, newLine=False):
    # DEBUG
    if level == 10:
        logger.debug(message)

    # INFO
    elif level == 20:
        logger.info(message)

    # WARNING
    elif level == 30:
        logger.warning(message)

    # EROOR
    elif level == 40:
        logger.error(message)

    # CRITICAL
    elif level == 50:
        logger.critical(message)

    elif level.upper() == 'EXCEPTION':
        logger.exception(message)

    if doPrint:
        if newLine is True:
            print('\n')
        PRINT_ACTION(message, indent, action=action, exit=exit)


def PRINT_ACTION(message, indent, action=True, exit=False):
    if action:
        print(''.join(['\t'] * indent), '[' + str(Configs().action_count) + ']' + message)
        Configs().action_count = Configs().action_count + 1
    elif exit is False:
        print(''.join(['\t'] * indent) + message)
    else:
        print('\n***** Exiting with error: *****\n', message, '\n***********************************\n')
        sys.exit()


def append_to_file(line, filename):
    f = open(filename, 'a')
    f.write((line + '\n'))
    f.close()


def print_progress(total_number_of_steps, extra_print=None, width=50):
    '''
    Prints progress bar.
    '''
    current_step = 1

    while current_step <= total_number_of_steps:
        sys.stdout.write('\r')
        sys.stdout.write(
            "\t[{}] {}% ({}/{})".format(('=' * int((current_step * width / total_number_of_steps))).ljust(width)
                                        , int(math.ceil(100 * current_step / float(total_number_of_steps)))
                                        , current_step
                                        , total_number_of_steps))
        if extra_print:
            sys.stdout.write(extra_print)

        sys.stdout.flush()

        if current_step == total_number_of_steps:
            print('\n')

        current_step += 1
        yield


class PermaData(object):
    def __init__(self, path='', fileName='uniqID.txt', size=10):
        if path != '':
            if not os.path.exists(path):
                os.makedirs(path)

        self.path = path + fileName

        try:
            with open(self.path, 'r') as f:
                [self.id, self.historyCount] = f.readline().split('\t')
                self.historyCount = int(self.historyCount)
        except IOError:
            self.id = ''.join(random.choice(string.ascii_letters + string.digits) for x in range(size))
            self.historyCount = 0
            self._update()

    def updateHistoryCount(self):
        self.historyCount += 1
        self._update()

    def _update(self):
        with open(self.path, 'w') as f:
            f.write((self.id + '\t' + str(self.historyCount)))


def dir_list(dir_name, subdir, *args):
    '''
    Return a list of file names in directory 'dir_name'
    If 'subdir' is True, recursively access subdirectories under 'dir_name'.
    Additional arguments, if any, are file extensions to add to the list.
    Example usage: fileList = dir_list(r'H:\TEMP', False, 'txt', 'py', 'dat', 'log', 'jpg')
    '''
    fileList = []
    for file in os.listdir(dir_name):
        dirfile = os.path.join(dir_name, file)
        if os.path.isfile(dirfile):
            if len(args) == 0:
                fileList.append(dirfile)
            else:
                if os.path.splitext(dirfile)[1][1:] in args:
                    fileList.append(dirfile)
        # recursively access file names in subdirectories
        elif os.path.isdir(dirfile) and subdir:
            # print "Accessing directory:", dirfile
            fileList += dir_list(dirfile, subdir, *args)
    return fileList


def read_client_ip(client_ip_file, follows=False):
    if follows:
        l = linecache.getline((client_ip_file + '/follow-stream-0.txt'), 5)
        return (l.split()[2]).partition(':')[0]
    f = open(client_ip_file, 'r')
    return (f.readline()).strip()


def convert_ip(ip):
    '''
    converts ip.port to tcpflow format
    ip.port = 1.2.3.4.1234
    tcpflow format = 001.002.003.004.01234
    
    It does NOT have to have a port section
    '''
    l = ip.split('.')
    l[:4] = [x.zfill(3) for x in l[:4]]
    try:
        l[4] = l[4].zfill(5)
    except IndexError:
        pass
    return '.'.join(l)


def convert_back_ip(ip):
    '''
    does the reverse of convert_ip(ip)
    '''
    return '.'.join(map(str, list(map(int, ip.split('.')))))


class IPAlias(object):
    def __init__(self, ip, interfaceName):
        self.ip = convert_back_ip(ip)
        self.interfaceName = interfaceName
        self._alias()

    def _alias(self):
        command = ' '.join(['sudo ifconfig', self.interfaceName, self.ip])
        output = subprocess.getoutput(command)
        PRINT_ACTION(' '.join(['Aliasing:', self.interfaceName, self.ip, output]), 1, action=False)

    def down(self):
        command = ' '.join(['sudo ifconfig', self.interfaceName, 'down'])
        output = subprocess.getoutput(command)
        PRINT_ACTION(' '.join(['Bringing down:', self.interfaceName, self.ip, output]), 1, action=False)


class TCP_UDPjsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, UDPset):
            obj = {'payload': obj.payload, 'timestamp': obj.timestamp, 'c_s_pair': obj.c_s_pair, 'end': obj.end}
        elif isinstance(obj, RequestSet):
            obj = {'payload': obj.payload, 'c_s_pair': obj.c_s_pair, 'timestamp': obj.timestamp,
                   'response_hash': obj.response_hash, 'response_len': obj.response_len}
        elif isinstance(obj, ResponseSet):
            obj = {'request_len': obj.request_len, 'request_hash': obj.request_hash, 'response_list': obj.response_list}
        elif isinstance(obj, OneResponse):
            obj = {'payload': obj.payload, 'payload': obj.payload}
        else:
            obj = super(TCP_UDPjsonEncoder, self).default(obj)
        return obj


class UDPjsonDecoder_client(json.JSONDecoder):
    def decode(self, json_string):
        default_obj = super(UDPjsonDecoder_client, self).decode(json_string)
        client_Q = []
        for udp in default_obj[0]:
            client_Q.append(UDPset(udp['payload'], udp['timestamp'], udp['c_s_pair'], udp['end']))
        return [client_Q] + default_obj[1:]


class UDPjsonDecoder_server(json.JSONDecoder):
    def decode(self, json_string):
        default_obj = super(UDPjsonDecoder_server, self).decode(json_string)
        server_Q = {}
        for server_port in default_obj[0]:
            server_Q[server_port] = []
            for udp in default_obj[0][server_port]:
                server_Q[server_port].append(UDPset(udp['payload'], udp['timestamp'], udp['c_s_pair'], udp['end']))
        return [server_Q] + default_obj[1:]


class TCPjsonDecoder_client(json.JSONDecoder):
    def decode(self, json_string):
        default_obj = super(TCPjsonDecoder_client, self).decode(json_string)
        client_Q = []
        for tcp in default_obj[0]:
            req = RequestSet(tcp['payload'], tcp['c_s_pair'], '', tcp['timestamp'])
            req.response_hash = tcp['response_hash']
            req.response_len = tcp['response_len']
            client_Q.append(req)
        return [client_Q] + default_obj[1:]


class UDPset(object):
    def __init__(self, payload, timestamp, c_s_pair, end=False):
        self.payload = payload
        self.timestamp = timestamp
        self.c_s_pair = c_s_pair
        self.end = end

    def __str__(self):
        return '{}--{}--{}--{}'.format(self.payload, self.timestamp, self.c_s_pair, self.end)

    def __repr__(self):
        return '{}--{}--{}--{}'.format(self.payload, self.timestamp, self.c_s_pair, self.end)


class RequestSet(object):
    '''
    NOTE: These objects are created in the parser and the payload is encoded in HEX.
          However, before replaying, the payload is decoded, so for hash and length,
          we need to use the decoded payload.
    '''

    def __init__(self, payload, c_s_pair, response, timestamp):
        self.payload = payload
        self.c_s_pair = c_s_pair
        self.timestamp = timestamp

        if response is None:
            self.response_hash = None
            self.response_len = 0
        else:
            try:
                if len(response) % 2:
                    response = response[:-1]
                bytes_response = bytes.fromhex(response)
            except Exception as e:
                print("HELL NO", response[:10], len(response), e)
                sys.exit()
            self.response_hash = hashlib.sha1(bytes_response).hexdigest()
            self.response_len = len(bytes_response)

    def setHash_len(self, inpu_hash, input_len):
        self.response_hash = inpu_hash
        self.response_len = input_len

    def __str__(self):
        return '{} -- {} -- {} -- {}'.format(self.payload, self.timestamp, self.c_s_pair, self.response_len)


class ResponseSet(object):
    '''
    NOTE: These objects are created in the parser and the payload is encoded in HEX.
          However, before replaying, the payload is decoded, so for hash and length,
          we need to use the decoded payload.
    '''

    def __init__(self, request, response_list):
        bytes_request = bytes.fromhex(request)
        self.request_len = len(bytes_request)
        self.request_hash = hashlib.sha1(bytes_request).hexdigest()
        self.response_list = response_list

    def __str__(self):
        return '{} -- {}'.format(self.request_len, self.response_list)


class OneResponse(object):
    def __init__(self, payload, timestamp):
        self.payload = payload
        self.timestamp = timestamp


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Configs(object, metaclass=Singleton):
    '''
    This object holds all configs
    
    BE CAREFUL: it's a singleton!
    '''
    _Config = None
    _configs = {}

    def __init__(self, config_file=None):
        self._Config = configparser.ConfigParser()
        self.action_count = 1
        self._maxlen = 0
        if config_file != None:
            self.read_config_file(config_file)

    def read_config_file(self, config_file):
        with open(config_file, 'r') as f:
            while True:
                try:
                    l = f.readline().strip()
                    if l == '':
                        break
                except:
                    break

                a = l.partition('=')

                if a[2] in ['True', 'true']:
                    self.set(a[0], True)
                elif a[2] in ['False', 'false']:
                    self.set(a[0], False)
                else:
                    try:
                        self.set(a[0], int(a[2]))
                    except ValueError:
                        try:
                            self.set(a[0], float(a[2]))
                        except ValueError:
                            self.set(a[0], a[2])

    def read_args(self, args):
        self.set('000-scriptName', args[0])
        for arg in args[1:]:
            a = ((arg.strip()).partition('--')[2]).partition('=')

            if a[0] == 'ConfigFile':
                self.read_config_file(a[2])

            if a[2] in ['True', 'true']:
                self.set(a[0], True)

            elif a[2] in ['False', 'false']:
                self.set(a[0], False)

            else:
                try:
                    self.set(a[0], int(a[2]))
                except ValueError:
                    try:
                        self.set(a[0], float(a[2]))
                    except ValueError:
                        self.set(a[0], a[2])

    #         if 'ConfigFile' in self._configs:
    #             self.read_config_file(self._configs['ConfigFile'])

    def check_for(self, list_of_mandotary):
        try:
            for l in list_of_mandotary:
                self.get(l)
        except:
            print('\nYou should provide \"--{}=[]\"\n'.format(l))
            sys.exit(-1)

    def get(self, key):
        return self._configs[key]

    def is_given(self, key):
        try:
            self._configs[key]
            return True
        except:
            return False

    def set(self, key, value):
        self._configs[key] = value
        if len(key) > self._maxlen:
            self._maxlen = len(key)

    def show(self, key):
        print(key, ':\t', value)

    def show_all(self):
        for key in sorted(self._configs):
            print('\t', key.ljust(self._maxlen), ':', self._configs[key])

    def __str__(self):
        return str(self._configs)

    def reset_action_count(self):
        self._configs['action_count'] = 0

    def reset(self):
        _configs = {}
        self._configs['action_count'] = 0

    def remove(self, key):
        del self._configs[key]


class Instance(object):
    def __init__(self):
        self.ips = {
            'yourInstanceName': 'yourInstanceAddress',
            'wehe': 'wehe3.meddle.mobi',
            'local': 'localhost',
        }

    def getIP(self, machineName):
        try:
            ip = socket.gethostbyname(self.ips[machineName])
        except KeyError:
            ip = socket.gethostbyname(machineName)
        return ip


# Get current cpu load, memory usage, disk usage and upload bandwidth usage
def getSystemStat():
    cpuPercent = psutil.cpu_percent(1)
    memPercent = psutil.virtual_memory()[2]
    diskPercent = psutil.disk_usage('/')[3]
    bytesSent0 = psutil.net_io_counters()[0]
    time.sleep(1)
    bytesSent1 = psutil.net_io_counters()[0]
    upLoad = (bytesSent1 - bytesSent0) * 8 / 1000000.0

    return cpuPercent, memPercent, diskPercent, upLoad


def clean_pcap(in_pcap, clientIP, anonymizedIP, port_list, realID, permResultsFolder):
    out_pcap = in_pcap.replace('.pcap', '_out.pcap')
    # If there is no content modification, we store only packet headers (first 128 bytes)
    interm_pcap = in_pcap.replace('.pcap', '_interm.pcap')
    interm2_pcap = in_pcap.replace('.pcap', '_interm2.pcap')

    port_list = list(map(int, port_list))

    filter = 'port ' + ' or port '.join(map(str, port_list))
    command = "tcpdump -r {} -w {} {}".format(in_pcap, interm_pcap, filter)
    p = subprocess.check_output(command, shell=True)

    # remove payload data from pcap file
    command = "editcap -C 128:10000 {} {}".format(interm_pcap, interm2_pcap)
    p = subprocess.check_output(command, shell=True)

    # anonymize the IP and update checksums
    if ":" in anonymizedIP:
        command = ["tcprewrite", "--fixcsum", "--pnat=[{}]:[{}]".format(clientIP, anonymizedIP),
                   "--infile={}".format(interm2_pcap),
                   "--outfile={}".format(out_pcap)]
    else:
        command = ["tcprewrite", "--fixcsum", "--pnat={}:{}".format(clientIP, anonymizedIP),
                   "--infile={}".format(interm2_pcap),
                   "--outfile={}".format(out_pcap)]

    p = subprocess.check_output(command)

    # Remove the intermediate pcaps
    interm_pcaps = [in_pcap, interm_pcap, interm2_pcap]
    for interm_pcap in interm_pcaps:
        try:
            os.remove(interm_pcap)
        except OSError as error:
            print("Removing error", error, interm_pcap.split("/")[-1])

    if not os.path.exists(permResultsFolder):
        os.mkdir(permResultsFolder)
    clientFolder = "{}/{}/".format(permResultsFolder, realID)
    if not os.path.exists(clientFolder):
        os.mkdir(clientFolder)
    tcpdumpFolder = "{}/{}/".format(clientFolder, "tcpdumpsResults")
    if not os.path.exists(tcpdumpFolder):
        os.mkdir(tcpdumpFolder)

    mv_command = "mv {} {}".format(out_pcap, tcpdumpFolder)

    if os.getenv("SUDO_UID"):
        uid = int(os.getenv("SUDO_UID"))
        for root, dirs, files in os.walk(tcpdumpFolder):
            for dir in dirs:
                os.chown(os.path.join(root, dir), uid, uid)
            for file in files:
                os.chown(os.path.join(root, file), uid, uid)

    p = subprocess.check_output(mv_command, shell=True)


class tcpdump(object):
    '''
    Class for taking tcpdump
    
    Everything is self-explanatory
    '''

    def __init__(self, dump_name=None, targetFolder='./', interface=None):
        self._interface = interface
        self._running = False
        self._p = None
        self.bufferSize = 131072

        if dump_name is None:
            self.dump_name = 'dump_' + time.strftime('%Y-%b-%d-%H-%M-%S', time.gmtime()) + '.pcap'
        else:
            self.dump_name = 'dump_' + dump_name + '.pcap'

        self.dump_name = targetFolder + self.dump_name

    def start(self, host=None):

        command = ['tcpdump', '-w', self.dump_name]

        if self._interface is not None:
            command += ['-i', self._interface]

        if host is not None:
            command += ['host', host]

        self._p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        '''
            Wait for tcpdump process to start listening for traffic by invoking self._p.stderr.readline()
        '''
        self._p.stderr.readline()
        self._running = True

        return ' '.join(command)

    def stop(self):
        output = ['-1', '-1', '-1']
        try:
            self._p.terminate()
            output = self._p.communicate()
        except AttributeError:
            return 'None'
        self._running = False
        return output

    def status(self):
        return self._running


############################################
##### ADDED BY HYUNGJOON KOO FROM HERE #####
############################################

# Determines both endpoints

def extractEndpoints(pcap_dir, file_name):
    extract = (
            "tshark -Tfields -E separator=- -e ip.src -e ip.dst -r " + pcap_dir + "/" + file_name + " | head -1 > " + pcap_dir + "/" + file_name + "_endpoints.txt")
    os.system(extract)
    with open(pcap_dir + "/" + file_name + "_endpoints.txt", 'r') as f:
        ends = f.read().splitlines()
    f.close()
    return ends[0].split("-")


# Returns the number of packets in a pcap file (pkt_type=[udp|tcp|total|other])

def pkt_ctr(pcap_dir, file_name, pkt_type):
    udp_ctr = 0
    tcp_ctr = 0
    other_ctr = 0
    total_ctr = 0

    filepath = pcap_dir + "/" + file_name
    f = open(filepath)
    for ts, buf in dpkt.pcap.Reader(file(filepath, "rb")):
        eth = dpkt.ethernet.Ethernet(buf)
        total_ctr += 1
        if eth.type == dpkt.ethernet.ETH_TYPE_IP:  # 2048
            ip = eth.data
            if ip.p == dpkt.ip.IP_PROTO_UDP:  # 17
                udp_ctr += 1

            if ip.p == dpkt.ip.IP_PROTO_TCP:  # 6
                tcp_ctr += 1
            else:
                other_ctr += 1

    # Returns the number of packets depending on the type
    if pkt_type == 'total':
        return total_ctr
    elif pkt_type == 'tcp':
        return tcp_ctr
    elif pkt_type == 'udp':
        return udp_ctr
    elif pkt_type == 'other':
        return other_ctr
    else:
        return -1


def parsedPktCnt(pcap_dir, endpoint):
    # Returns the count of parsed packets
    pktCntCmd = ("cat " + pcap_dir + "/" + endpoint + " " + " | wc -l")
    pktCnt = subprocess.getoutput(pktCntCmd)
    return pktCnt


def getTimestamp(pcap_dir, endpoint):
    # Extracts the timestamps for the endpoint to calculate jitter
    getTimestampCmd = (
            "cat " + pcap_dir + "/" + endpoint + " | awk '{print $2}' > " + pcap_dir + "/" + "ts_" + endpoint + ".tmp")
    os.system(getTimestampCmd)


# Saves the inter-packet intervals between when to sent

def interPacketSentInterval(pcap_dir, endpoint):
    tmp = open(pcap_dir + '/ts_' + endpoint + '.tmp', 'r')
    timestamps = tmp.read().splitlines()
    intervals = []
    i = 0
    ts_cnt = len(timestamps)
    while (i < ts_cnt - 1):
        intervals.append(format_float(float(timestamps[i + 1]) - float(timestamps[i]), 15))
        i = i + 1
    f = open(pcap_dir + '/' + endpoint + '_interPacketIntervals.txt', 'w')
    f.write('\n'.join(str(ts) for ts in intervals))
    os.system('rm -f ' + pcap_dir + '/ts_' + endpoint + '.tmp')


# Helps to write float format by removing characters

def format_float(value, precision=-1):
    if precision < 0:
        f = "%f" % value
    else:
        f = "%.*f" % (precision, value)
    p = f.partition(".")
    s = "".join((p[0], p[1], p[2][0], p[2][1:].rstrip("0")))
    return s


def java_byte_hashcode(s):
    if len(s) == 0:
        return 0
    hashCode = 1
    for b in s:
        i = ord(b)
        if i > 127:
            i = i - 256
        hashCode = (31 * hashCode + i) & 0xFFFFFFFF
    return hashCode


def get_anonymizedIP(ip):
    ip_address = ipaddress.ip_address(ip)

    if ip_address.version == 4:
        mask = ipaddress.ip_address('255.255.255.0')  # /24 mask
        anonymizedIP = str(ipaddress.ip_address(int(ip_address) & int(mask)))
    elif ip_address.version == 6:
        mask = ipaddress.ip_address('ffff:ffff:ffff:0000:0000:0000:0000:0000')  # /48
        anonymizedIP = str(ipaddress.ip_address(int(ip_address) & int(mask)))
    else:
        anonymizedIP = ip

    return anonymizedIP
