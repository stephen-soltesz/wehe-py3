FROM ubuntu:20.04

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install --yes \
   apt-utils gcc libc-dev libcap2-bin libmysqlclient-dev python3 python3-pip \
   tcpdump tcpreplay tshark wireshark scapy netcat traceroute

RUN pip3 install timezonefinder future gevent matplotlib multiprocessing_logging mysqlclient \
  netaddr prometheus_client psutil reverse-geocode reverse-geocoder \
  "tornado<6.0.0" requests jc

RUN setcap cap_net_raw=ep /usr/sbin/tcpdump

ADD src /wehe
ADD replayTraces /replayTraces
WORKDIR /wehe
# You must provide a local hostname argument when you start this image, as well
# as the net interface to listen on.
ENTRYPOINT ["/bin/bash", "./startserver.sh"]
