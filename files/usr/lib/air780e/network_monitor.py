"""Read USB interface kernel counters; never infer carrier billing from counters."""
import re,time
from pathlib import Path

class TrafficSampler:
    def __init__(self,root=Path('/sys/class/net')):
        self.root=root;self.previous=None
        self.latest={'available':False,'sampledAt':None,'interval':9}
    def sample(self,interface):
        if not interface or not re.fullmatch(r'[a-zA-Z0-9_.-]{1,32}',interface):
            self.previous=None
            self.latest={'available':False,'sampledAt':time.time(),'interval':9};return
        node=self.root/interface
        counters={k:int((node/'statistics'/k).read_text()) for k in ('tx_bytes','rx_bytes','tx_packets','rx_packets')}
        identity=(interface,(node/'ifindex').read_text().strip())
        now=time.monotonic();elapsed=0;upload=download=0
        if self.previous and self.previous[0]==identity:
            elapsed=now-self.previous[1]
            if elapsed>0 and all(counters[k]>=self.previous[2][k] for k in counters):
                upload=(counters['tx_bytes']-self.previous[2]['tx_bytes'])/elapsed
                download=(counters['rx_bytes']-self.previous[2]['rx_bytes'])/elapsed
        self.previous=(identity,now,counters)
        self.latest=dict(counters,available=True,interface=interface,sampledAt=time.time(),interval=9,
                         sampleSeconds=elapsed,uploadBps=upload,downloadBps=download)
