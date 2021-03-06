# Stateless vs Stateful LB in Software-defined Network

Project for Thesis "Comparative Analysis of Stateless and Stateful Application in Server Application for Software-defined Networking-Based Load Balancing". This project uses Ryu and Open vSwitch and OpenFlow 1.3 using a round-robin algorithm.

# How To Run

## Stateless

```bash
-- Terminal 1 --
$ sudo mn -c
-- Terminal 2 --
$ ryu-manager ~/loadbalancing/lb_stateless.py
-- Terminal 1 --
$ sudo mn --topo single,7 --mac --controller=remote --switch ovs,protocols=OpenFlow13
-- Terminal 3 --
$ sudo watch "ovs-ofctl -O OpenFlow13 dump-flows s1"
-- Mininet --
mininet > xterm h1 h2 h3 h4 h5 h6 h7 s1
-- Xterm --
~~ Server h1, h2, dan h3 ~~
h1# python -m SimpleHTTPServer 80
h2# python -m SimpleHTTPServer 80
h3# python -m SimpleHTTPServer 80
~~ Monitoring table ~~
s1# watch -n 1 "ovs-ofctl -O OpenFlow13 dump-flows s1 | wc -l"
~~ Test 10 request/sec ~~
h4# httperf --server=10.0.0.100 --uri=/ --num-conns=100 --rate=20
h5# httperf --server=10.0.0.100 --uri=/ --num-conns=100 --rate=20
h6# httperf --server=10.0.0.100 --uri=/ --num-conns=100 --rate=20
h7# httperf --server=10.0.0.100 --uri=/ --num-conns=100 --rate=20
```

## Stateful

```bash
-- Terminal 1 --
$ sudo mn -c
-- Terminal 2 --
$ ryu-manager ~/loadbalancing/lb_stateful.py
-- Terminal 1 --
$ sudo mn --topo single,7 --mac --controller=remote --switch ovs,protocols=OpenFlow13
-- Terminal 3 --
$ watch "ovs-ofctl -O OpenFlow13 dump-flows s1"
-- Mininet --
mininet > xterm h1 h2 h3 h4 h5 h6 h7 s1
-- Xterm --
~~ Server h1, h2, dan h3 ~~
h1# python -m SimpleHTTPServer 80
h2# python -m SimpleHTTPServer 80
h3# python -m SimpleHTTPServer 80
~~ Monitoring table ~~
s1# watch -n 1 "ovs-ofctl -O OpenFlow13 dump-flows s1 | wc -l"
~~ Test 10 request/sec ~~
h4# httperf --server=10.0.0.100 --uri=/ --num-conns=100 --rate=20
h5# httperf --server=10.0.0.100 --uri=/ --num-conns=100 --rate=20
h6# httperf --server=10.0.0.100 --uri=/ --num-conns=100 --rate=20
h7# httperf --server=10.0.0.100 --uri=/ --num-conns=100 --rate=20
```
